"""Algoritmo Genético Canónico aplicado a Scheduling de Alertas SOC.

El programa genera alertas sintéticas, construye una población inicial de
asignaciones alertas->analistas, evalúa cada cromosoma con una función fitness
orientada a tiempo de resolución, balance de carga, alertas críticas y backlog,
y compara tres estrategias evolutivas: ruleta, torneo y elitismo.
"""

from __future__ import annotations

import json
import random
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# =========================
# Configuracion general
# =========================
SEED_ALERTAS = 42
SEED_AG_BASE = 1000
N_REPETICIONES = 30
N_ANALISTAS = 10
N_ALERTAS = 500
TAM_POBLACION = 10
N_GENERACIONES = 20
P_CROSSOVER = 0.75
P_MUTACION = 0.05
TORNEO_K = 3
ELITE_SIZE = 2
HORIZONTE_MINUTOS = 8 * 60

PRIORIDADES = ("Baja", "Media", "Alta", "Critica")
PRIORIDAD_PESOS = (0.35, 0.30, 0.22, 0.13)
PRIORIDAD_RANK = {"Critica": 0, "Alta": 1, "Media": 2, "Baja": 3}
SLA_POR_PRIORIDAD = {"Baja": 240, "Media": 120, "Alta": 60, "Critica": 30}

BASE_RESOLUCION = {"Baja": 8, "Media": 15, "Alta": 25, "Critica": 40}
RANGO_RESOLUCION = {"Baja": 12, "Media": 18, "Alta": 25, "Critica": 35}
RANGO_SEVERIDAD = {"Baja": (10, 35), "Media": (30, 60), "Alta": (55, 85), "Critica": (80, 100)}

METODOS = ("ruleta", "torneo", "elitismo")

BASE_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = BASE_DIR / "outputs"
FIGURES_DIR = OUTPUTS_DIR / "figures"

METRICAS_CSV = OUTPUTS_DIR / "metricas_generacionales_soc.csv"
METRICAS_PROMEDIADAS_CSV = OUTPUTS_DIR / "metricas_generacionales_promediadas_soc.csv"
RESUMEN_REPETICIONES_CSV = OUTPUTS_DIR / "resumen_repeticiones_soc.csv"
RESUMEN_AGRUPADO_CSV = OUTPUTS_DIR / "resumen_resultados_agrupados_soc.csv"
RESUMEN_CSV = OUTPUTS_DIR / "resumen_resultados_soc.csv"
DISTRIBUCION_FINAL_CSV = OUTPUTS_DIR / "distribucion_final_alertas_soc.csv"
ASIGNACION_FINAL_CSV = OUTPUTS_DIR / "carga_final_analistas_soc.csv"


@dataclass(frozen=True)
class Alerta:
    id_alerta: int
    llegada_min: int
    prioridad: str
    severidad: int
    tiempo_estimado_min: int
    sla_min: int


def generar_alertas(n_alertas: int = N_ALERTAS, seed: int = SEED_ALERTAS) -> List[Alerta]:
    """Genera alertas sintéticas de un SOC con prioridad, severidad y tiempo estimado."""
    rng = random.Random(seed)
    prioridades = rng.choices(PRIORIDADES, weights=PRIORIDAD_PESOS, k=n_alertas)
    llegadas = sorted(rng.randint(0, HORIZONTE_MINUTOS - 1) for _ in range(n_alertas))

    alertas: List[Alerta] = []
    for idx, (prioridad, llegada_min) in enumerate(zip(prioridades, llegadas), start=1):
        severidad_min, severidad_max = RANGO_SEVERIDAD[prioridad]
        severidad = rng.randint(severidad_min, severidad_max)
        ruido = rng.randint(-3, 4)
        tiempo_estimado = BASE_RESOLUCION[prioridad] + int(round(severidad * 0.35)) + ruido
        tiempo_estimado = max(5, tiempo_estimado)
        alerta = Alerta(
            id_alerta=idx,
            llegada_min=llegada_min,
            prioridad=prioridad,
            severidad=severidad,
            tiempo_estimado_min=tiempo_estimado,
            sla_min=SLA_POR_PRIORIDAD[prioridad],
        )
        alertas.append(alerta)

    return alertas


def generar_poblacion(
    tam_poblacion: int = TAM_POBLACION,
    n_alertas: int = N_ALERTAS,
    n_analistas: int = N_ANALISTAS,
) -> List[List[int]]:
    """Genera una poblacion inicial aleatoria de cromosomas.

    Cada gen representa la asignacion de una alerta a un analista.
    Los analistas se numeran de 1 a N_ANALISTAS para que el cromosoma sea legible.
    """
    return [
        [random.randint(1, n_analistas) for _ in range(n_alertas)]
        for _ in range(tam_poblacion)
    ]


def _evaluar_asignacion(cromosoma: Sequence[int], alertas: Sequence[Alerta]) -> Dict[str, float | int | List[int]]:
    """Evalua una asignacion completa y devuelve metricas operativas del SOC."""
    asignadas_por_analista: List[List[int]] = [[] for _ in range(N_ANALISTAS)]
    for idx_alerta, analista in enumerate(cromosoma):
        asignadas_por_analista[analista - 1].append(idx_alerta)

    disponibilidad = [0] * N_ANALISTAS
    cargas = [0] * N_ANALISTAS
    espera_por_alerta = [0] * len(alertas)
    finalizacion_por_alerta = [0] * len(alertas)
    espera_critica = []
    retraso_critico = []

    for idx_analista, indices_alertas in enumerate(asignadas_por_analista):
        indices_alertas.sort(key=lambda idx: (alertas[idx].llegada_min, PRIORIDAD_RANK[alertas[idx].prioridad]))
        for idx_alerta in indices_alertas:
            alerta = alertas[idx_alerta]
            inicio = max(disponibilidad[idx_analista], alerta.llegada_min)
            espera = inicio - alerta.llegada_min
            fin = inicio + alerta.tiempo_estimado_min

            disponibilidad[idx_analista] = fin
            cargas[idx_analista] += alerta.tiempo_estimado_min
            espera_por_alerta[idx_alerta] = espera
            finalizacion_por_alerta[idx_alerta] = fin

            if alerta.prioridad == "Critica":
                espera_critica.append(espera)
                retraso_critico.append(max(0, espera - alerta.sla_min))

    tiempo_total_estimado = max(finalizacion_por_alerta) if finalizacion_por_alerta else 0
    espera_promedio = statistics.fmean(espera_por_alerta) if espera_por_alerta else 0.0
    espera_critica_promedio = statistics.fmean(espera_critica) if espera_critica else 0.0
    retraso_critico_promedio = statistics.fmean(retraso_critico) if retraso_critico else 0.0

    backlog_alertas = sum(1 for fin in finalizacion_por_alerta if fin > HORIZONTE_MINUTOS)
    backlog_minutos = sum(max(0, fin - HORIZONTE_MINUTOS) for fin in finalizacion_por_alerta)

    carga_total = sum(cargas)
    carga_media = carga_total / N_ANALISTAS if N_ANALISTAS else 0.0
    desbalance_carga = (statistics.pstdev(cargas) / carga_media) if carga_media else 0.0
    sobrecarga_relativa = (
        sum(max(0, carga - carga_media) for carga in cargas) / carga_total if carga_total else 0.0
    )

    penalizacion = (
        0.60 * espera_promedio
        + 1.80 * espera_critica_promedio
        + 8.00 * retraso_critico_promedio
        + 1.20 * backlog_alertas
        + 0.02 * backlog_minutos
        + 40.0 * desbalance_carga
        + 25.0 * sobrecarga_relativa
    )

    fitness = 1.0 / (1.0 + tiempo_total_estimado + penalizacion)

    return {
        "fitness": float(fitness),
        "tiempo_total_estimado_min": int(tiempo_total_estimado),
        "penalizacion": float(penalizacion),
        "espera_promedio_min": float(espera_promedio),
        "espera_critica_promedio_min": float(espera_critica_promedio),
        "retraso_critico_promedio_min": float(retraso_critico_promedio),
        "backlog_alertas": int(backlog_alertas),
        "backlog_minutos": float(backlog_minutos),
        "cargas_por_analista": cargas,
        "desbalance_carga": float(desbalance_carga),
        "sobrecarga_relativa": float(sobrecarga_relativa),
        "espera_por_alerta": espera_por_alerta,
        "finalizacion_por_alerta": finalizacion_por_alerta,
    }


def calcular_fitness(cromosoma: Sequence[int], alertas: Sequence[Alerta]) -> float:
    """Devuelve el fitness escalar de un cromosoma."""
    return _evaluar_asignacion(cromosoma, alertas)["fitness"]


def seleccion_ruleta(poblacion: Sequence[Sequence[int]], fitnesses: Sequence[float]) -> List[int]:
    """Seleccion por ruleta proporcional al fitness."""
    fitnesses_escalados = _escalar_fitness_para_ruleta(fitnesses)
    total = float(sum(fitnesses_escalados))
    if total <= 0:
        return list(random.choice(poblacion))

    objetivo = random.uniform(0, total)
    acumulado = 0.0
    for individuo, fitness in zip(poblacion, fitnesses_escalados):
        acumulado += fitness
        if acumulado >= objetivo:
            return list(individuo)
    return list(poblacion[-1])


def seleccion_torneo(
    poblacion: Sequence[Sequence[int]],
    fitnesses: Sequence[float],
    k: int = TORNEO_K,
) -> List[int]:
    """Seleccion por torneo de tamaño k."""
    cantidad = min(k, len(poblacion))
    indices = random.sample(range(len(poblacion)), cantidad)
    mejor_indice = max(indices, key=lambda idx: fitnesses[idx])
    return list(poblacion[mejor_indice])


def crossover(padre1: Sequence[int], padre2: Sequence[int]) -> Tuple[List[int], List[int]]:
    """Crossover de un punto."""
    if len(padre1) != len(padre2):
        raise ValueError("Los cromosomas deben tener la misma longitud")

    if len(padre1) < 2:
        return list(padre1), list(padre2)

    punto = random.randint(1, len(padre1) - 1)
    hijo1 = list(padre1[:punto]) + list(padre2[punto:])
    hijo2 = list(padre2[:punto]) + list(padre1[punto:])
    return hijo1, hijo2


def _escalar_fitness_para_ruleta(fitnesses: Sequence[float]) -> List[float]:
    """Reescala fitness positivos para que la ruleta sea menos sensible a valores muy pequeños."""
    if not fitnesses:
        return []

    fitness_min = min(fitnesses)
    fitness_max = max(fitnesses)
    if fitness_max <= fitness_min:
        return [1.0 for _ in fitnesses]

    rango = fitness_max - fitness_min
    return [((fitness - fitness_min) / rango) + 1e-9 for fitness in fitnesses]


def mutacion(cromosoma: Sequence[int], p_mutacion: float = P_MUTACION) -> List[int]:
    """Mutacion por reasignacion: cambia una alerta a otro analista aleatorio."""
    hijo = list(cromosoma)
    if len(hijo) < 2:
        return hijo

    if random.random() < p_mutacion:
        indice = random.randrange(len(hijo))
        analista_actual = hijo[indice]
        analistas_posibles = [analista for analista in range(1, N_ANALISTAS + 1) if analista != analista_actual]
        hijo[indice] = random.choice(analistas_posibles)
    return hijo


def calcular_estadisticas(fitnesses: Sequence[float], tiempo_seg: float) -> Dict[str, float]:
    """Calcula maximo, minimo, promedio, desvio y tiempo de una generacion."""
    return {
        "fitness_max": float(max(fitnesses)),
        "fitness_min": float(min(fitnesses)),
        "fitness_prom": float(statistics.fmean(fitnesses)),
        "desv_std": float(statistics.pstdev(fitnesses)) if len(fitnesses) > 1 else 0.0,
        "tiempo_seg": float(tiempo_seg),
    }


def _seleccionar_padre(metodo: str, poblacion: Sequence[Sequence[int]], fitnesses: Sequence[float]) -> List[int]:
    """Encapsula la estrategia de seleccion de padres."""
    if metodo == "torneo":
        return seleccion_torneo(poblacion, fitnesses)
    return seleccion_ruleta(poblacion, fitnesses)


def _formatear_cromosoma(cromosoma: Sequence[int], ancho: int = 32) -> str:
    """Devuelve una version compacta de un cromosoma largo para consola."""
    if len(cromosoma) <= ancho:
        return "[" + ", ".join(map(str, cromosoma)) + "]"
    cabeza = ", ".join(map(str, cromosoma[:16]))
    cola = ", ".join(map(str, cromosoma[-16:]))
    return f"[{cabeza}, ..., {cola}]"


def _resumen_distribucion(cromosoma: Sequence[int], alertas: Sequence[Alerta]) -> pd.DataFrame:
    """Construye la tabla final de carga por analista a partir del mejor cromosoma."""
    filas = []
    for analista in range(1, N_ANALISTAS + 1):
        indices = [idx for idx, asignado in enumerate(cromosoma) if asignado == analista]
        alertas_asignadas = [alertas[idx] for idx in indices]
        carga_total = sum(alerta.tiempo_estimado_min for alerta in alertas_asignadas)
        criticidad = sum(1 for alerta in alertas_asignadas if alerta.prioridad == "Critica")
        severidad_prom = statistics.fmean([alerta.severidad for alerta in alertas_asignadas]) if alertas_asignadas else 0.0
        filas.append(
            {
                "analista": analista,
                "alertas_asignadas": len(alertas_asignadas),
                "carga_total_min": carga_total,
                "criticidad_critica": criticidad,
                "severidad_promedio": float(severidad_prom),
                "carga_promedio_por_alerta_min": float(carga_total / len(alertas_asignadas)) if alertas_asignadas else 0.0,
            }
        )
    return pd.DataFrame(filas)


def evolucionar(
    alertas: Sequence[Alerta],
    metodo: str = "ruleta",
    n_generaciones: int = N_GENERACIONES,
    tam_poblacion: int = TAM_POBLACION,
    p_crossover: float = P_CROSSOVER,
    p_mutacion: float = P_MUTACION,
    seed: int = SEED_AG_BASE,
) -> Tuple[pd.DataFrame, Dict[str, object]]:
    """Ejecuta la evolucion genetica para un metodo de seleccion concreto."""
    if metodo not in METODOS:
        raise ValueError(f"Metodo no soportado: {metodo}")

    random.seed(seed)
    np.random.seed(seed)

    poblacion = generar_poblacion(tam_poblacion=tam_poblacion, n_alertas=len(alertas))
    historial: List[Dict[str, object]] = []

    mejor_global: List[int] | None = None
    mejor_global_eval: Dict[str, object] | None = None

    inicio_total = time.time()

    for generacion in range(1, n_generaciones + 1):
        inicio_gen = time.time()

        evaluaciones = [_evaluar_asignacion(individuo, alertas) for individuo in poblacion]
        fitnesses = [evaluacion["fitness"] for evaluacion in evaluaciones]
        idx_mejor = int(np.argmax(fitnesses))
        mejor_gen = list(poblacion[idx_mejor])
        evaluacion_mejor = evaluaciones[idx_mejor]

        if mejor_global_eval is None or evaluacion_mejor["fitness"] > mejor_global_eval["fitness"]:
            mejor_global = list(mejor_gen)
            mejor_global_eval = dict(evaluacion_mejor)

        if generacion < n_generaciones:
            nueva_poblacion: List[List[int]] = []
            if metodo == "elitismo":
                elite_indices = list(np.argsort(fitnesses)[::-1][:ELITE_SIZE])
                nueva_poblacion.extend(list(poblacion[idx]) for idx in elite_indices)

            while len(nueva_poblacion) < tam_poblacion:
                padre1 = _seleccionar_padre(metodo, poblacion, fitnesses)
                padre2 = _seleccionar_padre(metodo, poblacion, fitnesses)

                if random.random() < p_crossover:
                    hijo1, hijo2 = crossover(padre1, padre2)
                else:
                    hijo1, hijo2 = list(padre1), list(padre2)

                hijo1 = mutacion(hijo1, p_mutacion)
                hijo2 = mutacion(hijo2, p_mutacion)

                nueva_poblacion.append(hijo1)
                if len(nueva_poblacion) < tam_poblacion:
                    nueva_poblacion.append(hijo2)

            poblacion = nueva_poblacion[:tam_poblacion]

        estadisticas = calcular_estadisticas(fitnesses, time.time() - inicio_gen)
        estadisticas.update(
            {
                "generacion": generacion,
                "metodo": metodo,
                "fitness_mejor_gen": float(evaluacion_mejor["fitness"]),
                "tiempo_total_estimado_min": int(evaluacion_mejor["tiempo_total_estimado_min"]),
                "espera_promedio_min": float(evaluacion_mejor["espera_promedio_min"]),
                "espera_critica_promedio_min": float(evaluacion_mejor["espera_critica_promedio_min"]),
                "backlog_alertas": int(evaluacion_mejor["backlog_alertas"]),
                "desbalance_carga": float(evaluacion_mejor["desbalance_carga"]),
            }
        )
        historial.append(estadisticas)

    tiempo_total_seg = time.time() - inicio_total
    if mejor_global is None or mejor_global_eval is None:
        raise RuntimeError("No se pudo determinar una mejor solucion global")

    resumen = {
        "metodo": metodo,
        "mejor_cromosoma": mejor_global,
        "mejor_cromosoma_texto": json.dumps(mejor_global),
        "mejor_fitness_global": float(mejor_global_eval["fitness"]),
        "tiempo_total_estimado_min": int(mejor_global_eval["tiempo_total_estimado_min"]),
        "penalizacion_total": float(mejor_global_eval["penalizacion"]),
        "espera_promedio_min": float(mejor_global_eval["espera_promedio_min"]),
        "espera_critica_promedio_min": float(mejor_global_eval["espera_critica_promedio_min"]),
        "retraso_critico_promedio_min": float(mejor_global_eval["retraso_critico_promedio_min"]),
        "backlog_alertas": int(mejor_global_eval["backlog_alertas"]),
        "backlog_minutos": float(mejor_global_eval["backlog_minutos"]),
        "desbalance_carga": float(mejor_global_eval["desbalance_carga"]),
        "sobrecarga_relativa": float(mejor_global_eval["sobrecarga_relativa"]),
        "tiempo_ejecucion_seg": float(tiempo_total_seg),
    }

    return pd.DataFrame(historial), resumen


def _agrupar_metricas_repetidas(df_metricas: pd.DataFrame) -> pd.DataFrame:
    """Agrega las metricas generacionales para medir variacion entre corridas."""
    columnas_base = ["metodo", "generacion"]
    agregadas = (
        df_metricas.groupby(columnas_base, as_index=False)
        .agg(
            repeticiones=("corrida", "count"),
            fitness_max_media=("fitness_max", "mean"),
            fitness_max_desvio=("fitness_max", "std"),
            fitness_min_media=("fitness_min", "mean"),
            fitness_min_desvio=("fitness_min", "std"),
            fitness_prom_media=("fitness_prom", "mean"),
            fitness_prom_desvio=("fitness_prom", "std"),
            desv_std_media=("desv_std", "mean"),
            desv_std_desvio=("desv_std", "std"),
            fitness_mejor_gen_media=("fitness_mejor_gen", "mean"),
            fitness_mejor_gen_desvio=("fitness_mejor_gen", "std"),
            backlog_alertas_media=("backlog_alertas", "mean"),
            backlog_alertas_desvio=("backlog_alertas", "std"),
            desbalance_carga_media=("desbalance_carga", "mean"),
            desbalance_carga_desvio=("desbalance_carga", "std"),
            tiempo_gen_media=("tiempo_seg", "mean"),
            tiempo_gen_desvio=("tiempo_seg", "std"),
        )
        .fillna(0.0)
    )
    return agregadas


def _agrupar_resumen_repeticiones(df_resumen: pd.DataFrame) -> pd.DataFrame:
    """Resume cada metodo sobre todas las repeticiones del AG."""
    return (
        df_resumen.groupby("metodo", as_index=False)
        .agg(
            repeticiones=("corrida", "count"),
            mejor_fitness_global_media=("mejor_fitness_global", "mean"),
            mejor_fitness_global_min=("mejor_fitness_global", "min"),
            mejor_fitness_global_max=("mejor_fitness_global", "max"),
            mejor_fitness_global_desvio=("mejor_fitness_global", "std"),
            tiempo_total_estimado_min_media=("tiempo_total_estimado_min", "mean"),
            tiempo_total_estimado_min_min=("tiempo_total_estimado_min", "min"),
            tiempo_total_estimado_min_max=("tiempo_total_estimado_min", "max"),
            tiempo_total_estimado_min_desvio=("tiempo_total_estimado_min", "std"),
            penalizacion_total_media=("penalizacion_total", "mean"),
            penalizacion_total_min=("penalizacion_total", "min"),
            penalizacion_total_max=("penalizacion_total", "max"),
            penalizacion_total_desvio=("penalizacion_total", "std"),
            backlog_alertas_media=("backlog_alertas", "mean"),
            backlog_alertas_min=("backlog_alertas", "min"),
            backlog_alertas_max=("backlog_alertas", "max"),
            backlog_alertas_desvio=("backlog_alertas", "std"),
            desbalance_carga_media=("desbalance_carga", "mean"),
            desbalance_carga_min=("desbalance_carga", "min"),
            desbalance_carga_max=("desbalance_carga", "max"),
            desbalance_carga_desvio=("desbalance_carga", "std"),
            tiempo_ejecucion_seg_media=("tiempo_ejecucion_seg", "mean"),
            tiempo_ejecucion_seg_min=("tiempo_ejecucion_seg", "min"),
            tiempo_ejecucion_seg_max=("tiempo_ejecucion_seg", "max"),
            tiempo_ejecucion_seg_desvio=("tiempo_ejecucion_seg", "std"),
        )
        .fillna(0.0)
    )


def graficar_metricas(df_metricas: pd.DataFrame) -> None:
    """Genera graficos de maximo, minimo, promedio, desvio y comparacion entre metodos."""
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    configuraciones = [
        ("fitness_max", "Maximo por generacion", "Fitness maximo", "maximos_por_generacion.png"),
        ("fitness_prom", "Promedio por generacion", "Fitness promedio", "promedios_por_generacion.png"),
        ("fitness_min", "Minimo por generacion", "Fitness minimo", "minimos_por_generacion.png"),
        ("desv_std", "Desviacion estandar por generacion", "Desviacion estandar", "desviacion_estandar_por_generacion.png"),
    ]

    for metrica, titulo, etiqueta_y, archivo in configuraciones:
        plt.figure(figsize=(11, 6))
        for metodo, grupo in df_metricas.groupby("metodo"):
            grupo = grupo.sort_values("generacion")
            plt.plot(grupo["generacion"], grupo[metrica], marker="o", linewidth=2, label=metodo.capitalize())
        plt.title(titulo)
        plt.xlabel("Generacion")
        plt.ylabel(etiqueta_y)
        plt.grid(True, linestyle="--", alpha=0.35)
        plt.legend()
        plt.tight_layout()
        plt.savefig(FIGURES_DIR / archivo, dpi=200)
        plt.close()

    plt.figure(figsize=(11, 6))
    for metodo, grupo in df_metricas.groupby("metodo"):
        grupo = grupo.sort_values("generacion")
        plt.plot(grupo["generacion"], grupo["fitness_prom"], marker="o", linewidth=2, label=metodo.capitalize())
    plt.title("Comparacion entre Ruleta, Torneo y Elitismo")
    plt.xlabel("Generacion")
    plt.ylabel("Fitness promedio")
    plt.grid(True, linestyle="--", alpha=0.35)
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "comparacion_metodos.png", dpi=200)
    plt.close()


def _imprimir_encabezado(metodo: str) -> None:
    print("=" * 126)
    print(f"METODO: {metodo.upper()}")
    print("=" * 126)
    print(
        f"{'Gen':>4} | {'Fitness max':>12} | {'Fitness min':>12} | {'Fitness prom':>12} | "
        f"{'Desv. std':>12} | {'Tiempo gen (s)':>15} | {'Mejor fitness':>14} | {'Backlog':>8}"
    )
    print("-" * 126)


def _imprimir_fila(stats: Dict[str, object]) -> None:
    print(
        f"{stats['generacion']:>4} | {stats['fitness_max']:>12.6f} | {stats['fitness_min']:>12.6f} | "
        f"{stats['fitness_prom']:>12.6f} | {stats['desv_std']:>12.6f} | {stats['tiempo_seg']:>15.4f} | "
        f"{stats['fitness_mejor_gen']:>14.6f} | {stats['backlog_alertas']:>8}"
    )


def _imprimir_resumen_metodo(resumen: Dict[str, object]) -> None:
    print("-" * 126)
    print("RESUMEN FINAL DEL METODO")
    print(f"Mejor fitness global          : {resumen['mejor_fitness_global']:.10f}")
    print(f"Tiempo total estimado (min)   : {resumen['tiempo_total_estimado_min']}")
    print(f"Penalizacion total            : {resumen['penalizacion_total']:.4f}")
    print(f"Espera promedio (min)         : {resumen['espera_promedio_min']:.4f}")
    print(f"Espera critica promedio (min)  : {resumen['espera_critica_promedio_min']:.4f}")
    print(f"Backlog de alertas            : {resumen['backlog_alertas']}")
    print(f"Backlog acumulado (min)       : {resumen['backlog_minutos']:.4f}")
    print(f"Desbalance de carga           : {resumen['desbalance_carga']:.6f}")
    print(f"Sobrecarga relativa           : {resumen['sobrecarga_relativa']:.6f}")
    print(f"Cromosoma ganador (compacto)  : {_formatear_cromosoma(resumen['mejor_cromosoma'])}")


def _imprimir_resumen_global(df_resumen: pd.DataFrame, mejor_indice: int) -> None:
    print("\n" + "=" * 126)
    print("TABLA RESUMEN FINAL POR METODO")
    print("=" * 126)
    columnas = [
        "metodo",
        "mejor_fitness_global",
        "tiempo_total_estimado_min",
        "penalizacion_total",
        "espera_promedio_min",
        "espera_critica_promedio_min",
        "backlog_alertas",
        "backlog_minutos",
        "desbalance_carga",
        "tiempo_ejecucion_seg",
    ]
    print(df_resumen[columnas].to_string(index=False))

    ganador = df_resumen.iloc[mejor_indice]
    print("\n" + "=" * 126)
    print("MEJOR SOLUCION GLOBAL")
    print("=" * 126)
    print(f"Metodo ganador                 : {ganador['metodo']}")
    print(f"Mejor fitness global           : {ganador['mejor_fitness_global']:.10f}")
    print(f"Tiempo total estimado (min)    : {int(ganador['tiempo_total_estimado_min'])}")
    print(f"Penalizacion total             : {ganador['penalizacion_total']:.4f}")
    print(f"Cromosoma ganador (texto)      : {ganador['mejor_cromosoma_texto'][:180]}...")


def main() -> None:
    """Orquesta la simulacion completa y genera salidas tabuladas y graficas."""
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    alertas = generar_alertas(seed=SEED_ALERTAS)

    print("=" * 126)
    print("ALGORTIMO GENETICO CANONICO APLICADO A SCHEDULING DE ALERTAS SOC")
    print("=" * 126)
    print(f"Analistas SOC                 : {N_ANALISTAS}")
    print(f"Alertas sinteticas             : {N_ALERTAS}")
    print(f"Poblacion inicial              : {TAM_POBLACION}")
    print(f"Generaciones                   : {N_GENERACIONES}")
    print(f"Probabilidad de crossover      : {P_CROSSOVER}")
    print(f"Probabilidad de mutacion       : {P_MUTACION}")
    print(f"Horizonte de trabajo (min)     : {HORIZONTE_MINUTOS}")
    print(f"Repeticiones por metodo        : {N_REPETICIONES}")
    print("=" * 126)

    metricas_totales = []
    resueltas = []

    for metodo in METODOS:
        print("\n" + "=" * 126)
        print(f"METODO: {metodo.upper()}")
        print("=" * 126)
        for corrida in range(1, N_REPETICIONES + 1):
            seed_ag = SEED_AG_BASE + corrida
            df_historial, resumen = evolucionar(alertas, metodo=metodo, seed=seed_ag)

            df_historial = df_historial.copy()
            df_historial["metodo"] = metodo
            df_historial["corrida"] = corrida
            df_historial["seed_ag"] = seed_ag
            metricas_totales.append(df_historial)

            resumen = dict(resumen)
            resumen["corrida"] = corrida
            resumen["seed_ag"] = seed_ag
            resueltas.append(resumen)

            print(
                f"Corrida {corrida:02d} | seed AG {seed_ag} | "
                f"fitness {resumen['mejor_fitness_global']:.10f} | "
                f"backlog {resumen['backlog_alertas']} | "
                f"desbalance {resumen['desbalance_carga']:.6f} | "
                f"tiempo {resumen['tiempo_ejecucion_seg']:.4f}s"
            )

    df_metricas = pd.concat(metricas_totales, ignore_index=True)
    df_resumen_repeticiones = pd.DataFrame(resueltas)
    df_metricas_promediadas = _agrupar_metricas_repetidas(df_metricas)
    df_resumen_agrupado = _agrupar_resumen_repeticiones(df_resumen_repeticiones)
    df_resumen = df_resumen_repeticiones.loc[
        df_resumen_repeticiones.groupby("metodo")["mejor_fitness_global"].idxmax()
    ].sort_values("metodo")

    df_metricas.to_csv(METRICAS_CSV, index=False)
    df_metricas_promediadas.to_csv(METRICAS_PROMEDIADAS_CSV, index=False)
    df_resumen_repeticiones.to_csv(RESUMEN_REPETICIONES_CSV, index=False)
    df_resumen_agrupado.to_csv(RESUMEN_AGRUPADO_CSV, index=False)
    df_resumen.to_csv(RESUMEN_CSV, index=False)

    mejor_indice = int(df_resumen["mejor_fitness_global"].idxmax())
    mejor = df_resumen.iloc[mejor_indice]
    distribucion_final = _resumen_distribucion(mejor["mejor_cromosoma"], alertas)
    distribucion_final.to_csv(DISTRIBUCION_FINAL_CSV, index=False)

    resumen_cargas = distribucion_final[["analista", "alertas_asignadas", "carga_total_min", "criticidad_critica"]].copy()
    resumen_cargas.to_csv(ASIGNACION_FINAL_CSV, index=False)

    graficar_metricas(df_metricas)

    _imprimir_resumen_global(df_resumen, mejor_indice)

    print("\n" + "=" * 126)
    print("RESUMEN AGRUPADO DE REPETICIONES")
    print("=" * 126)
    columnas_resumen = [
        "metodo",
        "repeticiones",
        "mejor_fitness_global_media",
        "mejor_fitness_global_min",
        "mejor_fitness_global_max",
        "mejor_fitness_global_desvio",
        "tiempo_total_estimado_min_media",
        "tiempo_total_estimado_min_min",
        "tiempo_total_estimado_min_max",
        "tiempo_total_estimado_min_desvio",
        "desbalance_carga_media",
        "desbalance_carga_min",
        "desbalance_carga_max",
        "desbalance_carga_desvio",
        "tiempo_ejecucion_seg_media",
        "tiempo_ejecucion_seg_min",
        "tiempo_ejecucion_seg_max",
        "tiempo_ejecucion_seg_desvio",
    ]
    print(df_resumen_agrupado[columnas_resumen].to_string(index=False))

    print("\n" + "=" * 126)
    print("DISTRIBUCION FINAL DE ALERTAS EN EL MEJOR ESCENARIO")
    print("=" * 126)
    print(distribucion_final.to_string(index=False))


if __name__ == "__main__":
    main()