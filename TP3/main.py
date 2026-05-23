"""Problema del viajante aplicado a las capitales provinciales de Argentina.

El programa resuelve el problema mediante:
- una heurística de vecino más cercano desde una capital elegida por el usuario,
- la misma heurística probando todos los inicios posibles,
- un algoritmo genético sobre permutaciones con crossover cíclico.

También calcula el costo teórico del enfoque exhaustivo para justificar por qué
no resulta viable sobre las 23 capitales provinciales.
"""

from __future__ import annotations

import itertools
import math
import random
import shutil
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# =========================
# Configuracion general
# =========================
SEED = 42
N_CROMOSOMAS = 50
N_CICLOS = 200
P_CROSSOVER = 0.85
P_MUTACION = 0.12
TORNEO_K = 3
ELITE_SIZE = 2

BASE_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = BASE_DIR / "outputs"
FIGURES_DIR = OUTPUTS_DIR / "figures"
DOCS_DIR = BASE_DIR / "docs"
DOCS_FIGURES_DIR = DOCS_DIR / "assets" / "figures"

HEURISTICA_CSV = OUTPUTS_DIR / "resumen_heuristica.csv"
GA_CSV = OUTPUTS_DIR / "resumen_ag.csv"


@dataclass(frozen=True)
class Ciudad:
    provincia: str
    capital: str
    latitud: float
    longitud: float


CIUDADES: List[Ciudad] = [
    Ciudad("Buenos Aires", "La Plata", -34.9214, -57.9544),
    Ciudad("Catamarca", "San Fernando del Valle de Catamarca", -28.4696, -65.7795),
    Ciudad("Chaco", "Resistencia", -27.4516, -58.9867),
    Ciudad("Chubut", "Rawson", -43.3002, -65.1023),
    Ciudad("Córdoba", "Córdoba", -31.4201, -64.1888),
    Ciudad("Corrientes", "Corrientes", -27.4692, -58.8306),
    Ciudad("Entre Ríos", "Paraná", -31.7319, -60.5238),
    Ciudad("Formosa", "Formosa", -26.1850, -58.1731),
    Ciudad("Jujuy", "San Salvador de Jujuy", -24.1858, -65.2995),
    Ciudad("La Pampa", "Santa Rosa", -36.6203, -64.2906),
    Ciudad("La Rioja", "La Rioja", -29.4131, -66.8568),
    Ciudad("Mendoza", "Mendoza", -32.8895, -68.8458),
    Ciudad("Misiones", "Posadas", -27.3621, -55.9006),
    Ciudad("Neuquén", "Neuquén", -38.9516, -68.0591),
    Ciudad("Río Negro", "Viedma", -40.8135, -63.0000),
    Ciudad("Salta", "Salta", -24.7821, -65.4232),
    Ciudad("San Juan", "San Juan", -31.5375, -68.5364),
    Ciudad("San Luis", "San Luis", -33.3017, -66.3378),
    Ciudad("Santa Cruz", "Río Gallegos", -51.6230, -69.2168),
    Ciudad("Santa Fe", "Santa Fe", -31.6333, -60.7000),
    Ciudad("Santiago del Estero", "Santiago del Estero", -27.7844, -64.2667),
    Ciudad("Tierra del Fuego", "Ushuaia", -54.8019, -68.3030),
    Ciudad("Tucumán", "San Miguel de Tucumán", -26.8083, -65.2176),
]

PROVINCIA_A_CIUDAD = {ciudad.provincia.lower(): ciudad for ciudad in CIUDADES}
CAPITAL_A_CIUDAD = {ciudad.capital.lower(): ciudad for ciudad in CIUDADES}
N_CIUDADES = len(CIUDADES)


# =========================
# Utilidades de geometria
# =========================

def _normalizar(texto: str) -> str:
    return " ".join(texto.strip().lower().split())


def _nombre_ciudad(ciudad_idx: int) -> str:
    return CIUDADES[ciudad_idx].capital


def _nombre_provincia(ciudad_idx: int) -> str:
    return CIUDADES[ciudad_idx].provincia


def obtener_ciudad_por_entrada(texto: str) -> Ciudad:
    clave = _normalizar(texto)
    if clave in PROVINCIA_A_CIUDAD:
        return PROVINCIA_A_CIUDAD[clave]
    if clave in CAPITAL_A_CIUDAD:
        return CAPITAL_A_CIUDAD[clave]
    raise ValueError(f"No se reconoció la provincia o capital: {texto}")


def distancia_haversine(ciudad_a: Ciudad, ciudad_b: Ciudad) -> float:
    """Calcula la distancia geodésica aproximada en kilómetros."""
    radio_tierra = 6371.0
    lat1 = math.radians(ciudad_a.latitud)
    lon1 = math.radians(ciudad_a.longitud)
    lat2 = math.radians(ciudad_b.latitud)
    lon2 = math.radians(ciudad_b.longitud)

    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return radio_tierra * c


def construir_matriz_distancias() -> np.ndarray:
    matriz = np.zeros((N_CIUDADES, N_CIUDADES), dtype=float)
    for i, ciudad_a in enumerate(CIUDADES):
        for j, ciudad_b in enumerate(CIUDADES):
            if i == j:
                continue
            matriz[i, j] = distancia_haversine(ciudad_a, ciudad_b)
    return matriz


MATRIZ_DISTANCIAS = construir_matriz_distancias()


# =========================
# Representacion de rutas
# =========================

def ruta_distancia(ruta: Sequence[int]) -> float:
    total = 0.0
    for i in range(len(ruta) - 1):
        total += MATRIZ_DISTANCIAS[ruta[i], ruta[i + 1]]
    total += MATRIZ_DISTANCIAS[ruta[-1], ruta[0]]
    return total


def ruta_a_texto(ruta: Sequence[int]) -> str:
    nombres = [f"{_nombre_ciudad(idx)} ({_nombre_provincia(idx)})" for idx in ruta]
    nombres.append(f"{_nombre_ciudad(ruta[0])} ({_nombre_provincia(ruta[0])})")
    return " -> ".join(nombres)


def indice_ciudad_desde_texto(texto: str) -> int:
    ciudad = obtener_ciudad_por_entrada(texto)
    return CIUDADES.index(ciudad)


def mostrar_ciudades_disponibles() -> None:
    print("Capitales provinciales disponibles:")
    for idx, ciudad in enumerate(CIUDADES, start=1):
        print(f"{idx:>2}. {ciudad.provincia} - {ciudad.capital}")


# =========================
# Heuristica de vecino mas cercano
# =========================

def heuristica_vecino_mas_cercano(inicio: int) -> List[int]:
    ruta = [inicio]
    no_visitadas = set(range(N_CIUDADES))
    no_visitadas.remove(inicio)

    actual = inicio
    while no_visitadas:
        siguiente = min(no_visitadas, key=lambda idx: MATRIZ_DISTANCIAS[actual, idx])
        ruta.append(siguiente)
        no_visitadas.remove(siguiente)
        actual = siguiente
    return ruta


def mejor_heuristica_global() -> Tuple[int, List[int], float]:
    mejor_inicio = 0
    mejor_ruta = heuristica_vecino_mas_cercano(0)
    mejor_distancia = ruta_distancia(mejor_ruta)

    for inicio in range(1, N_CIUDADES):
        ruta = heuristica_vecino_mas_cercano(inicio)
        distancia = ruta_distancia(ruta)
        if distancia < mejor_distancia:
            mejor_inicio = inicio
            mejor_ruta = ruta
            mejor_distancia = distancia

    return mejor_inicio, mejor_ruta, mejor_distancia


# =========================
# Analisis exhaustivo
# =========================

def analisis_exhaustivo_teorico() -> Dict[str, float]:
    """Devuelve una estimacion teorica del costo de resolver el TSP exhaustivamente."""
    rutas_con_inicio_fijo = math.factorial(N_CIUDADES - 1)
    rutas_si_se_aprovecha_simetria = math.factorial(N_CIUDADES - 1) / 2
    evaluaciones_por_segundo = 1_000_000
    segundos_estimados = rutas_si_se_aprovecha_simetria / evaluaciones_por_segundo
    años_estimados = segundos_estimados / (60 * 60 * 24 * 365)
    return {
        "rutas_con_inicio_fijo": float(rutas_con_inicio_fijo),
        "rutas_si_se_aprovecha_simetria": float(rutas_si_se_aprovecha_simetria),
        "años_estimados_a_1e6_eval_s": float(años_estimados),
    }


# =========================
# Algoritmo genetico
# =========================

def generar_poblacion(tam_poblacion: int = N_CROMOSOMAS) -> List[List[int]]:
    base = list(range(N_CIUDADES))
    poblacion = []
    for _ in range(tam_poblacion):
        individuo = base[:]
        random.shuffle(individuo)
        poblacion.append(individuo)
    return poblacion


def seleccionar_ruleta(poblacion: Sequence[Sequence[int]], fitnesses: Sequence[float]) -> List[int]:
    total = float(sum(fitnesses))
    if total <= 0:
        return list(random.choice(poblacion))
    objetivo = random.uniform(0, total)
    acumulado = 0.0
    for individuo, fitness in zip(poblacion, fitnesses):
        acumulado += fitness
        if acumulado >= objetivo:
            return list(individuo)
    return list(poblacion[-1])


def seleccionar_torneo(poblacion: Sequence[Sequence[int]], fitnesses: Sequence[float], k: int = TORNEO_K) -> List[int]:
    cantidad = min(k, len(poblacion))
    indices = random.sample(range(len(poblacion)), cantidad)
    mejor_indice = max(indices, key=lambda idx: fitnesses[idx])
    return list(poblacion[mejor_indice])


def seleccionar_elitismo(poblacion: Sequence[Sequence[int]], fitnesses: Sequence[float], elite_size: int = ELITE_SIZE) -> List[List[int]]:
    orden = sorted(range(len(poblacion)), key=lambda idx: fitnesses[idx], reverse=True)
    return [list(poblacion[idx]) for idx in orden[:elite_size]]


def crossover_ciclico(padre1: Sequence[int], padre2: Sequence[int]) -> Tuple[List[int], List[int]]:
    """Cycle crossover para cromosomas permutacionales."""
    n = len(padre1)
    hijo1 = [None] * n
    hijo2 = [None] * n
    pos_en_padre1 = {gen: idx for idx, gen in enumerate(padre1)}
    visitado = [False] * n
    tomar_padre1 = True

    for inicio in range(n):
        if visitado[inicio]:
            continue
        ciclo = []
        idx = inicio
        while not visitado[idx]:
            visitado[idx] = True
            ciclo.append(idx)
            gen_correspondiente = padre2[idx]
            idx = pos_en_padre1[gen_correspondiente]
        for pos in ciclo:
            if tomar_padre1:
                hijo1[pos] = padre1[pos]
                hijo2[pos] = padre2[pos]
            else:
                hijo1[pos] = padre2[pos]
                hijo2[pos] = padre1[pos]
        tomar_padre1 = not tomar_padre1

    return [int(x) for x in hijo1], [int(x) for x in hijo2]


def mutacion_swap(cromosoma: Sequence[int], p_mutacion: float = P_MUTACION) -> List[int]:
    hijo = list(cromosoma)
    if random.random() < p_mutacion:
        i, j = random.sample(range(len(hijo)), 2)
        hijo[i], hijo[j] = hijo[j], hijo[i]
    return hijo


def ruta_fitness(ruta: Sequence[int]) -> float:
    distancia = ruta_distancia(ruta)
    return 1.0 / (1.0 + distancia)


def calcular_estadisticas_generacion(poblacion: Sequence[Sequence[int]], fitnesses: Sequence[float], tiempo_gen: float) -> Dict[str, float]:
    distancias = [ruta_distancia(ruta) for ruta in poblacion]
    return {
        "distancia_min": float(min(distancias)),
        "distancia_max": float(max(distancias)),
        "distancia_prom": float(statistics.fmean(distancias)),
        "fitness_max": float(max(fitnesses)),
        "fitness_prom": float(statistics.fmean(fitnesses)),
        "fitness_min": float(min(fitnesses)),
        "desv_std_fitness": float(statistics.pstdev(fitnesses) if len(fitnesses) > 1 else 0.0),
        "tiempo_gen_seg": float(tiempo_gen),
    }


def evolucionar_ag(
    metodo: str = "elitismo",
    n_ciclos: int = N_CICLOS,
    tam_poblacion: int = N_CROMOSOMAS,
    p_crossover: float = P_CROSSOVER,
    p_mutacion: float = P_MUTACION,
    verbose: bool = True,
) -> Tuple[pd.DataFrame, Dict[str, object]]:
    poblacion = generar_poblacion(tam_poblacion)
    historial: List[Dict[str, float]] = []

    mejor_global: List[int] | None = None
    mejor_global_distancia = float("inf")
    mejor_global_fitness = 0.0

    inicio_total = time.time()

    for ciclo in range(1, n_ciclos + 1):
        inicio_ciclo = time.time()
        fitnesses = [ruta_fitness(ruta) for ruta in poblacion]
        distancias = [ruta_distancia(ruta) for ruta in poblacion]

        idx_mejor = int(np.argmax(fitnesses))
        if distancias[idx_mejor] < mejor_global_distancia:
            mejor_global = list(poblacion[idx_mejor])
            mejor_global_distancia = float(distancias[idx_mejor])
            mejor_global_fitness = float(fitnesses[idx_mejor])

        if metodo == "elitismo":
            elite = seleccionar_elitismo(poblacion, fitnesses, ELITE_SIZE)
        else:
            elite = []

        nueva_poblacion: List[List[int]] = [list(ind) for ind in elite]
        while len(nueva_poblacion) < tam_poblacion:
            if metodo in ("ruleta", "elitismo"):
                padre1 = seleccionar_ruleta(poblacion, fitnesses)
                padre2 = seleccionar_ruleta(poblacion, fitnesses)
            elif metodo == "torneo":
                padre1 = seleccionar_torneo(poblacion, fitnesses)
                padre2 = seleccionar_torneo(poblacion, fitnesses)
            else:
                raise ValueError(f"Metodo no soportado: {metodo}")

            if random.random() < p_crossover:
                hijo1, hijo2 = crossover_ciclico(padre1, padre2)
            else:
                hijo1, hijo2 = list(padre1), list(padre2)

            hijo1 = mutacion_swap(hijo1, p_mutacion)
            hijo2 = mutacion_swap(hijo2, p_mutacion)
            nueva_poblacion.extend([hijo1, hijo2])

        poblacion = nueva_poblacion[:tam_poblacion]
        tiempo_ciclo = time.time() - inicio_ciclo
        stats = calcular_estadisticas_generacion(poblacion, [ruta_fitness(ruta) for ruta in poblacion], tiempo_ciclo)
        stats["ciclo"] = float(ciclo)
        historial.append(stats)

        if verbose:
            print(
                f"Ciclo {ciclo:>3}: distancia min={stats['distancia_min']:.2f} km, "
                f"prom={stats['distancia_prom']:.2f} km, desv={stats['desv_std_fitness']:.6f}"
            )

    tiempo_total = time.time() - inicio_total
    mejores_fit = [ruta_fitness(ruta) for ruta in poblacion]
    mejores_dist = [ruta_distancia(ruta) for ruta in poblacion]
    idx_final = int(np.argmax(mejores_fit))

    resultado = {
        "metodo": metodo,
        "mejor_ruta": mejor_global if mejor_global is not None else list(poblacion[idx_final]),
        "mejor_distancia": float(mejor_global_distancia if mejor_global is not None else mejores_dist[idx_final]),
        "mejor_fitness": float(mejor_global_fitness if mejor_global is not None else mejores_fit[idx_final]),
        "distancia_poblacion_final_min": float(min(mejores_dist)),
        "distancia_poblacion_final_max": float(max(mejores_dist)),
        "distancia_poblacion_final_prom": float(statistics.fmean(mejores_dist)),
        "tiempo_total_seg": float(tiempo_total),
    }
    return pd.DataFrame(historial), resultado


# =========================
# Visualizacion y salidas
# =========================

def asegurar_directorios() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_FIGURES_DIR.mkdir(parents=True, exist_ok=True)


def sincronizar_figuras_para_informe() -> None:
    asegurar_directorios()
    for archivo_png in FIGURES_DIR.glob("*.png"):
        shutil.copy2(archivo_png, DOCS_FIGURES_DIR / archivo_png.name)


def guardar_ruta_como_figura(ruta: Sequence[int], archivo_salida: Path, titulo: str) -> None:
    asegurar_directorios()
    lats = [CIUDADES[idx].latitud for idx in ruta] + [CIUDADES[ruta[0]].latitud]
    lons = [CIUDADES[idx].longitud for idx in ruta] + [CIUDADES[ruta[0]].longitud]

    fig, ax = plt.subplots(figsize=(10, 12))
    ax.set_facecolor("#f7f3ec")
    fig.patch.set_facecolor("#f7f3ec")

    ax.plot(lons, lats, color="#1f4e79", linewidth=2.2, marker="o", markersize=5, zorder=3)
    ax.scatter(lons[:-1], lats[:-1], s=55, color="#d1495b", edgecolor="white", linewidth=0.8, zorder=4)

    for idx in ruta:
        ciudad = CIUDADES[idx]
        ax.annotate(
            ciudad.capital,
            (ciudad.longitud, ciudad.latitud),
            xytext=(4, 4),
            textcoords="offset points",
            fontsize=8,
            color="#1d1d1d",
        )

    ax.set_title(titulo, fontsize=14, fontweight="bold")
    ax.set_xlabel("Longitud")
    ax.set_ylabel("Latitud")
    ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.45)
    ax.set_xlim(-73.5, -53.0)
    ax.set_ylim(-56.5, -22.0)
    ax.set_aspect("equal", adjustable="box")
    fig.tight_layout()
    fig.savefig(archivo_salida, dpi=160, bbox_inches="tight")
    plt.close(fig)


def guardar_evolucion_ag(historial: pd.DataFrame, archivo_salida: Path, titulo: str) -> None:
    asegurar_directorios()
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.plot(historial["ciclo"], historial["distancia_min"], label="Mínima", color="#1f4e79", linewidth=2)
    ax.plot(historial["ciclo"], historial["distancia_prom"], label="Promedio", color="#d1495b", linewidth=2)
    ax.set_title(titulo)
    ax.set_xlabel("Ciclo")
    ax.set_ylabel("Distancia total (km)")
    ax.grid(True, linestyle="--", alpha=0.35)
    ax.legend()
    fig.tight_layout()
    fig.savefig(archivo_salida, dpi=160, bbox_inches="tight")
    plt.close(fig)


def exportar_resumen_heuristica(inicio: int, ruta: Sequence[int], distancia: float) -> None:
    asegurar_directorios()
    df = pd.DataFrame(
        [
            {
                "provincia_inicio": _nombre_provincia(inicio),
                "capital_inicio": _nombre_ciudad(inicio),
                "distancia_total_km": distancia,
                "recorrido": ruta_a_texto(ruta),
            }
        ]
    )
    df.to_csv(HEURISTICA_CSV, index=False)


def exportar_resumen_ag(resultado: Dict[str, object]) -> None:
    asegurar_directorios()
    ruta = resultado["mejor_ruta"]
    df = pd.DataFrame(
        [
            {
                "metodo": resultado["metodo"],
                "distancia_total_km": resultado["mejor_distancia"],
                "fitness": resultado["mejor_fitness"],
                "recorrido": ruta_a_texto(ruta),
                "tiempo_total_seg": resultado["tiempo_total_seg"],
            }
        ]
    )
    df.to_csv(GA_CSV, index=False)


# =========================
# Interfaz de consola
# =========================

def resolver_opcion_a() -> None:
    print("\nOpción A: heurística desde una provincia elegida por el usuario")
    mostrar_ciudades_disponibles()
    entrada = input("Ingresá una provincia o capital: ")
    inicio = indice_ciudad_desde_texto(entrada)
    ruta = heuristica_vecino_mas_cercano(inicio)
    distancia = ruta_distancia(ruta)

    print(f"\nProvincia de inicio: {_nombre_provincia(inicio)}")
    print(f"Capital de inicio: {_nombre_ciudad(inicio)}")
    print(f"Recorrido completo: {ruta_a_texto(ruta)}")
    print(f"Longitud total: {distancia:.2f} km")

    archivo = FIGURES_DIR / "heuristica_inicio_elegido.png"
    guardar_ruta_como_figura(ruta, archivo, f"Heurística desde {_nombre_ciudad(inicio)}")
    exportar_resumen_heuristica(inicio, ruta, distancia)
    sincronizar_figuras_para_informe()
    print(f"Mapa guardado en: {archivo}")


def resolver_opcion_b() -> None:
    print("\nOpción B: mejor recorrido heurístico probando todos los inicios")
    inicio, ruta, distancia = mejor_heuristica_global()
    print(f"Provincia de inicio: {_nombre_provincia(inicio)}")
    print(f"Capital de inicio: {_nombre_ciudad(inicio)}")
    print(f"Recorrido completo: {ruta_a_texto(ruta)}")
    print(f"Longitud total: {distancia:.2f} km")

    archivo = FIGURES_DIR / "heuristica_mejor_inicio.png"
    guardar_ruta_como_figura(ruta, archivo, f"Mejor heurística global desde {_nombre_ciudad(inicio)}")
    sincronizar_figuras_para_informe()
    print(f"Mapa guardado en: {archivo}")


def resolver_opcion_c() -> None:
    print("\nOpción C: algoritmo genético con crossover cíclico")
    random.seed(SEED)
    np.random.seed(SEED)
    historial, resultado = evolucionar_ag(metodo="elitismo", n_ciclos=N_CICLOS, tam_poblacion=N_CROMOSOMAS, verbose=False)

    ruta = resultado["mejor_ruta"]
    distancia = resultado["mejor_distancia"]
    print(f"Mejor recorrido: {ruta_a_texto(ruta)}")
    print(f"Distancia mínima encontrada: {distancia:.2f} km")
    print(f"Fitness: {resultado['mejor_fitness']:.8f}")
    print(f"Tiempo total: {resultado['tiempo_total_seg']:.2f} s")

    figura_ruta = FIGURES_DIR / "ag_mejor_ruta.png"
    figura_evolucion = FIGURES_DIR / "ag_evolucion_distancia.png"
    guardar_ruta_como_figura(ruta, figura_ruta, "Mejor ruta encontrada por AG")
    guardar_evolucion_ag(historial, figura_evolucion, "Evolución de la distancia en el AG")
    exportar_resumen_ag(resultado)
    historial.to_csv(OUTPUTS_DIR / "metricas_generacionales_ag.csv", index=False)
    sincronizar_figuras_para_informe()
    print(f"Mapas y métricas guardados en: {OUTPUTS_DIR}")


def resolver_opcion_exhaustiva() -> None:
    print("\nAnálisis teórico del método exhaustivo")
    datos = analisis_exhaustivo_teorico()
    print(f"Rutas con inicio fijo: {datos['rutas_con_inicio_fijo']:.0f}")
    print(f"Rutas si se aprovecha la simetría: {datos['rutas_si_se_aprovecha_simetria']:.0f}")
    print(f"Tiempo estimado a 1e6 evaluaciones/seg: {datos['años_estimados_a_1e6_eval_s']:.2e} años")
    print("Conclusión: no es viable resolver exhaustivamente las 23 capitales en tiempo razonable.")


def menu() -> None:
    while True:
        print("\n=== TP3 - Problema del Viajante ===")
        print("1. Heurística desde una provincia elegida")
        print("2. Mejor heurística global")
        print("3. Algoritmo genético")
        print("4. Análisis exhaustivo teórico")
        print("0. Salir")
        opcion = input("Seleccioná una opción: ").strip()

        try:
            if opcion == "1":
                resolver_opcion_a()
            elif opcion == "2":
                resolver_opcion_b()
            elif opcion == "3":
                resolver_opcion_c()
            elif opcion == "4":
                resolver_opcion_exhaustiva()
            elif opcion == "0":
                print("Saliendo...")
                break
            else:
                print("Opción inválida.")
        except ValueError as exc:
            print(f"Error: {exc}")
        except KeyboardInterrupt:
            print("\nEjecución interrumpida por el usuario.")
            break


if __name__ == "__main__":
    menu()
