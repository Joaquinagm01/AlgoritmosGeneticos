"""Algoritmo Genético Canónico aplicado a Scheduling de Alertas SOC.

El programa genera alertas sintéticas, construye una población inicial de
asignaciones alertas->analistas, evalúa cada cromosoma con una función fitness
compuesta con penalizaciones ponderadas para tiempo de resolución, balance de
carga, alertas críticas y alertas pendientes fuera del horizonte, y compara
tres estrategias evolutivas: ruleta, torneo y ruleta con preservación elitista.
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
from scipy.stats import kruskal


# =========================
# Configuracion general
# =========================
SEED_ALERTAS = 42
SEED_AG_BASE = 1000
N_REPETICIONES = 30
N_ANALISTAS = 10
N_ALERTAS = 250
TAM_POBLACION = 100  # Aumentado para mayor diversidad en un espacio de busqueda de 10^250
N_GENERACIONES = 200  # Aumentado para permitir convergencia con una poblacion mayor
P_CROSSOVER = 0.8
P_MUTACION_GEN_MIN = 0.005  # Tasa de mutacion minima para la mutacion adaptativa
P_MUTACION_GEN_MAX = 0.05  # Tasa de mutacion maxima para la mutacion adaptativa
TORNEO_K = 3
ELITE_SIZE = 2
HORIZONTE_MINUTOS = 8 * 60

PRIORIDADES = ("Baja", "Media", "Alta", "Critica")
PRIORIDAD_PESOS = (0.35, 0.30, 0.22, 0.13)
PRIORIDAD_RANK = {"Critica": 0, "Alta": 1, "Media": 2, "Baja": 3}
SLA_POR_PRIORIDAD = {"Baja": 480, "Media": 120, "Alta": 60, "Critica": 30}

BASE_RESOLUCION = {"Baja": 8, "Media": 15, "Alta": 25, "Critica": 40}
RANGO_SEVERIDAD = {"Baja": (10, 35), "Media": (30, 60), "Alta": (55, 85), "Critica": (80, 100)}

METODOS = ("ruleta", "torneo", "ruleta_con_elitismo")
METODOS_AG = ("ruleta", "torneo", "ruleta_con_elitismo", "ruleta_uniforme")
BASE_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = BASE_DIR / "outputs"
FIGURES_DIR = OUTPUTS_DIR / "figures"

METRICAS_CSV = OUTPUTS_DIR / "metricas_generacionales_soc.csv"
METRICAS_PROMEDIADAS_CSV = OUTPUTS_DIR / "metricas_generacionales_promediadas_soc.csv"
RESUMEN_REPETICIONES_CSV = OUTPUTS_DIR / "resumen_repeticiones_soc.csv"
RESUMEN_AGRUPADO_CSV = OUTPUTS_DIR / "resumen_resultados_agrupados_soc.csv"
RESUMEN_CSV = OUTPUTS_DIR / "resumen_resultados_soc.csv"
BASELINES_CSV = OUTPUTS_DIR / "baselines_referencia_soc.csv"
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

@dataclass(frozen=True)
class Analista:
    id_analista: int
    nombre: str
    eficiencia: float  # 1.0 = normal, >1.0 = mas rapido, <1.0 = mas lento
    especialidades: List[str]  # Lista de prioridades en las que es experto



def generar_alertas(n_alertas: int = N_ALERTAS, seed: int = SEED_ALERTAS) -> List[Alerta]:
    """Genera alertas sintéticas de un SOC con prioridad, severidad y tiempo estimado."""
    rng = random.Random(seed)
    # Generacion de llegadas con picos para simular rafagas de alertas
    n_picos = rng.randint(2, 5)
    llegadas = []
    for _ in range(n_picos):
        centro_pico = rng.randint(0, HORIZONTE_MINUTOS)
        n_alertas_pico = int(n_alertas / n_picos * rng.uniform(0.5, 1.5))
        for _ in range(n_alertas_pico):
            llegada = int(rng.normalvariate(centro_pico, HORIZONTE_MINUTOS / 20))
            llegadas.append(max(0, min(HORIZONTE_MINUTOS - 1, llegada)))
    llegadas.extend(rng.randint(0, HORIZONTE_MINUTOS - 1) for _ in range(n_alertas - len(llegadas)))
    llegadas = sorted(llegadas[:n_alertas])

    alertas: List[Alerta] = []
    for idx, llegada_min in enumerate(llegadas, start=1):
        prioridad = rng.choices(PRIORIDADES, weights=PRIORIDAD_PESOS, k=1)[0]
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


def generar_analistas(n_analistas: int = N_ANALISTAS, seed: int = SEED_ALERTAS) -> List[Analista]:
    """Genera un equipo de analistas heterogeneo con distintas eficiencias y especialidades."""
    rng = random.Random(seed)
    nombres = [f"Analista-{i:02d}" for i in range(1, n_analistas + 1)]
    rng.shuffle(nombres)

    analistas = []
    for i in range(n_analistas):
        eficiencia = rng.uniform(0.85, 1.25)  # Variacion de eficiencia del -15% al +25%
        n_especialidades = rng.randint(1, 2)
        especialidades = rng.sample(PRIORIDADES, k=n_especialidades)
        analistas.append(Analista(id_analista=i + 1, nombre=nombres[i], eficiencia=eficiencia, especialidades=especialidades))
    return analistas


def generar_poblacion(
    tam_poblacion: int = TAM_POBLACION,
    n_alertas: int = N_ALERTAS,
    n_analistas: int = N_ANALISTAS,
    alertas: Sequence[Alerta] | None = None,
) -> List[List[int]]:
    """Genera una poblacion inicial aleatoria de cromosomas.

    Cada gen representa la asignacion de una alerta a un analista.
    Los analistas se numeran de 1 a N_ANALISTAS para que el cromosoma sea legible.
    Se inyecta una solucion 'least loaded' para mejorar la base inicial.
    """
    poblacion = [
        [random.randint(1, n_analistas) for _ in range(n_alertas)]
        for _ in range(tam_poblacion)
    ]
    if alertas and tam_poblacion > 0:
        poblacion[0] = _baseline_menos_cargado(alertas, n_analistas)  # Inyectar solucion greedy
    return poblacion


def _normalizar(valor: float, max_valor: float) -> float:
    """Normaliza un valor en el rango [0, 1] de forma segura."""
    return valor / max_valor if max_valor > 0 else 0.0


def _evaluar_asignacion(
    cromosoma: Sequence[int],
    alertas: Sequence[Alerta],
    analistas: Sequence[Analista],
) -> Dict[str, float | int | List[int]]:
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
            analista_obj = analistas[idx_analista]
            alerta = alertas[idx_alerta]

            tiempo_resolucion = alerta.tiempo_estimado_min / analista_obj.eficiencia
            # Bonificacion si el analista es especialista en la prioridad de la alerta
            if alerta.prioridad in analista_obj.especialidades:
                tiempo_resolucion *= 0.8  # 20% mas rapido

            inicio = max(disponibilidad[idx_analista], alerta.llegada_min)
            espera = inicio - alerta.llegada_min
            fin = inicio + tiempo_resolucion

            disponibilidad[idx_analista] = fin
            cargas[idx_analista] += tiempo_resolucion
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

    # Normalizacion de metricas para que los pesos sean mas interpretables
    # Se ajusta la normalizacion del makespan para darle mas sensibilidad. En lugar de la carga total,
    # se usa la carga media por analista como una referencia mas ajustada.
    carga_media_teorica = (sum(alerta.tiempo_estimado_min for alerta in alertas) / N_ANALISTAS) * 1.5
    norm_makespan = _normalizar(tiempo_total_estimado, carga_media_teorica)
    norm_espera = _normalizar(espera_promedio, HORIZONTE_MINUTOS)
    norm_espera_critica = _normalizar(espera_critica_promedio, SLA_POR_PRIORIDAD["Critica"])
    norm_retraso_critico = _normalizar(retraso_critico_promedio, SLA_POR_PRIORIDAD["Critica"])
    norm_backlog_alertas = _normalizar(backlog_alertas, len(alertas))
    norm_backlog_minutos = _normalizar(backlog_minutos, len(alertas) * HORIZONTE_MINUTOS)

    penalizacion = (
        # Pesos ajustados para metricas normalizadas
        2.0 * norm_makespan  # Minimizar el tiempo total de resolucion
        + 1.0 * norm_espera  # Minimizar la espera general
        + 5.0 * norm_espera_critica  # Penalizar fuertemente la espera de alertas criticas
        + 20.0 * norm_retraso_critico  # Penalizar muy fuertemente el incumplimiento de SLA critico
        + 2.0 * norm_backlog_alertas  # Penalizar las alertas que quedan fuera del turno
        + 10.0 * desbalance_carga  # Penalizar el desequilibrio en la carga de trabajo
    )

    fitness = 1.0 / (1.0 + penalizacion)

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


def calcular_fitness(cromosoma: Sequence[int], alertas: Sequence[Alerta], analistas: Sequence[Analista]) -> float:
    """Devuelve el fitness escalar de un cromosoma."""
    return _evaluar_asignacion(cromosoma, alertas, analistas)["fitness"]


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


def crossover_uniforme(padre1: Sequence[int], padre2: Sequence[int]) -> Tuple[List[int], List[int]]:
    """Crossover uniforme: cada gen se hereda de uno de los padres con 50% de probabilidad."""
    if len(padre1) != len(padre2):
        raise ValueError("Los cromosomas deben tener la misma longitud")

    hijo1 = list(padre1)
    hijo2 = list(padre2)
    for i in range(len(padre1)):
        if random.random() < 0.5:
            hijo1[i], hijo2[i] = hijo2[i], hijo1[i]
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


def mutacion(cromosoma: Sequence[int], p_mutacion_gen: float) -> List[int]:
    """Mutacion por gen: cada asignacion puede cambiar con probabilidad p_mutacion_gen."""
    hijo = list(cromosoma)
    for i in range(len(hijo)):
        if random.random() < p_mutacion_gen:
            analista_actual = hijo[i]
            analistas_posibles = [a for a in range(1, N_ANALISTAS + 1) if a != analista_actual]
            if analistas_posibles:
                hijo[i] = random.choice(analistas_posibles)
    return hijo


def _tasa_mutacion_adaptativa(fitness_prom: float, fitness_max: float) -> float:
    """Ajusta la tasa de mutacion segun la convergencia de la poblacion."""
    if fitness_max == 0:
        return P_MUTACION_GEN_MAX
    ratio = fitness_prom / fitness_max  # Cerca de 1 si la poblacion es homogenea
    # Si la poblacion converge (ratio > 0.98), aumenta la mutacion para explorar. Si no, la reduce.
    tasa = P_MUTACION_GEN_MIN + (P_MUTACION_GEN_MAX - P_MUTACION_GEN_MIN) * (ratio**10)
    return tasa


def calcular_diversidad_genetica(poblacion: Sequence[Sequence[int]]) -> float:
    """Calcula la diversidad genetica de la poblacion.

    Para cada gen, calcula 1 - la frecuencia del alelo mas comun.
    El resultado es el promedio de esta metrica sobre todos los genes.
    Un valor cercano a 0 significa baja diversidad (convergencia).
    Un valor cercano a 1 significa alta diversidad.
    """
    if not poblacion or not poblacion[0]:
        return 0.0

    tam_poblacion = len(poblacion)
    n_genes = len(poblacion[0])
    diversidad_por_gen = []

    for i in range(n_genes):
        conteo_alelos = pd.Series([cromosoma[i] for cromosoma in poblacion]).value_counts()
        frecuencia_max = conteo_alelos.max() / tam_poblacion
        diversidad_por_gen.append(1.0 - frecuencia_max)

    return statistics.fmean(diversidad_por_gen)


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


def _resumen_distribucion(cromosoma: Sequence[int], alertas: Sequence[Alerta], analistas: Sequence[Analista]) -> pd.DataFrame:
    """Construye la tabla final de carga por analista a partir del mejor cromosoma."""
    filas = []
    for analista_obj in analistas:
        indices = [idx for idx, asignado in enumerate(cromosoma) if asignado == analista_obj.id_analista]
        alertas_asignadas = [alertas[idx] for idx in indices]
        carga_total = sum(
            (alerta.tiempo_estimado_min / analista_obj.eficiencia) * (0.8 if alerta.prioridad in analista_obj.especialidades else 1.0)
            for alerta in alertas_asignadas
        )
        criticidad = sum(1 for alerta in alertas_asignadas if alerta.prioridad == "Critica")
        severidad_prom = statistics.fmean([alerta.severidad for alerta in alertas_asignadas]) if alertas_asignadas else 0.0
        filas.append(
            {
                "analista": analista_obj.id_analista,
                "alertas_asignadas": len(alertas_asignadas),
                "carga_total_min": carga_total,
                "criticidad_critica": criticidad,
                "severidad_promedio": float(severidad_prom),
                "carga_promedio_por_alerta_min": float(carga_total / len(alertas_asignadas)) if alertas_asignadas else 0.0,
            }
        )
    return pd.DataFrame(filas)


def _baseline_aleatorio(n_alertas: int, n_analistas: int, seed: int = 2026) -> List[int]:
    rng = random.Random(seed)
    return [rng.randint(1, n_analistas) for _ in range(n_alertas)]


def _baseline_round_robin(n_alertas: int, n_analistas: int) -> List[int]:
    return [(idx % n_analistas) + 1 for idx in range(n_alertas)]


def _baseline_menos_cargado(alertas: Sequence[Alerta], n_analistas: int) -> List[int]:
    cargas = [0] * n_analistas
    cromosoma = [0] * len(alertas)
    orden = sorted(range(len(alertas)), key=lambda idx: (alertas[idx].llegada_min, PRIORIDAD_RANK[alertas[idx].prioridad]))

    for idx_alerta in orden:
        analista = int(np.argmin(cargas))
        cromosoma[idx_alerta] = analista + 1
        cargas[analista] += alertas[idx_alerta].tiempo_estimado_min

    return cromosoma


def _baseline_greedy_prioridad_primero(alertas: Sequence[Alerta], analistas: Sequence[Analista]) -> List[int]:
    """Asigna la alerta mas critica/urgente al analista que se libera antes."""
    cromosoma = [0] * len(alertas)
    # Ordena por prioridad (mas alta primero), luego por llegada (mas temprana primero)
    orden_alertas = sorted(range(len(alertas)), key=lambda idx: (PRIORIDAD_RANK[alertas[idx].prioridad], alertas[idx].llegada_min))

    disponibilidad_analistas = [0.0] * len(analistas)

    for idx_alerta in orden_alertas:
        # Encuentra al analista que estara disponible antes
        idx_analista_elegido = int(np.argmin(disponibilidad_analistas))
        analista_obj = analistas[idx_analista_elegido]
        alerta = alertas[idx_alerta]

        cromosoma[idx_alerta] = analista_obj.id_analista
        tiempo_resolucion = (alerta.tiempo_estimado_min / analista_obj.eficiencia) * (0.8 if alerta.prioridad in analista_obj.especialidades else 1.0)
        disponibilidad_analistas[idx_analista_elegido] = max(disponibilidad_analistas[idx_analista_elegido], alerta.llegada_min) + tiempo_resolucion

    return cromosoma

def evolucionar(
    alertas: Sequence[Alerta],
    analistas: Sequence[Analista],
    metodo: str = "ruleta",
    n_generaciones: int = N_GENERACIONES,
    tam_poblacion: int = TAM_POBLACION,
    p_crossover: float = P_CROSSOVER,
    crossover_type: str = "punto",
    p_mutacion_gen_range: Tuple[float, float] = (P_MUTACION_GEN_MIN, P_MUTACION_GEN_MAX),
    seed: int = SEED_AG_BASE,
) -> Tuple[pd.DataFrame, Dict[str, object]]:
    """Ejecuta la evolucion genetica para un metodo de seleccion concreto."""
    if metodo not in METODOS:
        raise ValueError(f"Metodo no soportado: {metodo}")

    random.seed(seed)
    np.random.seed(seed)

    poblacion = generar_poblacion(tam_poblacion=tam_poblacion, n_alertas=len(alertas), alertas=alertas)
    historial: List[Dict[str, object]] = []

    mejor_global: List[int] | None = None
    mejor_global_eval: Dict[str, object] | None = None

    inicio_total = time.time()

    for generacion in range(1, n_generaciones + 1):
        inicio_gen = time.time()

        evaluaciones = [_evaluar_asignacion(individuo, alertas, analistas) for individuo in poblacion]
        fitnesses = [evaluacion["fitness"] for evaluacion in evaluaciones]
        idx_mejor = int(np.argmax(fitnesses))
        diversidad_genetica = calcular_diversidad_genetica(poblacion)
        mejor_gen = list(poblacion[idx_mejor])
        evaluacion_mejor = evaluaciones[idx_mejor]

        if mejor_global_eval is None or evaluacion_mejor["fitness"] > mejor_global_eval["fitness"]:
            mejor_global = list(mejor_gen)
            mejor_global_eval = dict(evaluacion_mejor)

        p_mutacion_actual = _tasa_mutacion_adaptativa(statistics.fmean(fitnesses), max(fitnesses))

        if generacion < n_generaciones:
            nueva_poblacion: List[List[int]] = []
            if metodo == "ruleta_con_elitismo":
                elite_indices = list(np.argsort(fitnesses)[::-1][:ELITE_SIZE])
                nueva_poblacion.extend(list(poblacion[idx]) for idx in elite_indices)

            while len(nueva_poblacion) < tam_poblacion:
                padre1 = _seleccionar_padre(metodo, poblacion, fitnesses)
                padre2 = _seleccionar_padre(metodo, poblacion, fitnesses)

                if random.random() < p_crossover:
                    if crossover_type == "uniforme":
                        hijo1, hijo2 = crossover_uniforme(padre1, padre2)
                    else:
                        hijo1, hijo2 = crossover(padre1, padre2)
                else:
                    hijo1, hijo2 = list(padre1), list(padre2)

                hijo1 = mutacion(hijo1, p_mutacion_actual)
                hijo2 = mutacion(hijo2, p_mutacion_actual)

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
                "p_mutacion": p_mutacion_actual,
                "diversidad_genetica": float(diversidad_genetica),
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
            diversidad_genetica_media=("diversidad_genetica", "mean"),
            diversidad_genetica_desvio=("diversidad_genetica", "std"),
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
        ("desbalance_carga", "Evolucion del Desbalance de Carga", "Desbalance de Carga (promedio de la generacion)", "evolucion_desbalance.png"),
        ("backlog_alertas", "Evolucion del Backlog", "Alertas en Backlog (promedio de la generacion)", "evolucion_backlog.png"),
        ("p_mutacion", "Tasa de Mutacion Adaptativa", "Probabilidad de Mutacion por Gen", "mutacion_adaptativa.png"),
        ("diversidad_genetica", "Evolucion de la Diversidad Genetica", "Diversidad Genetica Promedio", "evolucion_diversidad_genetica.png"),
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
    plt.title("Comparacion de Fitness Promedio entre Metodos de Seleccion")
    plt.xlabel("Generacion")
    plt.ylabel("Fitness promedio")
    plt.grid(True, linestyle="--", alpha=0.35)
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "comparacion_metodos.png", dpi=200)
    plt.close()

def graficar_distribucion_final(df_distribucion: pd.DataFrame) -> None:
    """Genera un grafico de barras con la carga final por analista."""
    if df_distribucion.empty:
        return

    plt.figure(figsize=(11, 6))
    analistas = df_distribucion["analista"]
    carga_min = df_distribucion["carga_total_min"]
    media_carga = carga_min.mean()

    plt.bar(analistas, carga_min, color="skyblue", label="Carga total (min)")
    plt.axhline(y=media_carga, color='r', linestyle='--', label=f"Carga media ({media_carga:.2f} min)")
    plt.title("Carga Final por Analista en la Mejor Solución Global")
    plt.xlabel("Analista")
    plt.ylabel("Carga de Trabajo Total (minutos)")
    plt.legend()
    plt.grid(True, axis="y", linestyle="--", alpha=0.5)
    plt.savefig(FIGURES_DIR / "carga_final_por_analista.png", dpi=200)
    plt.close()

def graficar_boxplots_comparativos(df_resumen_repeticiones: pd.DataFrame, df_baselines: pd.DataFrame) -> None:
    """Genera un boxplot comparando el fitness final de todos los metodos y baselines."""
    plt.figure(figsize=(14, 8))

    datos_ag = [grupo["mejor_fitness_global"].values for _, grupo in df_resumen_repeticiones.groupby("metodo")]
    etiquetas_ag = [metodo.replace("_", " ").title() for metodo in df_resumen_repeticiones["metodo"].unique()]

    datos_baseline = [df_baselines[df_baselines["metodo"] == metodo]["fitness"].values for metodo in df_baselines["metodo"].unique()]
    etiquetas_baseline = [metodo.replace("_", " ").title() for metodo in df_baselines["metodo"].unique()]

    todos_los_datos = datos_ag + datos_baseline
    todas_las_etiquetas = etiquetas_ag + etiquetas_baseline

    bp = plt.boxplot(todos_los_datos, patch_artist=True, labels=todas_las_etiquetas)

    # Colores para diferenciar AG de Baselines
    colores_ag = ['lightblue'] * len(datos_ag)
    colores_baseline = ['lightgreen'] * len(datos_baseline)
    for patch, color in zip(bp['boxes'], colores_ag + colores_baseline):
        patch.set_facecolor(color)

    plt.title("Distribución del Mejor Fitness Global por Método (30 Corridas)", fontsize=16)
    plt.ylabel("Mejor Fitness Global", fontsize=12)
    plt.xlabel("Método de Asignación", fontsize=12)
    plt.xticks(rotation=45, ha="right")
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "boxplot_comparativo_fitness.png", dpi=200)
    plt.close()


def realizar_pruebas_estadisticas(df_resumen_repeticiones: pd.DataFrame) -> None:
    """Realiza pruebas de Kruskal-Wallis para comparar los metodos del AG."""
    print("\n" + "=" * 126)
    print("PRUEBAS DE SIGNIFICANCIA ESTADÍSTICA (KRUSKAL-WALLIS)")
    print("=" * 126)
    print("H0: Las medianas de fitness de todos los métodos son iguales.")
    print("H1: Al menos una mediana es diferente.")
    print("Un p-valor < 0.05 sugiere que las diferencias observadas no son por azar.")
    print("-" * 126)

    grupos = [grupo["mejor_fitness_global"].values for _, grupo in df_resumen_repeticiones.groupby("metodo")]
    etiquetas = [metodo for metodo, _ in df_resumen_repeticiones.groupby("metodo")]

    if len(grupos) < 2:
        print("No hay suficientes grupos para realizar una prueba estadística.")
        return

    try:
        stat, p_valor = kruskal(*grupos)
        print(f"Estadístico Kruskal-Wallis: {stat:.4f}")
        print(f"P-valor: {p_valor:.4f}")
        if p_valor < 0.05:
            print("\nResultado: Se rechaza la hipótesis nula. Existen diferencias estadísticamente significativas entre los métodos.")
        else:
            print("\nResultado: No se puede rechazar la hipótesis nula. Las diferencias no son estadísticamente significativas.")
    except ValueError as e:
        print(f"No se pudo realizar la prueba: {e}")

def _imprimir_encabezado(metodo: str) -> None:
    print("=" * 126)
    print(f"METODO: {metodo.upper()}")
    print("=" * 126)
    print(
        f"{'Gen':>4} | {'Fitness max':>12} | {'Fitness min':>12} | {'Fitness prom':>12} | "
        f"{'Desv. std':>12} | {'Tiempo gen (s)':>15} | {'Mejor fitness':>14} | {'Pendientes':>10}"
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
    print(f"Alertas pendientes            : {resumen['backlog_alertas']}")
    print(f"Alertas pendientes fuera del horizonte (min) : {resumen['backlog_minutos']:.4f}")
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

    ganador = df_resumen.loc[mejor_indice]
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
    analistas = generar_analistas(seed=SEED_ALERTAS)

    print("=" * 126)
    print("ALGORITMO GENETICO CANONICO APLICADO A SCHEDULING DE ALERTAS SOC")
    print("=" * 126)
    print(f"Analistas SOC                 : {N_ANALISTAS}")
    print(f"Alertas sinteticas             : {N_ALERTAS}")
    print(f"Poblacion inicial              : {TAM_POBLACION}")
    print(f"Generaciones                   : {N_GENERACIONES}")
    print(f"Probabilidad de crossover      : {P_CROSSOVER}")
    print(f"Probabilidad de mutacion (rango): {P_MUTACION_GEN_MIN} - {P_MUTACION_GEN_MAX} (Adaptativa)")
    print(f"Horizonte de llegada (min)     : {HORIZONTE_MINUTOS}")
    print(f"Repeticiones por metodo        : {N_REPETICIONES}")
    print("=" * 126)

    metricas_totales: List[pd.DataFrame] = []
    resueltas = []

    for metodo in METODOS_AG:
        print("\n" + "=" * 126)
        print(f"METODO: {metodo.upper()}")
        print("=" * 126)
        for corrida in range(1, N_REPETICIONES + 1):
            seed_ag = SEED_AG_BASE + corrida
            crossover_type = "uniforme" if "uniforme" in metodo else "punto"
            metodo_seleccion = metodo.replace("_uniforme", "")
            df_historial, resumen = evolucionar(
                alertas, analistas, metodo=metodo_seleccion, seed=seed_ag, crossover_type=crossover_type
            )

            df_historial = df_historial.copy()
            df_historial["metodo"] = metodo
            df_historial["corrida"] = corrida
            df_historial["seed_ag"] = seed_ag
            metricas_totales.append(df_historial)

            resumen = dict(resumen)
            resumen["corrida"] = corrida
            resumen["metodo"] = metodo # Sobrescribir para incluir el tipo de crossover
            resumen["seed_ag"] = seed_ag
            resueltas.append(resumen)

            print(
                f"Corrida {corrida:02d} | seed AG {seed_ag} | "
                f"fitness {resumen['mejor_fitness_global']:.10f} | "
                f"alertas pendientes {resumen['backlog_alertas']} | "
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

    baselines = [
        {
            "metodo": "aleatorio",
            "cromosoma": _baseline_aleatorio(len(alertas), N_ANALISTAS),
        },
        {
            "metodo": "round_robin",
            "cromosoma": _baseline_round_robin(len(alertas), N_ANALISTAS),
        },
        {
            "metodo": "least_loaded",
            "cromosoma": _baseline_menos_cargado(alertas, N_ANALISTAS),
        },
        {
            "metodo": "greedy_prioridad",
            "cromosoma": _baseline_greedy_prioridad_primero(alertas, analistas),
        },
    ]

    baselines_resumen = []
    for baseline in baselines:
        evaluacion = _evaluar_asignacion(baseline["cromosoma"], alertas, analistas)
        baselines_resumen.append(
            {
                "metodo": baseline["metodo"],
                "fitness": float(evaluacion["fitness"]),
                "makespan_min": int(evaluacion["tiempo_total_estimado_min"]),
                "penalizacion_total": float(evaluacion["penalizacion"]),
                "espera_promedio_min": float(evaluacion["espera_promedio_min"]),
                "espera_critica_promedio_min": float(evaluacion["espera_critica_promedio_min"]),
                "backlog_alertas": int(evaluacion["backlog_alertas"]),
                "desbalance_carga": float(evaluacion["desbalance_carga"]),
            }
        )

    df_baselines = pd.DataFrame(baselines_resumen)
    df_baselines.to_csv(BASELINES_CSV, index=False)

    mejor_indice = df_resumen["mejor_fitness_global"].idxmax()
    mejor = df_resumen.loc[mejor_indice]
    distribucion_final = _resumen_distribucion(mejor["mejor_cromosoma"], alertas, analistas)
    distribucion_final.to_csv(DISTRIBUCION_FINAL_CSV, index=False)

    resumen_cargas = distribucion_final[["analista", "alertas_asignadas", "carga_total_min", "criticidad_critica"]].copy()
    resumen_cargas.to_csv(ASIGNACION_FINAL_CSV, index=False)

    graficar_metricas(df_metricas)
    graficar_boxplots_comparativos(df_resumen_repeticiones, df_baselines)
    graficar_distribucion_final(distribucion_final)

    _imprimir_resumen_global(df_resumen, mejor_indice)

    print("\n" + "=" * 126)
    print("LINEA DE BASE DE REFERENCIA")
    print("=" * 126)
    print(df_baselines.to_string(index=False))

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

    realizar_pruebas_estadisticas(df_resumen_repeticiones)



if __name__ == "__main__":
    main()