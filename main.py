import random
import statistics
import time
from dataclasses import dataclass
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# =========================
# Parámetros obligatorios
# =========================
N_ANALISTAS = 10
N_ALERTAS = 500
TAM_POBLACION = 10
N_GENERACIONES = 20
P_CROSSOVER = 0.75
P_MUTACION = 0.05
TORNEO_K = 3
ELITE_SIZE = 2
SEED = 42

PRIORIDADES = ["Baja", "Media", "Alta", "Critica"]
PROB_PRIORIDADES = [0.35, 0.30, 0.23, 0.12]
SLA_MINUTOS = {
    "Critica": 120,
    "Alta": 240,
    "Media": 480,
    "Baja": 720,
}
METODOS = ["ruleta", "torneo", "elitismo"]

PESO_DESBALANCE = 2.0
PESO_SOBRECARGA = 1.5
PESO_ESPERA_CRITICA = 1.2
PESO_BACKLOG = 30.0

METRICAS_GRAFICOS = [
    ("fitness_max", "maximos_por_generacion.png", "Fitness Máximo por Generación"),
    ("fitness_prom", "promedios_por_generacion.png", "Fitness Promedio por Generación"),
    ("fitness_min", "minimos_por_generacion.png", "Fitness Mínimo por Generación"),
    ("desv_std", "desviacion_estandar_por_generacion.png", "Desviación Estándar por Generación"),
]

ARCHIVOS_EXPORTADOS = [
    "metricas_generacionales_soc.csv",
    "resumen_resultados_soc.csv",
    "maximos_por_generacion.png",
    "promedios_por_generacion.png",
    "minimos_por_generacion.png",
    "desviacion_estandar_por_generacion.png",
    "comparacion_metodos.png",
]

Chromosome = List[int]
Population = List[Chromosome]


@dataclass
class Alerta:
    """Representa una alerta SOC con atributos de scheduling."""

    prioridad: str
    tiempo_estimado: int
    severidad: int


def generar_alertas(n_alertas=N_ALERTAS):
    """Genera alertas aleatorias con prioridad, tiempo estimado y severidad."""
    alertas: List[Alerta] = []
    for _ in range(n_alertas):
        prioridad = random.choices(PRIORIDADES, weights=PROB_PRIORIDADES, k=1)[0]
        if prioridad == "Baja":
            tiempo = random.randint(15, 60)
            severidad = random.randint(1, 3)
        elif prioridad == "Media":
            tiempo = random.randint(30, 90)
            severidad = random.randint(4, 6)
        elif prioridad == "Alta":
            tiempo = random.randint(60, 180)
            severidad = random.randint(7, 8)
        else:
            tiempo = random.randint(90, 240)
            severidad = random.randint(9, 10)

        alertas.append(Alerta(prioridad=prioridad, tiempo_estimado=tiempo, severidad=severidad))

    return alertas


def generar_poblacion(tam_poblacion=TAM_POBLACION, n_alertas=N_ALERTAS, n_analistas=N_ANALISTAS):
    """Crea una población inicial de cromosomas de asignación alerta-analista."""
    return [[random.randint(0, n_analistas - 1) for _ in range(n_alertas)] for _ in range(tam_poblacion)]


def _evaluar_cromosoma(cromosoma: Chromosome, alertas: List[Alerta], n_analistas=N_ANALISTAS) -> Dict[str, float | int | List[int]]:
    """Evalúa una solución y devuelve métricas de scheduling para SOC."""
    colas = [[] for _ in range(n_analistas)]
    for idx_alerta, idx_analista in enumerate(cromosoma):
        colas[idx_analista].append(idx_alerta)

    cargas: List[int] = []
    tiempos_criticos: List[int] = []
    backlog = 0

    for cola in colas:
        acumulado = 0
        for idx_alerta in cola:
            alerta = alertas[idx_alerta]
            acumulado += alerta.tiempo_estimado
            if alerta.prioridad == "Critica":
                tiempos_criticos.append(acumulado)
            if acumulado > SLA_MINUTOS[alerta.prioridad]:
                backlog += 1
        cargas.append(acumulado)

    tiempo_total = max(cargas) if cargas else 0
    carga_promedio = statistics.fmean(cargas) if cargas else 0
    desbalance = statistics.pstdev(cargas) if len(cargas) > 1 else 0
    sobrecarga = sum(max(0.0, carga - (1.20 * carga_promedio)) for carga in cargas)
    espera_critica = statistics.fmean(tiempos_criticos) if tiempos_criticos else 0

    penalizacion = (
        PESO_DESBALANCE * desbalance
        + PESO_SOBRECARGA * sobrecarga
        + PESO_ESPERA_CRITICA * espera_critica
        + PESO_BACKLOG * backlog
    )

    objetivo = tiempo_total + penalizacion
    fitness = 1.0 / (1.0 + objetivo)

    return {
        "fitness": fitness,
        "tiempo_total": tiempo_total,
        "cargas": cargas,
        "backlog": backlog,
        "desbalance": desbalance,
    }


def calcular_fitness(cromosoma, alertas):
    """Calcula fitness de un cromosoma según tiempo total y penalizaciones SOC."""
    return _evaluar_cromosoma(cromosoma, alertas)["fitness"]


def seleccion_ruleta(poblacion, fitnesses):
    """Selecciona un individuo con probabilidad proporcional a su fitness."""
    total = sum(fitnesses)
    if total <= 0:
        return random.choice(poblacion)

    r = random.uniform(0, total)
    acumulado = 0.0
    for individuo, fit in zip(poblacion, fitnesses):
        acumulado += fit
        if acumulado >= r:
            return individuo
    return poblacion[-1]


def seleccion_torneo(poblacion, fitnesses, k=TORNEO_K):
    """Selecciona un individuo mediante torneo de tamaño k."""
    indices = random.sample(range(len(poblacion)), k=min(k, len(poblacion)))
    mejor_idx = max(indices, key=lambda i: fitnesses[i])
    return poblacion[mejor_idx]


def seleccion_elitismo(poblacion, fitnesses, elite_size=ELITE_SIZE):
    """Retorna los mejores individuos para preservarlos en la siguiente generación."""
    orden = sorted(range(len(poblacion)), key=lambda i: fitnesses[i], reverse=True)
    return [poblacion[i][:] for i in orden[:elite_size]]


def crossover(padre1, padre2, p_crossover=P_CROSSOVER):
    """Aplica crossover de 1 punto para cromosomas de asignación."""
    if random.random() < p_crossover:
        punto = random.randint(1, len(padre1) - 1)
        hijo1 = padre1[:punto] + padre2[punto:]
        hijo2 = padre2[:punto] + padre1[punto:]
        return hijo1, hijo2
    return padre1[:], padre2[:]


def mutacion(cromosoma, p_mutacion=P_MUTACION):
    """Aplica mutación invertida invirtiendo un segmento aleatorio del cromosoma."""
    hijo = cromosoma[:]
    if random.random() < p_mutacion:
        i, j = sorted(random.sample(range(len(hijo)), 2))
        hijo[i : j + 1] = list(reversed(hijo[i : j + 1]))
    return hijo


def calcular_estadisticas(fitnesses, tiempo_gen):
    """Resume métricas de fitness de una generación."""
    return {
        "fitness_max": max(fitnesses),
        "fitness_min": min(fitnesses),
        "fitness_prom": statistics.fmean(fitnesses),
        "desv_std": statistics.pstdev(fitnesses),
        "tiempo_gen_seg": tiempo_gen,
    }


def _seleccionar_padre(metodo, poblacion, fitnesses):
    """Selecciona un padre según el método configurado."""
    if metodo == "ruleta" or metodo == "elitismo":
        return seleccion_ruleta(poblacion, fitnesses)
    if metodo == "torneo":
        return seleccion_torneo(poblacion, fitnesses)
    raise ValueError(f"Método de selección no soportado: {metodo}")


def _imprimir_encabezado_metodo(metodo):
    """Imprime cabecera de métricas por método de selección."""
    print("=" * 110)
    print(f"METODO: {metodo.upper()}")
    print("=" * 110)
    print(
        f"{'Gen':>3} | {'Fitness Máx':>12} | {'Fitness Mín':>12} | {'Fitness Prom':>12} | {'Desv. Std':>12} | {'Tiempo Gen (s)':>13}"
    )
    print("-" * 110)


def _imprimir_fila_generacion(gen, stats):
    """Imprime una fila tabulada de métricas por generación."""
    print(
        f"{gen:>3} | {stats['fitness_max']:>12.8f} | {stats['fitness_min']:>12.8f} | "
        f"{stats['fitness_prom']:>12.8f} | {stats['desv_std']:>12.8f} | {stats['tiempo_gen_seg']:>13.6f}"
    )


def _imprimir_resultado_metodo(resultado_final):
    """Imprime el resumen final para un método de selección."""
    print("-" * 110)
    print("RESULTADO FINAL DEL METODO")
    print(f"Mejor fitness global         : {resultado_final['mejor_fitness']:.10f}")
    print(f"Tiempo total estimado (min)  : {resultado_final['tiempo_total_estimado']}")
    print(f"Backlog estimado             : {resultado_final['backlog']}")
    print(f"Desbalance de carga          : {resultado_final['desbalance']:.4f}")
    print(f"Tiempo ejecución método (s)  : {resultado_final['tiempo_ejecucion_total_seg']:.4f}")
    print("=" * 110)


def evolucionar(alertas, metodo="ruleta"):
    """Evoluciona una población usando el método de selección indicado."""
    poblacion = generar_poblacion()
    historial: List[Dict[str, float | int | str]] = []

    mejor_global = None
    mejor_eval = None

    inicio_total = time.time()

    _imprimir_encabezado_metodo(metodo)

    for gen in range(1, N_GENERACIONES + 1):
        inicio_gen = time.time()

        evaluaciones = [_evaluar_cromosoma(ind, alertas) for ind in poblacion]
        fitnesses = [ev["fitness"] for ev in evaluaciones]

        idx_mejor = int(np.argmax(fitnesses))
        if mejor_eval is None or fitnesses[idx_mejor] > mejor_eval["fitness"]:
            mejor_global = poblacion[idx_mejor][:]
            mejor_eval = evaluaciones[idx_mejor]

        nueva_poblacion = []
        if metodo == "elitismo":
            nueva_poblacion.extend(seleccion_elitismo(poblacion, fitnesses, elite_size=ELITE_SIZE))

        while len(nueva_poblacion) < TAM_POBLACION:
            padre1 = _seleccionar_padre(metodo, poblacion, fitnesses)
            padre2 = _seleccionar_padre(metodo, poblacion, fitnesses)
            hijo1, hijo2 = crossover(padre1, padre2)
            hijo1 = mutacion(hijo1)
            hijo2 = mutacion(hijo2)

            nueva_poblacion.append(hijo1)
            if len(nueva_poblacion) < TAM_POBLACION:
                nueva_poblacion.append(hijo2)

        poblacion = nueva_poblacion[:TAM_POBLACION]
        tiempo_gen = time.time() - inicio_gen
        stats = calcular_estadisticas(fitnesses, tiempo_gen)
        stats["generacion"] = gen
        stats["metodo"] = metodo
        historial.append(stats)

        _imprimir_fila_generacion(gen, stats)

    tiempo_total = time.time() - inicio_total

    asignaciones = np.bincount(mejor_global, minlength=N_ANALISTAS)
    resultado_final = {
        "metodo": metodo,
        "mejor_cromosoma": mejor_global,
        "mejor_fitness": mejor_eval["fitness"],
        "tiempo_total_estimado": mejor_eval["tiempo_total"],
        "carga_por_analista": mejor_eval["cargas"],
        "distribucion_alertas": asignaciones.tolist(),
        "backlog": mejor_eval["backlog"],
        "desbalance": mejor_eval["desbalance"],
        "tiempo_ejecucion_total_seg": tiempo_total,
    }

    _imprimir_resultado_metodo(resultado_final)

    return pd.DataFrame(historial), resultado_final


def _graficar_metricas(df_metricas):
    """Genera gráficos obligatorios de métricas y comparación de métodos."""
    for metrica, archivo, titulo in METRICAS_GRAFICOS:
        plt.figure(figsize=(10, 6))
        for metodo, grupo in df_metricas.groupby("metodo"):
            plt.plot(grupo["generacion"], grupo[metrica], marker="o", label=metodo.capitalize())
        plt.title(titulo)
        plt.xlabel("Generación")
        plt.ylabel(metrica)
        plt.grid(True, linestyle="--", alpha=0.45)
        plt.legend()
        plt.tight_layout()
        plt.savefig(archivo, dpi=200)
        plt.close()

    plt.figure(figsize=(10, 6))
    for metodo, grupo in df_metricas.groupby("metodo"):
        plt.plot(grupo["generacion"], grupo["fitness_prom"], marker="o", linewidth=2, label=metodo.capitalize())
    plt.title("Comparación de Estrategias: Ruleta vs Torneo vs Elitismo")
    plt.xlabel("Generación")
    plt.ylabel("Fitness Promedio")
    plt.grid(True, linestyle="--", alpha=0.45)
    plt.legend()
    plt.tight_layout()
    plt.savefig("comparacion_metodos.png", dpi=200)
    plt.close()


def _construir_resumen_resultados(resultados):
    """Construye un DataFrame resumen con métricas finales por método."""
    return pd.DataFrame(
        [
            {
                "metodo": r["metodo"],
                "mejor_fitness": r["mejor_fitness"],
                "tiempo_total_estimado": r["tiempo_total_estimado"],
                "backlog": r["backlog"],
                "desbalance": r["desbalance"],
                "tiempo_ejecucion_total_seg": r["tiempo_ejecucion_total_seg"],
            }
            for r in resultados
        ]
    )


def _imprimir_resumen_global(df_resumen, mejor_global):
    """Imprime resumen consolidado y mejor solución global."""
    print("\n" + "=" * 110)
    print("RESUMEN TABULADO POR MÉTODO")
    print("=" * 110)
    print(df_resumen.to_string(index=False))

    print("\n" + "=" * 110)
    print("MEJOR SOLUCIÓN GLOBAL")
    print("=" * 110)
    print(f"Método ganador              : {mejor_global['metodo']}")
    print(f"Mejor fitness global        : {mejor_global['mejor_fitness']:.10f}")
    print(f"Tiempo total estimado (min) : {mejor_global['tiempo_total_estimado']}")
    print(f"Backlog                     : {mejor_global['backlog']}")
    print(f"Carga por analista (min)    : {mejor_global['carga_por_analista']}")
    print(f"Distribución de alertas     : {mejor_global['distribucion_alertas']}")
    print(f"Mejor cromosoma (primeros 60 genes): {mejor_global['mejor_cromosoma'][:60]}")
    print("\nArchivos exportados:")
    for archivo in ARCHIVOS_EXPORTADOS:
        print(f"- {archivo}")


def main():
    """Orquesta la simulación completa y exporta resultados para informe académico."""
    random.seed(SEED)
    np.random.seed(SEED)

    alertas = generar_alertas()
    tablas: List[pd.DataFrame] = []
    resultados: List[Dict[str, object]] = []

    for metodo in METODOS:
        df_metodo, resultado = evolucionar(alertas, metodo=metodo)
        tablas.append(df_metodo)
        resultados.append(resultado)

    df_metricas = pd.concat(tablas, ignore_index=True)
    df_metricas.to_csv("metricas_generacionales_soc.csv", index=False)

    df_resumen = _construir_resumen_resultados(resultados)
    df_resumen.to_csv("resumen_resultados_soc.csv", index=False)

    _graficar_metricas(df_metricas)

    mejor_global = max(resultados, key=lambda r: r["mejor_fitness"])

    _imprimir_resumen_global(df_resumen, mejor_global)


if __name__ == "__main__":
    main()
