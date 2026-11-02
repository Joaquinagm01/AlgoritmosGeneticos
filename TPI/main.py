"""Algoritmo Genético extendido aplicado a Scheduling de Alertas SOC.

Las alertas se derivan de una muestra real del dataset CICIDS2017 (flujos de red
de un ataque DDoS, columna `Label` en {DDoS, BENIGN}). El dataset no contiene
campos operativos de SOC (prioridad, severidad, SLA, tiempo de resolución,
analista, timestamp), por lo que esos campos se derivan de las columnas de
intensidad de tráfico y del `Label`, con una regla explícita documentada en
`derivar_alertas_desde_dataset()`.

El algoritmo genético implementa selección por ranking, cruza de un punto,
mutación por gen y elitismo, con una semilla inicial Round-Robin para disponer
de una solución de referencia desde la primera generación.

EXTENSIONES respecto de la versión original (a partir de las sugerencias de los revisores):

1. INCERTIDUMBRE EN LOS TIEMPOS DE RESOLUCIÓN (estilo Stochastic Job Shop Scheduling).
   El tiempo de resolución deja de ser un número fijo: se modela como una variable
   aleatoria lognormal de media igual al tiempo estimado y coeficiente de variación
   `--cv-duracion`. El fitness se evalúa sobre K escenarios fijos (enfoque
   "sample average approximation", con números aleatorios comunes) y se optimiza el
   valor esperado. La solución final se valida fuera de muestra con escenarios nuevos
   y se reportan media, desvío y cola de peor caso (percentil 95).

2. FLUJO CONTINUO EN TIEMPO REAL (`--flujo-continuo`).
   Además del modo "lote" (el GA conoce todas las llegadas del turno, como en la
   versión original), se simula un horizonte rodante: cada `--intervalo-replan`
   minutos el GA se re-ejecuta SOLO con las alertas ya llegadas y todavía no iniciadas,
   respetando la disponibilidad real de los analistas. Las alertas que arrancan antes
   de la próxima re-planificación quedan comprometidas; el resto se re-optimiza.
   La ejecución usa tiempos "reales" que el planificador no conoce.

3. CRITICIDAD DEL ACTIVO EN LA PENALIZACIÓN POR SLA Y EN EL CROMOSOMA.
   Cada alerta lleva la criticidad del activo afectado (1 = común, 2 = importante,
   3 = crítico). Esa criticidad (a) ajusta el SLA efectivo, (b) pondera la violación de
   SLA y el backlog, y (c) interviene en la regla de despacho que decodifica el
   cromosoma. El cromosoma agrega un bloque de dos pesos globales (`w2`, `w3`)
   que determina cuánto aprovecha la política evolucionada la criticidad observada
   del activo al ordenar la cola. Se agrega el término `sla_activo` (violación de SLA
   ponderada por prioridad y criticidad del activo, sobre TODAS las alertas) a la
   función objetivo.

Para reproducir la formulación original (determinista y sin activos):
    python main.py --n-alertas 500 --n-escenarios 1 --sin-activos
"""

from __future__ import annotations # Permite usar tipado moderno en versiones antiguas de Python

import argparse # Librería para recibir parámetros desde la consola (línea de comandos)
import heapq # Cola de prioridad: despacha en O(m log m) en vez de O(m^2)
import json # Librería para convertir listas y diccionarios a strings y viceversa
import random # Librería para todo lo relacionado al azar (cruza, mutación, inicialización)
import statistics # Librería para sacar promedios y desviaciones estándar
import time # Librería para medir cuánto demoran las ejecuciones
from dataclasses import dataclass, replace # Clases de datos limpias; replace crea copias modificadas
from pathlib import Path # Manejo seguro de rutas de archivos en cualquier sistema operativo
from typing import Dict, List, Optional, Sequence, Tuple # Tipado estático

import matplotlib # Librería base para graficar
matplotlib.use("Agg") # "Agg" genera PNGs sin abrir ventanas gráficas
import matplotlib.pyplot as plt # El motor de dibujado principal de matplotlib
import numpy as np # Operaciones matemáticas sobre arreglos
import pandas as pd # Tablas de datos (dataframes)

# =========================
# Configuracion general (constantes por defecto; se sobrescriben por consola)
# =========================
SEED = 42 # Semilla base para reproducibilidad
N_ANALISTAS = 10 # Cuántas personas están trabajando en el SOC
# Escenario oficial: exigido, pero no estructuralmente colapsado.
N_ALERTAS = 100 # Cuántas alertas vamos a procesar
TAM_POBLACION = 50 # Cuántas soluciones compiten por generación
N_GENERACIONES = 200 # Cuántas veces evoluciona la población
P_CROSSOVER = 0.75 # Probabilidad de que dos padres se crucen
P_MUTACION = 0.05 # Probabilidad de que un gen (alerta) mute (cambie de analista)
HORIZONTE_MINUTOS = 8 * 60 # 480 minutos = un turno de 8 horas

# --- Extensión 1: incertidumbre en tiempos de resolución ---
N_ESCENARIOS = 10 # Escenarios de duración usados dentro del GA (1 = determinista)
CV_DURACION = 0.25 # Coeficiente de variación (desvío/media) de la duración real
N_ESCENARIOS_VALIDACION = 200 # Escenarios NUEVOS para validar la solución final fuera de muestra
MAX_ESCENARIOS_REPLAN = 5 # Tope de escenarios por re-planificación (controla el costo en flujo continuo)

# --- Extensión 2: flujo continuo ---
INTERVALO_REPLAN = 15 # Cada cuántos minutos se re-planifica
GEN_REPLAN = 30 # Generaciones del GA en cada re-planificación
POBLACION_REPLAN = 30 # Tamaño de población del GA en cada re-planificación

# --- Extensión 4: el cromosoma evoluciona la prioridad de despacho ---
AJUSTE_ACTIVO = True # False = desactiva el bloque de ajustes individuales; se cambia con --sin-ajuste
AJUSTE_MAX = 0.5 # El ajuste d_i vive en [-AJUSTE_MAX, AJUSTE_MAX] (fraccion de n posiciones de la cola)
SIGMA_AJUSTE = 0.10 # Desvio de la mutacion gaussiana del ajuste
CRITICIDAD_EN_CROMOSOMA = True # El tercer bloque aprende una política global por nivel de activo
WMAX_CRITICIDAD = 1.0 # w2 y w3 viven en [0, WMAX_CRITICIDAD]
SIGMA_CRITICIDAD = 0.10 # Desvío de la mutación de w2 y w3
BONO_CRITICIDAD_MAX = 0.50 # Máximo desplazamiento relativo del orden por criticidad aprendida

# --- Extensión 3: criticidad del activo ---
# 1 = activo común, 2 = activo importante (servicio expuesto), 3 = activo crítico (administración / datos / identidad)
FACTOR_SLA_ACTIVO = {1: 1.0, 2: 0.75, 3: 0.5} # Un activo más crítico acorta el SLA efectivo
PESO_ACTIVO = {1: 1.0, 2: 1.5, 3: 2.5} # Un activo más crítico pesa más en SLA y backlog
PESO_PENAL_SLA_ACTIVO = 8.0 # Peso del término nuevo en la penalización "de negocio" (en minutos)
PESO_OBJ_SLA_ACTIVO = 0.25 # Peso del término nuevo en el objetivo normalizado
# Proxy de criticidad por puerto destino (el dataset no trae un CMDB). En un SOC real
# este dato sale del inventario de activos / CMDB.
PUERTOS_ACTIVO_CRITICO = {22, 23, 88, 135, 139, 389, 445, 636, 1433, 1521, 3306, 3389, 5432, 5900}
PUERTOS_ACTIVO_IMPORTANTE = {21, 25, 53, 80, 110, 143, 443, 465, 587, 993, 995, 8080, 8443}

# Mapeos de las reglas de negocio del SOC
PRIORIDADES = ("Baja", "Media", "Alta", "Critica") # Niveles de prioridad disponibles
PRIORIDAD_RANK = {"Baja": 0, "Media": 1, "Alta": 2, "Critica": 3} # Jerarquía numérica
SLA_POR_PRIORIDAD = {"Baja": 240, "Media": 120, "Alta": 60, "Critica": 30} # Espera MÁXIMA (min) antes de violar el SLA
BASE_RESOLUCION = {"Baja": 8, "Media": 15, "Alta": 25, "Critica": 40} # Tiempo BASE (min) de resolución
PESO_BACKLOG_PRIORIDAD = {"Baja": 0.5, "Media": 1.0, "Alta": 2.0, "Critica": 4.0}
COEF_BACKLOG_PONDERADO = 1.20

BASE_DIR = Path(__file__).resolve().parent # Carpeta donde está este archivo
DATASET_CSV = BASE_DIR / "dataset" / "Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv" # Dataset CICIDS2017
OUTPUTS_DIR = BASE_DIR / "outputs" # Carpeta de salidas
FIGURES_DIR = OUTPUTS_DIR / "figures" # Carpeta de gráficos PNG

METRICAS_CSV = OUTPUTS_DIR / "metricas_generacionales_soc.csv"
RESUMEN_CSV = OUTPUTS_DIR / "resumen_resultados_soc.csv"
DISTRIBUCION_FINAL_CSV = OUTPUTS_DIR / "distribucion_final_alertas_soc.csv"
ASIGNACION_FINAL_CSV = OUTPUTS_DIR / "carga_final_analistas_soc.csv"
ALERTAS_DERIVADAS_CSV = OUTPUTS_DIR / "alertas_derivadas_dataset.csv"
VALIDACION_CSV = OUTPUTS_DIR / "validacion_robustez_soc.csv" # Detalle por escenario (fuera de muestra)
VALIDACION_RESUMEN_CSV = OUTPUTS_DIR / "validacion_robustez_resumen_soc.csv" # Media / desvío / peor 5 %
COMPARACION_FLUJO_CSV = OUTPUTS_DIR / "comparacion_lote_vs_continuo_soc.csv"


@dataclass(frozen=True) # frozen=True: el objeto es inmutable
class Alerta:
    id_alerta: int # Número de identificación único
    llegada_min: int # Minuto en que saltó en el sistema (0 a 480)
    prioridad: str # Critica, Alta, Media, Baja
    severidad: int # Puntaje 1 a 100 de qué tan dañina es
    tiempo_estimado_min: int # Tiempo esperado de resolución (minutos)
    sla_min: int # Espera máxima en cola según la prioridad
    criticidad_activo: int = 1 # 1 = común, 2 = importante, 3 = crítico (activo afectado)
    sla_efectivo_min: int = 0 # SLA ajustado por criticidad del activo (0 = no calculado)


def _clasificar_prioridad(label: str, severidad: int) -> str:
    """Deriva la prioridad de la alerta a partir del Label del flujo y su severidad."""
    if label == "DDoS": # Ataque DDoS real
        return "Critica" if severidad >= 80 else "Alta"
    return "Media" if severidad >= 30 else "Baja" # Tráfico benigno


def _criticidad_por_puerto(puerto: Optional[int]) -> int:
    """Proxy de la criticidad del activo según el servicio (puerto destino) del flujo."""
    if puerto is None:
        return 1
    if puerto in PUERTOS_ACTIVO_CRITICO:
        return 3
    if puerto in PUERTOS_ACTIVO_IMPORTANTE:
        return 2
    return 1


def derivar_alertas_desde_dataset(
    n_alertas: int = N_ALERTAS,
    seed: int = SEED,
    dataset_csv: Path = DATASET_CSV,
    modo_activo: str = "puerto",
) -> List[Alerta]:
    """Construye alertas SOC a partir de una muestra del dataset CICIDS2017.

    modo_activo:
      - "puerto": criticidad del activo según el puerto destino del flujo (si el CSV lo trae).
      - "cmdb": criticidad sorteada de un catálogo simulado (60 % común, 30 % importante, 10 % crítico).
        Útil porque en el ataque DDoS casi todo el tráfico apunta al mismo puerto (80).
    """
    rng = random.Random(seed) # Generador aislado: el mismo seed da siempre las mismas alertas
    rng_activos = random.Random(seed + 101) # Generador aparte para no alterar el ruido original

    df = pd.read_csv(dataset_csv)
    df.columns = [c.strip() for c in df.columns] # Limpia espacios en los nombres de columnas
    df = df.reset_index().rename(columns={"index": "orden_captura"}) # Orden original de la captura

    muestra = df.sample(n=n_alertas, random_state=seed).sort_values("orden_captura").reset_index(drop=True)

    # Bytes/seg y paquetes/seg como números puros (sin infinitos)
    bytes_s = pd.to_numeric(muestra["Flow Bytes/s"], errors="coerce").replace([np.inf, -np.inf], np.nan)
    packets_s = pd.to_numeric(muestra["Flow Packets/s"], errors="coerce").replace([np.inf, -np.inf], np.nan)
    bytes_s = bytes_s.fillna(bytes_s.median())
    packets_s = packets_s.fillna(packets_s.median())

    intensidad = np.log1p(bytes_s) + np.log1p(packets_s) # Intensidad logarítmica
    percentil = intensidad.rank(pct=True) * 100.0 # Percentil 0-100

    col_puerto = next((c for c in muestra.columns if c.replace(" ", "").lower() == "destinationport"), None)

    orden_min = muestra["orden_captura"].min()
    orden_max = muestra["orden_captura"].max()
    rango_orden = max(1, orden_max - orden_min)

    alertas: List[Alerta] = []
    for idx, fila in muestra.iterrows():
        label = str(fila["Label"]).strip()
        pct = float(percentil.iloc[idx])

        if label == "DDoS":
            severidad = int(round(45 + pct * 0.55))
        else:
            severidad = int(round(5 + pct * 0.45))
        severidad = max(1, min(100, severidad))

        prioridad = _clasificar_prioridad(label, severidad)

        llegada_min = int(round((fila["orden_captura"] - orden_min) / rango_orden * (HORIZONTE_MINUTOS - 1)))

        ruido = rng.randint(-3, 4) # Ruido humano (-3 a +4 min)
        tiempo_estimado = BASE_RESOLUCION[prioridad] + int(round(severidad * 0.35)) + ruido
        tiempo_estimado = max(5, tiempo_estimado)

        # Criticidad del activo afectado (extensión 3)
        if modo_activo == "puerto" and col_puerto is not None:
            puerto = pd.to_numeric(fila[col_puerto], errors="coerce")
            criticidad = _criticidad_por_puerto(None if pd.isna(puerto) else int(puerto))
        else:
            criticidad = rng_activos.choices((1, 2, 3), weights=(0.60, 0.30, 0.10))[0]
        sla_base = SLA_POR_PRIORIDAD[prioridad]
        sla_efectivo = max(1, int(round(sla_base * FACTOR_SLA_ACTIVO[criticidad])))

        alertas.append(
            Alerta(
                id_alerta=idx + 1,
                llegada_min=llegada_min,
                prioridad=prioridad,
                severidad=severidad,
                tiempo_estimado_min=tiempo_estimado,
                sla_min=sla_base,
                criticidad_activo=criticidad,
                sla_efectivo_min=sla_efectivo,
            )
        )

    # Orden cronológico y reasignación de IDs correlativos
    alertas.sort(key=lambda alerta: alerta.llegada_min)
    alertas = [replace(a, id_alerta=idx + 1) for idx, a in enumerate(alertas)]
    return alertas


def _guardar_alertas_derivadas(alertas: Sequence[Alerta]) -> None:
    """Guarda la tabla de alertas derivadas del dataset para trazabilidad."""
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame([a.__dict__ for a in alertas])
    df.to_csv(ALERTAS_DERIVADAS_CSV, index=False)


# ======================================================================
# Instancia del problema: arreglos precomputados para evaluar rápido
# ======================================================================
class Instancia:
    """Precomputa los vectores de la instancia (llegadas, SLA, pesos, orden de despacho).

    Con usar_activos=False se ignora la criticidad del activo (formulación original).
    """

    def __init__(self, alertas: Sequence[Alerta], usar_activos: bool = True) -> None:
        self.alertas = list(alertas)
        self.n = len(self.alertas)
        self.usar_activos = usar_activos

        crit = np.array([a.criticidad_activo if usar_activos else 1 for a in self.alertas], dtype=int)
        self.criticidad = crit
        self.llegada = np.array([a.llegada_min for a in self.alertas], dtype=float)
        self.dur_nominal = np.array([a.tiempo_estimado_min for a in self.alertas], dtype=float)
        self.prio = np.array([PRIORIDAD_RANK[a.prioridad] for a in self.alertas], dtype=int)
        self.sla = np.array([a.sla_min for a in self.alertas], dtype=float)
        self.sla_ef = np.array(
            [a.sla_efectivo_min if (usar_activos and a.sla_efectivo_min > 0) else a.sla_min for a in self.alertas],
            dtype=float,
        )
        peso = np.array(
            [PESO_BACKLOG_PRIORIDAD[a.prioridad] * PESO_ACTIVO[int(c)] for a, c in zip(self.alertas, crit)],
            dtype=float,
        )
        self.peso_sla = peso # Peso de cada alerta en la violación de SLA
        self.peso_backlog = peso # Peso de cada alerta en el backlog ponderado
        self.es_critica = self.prio == PRIORIDAD_RANK["Critica"]
        self.peso_backlog_max = max(PESO_BACKLOG_PRIORIDAD.values()) * (
            max(PESO_ACTIVO.values()) if usar_activos else 1.0
        )

        # Regla de despacho (estática): prioridad, criticidad del activo, severidad y vencimiento más cercano.
        # Como todos los candidatos comparten el mismo reloj, "menor holgura de SLA" equivale a
        # "menor llegada + SLA", por lo que la clave no depende del tiempo y se puede usar un heap.
        severidad = [a.severidad for a in self.alertas]
        claves = sorted(
            range(self.n),
            key=lambda i: (-self.prio[i], -crit[i], -severidad[i], self.llegada[i] + self.sla_ef[i], i),
        )
        orden = [0] * self.n
        for posicion, i in enumerate(claves):
            orden[i] = posicion
        self.orden = orden # orden[i] menor = más urgente
        self.llegada_list = self.llegada.tolist() # Listas nativas: más rápidas dentro de bucles


# ======================================================================
# Escenarios de duración (extensión 1)
# ======================================================================
def _muestrear_duraciones(dur_nominal: np.ndarray, n: int, cv: float, seed: int) -> np.ndarray:
    """Devuelve n vectores de duraciones lognormales con media = tiempo estimado y CV = cv."""
    if cv <= 0:
        return np.tile(dur_nominal, (n, 1))
    rng = np.random.default_rng(seed)
    sigma = float(np.sqrt(np.log1p(cv ** 2)))
    mu = -0.5 * sigma ** 2 # Garantiza E[factor] = 1
    factores = rng.lognormal(mu, sigma, size=(n, len(dur_nominal)))
    return np.maximum(1.0, dur_nominal[None, :] * factores) # Mínimo 1 minuto


def generar_escenarios_duracion(dur_nominal: np.ndarray, n_escenarios: int, cv: float, seed: int) -> np.ndarray:
    """Escenarios usados dentro del GA. Con n_escenarios <= 1 (o cv = 0) es el caso determinista."""
    if n_escenarios <= 1 or cv <= 0:
        return dur_nominal[None, :].astype(float)
    return _muestrear_duraciones(dur_nominal, n_escenarios, cv, seed)


# ======================================================================
# Población y simulación
# ======================================================================
def generar_poblacion(
    tam_poblacion: int = TAM_POBLACION,
    n_alertas: int = N_ALERTAS,
    n_analistas: int = N_ANALISTAS,
    con_ajuste: bool = False,
    con_criticidad: bool = False,
) -> List[List[float]]:
    """Población inicial por bloques.

    Genes [0:m] = analista; [m:2m] (opcional) = ajuste de prioridad;
    [2m:2m+2] (opcional) = (w2, w3), pesos globales por nivel de criticidad.

    El individuo 0 es Round-Robin con ajustes neutros.
    """
    poblacion: List[List[float]] = []
    for k in range(tam_poblacion):
        asign = [random.randint(1, n_analistas) for _ in range(n_alertas)]
        if con_ajuste:
            if k % 2 == 0:
                ajuste = [0.0] * n_alertas # La mitad de la poblacion parte de la regla fija
            else:
                ajuste = [max(-AJUSTE_MAX, min(AJUSTE_MAX, random.gauss(0.0, 0.2))) for _ in range(n_alertas)]
        else:
            ajuste = []
        pesos_criticidad = (
            [WMAX_CRITICIDAD, WMAX_CRITICIDAD]
            if con_criticidad and k % 2 == 0
            else (
                [max(0.0, min(WMAX_CRITICIDAD, random.gauss(1.0, 0.2))) for _ in range(2)]
                if con_criticidad
                else []
            )
        )
        poblacion.append(asign + ajuste + pesos_criticidad)
    if poblacion:
        rr = [(indice % n_analistas) + 1 for indice in range(n_alertas)]
        poblacion[0] = (
            rr
            + ([0.0] * n_alertas if con_ajuste else [])
            + ([WMAX_CRITICIDAD, WMAX_CRITICIDAD] if con_criticidad else [])
        )
    return poblacion


def _despachar_analista(
    indices: Sequence[int],
    inst: Instancia,
    dur: Sequence[float],
    disponibilidad: float,
    t_min: float = 0.0,
    t_corte: Optional[float] = None,
    orden: Optional[Sequence[float]] = None,
) -> Tuple[List[Tuple[int, float, float]], float, List[int]]:
    """Simula la bandeja de UN analista.

    indices: alertas asignadas, ordenadas por llegada.
    dur: duración de cada alerta en este escenario.
    t_min: instante de decisión (nadie empieza antes; sirve para el flujo continuo).
    t_corte: si se indica, no se inicia ninguna alerta en t >= t_corte (quedan pendientes).
    Devuelve (ejecutadas[(idx, inicio, fin)], instante en que queda libre, alertas restantes).
    """
    llegada = inst.llegada_list
    orden = inst.orden if orden is None else orden # Orden base o base + ajuste evolucionado
    reloj = max(disponibilidad, t_min)
    libre = disponibilidad
    cola: List[Tuple[int, int]] = [] # Heap de alertas ya llegadas, ordenadas por urgencia
    p, m = 0, len(indices)
    ejecutadas: List[Tuple[int, float, float]] = []

    while p < m or cola:
        while p < m and llegada[indices[p]] <= reloj: # Entran a la cola las alertas ya llegadas
            idx = indices[p]
            heapq.heappush(cola, (orden[idx], idx))
            p += 1
        if not cola: # Analista ocioso: salta hasta la próxima llegada
            reloj = llegada[indices[p]]
            continue
        if t_corte is not None and reloj >= t_corte:
            break
        _, idx = heapq.heappop(cola) # La más urgente según la regla de despacho
        fin = reloj + dur[idx]
        ejecutadas.append((idx, reloj, fin))
        reloj = fin
        libre = fin

    restantes = [idx for _, idx in cola] + list(indices[p:])
    return ejecutadas, libre, restantes


def _orden_efectivo(cromosoma: Sequence[float], idx_g: Sequence[int], inst: Instancia) -> Sequence[float]:
    """Decodifica los bloques de prioridad y criticidad del cromosoma."""
    m = len(idx_g)
    orden = list(inst.orden)
    tiene_ajuste = AJUSTE_ACTIVO and len(cromosoma) >= 2 * m
    offset_criticidad = m * (1 + int(AJUSTE_ACTIVO))
    tiene_criticidad = CRITICIDAD_EN_CROMOSOMA and len(cromosoma) >= offset_criticidad + 2
    for pos, idx in enumerate(idx_g):
        ajuste = cromosoma[m + pos] if tiene_ajuste else 0.0
        w2 = cromosoma[offset_criticidad] if tiene_criticidad else 1.0
        w3 = cromosoma[offset_criticidad + 1] if tiene_criticidad else 1.0
        peso_critico = (
            w2 if inst.criticidad[idx] == 2 else w3 if inst.criticidad[idx] == 3 else 0.0
        ) if tiene_criticidad else 0.0
        criticidad_normalizada = 1.0 if inst.usar_activos and inst.criticidad[idx] in (2, 3) else 0.0
        orden[idx] = (
            inst.orden[idx]
            + ajuste * inst.n
            - peso_critico * criticidad_normalizada * BONO_CRITICIDAD_MAX * inst.n
        )
    return orden


def _pesos_criticidad(cromosoma: Sequence[float], n_alertas: int) -> Tuple[float, float]:
    """Obtiene los pesos globales w2 y w3 del cromosoma, o la política neutra."""
    offset = n_alertas * (1 + int(AJUSTE_ACTIVO))
    if not CRITICIDAD_EN_CROMOSOMA or len(cromosoma) < offset + 2:
        return 1.0, 1.0
    return float(cromosoma[offset]), float(cromosoma[offset + 1])


def _simular(
    cromosoma: Sequence[float],
    idx_g: Sequence[int],
    inst: Instancia,
    dur: Sequence[float],
    disp_inicial: Optional[Sequence[float]] = None,
    t_min: float = 0.0,
) -> Tuple[List[float], List[float], List[float]]:
    """Decodifica el cromosoma (gen i = analista de la alerta idx_g[i]) y simula las colas."""
    m = len(idx_g)
    orden = _orden_efectivo(cromosoma, idx_g, inst)
    colas: List[List[int]] = [[] for _ in range(N_ANALISTAS)]
    for pos in range(m): # Solo el primer bloque es asignacion de analistas
        colas[int(cromosoma[pos]) - 1].append(idx_g[pos])

    inicio = [0.0] * inst.n
    fin = [0.0] * inst.n
    cargas = [0.0] * N_ANALISTAS
    for a, cola in enumerate(colas):
        if not cola:
            continue
        disp = disp_inicial[a] if disp_inicial is not None else 0.0
        ejecutadas, _, _ = _despachar_analista(cola, inst, dur, disp, t_min, orden=orden)
        for idx, ini, f in ejecutadas:
            inicio[idx] = ini
            fin[idx] = f
            cargas[a] += f - ini
    return inicio, fin, cargas


def _metricas(
    idx_arr: np.ndarray,
    inicio: Sequence[float],
    fin: Sequence[float],
    cargas: Sequence[float],
    inst: Instancia,
) -> Dict[str, object]:
    """Métricas operativas de UN escenario sobre el subconjunto de alertas idx_arr."""
    H = HORIZONTE_MINUTOS
    ini = np.asarray(inicio)[idx_arr]
    fn = np.asarray(fin)[idx_arr]
    esp = ini - inst.llegada[idx_arr]
    crit = inst.es_critica[idx_arr]
    prio = inst.prio[idx_arr]
    cargas_arr = np.asarray(cargas, dtype=float)

    tiempo_total = float(fn.max()) if fn.size else 0.0
    espera_prom = float(esp.mean()) if esp.size else 0.0
    if crit.any():
        espera_crit = float(esp[crit].mean())
        retraso_crit = float(np.maximum(0.0, esp[crit] - inst.sla_ef[idx_arr][crit]).mean())
    else:
        espera_crit = 0.0
        retraso_crit = 0.0

    # Backlog: alertas que terminan después de la campana del turno
    fuera = fn > H
    out: Dict[str, object] = {
        "n_alertas_eval": float(idx_arr.size),
        "tiempo_total_estimado_min": tiempo_total,
        "espera_promedio_min": espera_prom,
        "espera_critica_promedio_min": espera_crit,
        "retraso_critico_promedio_min": retraso_crit,
        "backlog_alertas": float(fuera.sum()),
        "backlog_minutos": float(np.clip(fn - H, 0.0, None).sum()),
        "backlog_ponderado": float(inst.peso_backlog[idx_arr][fuera].sum()),
    }
    for nombre in PRIORIDADES:
        out[f"backlog_{nombre.lower()}"] = float((fuera & (prio == PRIORIDAD_RANK[nombre])).sum())

    # Equilibrio de carga
    carga_total = float(cargas_arr.sum())
    carga_media = carga_total / N_ANALISTAS if N_ANALISTAS else 0.0
    out["desbalance_carga"] = float(cargas_arr.std() / carga_media) if carga_media else 0.0
    out["sobrecarga_relativa"] = (
        float(np.clip(cargas_arr - carga_media, 0.0, None).sum() / carga_total) if carga_total else 0.0
    )

    # Violación de SLA con SLA efectivo (criticidad del activo) sobre TODAS las alertas
    if esp.size:
        retraso_ef = np.maximum(0.0, esp - inst.sla_ef[idx_arr])
        w = inst.peso_sla[idx_arr]
        out["violacion_sla_ponderada_min"] = float((w * retraso_ef).sum() / w.sum())
        out["sla_incumplidos_pct"] = float((retraso_ef > 0).mean() * 100.0)
        out["sla_incumplidos_critica_pct"] = float((retraso_ef[crit] > 0).mean() * 100.0) if crit.any() else 0.0
    else:
        out["violacion_sla_ponderada_min"] = 0.0
        out["sla_incumplidos_pct"] = 0.0
        out["sla_incumplidos_critica_pct"] = 0.0

    out["cargas_por_analista"] = cargas_arr
    return out


def _promediar(ms: Sequence[Dict[str, object]]) -> Dict[str, object]:
    """Promedia las métricas de varios escenarios (valor esperado)."""
    if len(ms) == 1:
        return dict(ms[0])
    promedio: Dict[str, object] = {}
    for clave in ms[0]:
        valor = np.mean([m[clave] for m in ms], axis=0)
        promedio[clave] = valor if np.ndim(valor) else float(valor)
    return promedio


def _objetivo(m: Dict[str, object], inst: Instancia, peso_tiempo_objetivo: float) -> Dict[str, object]:
    """Calcula penalización, objetivo normalizado y fitness a partir de métricas (esperadas).

    Todos los términos son lineales en las métricas, así que el objetivo evaluado sobre las
    métricas promedio es exactamente el objetivo esperado sobre los escenarios.
    """
    horizonte = max(1, HORIZONTE_MINUTOS)
    n = max(1.0, float(m["n_alertas_eval"]))

    # Penalización "de negocio" (minutos ponderados). A mayor daño, mayor el multiplicador.
    contribuciones_penalizacion = {
        "espera_general": 0.60 * m["espera_promedio_min"],
        "espera_critica": 1.80 * m["espera_critica_promedio_min"],
        "retraso_critico": 8.00 * m["retraso_critico_promedio_min"],
        "backlog_ponderado": COEF_BACKLOG_PONDERADO * m["backlog_ponderado"],
        "backlog_minutos": 0.02 * m["backlog_minutos"],
        "desbalance": 40.0 * m["desbalance_carga"],
        "sobrecarga": 25.0 * m["sobrecarga_relativa"],
        "sla_activo": (PESO_PENAL_SLA_ACTIVO * m["violacion_sla_ponderada_min"]) if inst.usar_activos else 0.0,
    }
    penalizacion = float(sum(contribuciones_penalizacion.values()))

    # Objetivo normalizado (A MINIMIZAR): escala acotada y comparable entre individuos
    contribuciones_objetivo = {
        "tiempo_total": peso_tiempo_objetivo * (m["tiempo_total_estimado_min"] / horizonte),
        "espera_general": 0.10 * (m["espera_promedio_min"] / horizonte),
        "espera_critica": 0.20 * (m["espera_critica_promedio_min"] / horizonte),
        "retraso_critico": 0.25 * (m["retraso_critico_promedio_min"] / horizonte),
        "backlog_ponderado": 0.10 * (m["backlog_ponderado"] / (inst.peso_backlog_max * n)),
        "backlog_minutos": 0.05 * (m["backlog_minutos"] / (n * horizonte)),
        "desbalance": 0.15 * m["desbalance_carga"],
        "sobrecarga": 0.05 * m["sobrecarga_relativa"],
        "sla_activo": (PESO_OBJ_SLA_ACTIVO * (m["violacion_sla_ponderada_min"] / horizonte))
        if inst.usar_activos else 0.0,
    }
    objetivo_normalizado = float(sum(contribuciones_objetivo.values()))

    resultado = dict(m)
    resultado.update(
        {
            "fitness": float(1.0 / (1.0 + objetivo_normalizado)), # A MAXIMIZAR
            "penalizacion": penalizacion,
            "objetivo_normalizado": objetivo_normalizado,
            "contribuciones_penalizacion": contribuciones_penalizacion,
            "contribuciones_objetivo": contribuciones_objetivo,
        }
    )
    return resultado


def evaluar_cromosoma(
    cromosoma: Sequence[int],
    idx_g: Sequence[int],
    idx_arr: np.ndarray,
    inst: Instancia,
    esc_list: Sequence[Sequence[float]],
    peso_tiempo_objetivo: float = 0.10,
    disp_inicial: Optional[Sequence[float]] = None,
    t_min: float = 0.0,
) -> Dict[str, object]:
    """Evalúa un cromosoma: valor esperado del objetivo sobre los escenarios de duración."""
    ms = []
    for dur in esc_list:
        inicio, fin, cargas = _simular(cromosoma, idx_g, inst, dur, disp_inicial, t_min)
        ms.append(_metricas(idx_arr, inicio, fin, cargas, inst))
    return _objetivo(_promediar(ms), inst, peso_tiempo_objetivo)


def calcular_fitness(
    cromosoma: Sequence[int],
    alertas: Sequence[Alerta],
    usar_activos: bool = True,
) -> float:
    """Calcula el fitness determinista respetando la configuración de activos."""
    inst = Instancia(alertas, usar_activos=usar_activos)
    idx_g = list(range(inst.n))
    return evaluar_cromosoma(cromosoma, idx_g, np.arange(inst.n), inst, [inst.dur_nominal.tolist()])["fitness"]


# ======================================================================
# Operadores del algoritmo genético y estrategias de selección alternativas.
# ======================================================================
def seleccion_ruleta(poblacion: Sequence[Sequence[int]], fitnesses: Sequence[float]) -> List[int]:
    """Selección por ruleta (mejor fitness = más porción de la ruleta)."""
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


def seleccion_torneo(
    poblacion: Sequence[Sequence[int]],
    fitnesses: Sequence[float],
    tam_torneo: int = 3,
) -> List[int]:
    """Selecciona el mejor individuo de una muestra aleatoria de la población."""
    cantidad = min(max(2, tam_torneo), len(poblacion))
    indices = random.sample(range(len(poblacion)), cantidad)
    ganador = max(indices, key=lambda indice: fitnesses[indice])
    return list(poblacion[ganador])


def seleccion_ranking(
    poblacion: Sequence[Sequence[int]],
    fitnesses: Sequence[float],
) -> List[int]:
    """Selecciona por rango para evitar que la escala del fitness domine la presión selectiva."""
    orden = sorted(range(len(poblacion)), key=lambda indice: fitnesses[indice])
    pesos = list(range(1, len(orden) + 1))
    indice_rango = random.choices(orden, weights=pesos, k=1)[0]
    return list(poblacion[indice_rango])


def seleccionar_padre(
    poblacion: Sequence[Sequence[int]],
    fitnesses: Sequence[float],
    metodo: str,
) -> List[int]:
    """Despacha la estrategia de selección configurada."""
    if metodo == "ruleta":
        return seleccion_ruleta(poblacion, fitnesses)
    if metodo == "torneo":
        return seleccion_torneo(poblacion, fitnesses)
    if metodo == "ranking":
        return seleccion_ranking(poblacion, fitnesses)
    raise ValueError("El metodo de seleccion debe ser 'ruleta', 'torneo' o 'ranking'")


def crossover(padre1: Sequence[int], padre2: Sequence[int]) -> Tuple[List[int], List[int]]:
    """Crossover de un punto (cruza clásica)."""
    if len(padre1) != len(padre2):
        raise ValueError("Los cromosomas deben tener la misma longitud")

    if len(padre1) < 2:
        return list(padre1), list(padre2)

    punto = random.randint(1, len(padre1) - 1)
    hijo1 = list(padre1[:punto]) + list(padre2[punto:])
    hijo2 = list(padre2[:punto]) + list(padre1[punto:])
    return hijo1, hijo2


def mutacion(cromosoma: Sequence[int], p_mutacion: float = P_MUTACION, n_analistas: int = N_ANALISTAS) -> List[int]:
    """Mutación: reasigna cada gen con la probabilidad indicada."""
    hijo = list(cromosoma)
    for idx in range(len(hijo)):
        if random.random() < p_mutacion:
            hijo[idx] = random.randint(1, n_analistas)
    return hijo


def crossover_bloques(
    padre1: Sequence[float], padre2: Sequence[float], m: int, n_bloques: int = 3
) -> Tuple[List[float], List[float]]:
    """Cruza por separado asignación, ajuste por alerta y política global (w2, w3)."""
    if len(padre1) <= m or n_bloques <= 1:
        return crossover(padre1, padre2)
    bloques_1: List[List[float]] = []
    bloques_2: List[List[float]] = []
    for bloque in range(n_bloques):
        inicio = bloque * m
        es_ultimo = bloque == n_bloques - 1
        tamano = len(padre1) - inicio if es_ultimo else m
        fin = inicio + tamano
        if inicio >= len(padre1):
            break
        a1, a2 = crossover(padre1[inicio:fin], padre2[inicio:fin])
        bloques_1.append(a1)
        bloques_2.append(a2)
    return [gen for bloque in bloques_1 for gen in bloque], [gen for bloque in bloques_2 for gen in bloque]


def mutacion_bloques(
    cromosoma: Sequence[float],
    m: int,
    p_mutacion: float = P_MUTACION,
    n_analistas: int = N_ANALISTAS,
    n_bloques: int = 3,
) -> List[float]:
    """Muta asignación, ajuste por alerta y los pesos globales w2/w3 por separado."""
    hijo: List[float] = mutacion(cromosoma[:m], p_mutacion, n_analistas)
    tiene_ajuste = len(cromosoma) >= 2 * m
    if tiene_ajuste:
        for g in cromosoma[m:2 * m]:
            valor = float(g)
            if random.random() < p_mutacion:
                valor = max(
                    -AJUSTE_MAX,
                    min(AJUSTE_MAX, valor + random.gauss(0.0, SIGMA_AJUSTE)),
                )
            hijo.append(valor)
    offset_criticidad = m * (1 + int(AJUSTE_ACTIVO))
    tiene_criticidad = CRITICIDAD_EN_CROMOSOMA and len(cromosoma) >= offset_criticidad + 2
    if tiene_criticidad:
        for g in cromosoma[offset_criticidad:offset_criticidad + 2]:
            valor = float(g)
            if random.random() < p_mutacion:
                valor = max(
                    0.0,
                    min(WMAX_CRITICIDAD, valor + random.gauss(0.0, SIGMA_CRITICIDAD)),
                )
            hijo.append(valor)
    return hijo


def calcular_estadisticas(fitnesses: Sequence[float], tiempo_seg: float) -> Dict[str, float]:
    """Métricas básicas de la generación para el log de la terminal."""
    return {
        "fitness_max": float(max(fitnesses)),
        "fitness_min": float(min(fitnesses)),
        "fitness_prom": float(statistics.fmean(fitnesses)),
        "desv_std": float(statistics.pstdev(fitnesses)) if len(fitnesses) > 1 else 0.0,
        "tiempo_seg": float(tiempo_seg),
    }


def _formatear_cromosoma(cromosoma: Sequence[int], ancho: int = 32) -> str:
    """Acorta el cromosoma visualmente para no imprimir 500 números en consola."""
    if len(cromosoma) <= ancho:
        return "[" + ", ".join(map(str, cromosoma)) + "]"
    cabeza = ", ".join(map(str, cromosoma[:16]))
    cola = ", ".join(map(str, cromosoma[-16:]))
    return f"[{cabeza}, ..., {cola}]"


def _resumen_distribucion(cromosoma: Sequence[int], alertas: Sequence[Alerta]) -> pd.DataFrame:
    """Tabla de carga por analista (alertas, minutos, críticas y activos críticos)."""
    filas = []
    for analista in range(1, N_ANALISTAS + 1):
        indices = [idx for idx, asignado in enumerate(cromosoma) if asignado == analista]
        alertas_asignadas = [alertas[idx] for idx in indices]

        carga_total = sum(alerta.tiempo_estimado_min for alerta in alertas_asignadas)
        criticidad = sum(1 for alerta in alertas_asignadas if alerta.prioridad == "Critica")
        activos_criticos = sum(1 for alerta in alertas_asignadas if alerta.criticidad_activo == 3)
        severidad_prom = statistics.fmean([alerta.severidad for alerta in alertas_asignadas]) if alertas_asignadas else 0.0

        filas.append(
            {
                "analista": analista,
                "alertas_asignadas": len(alertas_asignadas),
                "carga_total_min": carga_total,
                "criticidad_critica": criticidad,
                "activos_criticos": activos_criticos,
                "severidad_promedio": float(severidad_prom),
                "carga_promedio_por_alerta_min": float(carga_total / len(alertas_asignadas)) if alertas_asignadas else 0.0,
            }
        )
    return pd.DataFrame(filas)


# ======================================================================
# Motor del GA
# ======================================================================
def _ejecutar_ga(
    idx_g: Sequence[int],
    inst: Instancia,
    esc_list: Sequence[Sequence[float]],
    n_generaciones: int,
    tam_poblacion: int,
    p_crossover: float,
    p_mutacion: float,
    metodo_seleccion: str,
    peso_tiempo_objetivo: float,
    disp_inicial: Optional[Sequence[float]] = None,
    t_min: float = 0.0,
    individuo_semilla: Optional[Sequence[int]] = None,
) -> Tuple[pd.DataFrame, List[int], Dict[str, object]]:
    """Bucle del GA sobre las alertas idx_g. Devuelve (historial, mejor cromosoma, su evaluación).

    individuo_semilla: solución inicial adicional (en flujo continuo, el plan anterior).
    """
    idx_arr = np.asarray(idx_g, dtype=int)
    poblacion = generar_poblacion(
        tam_poblacion=tam_poblacion,
        n_alertas=len(idx_g),
        n_analistas=N_ANALISTAS,
        con_ajuste=AJUSTE_ACTIVO,
        con_criticidad=CRITICIDAD_EN_CROMOSOMA,
    )
    if individuo_semilla is not None and tam_poblacion > 1:
        poblacion[1] = list(individuo_semilla)

    historial: List[Dict[str, object]] = []
    mejor_global: Optional[List[int]] = None
    mejor_global_eval: Optional[Dict[str, object]] = None

    for generacion in range(1, n_generaciones + 1):
        inicio_gen = time.time()

        # 1. EVALUACIÓN
        evaluaciones = [
            evaluar_cromosoma(ind, idx_g, idx_arr, inst, esc_list, peso_tiempo_objetivo, disp_inicial, t_min)
            for ind in poblacion
        ]
        fitnesses = [e["fitness"] for e in evaluaciones]

        idx_mejor = int(np.argmax(fitnesses))
        mejor_gen = list(poblacion[idx_mejor])
        evaluacion_mejor = evaluaciones[idx_mejor]

        # 2. SEGUIMIENTO GLOBAL
        if mejor_global_eval is None or evaluacion_mejor["fitness"] > mejor_global_eval["fitness"]:
            mejor_global = list(mejor_gen)
            mejor_global_eval = dict(evaluacion_mejor)

        # 3. REPRODUCCIÓN (elitismo + selección + cruza + mutación)
        if generacion < n_generaciones:
            elite_count = min(3, max(1, tam_poblacion // 10))
            elite_indices = sorted(range(len(poblacion)), key=lambda i: fitnesses[i], reverse=True)[:elite_count]
            nueva_poblacion: List[List[int]] = [list(poblacion[i]) for i in elite_indices]

            while len(nueva_poblacion) < tam_poblacion:
                padre1 = seleccionar_padre(poblacion, fitnesses, metodo_seleccion)
                padre2 = seleccionar_padre(poblacion, fitnesses, metodo_seleccion)

                if random.random() < p_crossover:
                    hijo1, hijo2 = crossover_bloques(
                        padre1,
                        padre2,
                        len(idx_g),
                        n_bloques=1 + int(AJUSTE_ACTIVO) + int(CRITICIDAD_EN_CROMOSOMA),
                    )
                else:
                    hijo1, hijo2 = list(padre1), list(padre2)

                hijo1 = mutacion_bloques(
                    hijo1,
                    len(idx_g),
                    p_mutacion,
                    n_analistas=N_ANALISTAS,
                    n_bloques=1 + int(AJUSTE_ACTIVO) + int(CRITICIDAD_EN_CROMOSOMA),
                )
                hijo2 = mutacion_bloques(
                    hijo2,
                    len(idx_g),
                    p_mutacion,
                    n_analistas=N_ANALISTAS,
                    n_bloques=1 + int(AJUSTE_ACTIVO) + int(CRITICIDAD_EN_CROMOSOMA),
                )

                nueva_poblacion.append(hijo1)
                if len(nueva_poblacion) < tam_poblacion:
                    nueva_poblacion.append(hijo2)

            poblacion = nueva_poblacion[:tam_poblacion]

        # 4. REPORTES
        estadisticas = calcular_estadisticas(fitnesses, time.time() - inicio_gen)
        estadisticas.update(
            {
                "generacion": generacion,
                "fitness_mejor_gen": float(evaluacion_mejor["fitness"]),
                "tiempo_total_estimado_min": float(evaluacion_mejor["tiempo_total_estimado_min"]),
                "espera_promedio_min": float(evaluacion_mejor["espera_promedio_min"]),
                "espera_critica_promedio_min": float(evaluacion_mejor["espera_critica_promedio_min"]),
                "backlog_alertas": float(evaluacion_mejor["backlog_alertas"]),
                "sla_incumplidos_pct": float(evaluacion_mejor["sla_incumplidos_pct"]),
                "desbalance_carga": float(evaluacion_mejor["desbalance_carga"]),
            }
        )
        historial.append(estadisticas)

    if mejor_global is None or mejor_global_eval is None:
        raise RuntimeError("No se pudo determinar una mejor solucion global")
    return pd.DataFrame(historial), mejor_global, mejor_global_eval


def evolucionar(
    alertas: Sequence[Alerta],
    n_generaciones: int = N_GENERACIONES,
    tam_poblacion: int = TAM_POBLACION,
    p_crossover: float = P_CROSSOVER,
    p_mutacion: float = P_MUTACION,
    seed: int = SEED,
    metodo_seleccion: str = "ranking",
    peso_tiempo_objetivo: float = 0.10,
    n_escenarios: int = N_ESCENARIOS,
    cv_duracion: float = CV_DURACION,
    usar_activos: bool = True,
    inst: Optional[Instancia] = None,
    escenarios: Optional[np.ndarray] = None,
) -> Tuple[pd.DataFrame, Dict[str, object]]:
    """Modo LOTE: el GA conoce todas las llegadas del turno y optimiza el valor esperado."""
    random.seed(seed)
    np.random.seed(seed)

    if inst is None:
        inst = Instancia(alertas, usar_activos)
    if escenarios is None:
        escenarios = generar_escenarios_duracion(inst.dur_nominal, n_escenarios, cv_duracion, seed)
    esc_list = escenarios.tolist()

    inicio_total = time.time()
    df_historial, mejor_global, ev = _ejecutar_ga(
        list(range(inst.n)), inst, esc_list, n_generaciones, tam_poblacion,
        p_crossover, p_mutacion, metodo_seleccion, peso_tiempo_objetivo,
    )
    tiempo_total_seg = time.time() - inicio_total

    resumen = {
        "mejor_cromosoma": mejor_global,
        "mejor_cromosoma_texto": json.dumps(mejor_global),
        "mejor_fitness_global": float(ev["fitness"]),
        "n_analistas": N_ANALISTAS, # Para que otros scripts (ej. baseline_comparacion.py) sepan el escenario
        "n_escenarios": int(escenarios.shape[0]),
        "cv_duracion": float(cv_duracion if escenarios.shape[0] > 1 else 0.0),
        "usa_criticidad_activo": bool(inst.usar_activos),
        "cromosoma_con_ajuste": bool(AJUSTE_ACTIVO),
        "cromosoma_con_criticidad": bool(CRITICIDAD_EN_CROMOSOMA),
        "n_bloques_cromosoma": 1 + int(AJUSTE_ACTIVO) + int(CRITICIDAD_EN_CROMOSOMA),
        "w2_criticidad": _pesos_criticidad(mejor_global, inst.n)[0],
        "w3_criticidad": _pesos_criticidad(mejor_global, inst.n)[1],
        "n_alertas": int(inst.n), # Largo del bloque de asignacion: mejor_cromosoma[:n_alertas]
        "tiempo_total_estimado_min": float(ev["tiempo_total_estimado_min"]),
        "penalizacion_total": float(ev["penalizacion"]),
        "espera_promedio_min": float(ev["espera_promedio_min"]),
        "espera_critica_promedio_min": float(ev["espera_critica_promedio_min"]),
        "retraso_critico_promedio_min": float(ev["retraso_critico_promedio_min"]),
        "violacion_sla_ponderada_min": float(ev["violacion_sla_ponderada_min"]),
        "sla_incumplidos_pct": float(ev["sla_incumplidos_pct"]),
        "sla_incumplidos_critica_pct": float(ev["sla_incumplidos_critica_pct"]),
        "backlog_alertas": float(ev["backlog_alertas"]),
        "backlog_minutos": float(ev["backlog_minutos"]),
        "backlog_ponderado": float(ev["backlog_ponderado"]),
        "backlog_baja": float(ev["backlog_baja"]),
        "backlog_media": float(ev["backlog_media"]),
        "backlog_alta": float(ev["backlog_alta"]),
        "backlog_critica": float(ev["backlog_critica"]),
        "desbalance_carga": float(ev["desbalance_carga"]),
        "sobrecarga_relativa": float(ev["sobrecarga_relativa"]),
        "tiempo_ejecucion_seg": float(tiempo_total_seg),
    }
    return df_historial, resumen


# ======================================================================
# Validación de robustez fuera de muestra (extensión 1)
# ======================================================================
COLUMNAS_VALIDACION = {
    # columna: True si "más es mejor" (el peor caso es la cola inferior)
    "fitness": True,
    "backlog_alertas": False,
    "sla_incumplidos_pct": False,
    "sla_incumplidos_critica_pct": False,
    "espera_critica_promedio_min": False,
    "tiempo_total_estimado_min": False,
}


def validar_robustez(
    soluciones: Dict[str, Sequence[int]],
    inst: Instancia,
    n_validacion: int,
    cv: float,
    seed: int,
    peso_tiempo_objetivo: float = 0.10,
) -> pd.DataFrame:
    """Evalúa cada solución sobre escenarios NUEVOS (distintos de los usados para optimizar)."""
    esc = _muestrear_duraciones(inst.dur_nominal, n_validacion, cv, seed + 7919).tolist()
    idx_g = list(range(inst.n))
    idx_arr = np.arange(inst.n)
    filas = []
    for nombre, cromosoma in soluciones.items():
        for k, dur in enumerate(esc):
            inicio, fin, cargas = _simular(cromosoma, idx_g, inst, dur)
            ev = _objetivo(_metricas(idx_arr, inicio, fin, cargas, inst), inst, peso_tiempo_objetivo)
            fila = {"solucion": nombre, "escenario": k}
            fila.update({c: float(ev[c]) for c in COLUMNAS_VALIDACION})
            filas.append(fila)
    return pd.DataFrame(filas)


def resumir_validacion(df_val: pd.DataFrame) -> pd.DataFrame:
    """Media, desvío y peor 5 % (cola de riesgo) de cada métrica por solución."""
    filas = []
    for nombre, grupo in df_val.groupby("solucion", sort=False):
        fila: Dict[str, object] = {"solucion": nombre, "n_escenarios": len(grupo)}
        for columna, mas_es_mejor in COLUMNAS_VALIDACION.items():
            fila[f"{columna}_media"] = float(grupo[columna].mean())
            fila[f"{columna}_desv"] = float(grupo[columna].std(ddof=0))
            fila[f"{columna}_peor5pct"] = float(grupo[columna].quantile(0.05 if mas_es_mejor else 0.95))
        filas.append(fila)
    return pd.DataFrame(filas)


# ======================================================================
# Flujo continuo / horizonte rodante (extensión 2)
# ======================================================================
def evaluar_en_ejecucion_real(
    cromosoma: Sequence[int],
    inst: Instancia,
    dur_real: np.ndarray,
    peso_tiempo_objetivo: float = 0.10,
) -> Dict[str, object]:
    """Evalúa una asignación de lote usando los tiempos 'reales' (que el planificador no conoce)."""
    inicio, fin, cargas = _simular(cromosoma, list(range(inst.n)), inst, dur_real.tolist())
    return _objetivo(_metricas(np.arange(inst.n), inicio, fin, cargas, inst), inst, peso_tiempo_objetivo)


def simular_flujo_continuo(
    inst: Instancia,
    esc_plan: np.ndarray,
    dur_real: np.ndarray,
    intervalo: int,
    gens_replan: int,
    tam_poblacion: int,
    p_crossover: float,
    p_mutacion: float,
    metodo_seleccion: str,
    peso_tiempo_objetivo: float,
    seed: int,
) -> Dict[str, object]:
    """Horizonte rodante: cada `intervalo` minutos se re-optimiza con lo que ya llegó.

    - El GA solo ve alertas con llegada <= t y todavía no iniciadas (no conoce el futuro).
    - Nadie puede empezar una alerta antes del instante de decisión t.
    - Las alertas que arrancan antes de t + intervalo quedan comprometidas con los tiempos REALES;
      el resto vuelve a la bolsa y se re-planifica (con el plan anterior como individuo semilla).
    """
    random.seed(seed + 555)
    n = inst.n
    disp = [0.0] * N_ANALISTAS
    inicio = [0.0] * n
    fin = [0.0] * n
    analista = [0] * n
    comprometida = [False] * n
    n_comprometidas = 0
    plan_previo: Dict[int, Tuple[int, float]] = {} # alerta -> (analista, ajuste)
    pesos_criticidad_previos = [WMAX_CRITICIDAD, WMAX_CRITICIDAD]
    ultima_llegada = float(inst.llegada.max())
    dur_real_l = dur_real.tolist()
    esc_l = esc_plan.tolist()
    t = 0.0
    n_replans = 0

    while n_comprometidas < n:
        conocidas = [i for i in range(n) if not comprometida[i] and inst.llegada_list[i] <= t]
        es_ultimo = t >= ultima_llegada # Ya llegó todo: se compromete lo que queda
        t_corte = None if es_ultimo else t + intervalo

        if conocidas:
            m = len(conocidas)
            semilla = [
                plan_previo.get(i, ((pos % N_ANALISTAS) + 1, 0.0, 1.0))[0]
                for pos, i in enumerate(conocidas)
            ]
            if AJUSTE_ACTIVO:
                semilla += [plan_previo.get(i, (0, 0.0))[1] for i in conocidas]
            if CRITICIDAD_EN_CROMOSOMA:
                semilla += pesos_criticidad_previos
            _, mejor, _ = _ejecutar_ga(
                conocidas, inst, esc_l, gens_replan, tam_poblacion, p_crossover, p_mutacion,
                metodo_seleccion, peso_tiempo_objetivo, disp_inicial=disp, t_min=t, individuo_semilla=semilla,
            )
            orden_ef = _orden_efectivo(mejor, conocidas, inst)
            colas: List[List[int]] = [[] for _ in range(N_ANALISTAS)]
            for pos in range(m):
                colas[int(mejor[pos]) - 1].append(conocidas[pos])
            for a, cola in enumerate(colas):
                if not cola:
                    continue
                ejecutadas, libre, _ = _despachar_analista(
                    cola, inst, dur_real_l, disp[a], t, t_corte, orden=orden_ef
                )
                for idx, ini, f in ejecutadas:
                    inicio[idx], fin[idx], analista[idx] = ini, f, a + 1
                    comprometida[idx] = True
                    n_comprometidas += 1
                disp[a] = libre
            plan_previo = {
                conocidas[pos]: (
                    int(mejor[pos]),
                    float(mejor[m + pos]) if AJUSTE_ACTIVO else 0.0,
                )
                for pos in range(m)
            }
            if CRITICIDAD_EN_CROMOSOMA:
                offset_criticidad = m * (1 + int(AJUSTE_ACTIVO))
                pesos_criticidad_previos = [
                    float(mejor[offset_criticidad]),
                    float(mejor[offset_criticidad + 1]),
                ]

        t += intervalo
        n_replans += 1

    cargas = [0.0] * N_ANALISTAS
    for i in range(n):
        cargas[analista[i] - 1] += fin[i] - inicio[i]
    ev = _objetivo(_metricas(np.arange(n), inicio, fin, cargas, inst), inst, peso_tiempo_objetivo)
    ev["cromosoma"] = analista
    ev["n_replanificaciones"] = n_replans
    return ev


# ======================================================================
# Gráficos
# ======================================================================
def graficar_metricas(df_metricas: pd.DataFrame) -> None:
    """Gráficos de líneas (fitness y desviación por generación)."""
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    configuraciones = [
        ("fitness_max", "Maximo por generacion", "Fitness maximo", "maximos_por_generacion.png"),
        ("fitness_prom", "Promedio por generacion", "Fitness promedio", "promedios_por_generacion.png"),
        ("fitness_min", "Minimo por generacion", "Fitness minimo", "minimos_por_generacion.png"),
        ("desv_std", "Desviacion estandar por generacion", "Desviacion estandar", "desviacion_estandar_por_generacion.png"),
    ]

    df_ordenado = df_metricas.sort_values("generacion")
    for metrica, titulo, etiqueta_y, archivo in configuraciones:
        plt.figure(figsize=(11, 6))
        plt.plot(df_ordenado["generacion"], df_ordenado[metrica], marker="o", linewidth=2, color="#2a78d6")
        plt.title(titulo)
        plt.xlabel("Generacion")
        plt.ylabel(etiqueta_y)
        plt.grid(True, linestyle="--", alpha=0.35)
        plt.tight_layout()
        plt.savefig(FIGURES_DIR / archivo, dpi=200)
        plt.close()


def graficar_carga_final(distribucion_final: pd.DataFrame) -> None:
    """Gráfico de barras con la carga de cada analista."""
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    df = distribucion_final.sort_values("analista")

    fig, ax = plt.subplots(figsize=(11, 6))
    barras = ax.bar(df["analista"].astype(str), df["carga_total_min"], color="#2a78d6", width=0.62, zorder=3)

    carga_media = df["carga_total_min"].mean()
    ax.axhline(carga_media, color="#898781", linestyle="--", linewidth=1.3, zorder=2)
    ax.text(
        len(df) - 3.5,
        carga_media - (df["carga_total_min"].max() * 0.06),
        f"Carga media: {carga_media:.0f} min",
        color="#898781",
        fontsize=9,
    )

    for barra in barras:
        altura = barra.get_height()
        ax.text(barra.get_x() + barra.get_width() / 2, altura + df["carga_total_min"].max() * 0.012, f"{int(altura)}",
                 ha="center", va="bottom", fontsize=9, color="#0b0b0b")

    ax.set_title("Carga final por analista en la mejor solución encontrada", fontsize=13)
    ax.set_xlabel("Analista SOC")
    ax.set_ylabel("Carga total asignada (minutos)")
    ax.set_ylim(0, df["carga_total_min"].max() * 1.15)
    ax.grid(axis="y", color="#e1e0d9", linestyle="--", linewidth=0.8, zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "carga_final_por_analista.png", dpi=200)
    plt.close()


def graficar_validacion(df_val: pd.DataFrame) -> None:
    """Boxplots de fitness y de % de SLA incumplidos sobre los escenarios de validación."""
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    etiquetas = list(df_val["solucion"].unique())
    fig, ejes = plt.subplots(1, 2, figsize=(12, 5.5))
    paneles = [
        ("fitness", "Fitness (mayor es mejor)"),
        ("sla_incumplidos_pct", "% de alertas con SLA incumplido (menor es mejor)"),
    ]
    for ax, (columna, titulo) in zip(ejes, paneles):
        datos = [df_val.loc[df_val["solucion"] == e, columna].values for e in etiquetas]
        ax.boxplot(datos)
        ax.set_xticks(range(1, len(etiquetas) + 1))
        ax.set_xticklabels(etiquetas)
        ax.set_title(titulo, fontsize=11)
        ax.grid(axis="y", color="#e1e0d9", linestyle="--", linewidth=0.8)
    fig.suptitle("Validación fuera de muestra con tiempos de resolución aleatorios", fontsize=13)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "validacion_robustez.png", dpi=200)
    plt.close()


# ======================================================================
# Salida por terminal
# ======================================================================
def _imprimir_encabezado() -> None:
    print("=" * 126)
    print(
        f"{'Gen':>4} | {'Fitness max':>12} | {'Fitness min':>12} | {'Fitness prom':>12} | "
        f"{'Desv. std':>12} | {'Tiempo gen (s)':>15} | {'Mejor fitness':>14} | {'Backlog':>8}"
    )
    print("-" * 126)


def _imprimir_fila(stats: Dict[str, object]) -> None:
    print(
        f"{int(stats['generacion']):>4} | {stats['fitness_max']:>12.6f} | {stats['fitness_min']:>12.6f} | "
        f"{stats['fitness_prom']:>12.6f} | {stats['desv_std']:>12.6f} | {stats['tiempo_seg']:>15.4f} | "
        f"{stats['fitness_mejor_gen']:>14.6f} | {stats['backlog_alertas']:>8.1f}"
    )


def _imprimir_resumen(resumen: Dict[str, object]) -> None:
    print("-" * 126)
    print("RESUMEN FINAL (valores esperados sobre los escenarios de optimizacion)")
    print(f"Mejor fitness global          : {resumen['mejor_fitness_global']:.10f}")
    print(f"Tiempo total estimado (min)   : {resumen['tiempo_total_estimado_min']:.2f}")
    print(f"Penalizacion total            : {resumen['penalizacion_total']:.4f}")
    print(f"Espera promedio (min)         : {resumen['espera_promedio_min']:.4f}")
    print(f"Espera critica promedio (min) : {resumen['espera_critica_promedio_min']:.4f}")
    print(f"Violacion SLA ponderada (min) : {resumen['violacion_sla_ponderada_min']:.4f}")
    print(f"Alertas con SLA incumplido (%) : {resumen['sla_incumplidos_pct']:.2f}  (criticas: {resumen['sla_incumplidos_critica_pct']:.2f})")
    print(f"Backlog de alertas            : {resumen['backlog_alertas']:.2f}")
    print(f"Backlog acumulado (min)       : {resumen['backlog_minutos']:.4f}")
    print(f"Desbalance de carga           : {resumen['desbalance_carga']:.6f}")
    print(f"Sobrecarga relativa           : {resumen['sobrecarga_relativa']:.6f}")
    if resumen.get("cromosoma_con_criticidad", False):
        print(f"Politica de criticidad (w2,w3): ({resumen['w2_criticidad']:.4f}, {resumen['w3_criticidad']:.4f})")
    print(f"Tiempo de ejecucion (s)       : {resumen['tiempo_ejecucion_seg']:.6f}")
    print(f"Cromosoma ganador (compacto)  : {_formatear_cromosoma(resumen['mejor_cromosoma'][:resumen['n_alertas']])}")


def main() -> None:
    """Orquesta la simulacion completa: lee args, corre el algoritmo y genera salidas tabuladas y graficas."""
    global SEED, N_ANALISTAS, N_ALERTAS, TAM_POBLACION, N_GENERACIONES, P_CROSSOVER, P_MUTACION, HORIZONTE_MINUTOS, DATASET_CSV, AJUSTE_ACTIVO, CRITICIDAD_EN_CROMOSOMA

    parser = argparse.ArgumentParser(description="Algoritmo Genético extendido aplicado a Scheduling de Alertas SOC.")
    # Nota: --seed-aleatoria no lleva valor; imprime la semilla elegida para repetir la corrida con --seed.
    parser.add_argument("--seed", type=int, default=SEED,
                        help=f"Semilla del GA y de los escenarios (por defecto {SEED}, corrida repetible)")
    parser.add_argument("--seed-aleatoria", action="store_true",
                        help="Sortea una semilla distinta en cada corrida (se imprime y se guarda para poder repetirla). Tiene prioridad sobre --seed")
    parser.add_argument("--seed-datos", type=int, default=None,
                        help="Semilla de la muestra de alertas del dataset. Si se omite, usa la misma que la semilla del GA. Fijala para comparar corridas sobre las MISMAS alertas")
    parser.add_argument("--dataset", type=str, default=str(DATASET_CSV), help="Ruta al CSV de CICIDS2017")
    parser.add_argument("--n-analistas", type=int, default=N_ANALISTAS, help="Cantidad de analistas SOC")
    parser.add_argument("--n-alertas", type=int, default=N_ALERTAS, help="Cantidad de alertas a muestrear")
    parser.add_argument("--tam-poblacion", type=int, default=TAM_POBLACION, help="Tamano de la poblacion")
    parser.add_argument("--n-generaciones", type=int, default=N_GENERACIONES, help="Numero de generaciones")
    parser.add_argument("--p-crossover", type=float, default=P_CROSSOVER, help="Probabilidad de cruza")
    parser.add_argument("--p-mutacion", type=float, default=P_MUTACION, help="Probabilidad de mutacion")
    parser.add_argument("--seleccion", choices=("ranking", "torneo", "ruleta"), default="ranking", help="Estrategia de seleccion de padres")
    parser.add_argument("--horizonte-minutos", type=int, default=HORIZONTE_MINUTOS, help="Horizonte de trabajo en minutos")
    # Extension 1
    parser.add_argument("--n-escenarios", type=int, default=N_ESCENARIOS, help="Escenarios de duracion dentro del GA (1 = determinista)")
    parser.add_argument("--cv-duracion", type=float, default=CV_DURACION, help="Coeficiente de variacion de la duracion real")
    parser.add_argument("--n-validacion", type=int, default=N_ESCENARIOS_VALIDACION, help="Escenarios de validacion fuera de muestra (0 = omitir)")
    # Extension 2
    parser.add_argument("--flujo-continuo", action="store_true", help="Simula ademas el horizonte rodante y lo compara con el modo lote")
    parser.add_argument("--intervalo-replan", type=int, default=INTERVALO_REPLAN, help="Minutos entre re-planificaciones")
    parser.add_argument("--gen-replan", type=int, default=GEN_REPLAN, help="Generaciones del GA en cada re-planificacion")
    parser.add_argument("--poblacion-replan", type=int, default=POBLACION_REPLAN, help="Poblacion del GA en cada re-planificacion")
    # Extension 3
    parser.add_argument("--sin-activos", action="store_true", help="Ignora la criticidad del activo (formulacion original)")
    parser.add_argument("--criticidad-activo", choices=("puerto", "cmdb"), default="cmdb", help="Origen de la criticidad del activo")
    # Extension 4
    parser.add_argument("--sin-ajuste", action="store_true",
                        help="Desactiva el bloque de ajuste individual d_i")
    parser.add_argument("--sin-criticidad", action="store_true",
                        help="Desactiva los dos genes globales de política de criticidad (w2, w3)")
    args = parser.parse_args()

    # Por defecto la semilla es fija (42). Con --seed-aleatoria se sortea del sistema operativo y se informa para poder reproducir la corrida
    semilla_fijada = not args.seed_aleatoria
    SEED = args.seed if semilla_fijada else random.SystemRandom().randrange(2 ** 31)
    SEED_DATOS = args.seed_datos if args.seed_datos is not None else SEED
    DATASET_CSV = Path(args.dataset)
    N_ANALISTAS = args.n_analistas
    N_ALERTAS = args.n_alertas
    TAM_POBLACION = args.tam_poblacion
    N_GENERACIONES = args.n_generaciones
    P_CROSSOVER = args.p_crossover
    P_MUTACION = args.p_mutacion
    HORIZONTE_MINUTOS = args.horizonte_minutos
    usar_activos = not args.sin_activos
    AJUSTE_ACTIVO = not args.sin_ajuste
    CRITICIDAD_EN_CROMOSOMA = not args.sin_criticidad

    if not DATASET_CSV.exists():
        raise SystemExit(f"No se encontro el dataset: {DATASET_CSV}")

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    random.seed(SEED)
    np.random.seed(SEED)

    # 1. DATOS: alertas, instancia y escenarios de duracion
    alertas = derivar_alertas_desde_dataset(
        n_alertas=N_ALERTAS, seed=SEED_DATOS, dataset_csv=DATASET_CSV, modo_activo=args.criticidad_activo
    )
    _guardar_alertas_derivadas(alertas)
    inst = Instancia(alertas, usar_activos)
    escenarios = generar_escenarios_duracion(inst.dur_nominal, args.n_escenarios, args.cv_duracion, SEED)
    dur_real = _muestrear_duraciones(inst.dur_nominal, 1, args.cv_duracion, SEED + 31337)[0] # "Realidad" desconocida para el planificador

    print("=" * 126)
    print("ALGORITMO GENETICO CANONICO APLICADO A SCHEDULING DE ALERTAS SOC (dataset real CICIDS2017)")
    print("=" * 126)
    print(f"Semilla (GA y escenarios)     : {SEED}  ({'fija' if semilla_fijada else 'sorteada con --seed-aleatoria; usa --seed ' + str(SEED) + ' para repetir'})")
    print(f"Semilla de la muestra         : {SEED_DATOS}  ({'fijada por --seed-datos' if args.seed_datos is not None else 'igual a la anterior'})")
    print(f"Dataset fuente                : {DATASET_CSV.name}")
    print(f"Analistas SOC                 : {N_ANALISTAS}")
    print(f"Alertas muestreadas           : {N_ALERTAS}")
    print(f"Poblacion inicial             : {TAM_POBLACION}")
    print(f"Generaciones                  : {N_GENERACIONES}")
    print(f"Seleccion de padres           : {args.seleccion}")
    print(f"Probabilidad de crossover     : {P_CROSSOVER}")
    print(f"Probabilidad de mutacion      : {P_MUTACION}")
    print(f"Horizonte de trabajo (min)    : {HORIZONTE_MINUTOS}")
    print(f"Escenarios de duracion (GA)   : {escenarios.shape[0]}  (CV = {args.cv_duracion if escenarios.shape[0] > 1 else 0.0})")
    print(f"Criticidad del activo         : {'desactivada' if not usar_activos else args.criticidad_activo}")
    bloques = ["asignacion"]
    if AJUSTE_ACTIVO:
        bloques.append("ajuste de prioridad")
    if CRITICIDAD_EN_CROMOSOMA:
        bloques.append("peso de criticidad")
    print(f"Cromosoma                     : {' + '.join(bloques)}")
    print("=" * 126)

    # 2. GA EN MODO LOTE
    _imprimir_encabezado()
    df_historial, resumen = evolucionar(
        alertas,
        n_generaciones=N_GENERACIONES,
        tam_poblacion=TAM_POBLACION,
        p_crossover=P_CROSSOVER,
        p_mutacion=P_MUTACION,
        seed=SEED,
        metodo_seleccion=args.seleccion,
        inst=inst,
        escenarios=escenarios,
    )
    resumen["seed"] = SEED # Queda en el CSV de resultados para poder reproducir la corrida
    resumen["seed_datos"] = SEED_DATOS
    for _, fila in df_historial.iterrows():
        _imprimir_fila(fila.to_dict())
    _imprimir_resumen(resumen)

    # 3. EXPORTACION DE RESULTADOS DEL MODO LOTE
    df_historial.to_csv(METRICAS_CSV, index=False)
    pd.DataFrame([resumen]).to_csv(RESUMEN_CSV, index=False)

    distribucion_final = _resumen_distribucion(resumen["mejor_cromosoma"][:inst.n], alertas)
    distribucion_final.to_csv(DISTRIBUCION_FINAL_CSV, index=False)
    distribucion_final[["analista", "alertas_asignadas", "carga_total_min", "criticidad_critica", "activos_criticos"]].to_csv(
        ASIGNACION_FINAL_CSV, index=False
    )
    graficar_metricas(df_historial)
    graficar_carga_final(distribucion_final)

    round_robin = [(i % N_ANALISTAS) + 1 for i in range(inst.n)]

    # 4. VALIDACION DE ROBUSTEZ FUERA DE MUESTRA
    if args.n_validacion > 0 and args.cv_duracion > 0:
        df_val = validar_robustez(
            {"Round-Robin": round_robin, "GA (lote)": resumen["mejor_cromosoma"]},
            inst, args.n_validacion, args.cv_duracion, SEED,
        )
        df_val.to_csv(VALIDACION_CSV, index=False)
        df_val_resumen = resumir_validacion(df_val)
        df_val_resumen.to_csv(VALIDACION_RESUMEN_CSV, index=False)
        graficar_validacion(df_val)

        print("\n" + "=" * 126)
        print(f"VALIDACION FUERA DE MUESTRA ({args.n_validacion} escenarios nuevos de duracion)")
        print("=" * 126)
        vista = df_val_resumen[
            ["solucion", "fitness_media", "fitness_desv", "fitness_peor5pct",
             "backlog_alertas_media", "backlog_alertas_peor5pct",
             "sla_incumplidos_pct_media", "sla_incumplidos_critica_pct_media"]
        ]
        print(vista.to_string(index=False, float_format=lambda x: f"{x:.4f}"))

    # 5. FLUJO CONTINUO (HORIZONTE RODANTE) Y COMPARACION CON LOTE
    if args.flujo_continuo:
        print("\n" + "=" * 126)
        print(f"FLUJO CONTINUO: re-planificacion cada {args.intervalo_replan} min "
              f"({args.gen_replan} generaciones, poblacion {args.poblacion_replan})")
        print("=" * 126)
        inicio_c = time.time()
        esc_plan = escenarios[:MAX_ESCENARIOS_REPLAN]
        ev_continuo = simular_flujo_continuo(
            inst, esc_plan, dur_real, args.intervalo_replan, args.gen_replan, args.poblacion_replan,
            P_CROSSOVER, P_MUTACION, args.seleccion, 0.10, SEED,
        )
        tiempo_c = time.time() - inicio_c
        ev_lote = evaluar_en_ejecucion_real(resumen["mejor_cromosoma"], inst, dur_real)
        ev_rr = evaluar_en_ejecucion_real(round_robin, inst, dur_real)

        filas = []
        for nombre, ev in (
            ("Round-Robin", ev_rr),
            ("GA lote (conoce todas las llegadas)", ev_lote),
            (f"GA continuo (replan {args.intervalo_replan} min)", ev_continuo),
        ):
            filas.append(
                {
                    "solucion": nombre,
                    "fitness": float(ev["fitness"]),
                    "espera_promedio_min": float(ev["espera_promedio_min"]),
                    "espera_critica_promedio_min": float(ev["espera_critica_promedio_min"]),
                    "sla_incumplidos_pct": float(ev["sla_incumplidos_pct"]),
                    "sla_incumplidos_critica_pct": float(ev["sla_incumplidos_critica_pct"]),
                    "backlog_alertas": float(ev["backlog_alertas"]),
                    "desbalance_carga": float(ev["desbalance_carga"]),
                }
            )
        df_comp = pd.DataFrame(filas)
        df_comp.to_csv(COMPARACION_FLUJO_CSV, index=False)
        print(f"Replanificaciones: {ev_continuo['n_replanificaciones']} | tiempo de calculo: {tiempo_c:.1f} s")
        print("Todas las soluciones se ejecutan con los MISMOS tiempos reales (desconocidos para el planificador):")
        print(df_comp.to_string(index=False, float_format=lambda x: f"{x:.4f}"))

    print("\n" + "=" * 126)
    print("DISTRIBUCION FINAL DE ALERTAS EN LA MEJOR SOLUCION ENCONTRADA (MODO LOTE)")
    print("=" * 126)
    print(distribucion_final.to_string(index=False))


if __name__ == "__main__":
    main()
