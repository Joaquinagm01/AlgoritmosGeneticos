"""
Trabajo Práctico N° 1 - Algoritmo Genético Canónico
Materia: Inteligencia Artificial

Objetivo: maximizar f(x) = (x / coef)^2 en el dominio [0, 2^30 - 1]
donde coef = 2^30 - 1.

Codificación: binaria de 30 bits.
"""

import random
import shutil
import statistics
import time
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# =========================
# Parámetros del Algoritmo
# =========================
TAM_POBLACION = 10
N_GENERACIONES = 20
P_CROSSOVER = 0.75
P_MUTACION = 0.05
N_BITS = 30
COEF = (2 ** N_BITS) - 1  # 2^30 - 1 = 1,073,741,823
TORNEO_K = 3
ELITE_SIZE = 2
SEED = 42

# Variantes de corridas
VARIANTES_GENERACIONES = [20, 100, 200]
REPETICIONES_POR_CONFIG = 3

METODOS = ["ruleta", "torneo", "elitismo"]

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = BASE_DIR / "outputs"
FIGURES_DIR = OUTPUTS_DIR / "figures"
DOCS_DIR = BASE_DIR / "docs"
DOCS_FIGURES_DIR = DOCS_DIR / "assets" / "figures"

# Archivos de salida
METRICS_CSV = OUTPUTS_DIR / "metricas_generacionales.csv"
SUMMARY_CSV = OUTPUTS_DIR / "resumen_resultados.csv"

ARCHIVOS_EXPORTADOS = [
    METRICS_CSV,
    SUMMARY_CSV,
    OUTPUTS_DIR / "resumen_variantes_generaciones.csv",
    OUTPUTS_DIR / "experimentos_repetidos.csv",
    OUTPUTS_DIR / "tabla_mins_prom_maxs_por_configuracion.csv",
    OUTPUTS_DIR / "metricas_variantes_generaciones.csv",
    OUTPUTS_DIR / "tabla_estabilidad_tiempos.csv",
    OUTPUTS_DIR / "experimentos_adicionales.csv",
    FIGURES_DIR / "maximos_por_generacion.png",
    FIGURES_DIR / "promedios_por_generacion.png",
    FIGURES_DIR / "minimos_por_generacion.png",
    FIGURES_DIR / "desviacion_estandar_por_generacion.png",
    FIGURES_DIR / "comparacion_metodos.png",
    FIGURES_DIR / "comparativa_20_fitness_max.png",
    FIGURES_DIR / "comparativa_20_fitness_min.png",
    FIGURES_DIR / "comparativa_20_fitness_prom.png",
    FIGURES_DIR / "comparativa_100_fitness_max.png",
    FIGURES_DIR / "comparativa_100_fitness_min.png",
    FIGURES_DIR / "comparativa_100_fitness_prom.png",
    FIGURES_DIR / "comparativa_200_fitness_max.png",
    FIGURES_DIR / "comparativa_200_fitness_min.png",
    FIGURES_DIR / "comparativa_200_fitness_prom.png",
    FIGURES_DIR / "comparativa_20_iteraciones.png",
    FIGURES_DIR / "comparativa_100_iteraciones.png",
    FIGURES_DIR / "comparativa_200_iteraciones.png",
]

METRICAS_GRAFICOS = [
    ("fitness_max", FIGURES_DIR / "maximos_por_generacion.png", "Fitness Máximo por Generación"),
    ("fitness_prom", FIGURES_DIR / "promedios_por_generacion.png", "Fitness Promedio por Generación"),
    ("fitness_min", FIGURES_DIR / "minimos_por_generacion.png", "Fitness Mínimo por Generación"),
    ("desv_std", FIGURES_DIR / "desviacion_estandar_por_generacion.png", "Desviación Estándar por Generación"),
]

Chromosome = List[int]
Population = List[Chromosome]


def funcion_objetivo(x: int) -> float:
    """f(x) = (x / coef)^2"""
    return (x / COEF) ** 2


def binario_a_entero(cromosoma: Chromosome) -> int:
    """Convierte un cromosoma binario a entero."""
    valor = 0
    for bit in cromosoma:
        valor = (valor << 1) | bit
    return valor


def generar_poblacion(tam_poblacion: int = TAM_POBLACION, n_bits: int = N_BITS) -> Population:
    """Genera población inicial aleatoria de cromosomas binarios."""
    return [[random.randint(0, 1) for _ in range(n_bits)] for _ in range(tam_poblacion)]


def calcular_fitness_poblacion(poblacion: Population) -> List[float]:
    """Calcula el fitness de cada individuo en la población."""
    return [funcion_objetivo(binario_a_entero(ind)) for ind in poblacion]


def seleccion_ruleta(poblacion: Population, fitnesses: List[float]) -> Chromosome:
    """Selección proporcional (ruleta)."""
    total = sum(fitnesses)
    if total <= 0:
        return random.choice(poblacion)[:]

    r = random.uniform(0, total)
    acumulado = 0.0
    for individuo, fit in zip(poblacion, fitnesses):
        acumulado += fit
        if acumulado >= r:
            return individuo[:]
    return poblacion[-1][:]


def seleccion_torneo(poblacion: Population, fitnesses: List[float], k: int = TORNEO_K) -> Chromosome:
    """Selección por torneo de tamaño k."""
    indices = random.sample(range(len(poblacion)), k=min(k, len(poblacion)))
    mejor_idx = max(indices, key=lambda i: fitnesses[i])
    return poblacion[mejor_idx][:]


def seleccion_elitismo(poblacion: Population, fitnesses: List[float], elite_size: int = ELITE_SIZE) -> List[Chromosome]:
    """Retorna los mejores individuos (élite) para preservarlos."""
    orden = sorted(range(len(poblacion)), key=lambda i: fitnesses[i], reverse=True)
    return [poblacion[i][:] for i in orden[:elite_size]]


def crossover(padre1: Chromosome, padre2: Chromosome, p_crossover: float = P_CROSSOVER) -> Tuple[Chromosome, Chromosome]:
    """Crossover de 1 punto."""
    if random.random() < p_crossover:
        punto = random.randint(1, len(padre1) - 1)
        hijo1 = padre1[:punto] + padre2[punto:]
        hijo2 = padre2[:punto] + padre1[punto:]
        return hijo1, hijo2
    return padre1[:], padre2[:]


def mutacion(cromosoma: Chromosome, p_mutacion: float = P_MUTACION) -> Chromosome:
    """Mutación invertida: invierte un segmento aleatorio [i, j]."""
    hijo = cromosoma[:]
    if random.random() < p_mutacion:
        i, j = sorted(random.sample(range(len(hijo)), 2))
        hijo[i:j + 1] = list(reversed(hijo[i:j + 1]))
    return hijo


def calcular_estadisticas(fitnesses: List[float], tiempo_gen: float) -> Dict:
    """Calcula estadísticas de una generación."""
    return {
        "fitness_max": max(fitnesses),
        "fitness_min": min(fitnesses),
        "fitness_prom": statistics.fmean(fitnesses),
        "desv_std": statistics.pstdev(fitnesses) if len(fitnesses) > 1 else 0.0,
        "tiempo_gen_seg": tiempo_gen,
    }


def _seleccionar_padre(metodo: str, poblacion: Population, fitnesses: List[float]) -> Chromosome:
    """Selecciona un padre según el método configurado."""
    if metodo in ("ruleta", "elitismo"):
        return seleccion_ruleta(poblacion, fitnesses)
    if metodo == "torneo":
        return seleccion_torneo(poblacion, fitnesses)
    raise ValueError(f"Método no soportado: {metodo}")


def _imprimir_encabezado_metodo(metodo: str):
    """Imprime encabezado de tabla por método."""
    print("=" * 120)
    print(f"METODO: {metodo.upper()}")
    print("=" * 120)
    print(
        f"{'Gen':>4} | {'Fitness Máx':>14} | {'Fitness Mín':>14} | {'Fitness Prom':>14} | "
        f"{'Desv. Std':>14} | {'Tiempo Gen (s)':>14} | {'Mejor x':>12}"
    )
    print("-" * 120)


def _imprimir_fila_generacion(gen: int, stats: Dict, mejor_x: int):
    """Imprime fila de métricas por generación."""
    print(
        f"{gen:>4} | {stats['fitness_max']:>14.10f} | {stats['fitness_min']:>14.10f} | "
        f"{stats['fitness_prom']:>14.10f} | {stats['desv_std']:>14.10f} | "
        f"{stats['tiempo_gen_seg']:>14.8f} | {mejor_x:>12}"
    )


def _imprimir_resultado_metodo(resultado: Dict):
    """Imprime resumen final del método."""
    print("-" * 120)
    print("RESULTADO FINAL DEL METODO")
    print(f"Mejor fitness global         : {resultado['mejor_fitness']:.12f}")
    print(f"Mejor valor de x             : {resultado['mejor_x']}")
    print(f"Cromosoma del mejor          : {''.join(map(str, resultado['mejor_cromosoma']))}")
    print(f"Valor máximo de la población : {resultado['fitness_max_poblacion']:.12f}")
    print(f"Valor mínimo de la población : {resultado['fitness_min_poblacion']:.12f}")
    print(f"Valor promedio de la población: {resultado['fitness_prom_poblacion']:.12f}")
    print(f"Desv. std última generación  : {resultado['desv_std_final']:.12f}")
    print(f"Tiempo ejecución método (s)  : {resultado['tiempo_ejecucion_total_seg']:.6f}")
    print("=" * 120)


def sincronizar_figuras_para_informe():
    """Copia las figuras generadas a la carpeta usada por el informe HTML."""
    DOCS_FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    for archivo_png in FIGURES_DIR.glob("*.png"):
        shutil.copy2(archivo_png, DOCS_FIGURES_DIR / archivo_png.name)


def evolucionar(metodo: str = "ruleta", n_generaciones: int = N_GENERACIONES,
                tam_poblacion: int = TAM_POBLACION, p_crossover: float = P_CROSSOVER,
                p_mutacion: float = P_MUTACION, verbose: bool = True) -> Tuple[pd.DataFrame, Dict]:
    """Evoluciona una población usando el método de selección indicado."""
    poblacion = generar_poblacion(tam_poblacion)
    historial: List[Dict] = []

    mejor_global_cromosoma = None
    mejor_global_fitness = -1.0
    mejor_global_x = -1

    inicio_total = time.time()

    if verbose:
        _imprimir_encabezado_metodo(metodo)

    for gen in range(1, n_generaciones + 1):
        inicio_gen = time.time()

        fitnesses = calcular_fitness_poblacion(poblacion)

        # Actualizar mejor global
        idx_mejor = int(np.argmax(fitnesses))
        if fitnesses[idx_mejor] > mejor_global_fitness:
            mejor_global_fitness = fitnesses[idx_mejor]
            mejor_global_cromosoma = poblacion[idx_mejor][:]
            mejor_global_x = binario_a_entero(mejor_global_cromosoma)

        # Crear nueva población
        nueva_poblacion = []
        if metodo == "elitismo":
            nueva_poblacion.extend(seleccion_elitismo(poblacion, fitnesses, elite_size=ELITE_SIZE))

        while len(nueva_poblacion) < tam_poblacion:
            padre1 = _seleccionar_padre(metodo, poblacion, fitnesses)
            padre2 = _seleccionar_padre(metodo, poblacion, fitnesses)
            hijo1, hijo2 = crossover(padre1, padre2, p_crossover)
            hijo1 = mutacion(hijo1, p_mutacion)
            hijo2 = mutacion(hijo2, p_mutacion)
            nueva_poblacion.append(hijo1)
            if len(nueva_poblacion) < tam_poblacion:
                nueva_poblacion.append(hijo2)

        poblacion = nueva_poblacion[:tam_poblacion]
        tiempo_gen = time.time() - inicio_gen
        stats = calcular_estadisticas(fitnesses, tiempo_gen)
        stats["generacion"] = gen
        stats["metodo"] = metodo
        stats["n_generaciones"] = n_generaciones
        stats["tam_poblacion"] = tam_poblacion
        stats["mejor_x"] = mejor_global_x
        historial.append(stats)

        if verbose:
            _imprimir_fila_generacion(gen, stats, mejor_global_x)

    tiempo_total = time.time() - inicio_total

    # Estadísticas de la última generación
    fitnesses_final = calcular_fitness_poblacion(poblacion)

    resultado = {
        "metodo": metodo,
        "n_generaciones": n_generaciones,
        "tam_poblacion": tam_poblacion,
        "p_crossover": p_crossover,
        "p_mutacion": p_mutacion,
        "mejor_cromosoma": mejor_global_cromosoma,
        "mejor_fitness": mejor_global_fitness,
        "mejor_x": mejor_global_x,
        "fitness_max_poblacion": max(fitnesses_final),
        "fitness_min_poblacion": min(fitnesses_final),
        "fitness_prom_poblacion": statistics.fmean(fitnesses_final),
        "desv_std_final": statistics.pstdev(fitnesses_final) if len(fitnesses_final) > 1 else 0.0,
        "tiempo_ejecucion_total_seg": tiempo_total,
    }

    if verbose:
        _imprimir_resultado_metodo(resultado)

    return pd.DataFrame(historial), resultado


def ejecutar_bateria_experimentos() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Ejecuta batería de 20, 100 y 200 generaciones por cada método."""
    filas_metricas = []
    filas_resumen = []
    filas_repetidos = []

    for n_generaciones in VARIANTES_GENERACIONES:
        for metodo in METODOS:
            for repeticion in range(1, REPETICIONES_POR_CONFIG + 1):
                random.seed(SEED + n_generaciones + repeticion)
                np.random.seed(SEED + n_generaciones + repeticion)

                df_historial, resultado = evolucionar(
                    metodo=metodo,
                    n_generaciones=n_generaciones,
                    tam_poblacion=TAM_POBLACION,
                    verbose=False,
                )

                df_historial["repeticion"] = repeticion
                filas_metricas.append(df_historial)

                # Encontrar generación donde se alcanzó el mejor fitness
                gen_mejor = int(df_historial.loc[df_historial["fitness_max"].idxmax(), "generacion"])

                filas_repetidos.append({
                    "n_generaciones": n_generaciones,
                    "metodo": metodo,
                    "repeticion": repeticion,
                    "mejor_fitness": resultado["mejor_fitness"],
                    "generacion_mejor_fitness": gen_mejor,
                    "mejor_x": resultado["mejor_x"],
                    "tiempo_ejecucion_seg": resultado["tiempo_ejecucion_total_seg"],
                })

                filas_resumen.append({
                    "n_generaciones": n_generaciones,
                    "metodo": metodo,
                    "repeticion": repeticion,
                    "mejor_fitness": resultado["mejor_fitness"],
                    "generacion_mejor_fitness": gen_mejor,
                    "mejor_x": resultado["mejor_x"],
                    "estabilidad_desv_prom": float(df_historial["fitness_prom"].std()),
                    "tiempo_ejecucion_seg": resultado["tiempo_ejecucion_total_seg"],
                })

    df_metricas_variantes = pd.concat(filas_metricas, ignore_index=True)
    df_repetidos = pd.DataFrame(filas_repetidos)
    df_resumen_variantes = pd.DataFrame(filas_resumen)

    return df_metricas_variantes, df_repetidos, df_resumen_variantes


def ejecutar_experimentos_adicionales() -> pd.DataFrame:
    """Ejecuta experimentos con parámetros modificados."""
    configs = [
        {"metodo": "ruleta", "tam_poblacion": 20, "p_mutacion": 0.05, "label": "Ruleta, Pobl=20"},
        {"metodo": "ruleta", "tam_poblacion": 10, "p_mutacion": 0.10, "label": "Ruleta, Pmut=0.10"},
        {"metodo": "torneo", "tam_poblacion": 20, "p_mutacion": 0.05, "label": "Torneo, Pobl=20"},
        {"metodo": "torneo", "tam_poblacion": 10, "p_mutacion": 0.10, "label": "Torneo, Pmut=0.10"},
        {"metodo": "elitismo", "tam_poblacion": 20, "p_mutacion": 0.05, "label": "Elitismo, Pobl=20"},
        {"metodo": "elitismo", "tam_poblacion": 10, "p_mutacion": 0.10, "label": "Elitismo, Pmut=0.10"},
        {"metodo": "ruleta", "tam_poblacion": 10, "p_mutacion": 0.01, "label": "Ruleta, Pmut=0.01"},
        {"metodo": "elitismo", "tam_poblacion": 10, "p_mutacion": 0.01, "label": "Elitismo, Pmut=0.01"},
    ]

    filas = []
    for cfg in configs:
        random.seed(SEED + hash(cfg["label"]) % 10000)
        np.random.seed(SEED + hash(cfg["label"]) % 10000)
        _, resultado = evolucionar(
            metodo=cfg["metodo"],
            n_generaciones=100,
            tam_poblacion=cfg["tam_poblacion"],
            p_mutacion=cfg["p_mutacion"],
            verbose=False,
        )
        filas.append({
            "configuracion": cfg["label"],
            "metodo": cfg["metodo"],
            "tam_poblacion": cfg["tam_poblacion"],
            "p_mutacion": cfg["p_mutacion"],
            "mejor_fitness": resultado["mejor_fitness"],
            "mejor_x": resultado["mejor_x"],
            "tiempo_ejecucion_seg": resultado["tiempo_ejecucion_total_seg"],
        })

    return pd.DataFrame(filas)


def _graficar_metricas(df_metricas: pd.DataFrame):
    """Genera gráficos de métricas por generación."""
    for metrica, archivo, titulo in METRICAS_GRAFICOS:
        plt.figure(figsize=(10, 6))
        for metodo, grupo in df_metricas.groupby("metodo"):
            plt.plot(grupo["generacion"], grupo[metrica], marker="o", label=metodo.capitalize())
        plt.title(titulo)
        plt.xlabel("Generación")
        plt.ylabel(metrica.replace("_", " ").title())
        plt.grid(True, linestyle="--", alpha=0.45)
        plt.legend()
        plt.tight_layout()
        plt.savefig(archivo, dpi=200)
        plt.close()

    # Gráfico comparativo de métodos (fitness promedio)
    plt.figure(figsize=(10, 6))
    for metodo, grupo in df_metricas.groupby("metodo"):
        plt.plot(grupo["generacion"], grupo["fitness_prom"], marker="o", linewidth=2, label=metodo.capitalize())
    plt.title("Comparación de Estrategias: Ruleta vs Torneo vs Elitismo")
    plt.xlabel("Generación")
    plt.ylabel("Fitness Promedio")
    plt.grid(True, linestyle="--", alpha=0.45)
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "comparacion_metodos.png", dpi=200)
    plt.close()


def _graficar_por_variantes(df_variantes: pd.DataFrame):
    """Genera una gráfica por cada conjunto de iteraciones (20, 100, 200)."""
    for n_generaciones, grupo_variantes in df_variantes.groupby("n_generaciones"):
        for metrica, sufijo, titulo_metrica in [
            ("fitness_max", "fitness_max", "Fitness máximo"),
            ("fitness_min", "fitness_min", "Fitness mínimo"),
            ("fitness_prom", "fitness_prom", "Fitness promedio"),
        ]:
            plt.figure(figsize=(10, 6))
            for metodo, grupo in grupo_variantes.groupby("metodo"):
                promedio_por_gen = grupo.groupby("generacion")[metrica].mean().reset_index()
                plt.plot(
                    promedio_por_gen["generacion"],
                    promedio_por_gen[metrica],
                    marker="o",
                    label=metodo.capitalize(),
                )
            plt.title(f"{titulo_metrica} por generación - {n_generaciones} iteraciones")
            plt.xlabel("Generación")
            plt.ylabel(titulo_metrica)
            plt.grid(True, linestyle="--", alpha=0.45)
            plt.legend()
            plt.tight_layout()
            plt.savefig(FIGURES_DIR / f"comparativa_{n_generaciones}_{sufijo}.png", dpi=200)
            plt.close()

        plt.figure(figsize=(10, 6))
        for metodo, grupo in grupo_variantes.groupby("metodo"):
            # Promediamos por generación entre repeticiones
            promedio_por_gen = grupo.groupby("generacion")["fitness_prom"].mean().reset_index()
            plt.plot(promedio_por_gen["generacion"], promedio_por_gen["fitness_prom"],
                     marker="o", label=metodo.capitalize())
        plt.title(f"Fitness promedio por generación - {n_generaciones} iteraciones")
        plt.xlabel("Generación")
        plt.ylabel("Fitness Promedio")
        plt.grid(True, linestyle="--", alpha=0.45)
        plt.legend()
        plt.tight_layout()
        plt.savefig(FIGURES_DIR / f"comparativa_{n_generaciones}_iteraciones.png", dpi=200)
        plt.close()


def _imprimir_resumen_global(df_resumen: pd.DataFrame, mejor_global: Dict):
    """Imprime resumen consolidado."""
    print("\n" + "=" * 120)
    print("RESUMEN TABULADO POR MÉTODO (20 generaciones)")
    print("=" * 120)
    print(df_resumen.to_string(index=False))

    print("\n" + "=" * 120)
    print("MEJOR SOLUCIÓN GLOBAL")
    print("=" * 120)
    print(f"Método ganador              : {mejor_global['metodo']}")
    print(f"Mejor fitness global        : {mejor_global['mejor_fitness']:.12f}")
    print(f"Mejor valor de x            : {mejor_global['mejor_x']}")
    print(f"Cromosoma (30 bits)         : {''.join(map(str, mejor_global['mejor_cromosoma']))}")
    print(f"Valor máximo población final: {mejor_global['fitness_max_poblacion']:.12f}")
    print(f"Valor mínimo población final: {mejor_global['fitness_min_poblacion']:.12f}")
    print(f"Valor promedio población final: {mejor_global['fitness_prom_poblacion']:.12f}")
    print(f"Desv. std población final   : {mejor_global['desv_std_final']:.12f}")


def _imprimir_resumen_variantes(df_resumen_variantes: pd.DataFrame, df_repetidos: pd.DataFrame):
    """Imprime tablas de resumen para variantes."""
    print("\n" + "=" * 120)
    print("RESUMEN POR VARIANTE Y METODO (20, 100, 200 generaciones)")
    print("=" * 120)

    # Tabla de mins, proms, maxs por configuración
    tabla_agg = df_resumen_variantes.groupby(["n_generaciones", "metodo"]).agg(
        mejor_fitness_promedio=("mejor_fitness", "mean"),
        mejor_fitness_max=("mejor_fitness", "max"),
        mejor_fitness_min=("mejor_fitness", "min"),
        tiempo_ejecucion_promedio_seg=("tiempo_ejecucion_seg", "mean"),
        generacion_mejor_fitness_promedio=("generacion_mejor_fitness", "mean"),
    ).reset_index()
    print(tabla_agg.to_string(index=False))

    print("\n" + "=" * 120)
    print("TIEMPO PROMEDIO DE EJECUCION POR CONFIGURACION")
    print("=" * 120)
    tiempo_prom = (
        df_repetidos.groupby(["n_generaciones", "metodo"])["tiempo_ejecucion_seg"]
        .mean()
        .reset_index()
        .sort_values(["n_generaciones", "metodo"])
    )
    print(tiempo_prom.to_string(index=False))

    print("\n" + "=" * 120)
    print("TABLA DE ESTABILIDAD Y TIEMPOS")
    print("=" * 120)
    estabilidad = (
        df_repetidos.groupby(["n_generaciones", "metodo"])
        .agg(
            mejor_fitness_mean=("mejor_fitness", "mean"),
            mejor_fitness_std=("mejor_fitness", "std"),
            mejor_x_mean=("mejor_x", "mean"),
            tiempo_mean=("tiempo_ejecucion_seg", "mean"),
            tiempo_std=("tiempo_ejecucion_seg", "std"),
        )
        .reset_index()
    )
    print(estabilidad.to_string(index=False))


def main():
    """Orquesta la simulación completa del AG canónico."""
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    random.seed(SEED)
    np.random.seed(SEED)

    print("=" * 120)
    print("ALGORITMO GENÉTICO CANÓNICO - TP N° 1")
    print(f"Función objetivo: f(x) = (x / {COEF})²  en el dominio [0, {COEF}]")
    print(f"Codificación: Binaria de {N_BITS} bits")
    print("=" * 120)

    # ============================================================
    # Ejecución base: 20 generaciones, los 3 métodos
    # ============================================================
    tablas: List[pd.DataFrame] = []
    resultados: List[Dict] = []

    for metodo in METODOS:
        df_metodo, resultado = evolucionar(metodo=metodo, n_generaciones=N_GENERACIONES)
        tablas.append(df_metodo)
        resultados.append(resultado)

    df_metricas = pd.concat(tablas, ignore_index=True)
    df_metricas.to_csv(METRICS_CSV, index=False)

    df_resumen = pd.DataFrame([
        {
            "metodo": r["metodo"],
            "mejor_fitness": r["mejor_fitness"],
            "mejor_x": r["mejor_x"],
            "fitness_max_final": r["fitness_max_poblacion"],
            "fitness_min_final": r["fitness_min_poblacion"],
            "fitness_prom_final": r["fitness_prom_poblacion"],
            "desv_std_final": r["desv_std_final"],
            "tiempo_ejecucion_total_seg": r["tiempo_ejecucion_total_seg"],
        }
        for r in resultados
    ])
    df_resumen.to_csv(SUMMARY_CSV, index=False)

    _graficar_metricas(df_metricas)

    # ============================================================
    # Batería de experimentos: 20, 100, 200 generaciones
    # ============================================================
    print("\n" + "=" * 120)
    print("EJECUTANDO BATERÍA DE EXPERIMENTOS (20, 100, 200 generaciones)")
    print("=" * 120)

    df_metricas_variantes, df_repetidos, df_resumen_variantes = ejecutar_bateria_experimentos()
    df_metricas_variantes.to_csv(OUTPUTS_DIR / "metricas_variantes_generaciones.csv", index=False)
    df_repetidos.to_csv(OUTPUTS_DIR / "experimentos_repetidos.csv", index=False)
    df_resumen_variantes.to_csv(OUTPUTS_DIR / "resumen_variantes_generaciones.csv", index=False)

    tabla_agg = df_resumen_variantes.groupby(["n_generaciones", "metodo"]).agg(
        mejor_fitness_promedio=("mejor_fitness", "mean"),
        mejor_fitness_max=("mejor_fitness", "max"),
        mejor_fitness_min=("mejor_fitness", "min"),
        tiempo_ejecucion_promedio_seg=("tiempo_ejecucion_seg", "mean"),
        generacion_mejor_fitness_promedio=("generacion_mejor_fitness", "mean"),
    ).reset_index()
    tabla_agg.to_csv(OUTPUTS_DIR / "tabla_mins_prom_maxs_por_configuracion.csv", index=False)

    # Tabla de estabilidad y tiempos
    estabilidad = (
        df_repetidos.groupby(["n_generaciones", "metodo"])
        .agg(
            mejor_fitness_mean=("mejor_fitness", "mean"),
            mejor_fitness_std=("mejor_fitness", "std"),
            mejor_x_mean=("mejor_x", "mean"),
            tiempo_mean=("tiempo_ejecucion_seg", "mean"),
            tiempo_std=("tiempo_ejecucion_seg", "std"),
        )
        .reset_index()
    )
    estabilidad.to_csv(OUTPUTS_DIR / "tabla_estabilidad_tiempos.csv", index=False)

    _graficar_por_variantes(df_metricas_variantes)
    sincronizar_figuras_para_informe()

    # ============================================================
    # Experimentos adicionales (cambio de parámetros)
    # ============================================================
    print("\n" + "=" * 120)
    print("EXPERIMENTOS ADICIONALES (cambio de parámetros)")
    print("=" * 120)

    df_exp_adicionales = ejecutar_experimentos_adicionales()
    df_exp_adicionales.to_csv(OUTPUTS_DIR / "experimentos_adicionales.csv", index=False)
    print(df_exp_adicionales.to_string(index=False))

    # ============================================================
    # Resúmenes finales
    # ============================================================
    mejor_global = max(resultados, key=lambda r: r["mejor_fitness"])
    _imprimir_resumen_global(df_resumen, mejor_global)
    _imprimir_resumen_variantes(df_resumen_variantes, df_repetidos)

    print("\n" + "=" * 120)
    print("ARCHIVOS EXPORTADOS")
    print("=" * 120)
    for archivo in ARCHIVOS_EXPORTADOS:
        if archivo.exists():
            print(f"✓ {archivo.relative_to(BASE_DIR)}")
        else:
            print(f"✗ {archivo.relative_to(BASE_DIR)} (NO GENERADO)")

    print("\n" + "=" * 120)
    print("EJECUCIÓN COMPLETADA")
    print("=" * 120)


if __name__ == "__main__":
    main()
