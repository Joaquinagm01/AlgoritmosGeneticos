"""Algoritmo Genético Canónico aplicado a Scheduling de Alertas SOC.

Las alertas se derivan de una muestra real del dataset CICIDS2017 (flujos de red
de un ataque DDoS, columna `Label` en {DDoS, BENIGN}). El dataset no contiene
campos operativos de SOC (prioridad, severidad, SLA, tiempo de resolución,
analista, timestamp), por lo que esos campos se derivan de las columnas de
intensidad de tráfico y del `Label`, con una regla explícita documentada en
`derivar_alertas_desde_dataset()`.

El algoritmo genético implementa la forma canónica simple: selección de padres
por ruleta (proporcional al fitness), cruza de un punto y mutación por
reasignación, sin mecanismos adicionales de selección ni de elitismo.
"""

from __future__ import annotations # Permite usar tipado moderno en versiones antiguas de Python

import argparse # Librería para recibir parámetros desde la consola (línea de comandos)
import json # Librería para convertir listas y diccionarios a strings y viceversa
import random # Librería para todo lo relacionado al azar (cruza, mutación, inicialización)
import statistics # Librería para sacar promedios y desviaciones estándar
import time # Librería para medir cuánto demoran las ejecuciones
from dataclasses import dataclass # Decorador para estructurar clases de datos limpias sin boilerplate
from pathlib import Path # Manejo seguro de rutas de archivos en cualquier sistema operativo (Windows/Mac/Linux)
from typing import Dict, List, Sequence, Tuple # Herramientas de tipado estático para código más robusto

import matplotlib # Librería base para graficar
matplotlib.use("Agg") # "Agg" permite generar PNGs en segundo plano sin abrir ventanas gráficas que bloqueen el script
import matplotlib.pyplot as plt # El motor de dibujado principal de matplotlib
import numpy as np # Librería para operaciones matemáticas super veloces con matrices
import pandas as pd # Librería para manejar tablas de datos (dataframes) estilo Excel

# =========================
# Configuracion general (Constantes por defecto que se sobrescriben si se pasan por consola)
# =========================
SEED = 42 # Semilla base para que siempre dé el mismo resultado si no la cambiamos
N_ANALISTAS = 10 # Cuántas personas están trabajando en el SOC
N_ALERTAS = 500 # Cuántas alertas vamos a procesar
TAM_POBLACION = 10 # Cuántas soluciones posibles compiten por generación
N_GENERACIONES = 20 # Cuántas veces va a evolucionar la población
P_CROSSOVER = 0.75 # 75% de chances de que dos padres se crucen
P_MUTACION = 0.05 # 5% de chances de que un gen (alerta) mute (cambie de analista) al azar
HORIZONTE_MINUTOS = 8 * 60 # 480 minutos = 8 horas (un turno normal de trabajo)

# Mapeos de las reglas de negocio del SOC
PRIORIDADES = ("Baja", "Media", "Alta", "Critica") # Niveles de prioridad disponibles
PRIORIDAD_RANK = {"Baja": 0, "Media": 1, "Alta": 2, "Critica": 3} # Jerarquía numérica para ordenar las alertas
SLA_POR_PRIORIDAD = {"Baja": 240, "Media": 120, "Alta": 60, "Critica": 30} # Tiempo MÁXIMO (minutos) que puede esperar antes de ser penalizada
BASE_RESOLUCION = {"Baja": 8, "Media": 15, "Alta": 25, "Critica": 40} # Tiempo BASE (minutos) que demora resolver cada tipo

BASE_DIR = Path(__file__).resolve().parent # Obtenemos la ruta absoluta de la carpeta donde está este archivo main.py
DATASET_CSV = BASE_DIR / "dataset" / "Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv" # Ruta al dataset original de CICIDS2017
OUTPUTS_DIR = BASE_DIR / "outputs" # Carpeta para guardar los excels de salida
FIGURES_DIR = OUTPUTS_DIR / "figures" # Carpeta para guardar los gráficos PNG

# Definimos las rutas exactas donde guardaremos cada reporte
METRICAS_CSV = OUTPUTS_DIR / "metricas_generacionales_soc.csv"
RESUMEN_CSV = OUTPUTS_DIR / "resumen_resultados_soc.csv"
DISTRIBUCION_FINAL_CSV = OUTPUTS_DIR / "distribucion_final_alertas_soc.csv"
ASIGNACION_FINAL_CSV = OUTPUTS_DIR / "carga_final_analistas_soc.csv"
ALERTAS_DERIVADAS_CSV = OUTPUTS_DIR / "alertas_derivadas_dataset.csv"


@dataclass(frozen=True) # frozen=True hace que el objeto sea inmutable (no se puede modificar una alerta una vez creada)
class Alerta:
    id_alerta: int # Número de identificación único
    llegada_min: int # Minuto exacto en que saltó en el sistema (del 0 al 480)
    prioridad: str # Critica, Alta, Media, Baja
    severidad: int # Puntaje del 1 al 100 de qué tan dañina es
    tiempo_estimado_min: int # Cuánto le va a costar al analista resolverla (en minutos)
    sla_min: int # Tiempo máximo permitido en cola antes de fallar el acuerdo de nivel de servicio


def _clasificar_prioridad(label: str, severidad: int) -> str:
    """Deriva la prioridad de la alerta a partir del Label del flujo y su severidad."""
    if label == "DDoS": # Si el tráfico era un ataque DDoS real...
        return "Critica" if severidad >= 80 else "Alta" # Es Crítica si su severidad es altísima, si no, es Alta
    return "Media" if severidad >= 30 else "Baja" # Si era tráfico benigno, es Media o Baja según qué tan raro se veía


def derivar_alertas_desde_dataset(
    n_alertas: int = N_ALERTAS,
    seed: int = SEED,
    dataset_csv: Path = DATASET_CSV,
) -> List[Alerta]:
    """Construye alertas SOC reales a partir de una muestra del dataset CICIDS2017."""
    rng = random.Random(seed) # Aislamos el generador aleatorio para que esta función siempre sea determinística según la semilla

    df = pd.read_csv(dataset_csv) # Leemos el dataset gigante
    df.columns = [c.strip() for c in df.columns] # Limpiamos espacios en blanco de los nombres de las columnas
    df = df.reset_index().rename(columns={"index": "orden_captura"}) # Guardamos el orden original de la captura de red

    # Tomamos 'n_alertas' al azar usando la semilla, las volvemos a ordenar cronológicamente y reiniciamos el índice
    muestra = df.sample(n=n_alertas, random_state=seed).sort_values("orden_captura").reset_index(drop=True)

    # Extraemos los bytes/seg y paquetes/seg y los convertimos a números puros (quitando infinitos que rompen todo)
    bytes_s = pd.to_numeric(muestra["Flow Bytes/s"], errors="coerce").replace([np.inf, -np.inf], np.nan)
    packets_s = pd.to_numeric(muestra["Flow Packets/s"], errors="coerce").replace([np.inf, -np.inf], np.nan)
    # Rellenamos los datos faltantes o rotos con la mediana de los demás
    bytes_s = bytes_s.fillna(bytes_s.median())
    packets_s = packets_s.fillna(packets_s.median())

    # Calculamos una "intensidad" matemática logarítmica para que los números gigantes no dominen a los chicos
    intensidad = np.log1p(bytes_s) + np.log1p(packets_s)
    percentil = intensidad.rank(pct=True) * 100.0 # Convertimos esa intensidad en un percentil (0 al 100)

    # Ubicamos cuál fue la primera y última alerta en tiempo real
    orden_min = muestra["orden_captura"].min()
    orden_max = muestra["orden_captura"].max()
    rango_orden = max(1, orden_max - orden_min) # Rango de la captura (evitamos dividir por cero)

    alertas: List[Alerta] = [] # Inicializamos la lista vacía
    for idx, fila in muestra.iterrows(): # Iteramos fila por fila de nuestra muestra del CSV
        label = str(fila["Label"]).strip() # Vemos si era DDoS o BENIGN
        pct = float(percentil.iloc[idx]) # Vemos qué tan intenso fue (0-100)

        if label == "DDoS": # Si es ataque...
            severidad = int(round(45 + pct * 0.55)) # Le damos una base de 45 de severidad, más un extra según su intensidad
        else: # Si es normal...
            severidad = int(round(5 + pct * 0.45)) # Le damos una base baja de 5 de severidad
        severidad = max(1, min(100, severidad)) # Nos aseguramos que quede entre 1 y 100 (topeado)

        prioridad = _clasificar_prioridad(label, severidad) # Calculamos si es Crítica, Alta, etc.

        # Escalamos el momento de captura (que capaz fue en milisegundos) a los 480 minutos de nuestro turno
        llegada_min = int(round((fila["orden_captura"] - orden_min) / rango_orden * (HORIZONTE_MINUTOS - 1)))

        ruido = rng.randint(-3, 4) # Le agregamos un factor de ruido aleatorio humano (-3 a +4 minutos)
        # El tiempo de resolución depende de la prioridad, más el 35% de la severidad, más el ruido
        tiempo_estimado = BASE_RESOLUCION[prioridad] + int(round(severidad * 0.35)) + ruido
        tiempo_estimado = max(5, tiempo_estimado) # Como mínimo, cualquier alerta toma 5 minutos en leerse y cerrarse

        # Instanciamos el objeto Alerta y lo guardamos
        alertas.append(
            Alerta(
                id_alerta=idx + 1, # ID del 1 en adelante
                llegada_min=llegada_min,
                prioridad=prioridad,
                severidad=severidad,
                tiempo_estimado_min=tiempo_estimado,
                sla_min=SLA_POR_PRIORIDAD[prioridad], # Sacamos el SLA del diccionario fijo
            )
        )

    # Re-ordenamos todas las alertas por el minuto en que llegaron (cronológicamente)
    alertas.sort(key=lambda alerta: alerta.llegada_min)
    # Reasignamos los IDs para que el orden temporal sea correlativo (la alerta 1 es la primera, la 2 la segunda...)
    alertas = [
        Alerta(idx + 1, a.llegada_min, a.prioridad, a.severidad, a.tiempo_estimado_min, a.sla_min)
        for idx, a in enumerate(alertas)
    ]
    return alertas # Devolvemos el array final listo para el genético


def _guardar_alertas_derivadas(alertas: Sequence[Alerta]) -> None:
    """Guarda la tabla de alertas derivadas del dataset para trazabilidad."""
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True) # Crea la carpeta si no existe
    df = pd.DataFrame([a.__dict__ for a in alertas]) # Convierte los objetos a diccionario y luego a tabla
    df.to_csv(ALERTAS_DERIVADAS_CSV, index=False) # Exporta a CSV


def generar_poblacion(
    tam_poblacion: int = TAM_POBLACION,
    n_alertas: int = N_ALERTAS,
    n_analistas: int = N_ANALISTAS,
) -> List[List[int]]:
    """Genera una poblacion inicial aleatoria de cromosomas. Cada gen = a qué analista va esa alerta."""
    # List comprehension que crea 'tam_poblacion' listas. Cada lista tiene 'n_alertas' números aleatorios (del 1 al 10)
    return [
        [random.randint(1, n_analistas) for _ in range(n_alertas)]
        for _ in range(tam_poblacion)
    ]


def _evaluar_asignacion(cromosoma: Sequence[int], alertas: Sequence[Alerta]) -> Dict[str, float | int | List[int]]:
    """Evalua una asignacion completa y devuelve metricas operativas del SOC y el fitness."""
    asignadas_por_analista: List[List[int]] = [[] for _ in range(N_ANALISTAS)] # Bandejas de entrada vacías para cada analista
    for idx_alerta, analista in enumerate(cromosoma): # Leemos el cromosoma
        asignadas_por_analista[analista - 1].append(idx_alerta) # Metemos la alerta en la bandeja del analista que diga el gen

    disponibilidad = [0] * N_ANALISTAS # Reloj personal de cada analista (minuto en que se desocupa)
    cargas = [0] * N_ANALISTAS # Cuántos minutos en total trabajó cada uno
    espera_por_alerta = [0] * len(alertas) # Array para guardar cuánto esperó cada alerta individual
    finalizacion_por_alerta = [0] * len(alertas) # Array para guardar a qué hora exacta se terminó cada alerta
    espera_critica = [] # Lista de tiempos de espera de las alertas graves
    retraso_critico = [] # Lista de cuánto se pasaron del SLA las alertas graves

    for idx_analista, indices_alertas in enumerate(asignadas_por_analista): # Iteramos por las bandejas de cada analista
        # El analista ordena su propia bandeja: primero por llegada, y si llegan juntas, prioriza las más críticas
        indices_alertas.sort(key=lambda idx: (alertas[idx].llegada_min, PRIORIDAD_RANK[alertas[idx].prioridad]))
        
        for idx_alerta in indices_alertas: # Procesa sus alertas una por una en orden
            alerta = alertas[idx_alerta]
            # Empieza cuando se desocupe O cuando llegue la alerta (lo que sea más tarde)
            inicio = max(disponibilidad[idx_analista], alerta.llegada_min) 
            espera = inicio - alerta.llegada_min # Calculamos espera
            fin = inicio + alerta.tiempo_estimado_min # Calculamos fin

            disponibilidad[idx_analista] = fin # Actualiza su reloj
            cargas[idx_analista] += alerta.tiempo_estimado_min # Suma su carga de trabajo
            espera_por_alerta[idx_alerta] = espera # Guarda métrica
            finalizacion_por_alerta[idx_alerta] = fin # Guarda métrica

            if alerta.prioridad == "Critica": # Si la alerta era gravísima...
                espera_critica.append(espera) # Registramos cuánto esperó para penalizar luego
                retraso_critico.append(max(0, espera - alerta.sla_min)) # Registramos cuántos minutos excedió el SLA (0 si cumplió)

    tiempo_total_estimado = max(finalizacion_por_alerta) if finalizacion_por_alerta else 0 # El sistema termina cuando termina la última alerta
    espera_promedio = statistics.fmean(espera_por_alerta) if espera_por_alerta else 0.0 # Promedio de espera de las 500 alertas
    espera_critica_promedio = statistics.fmean(espera_critica) if espera_critica else 0.0 # Promedio de espera de las críticas
    retraso_critico_promedio = statistics.fmean(retraso_critico) if retraso_critico else 0.0 # Promedio de atraso de SLA de las críticas

    # Backlog: Alertas que quedaron sin terminar cuando tocó la campana de las 8 horas (480 minutos)
    backlog_alertas = sum(1 for fin in finalizacion_por_alerta if fin > HORIZONTE_MINUTOS) # Cantidad
    backlog_minutos = sum(max(0, fin - HORIZONTE_MINUTOS) for fin in finalizacion_por_alerta) # Minutos totales extras

    carga_total = sum(cargas) # Suma de todos los minutos trabajados por todos
    carga_media = carga_total / N_ANALISTAS if N_ANALISTAS else 0.0 # Idealmente, cuánto debería trabajar cada uno
    # Desbalance: Qué tan lejos están los analistas de la media (Desviación estándar / Media para normalizar)
    desbalance_carga = (statistics.pstdev(cargas) / carga_media) if carga_media else 0.0 
    # Sobrecarga relativa: Porcentaje extra del trabajo que hacen los que trabajan MÁS que el promedio
    sobrecarga_relativa = (
        sum(max(0, carga - carga_media) for carga in cargas) / carga_total if carga_total else 0.0
    )

    # ==========================
    # FUNCIÓN OBJETIVO (A MINIMIZAR)
    # Sumamos todos los males multiplicados por un peso. A mayor daño al negocio, mayor el multiplicador.
    # ==========================
    penalizacion = (
        0.60 * espera_promedio # Castigo leve por demora general
        + 1.80 * espera_critica_promedio # Castigo fuerte si las críticas demoran en arrancar
        + 8.00 * retraso_critico_promedio # Castigo MASIVO si las críticas rompen su SLA
        + 1.20 * backlog_alertas # Castigo medio por dejar tickets para mañana
        + 0.02 * backlog_minutos # Castigo ínfimo por los minutos fuera de horario
        + 40.0 * desbalance_carga # Castigo ALTO por dejar que unos analistas trabajen mucho y otros nada
        + 25.0 * sobrecarga_relativa # Castigo ALTO por sobrecargar a los analistas ocupados
    )

    # Fitness (A MAXIMIZAR). Como el genético busca maximizar, invertimos la penalización usando 1 / (1 + x)
    fitness = 1.0 / (1.0 + tiempo_total_estimado + penalizacion)

    # Devolvemos un mega-diccionario con el fitness y todos los datos forenses
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
    """Devuelve solo el valor float del fitness (atajo para funciones externas)."""
    return _evaluar_asignacion(cromosoma, alertas)["fitness"]


def seleccion_ruleta(poblacion: Sequence[Sequence[int]], fitnesses: Sequence[float]) -> List[int]:
    """Seleccion de padres por ruleta (los que tienen mejor fitness ocupan más 'porciones' de la ruleta)."""
    total = float(sum(fitnesses)) # Suma total de todos los fitness (tamaño total de la ruleta)
    if total <= 0: # Caso de seguridad extremo (nunca debería pasar con nuestro fitness > 0)
        return list(random.choice(poblacion))

    objetivo = random.uniform(0, total) # Tiramos la bolita de la ruleta en un lugar al azar
    acumulado = 0.0
    for individuo, fitness in zip(poblacion, fitnesses): # Iteramos sumando porciones
        acumulado += fitness
        if acumulado >= objetivo: # Si la suma superó el lugar donde cayó la bolita...
            return list(individuo) # ... este es el individuo seleccionado
    return list(poblacion[-1]) # Fallback de seguridad (devuelve el último si hay problema de redondeo)


def crossover(padre1: Sequence[int], padre2: Sequence[int]) -> Tuple[List[int], List[int]]:
    """Crossover de un punto (Cruza clásica). Corta a la mitad y cruza el ADN."""
    if len(padre1) != len(padre2): # Medida de seguridad
        raise ValueError("Los cromosomas deben tener la misma longitud")

    if len(padre1) < 2: # Si tienen largo 1 (rarísimo en el SOC), no se puede cruzar
        return list(padre1), list(padre2)

    punto = random.randint(1, len(padre1) - 1) # Elegimos el punto de corte (ej: gen 250 de 500)
    hijo1 = list(padre1[:punto]) + list(padre2[punto:]) # El hijo 1 es la cabeza del P1 pegado con la cola del P2
    hijo2 = list(padre2[:punto]) + list(padre1[punto:]) # El hijo 2 es la cabeza del P2 pegado con la cola del P1
    return hijo1, hijo2 # Devolvemos los dos bebés nuevos


def mutacion(cromosoma: Sequence[int], p_mutacion: float = P_MUTACION, n_analistas: int = N_ANALISTAS) -> List[int]:
    """Mutacion: Cambia un gen (una alerta) de dueño."""
    hijo = list(cromosoma)
    if random.random() < p_mutacion: # Tiramos un dado de 100 caras. Si saca menos que la prob. de mutación...
        idx = random.randrange(len(hijo)) # Elegimos un gen (alerta) cualquiera
        hijo[idx] = random.randint(1, n_analistas) # Le asignamos un analista cualquiera nuevo
    return hijo # Devolvemos el hijo (mutado o igual)


def calcular_estadisticas(fitnesses: Sequence[float], tiempo_seg: float) -> Dict[str, float]:
    """Saca las métricas matemáticas básicas para el log de la terminal."""
    return {
        "fitness_max": float(max(fitnesses)), # El mejor puntaje de esta generación
        "fitness_min": float(min(fitnesses)), # El peor puntaje
        "fitness_prom": float(statistics.fmean(fitnesses)), # El promedio de la clase
        "desv_std": float(statistics.pstdev(fitnesses)) if len(fitnesses) > 1 else 0.0, # Varianza
        "tiempo_seg": float(tiempo_seg), # Cuánto tardó esta generación
    }


def _formatear_cromosoma(cromosoma: Sequence[int], ancho: int = 32) -> str:
    """Acorta el cromosoma visualmente para no imprimir 500 números en consola y romper la pantalla."""
    if len(cromosoma) <= ancho:
        return "[" + ", ".join(map(str, cromosoma)) + "]"
    cabeza = ", ".join(map(str, cromosoma[:16])) # Muestra los primeros 16
    cola = ", ".join(map(str, cromosoma[-16:])) # Muestra los últimos 16
    return f"[{cabeza}, ..., {cola}]" # Pone puntos suspensivos en el medio


def _resumen_distribucion(cromosoma: Sequence[int], alertas: Sequence[Alerta]) -> pd.DataFrame:
    """Genera la tabla bonita que ves en el dashboard sobre 'Carga por Analista'."""
    filas = []
    for analista in range(1, N_ANALISTAS + 1): # Por cada analista
        # Obtenemos qué alertas tiene asignadas en el genético
        indices = [idx for idx, asignado in enumerate(cromosoma) if asignado == analista] 
        alertas_asignadas = [alertas[idx] for idx in indices]
        
        # Calculamos totales
        carga_total = sum(alerta.tiempo_estimado_min for alerta in alertas_asignadas)
        criticidad = sum(1 for alerta in alertas_asignadas if alerta.prioridad == "Critica")
        severidad_prom = statistics.fmean([alerta.severidad for alerta in alertas_asignadas]) if alertas_asignadas else 0.0
        
        # Guardamos la fila
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
    return pd.DataFrame(filas) # Retornamos la tabla limpia para exportar


def evolucionar(
    alertas: Sequence[Alerta],
    n_generaciones: int = N_GENERACIONES,
    tam_poblacion: int = TAM_POBLACION,
    p_crossover: float = P_CROSSOVER,
    p_mutacion: float = P_MUTACION,
    seed: int = SEED,
) -> Tuple[pd.DataFrame, Dict[str, object]]:
    """El motor principal: Ejecuta el bucle del algoritmo genetico canonico entero."""
    random.seed(seed) # Fijamos semilla de python
    np.random.seed(seed) # Fijamos semilla de numpy

    poblacion = generar_poblacion(tam_poblacion=tam_poblacion, n_alertas=len(alertas), n_analistas=N_ANALISTAS) # Creamos Adán y Eva (x10)
    historial: List[Dict[str, object]] = [] # Acá guardaremos el progreso iteración a iteración

    mejor_global: List[int] | None = None # El mejor cromosoma de TODOS LOS TIEMPOS
    mejor_global_eval: Dict[str, object] | None = None # Su evaluación respectiva

    inicio_total = time.time() # Stopwatch del sistema

    for generacion in range(1, n_generaciones + 1): # Bucle principal de evolución
        inicio_gen = time.time()

        # 1. EVALUACIÓN (Calcula el fitness de los 10 individuos)
        evaluaciones = [_evaluar_asignacion(individuo, alertas) for individuo in poblacion]
        fitnesses = [evaluacion["fitness"] for evaluacion in evaluaciones]
        
        # Busca quién fue el ganador en ESTA generación
        idx_mejor = int(np.argmax(fitnesses)) 
        mejor_gen = list(poblacion[idx_mejor])
        evaluacion_mejor = evaluaciones[idx_mejor]

        # 2. SEGUIMIENTO GLOBAL (Compara al ganador de esta gen con el campeón histórico)
        if mejor_global_eval is None or evaluacion_mejor["fitness"] > mejor_global_eval["fitness"]:
            mejor_global = list(mejor_gen) # Si le gana, destrona al campeón
            mejor_global_eval = dict(evaluacion_mejor)

        # 3. REPRODUCCIÓN (Creamos la siguiente generación, excepto si estamos en la última)
        if generacion < n_generaciones:
            nueva_poblacion: List[List[int]] = [] # La guardería vacía
            
            while len(nueva_poblacion) < tam_poblacion: # Llenamos la guardería de a 2 bebés
                padre1 = seleccion_ruleta(poblacion, fitnesses) # Elegimos a papá
                padre2 = seleccion_ruleta(poblacion, fitnesses) # Elegimos a mamá

                if random.random() < p_crossover: # Tiramos la ruleta del amor
                    hijo1, hijo2 = crossover(padre1, padre2) # Si toca, cruzan ADN
                else:
                    hijo1, hijo2 = list(padre1), list(padre2) # Si no, son clones de sus padres

                hijo1 = mutacion(hijo1, p_mutacion, n_analistas=N_ANALISTAS) # Puede que muten por radiación
                hijo2 = mutacion(hijo2, p_mutacion, n_analistas=N_ANALISTAS) 

                nueva_poblacion.append(hijo1) # Metemos al H1 a la guardería
                if len(nueva_poblacion) < tam_poblacion: 
                    nueva_poblacion.append(hijo2) # Metemos al H2 si queda lugar

            poblacion = nueva_poblacion[:tam_poblacion] # Reemplazamos al mundo viejo por la nueva generación

        # 4. REPORTES
        estadisticas = calcular_estadisticas(fitnesses, time.time() - inicio_gen)
        estadisticas.update( # Le agregamos datos útiles para el Excel final
            {
                "generacion": generacion,
                "fitness_mejor_gen": float(evaluacion_mejor["fitness"]),
                "tiempo_total_estimado_min": int(evaluacion_mejor["tiempo_total_estimado_min"]),
                "espera_promedio_min": float(evaluacion_mejor["espera_promedio_min"]),
                "espera_critica_promedio_min": float(evaluacion_mejor["espera_critica_promedio_min"]),
                "backlog_alertas": int(evaluacion_mejor["backlog_alertas"]),
                "desbalance_carga": float(evaluacion_mejor["desbalance_carga"]),
            }
        )
        historial.append(estadisticas) # Guardamos esta fila en la historia

    tiempo_total_seg = time.time() - inicio_total # Frenamos el cronómetro
    if mejor_global is None or mejor_global_eval is None: # Si algo falló catastróficamente
        raise RuntimeError("No se pudo determinar una mejor solucion global")

    # Creamos un resumen limpio del gran ganador de toda la corrida
    resumen = {
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

    return pd.DataFrame(historial), resumen # Devolvemos el dataframe (tabla) y el diccionario con el ganador


def graficar_metricas(df_metricas: pd.DataFrame) -> None:
    """Genera los graficos de líneas (Fitness, Desviación) azules para la carpeta figures/."""
    FIGURES_DIR.mkdir(parents=True, exist_ok=True) # Crea carpeta si no existe

    # Una lista de tuplas con (columna, Título, Eje Y, Nombre Archivo)
    configuraciones = [
        ("fitness_max", "Maximo por generacion", "Fitness maximo", "maximos_por_generacion.png"),
        ("fitness_prom", "Promedio por generacion", "Fitness promedio", "promedios_por_generacion.png"),
        ("fitness_min", "Minimo por generacion", "Fitness minimo", "minimos_por_generacion.png"),
        ("desv_std", "Desviacion estandar por generacion", "Desviacion estandar", "desviacion_estandar_por_generacion.png"),
    ]

    df_ordenado = df_metricas.sort_values("generacion") # Ordena por generación 1 a N
    for metrica, titulo, etiqueta_y, archivo in configuraciones: # Bucle que dibuja los 4 gráficos
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
    """Genera el gráfico de barras azules que muestra cuánto trabajó cada analista."""
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    df = distribucion_final.sort_values("analista")

    fig, ax = plt.subplots(figsize=(11, 6))
    # Dibuja las barras (analista en X, carga total en Y)
    barras = ax.bar(df["analista"].astype(str), df["carga_total_min"], color="#2a78d6", width=0.62, zorder=3)

    carga_media = df["carga_total_min"].mean() # Calcula el promedio
    # Dibuja la línea punteada horizontal del promedio
    ax.axhline(carga_media, color="#898781", linestyle="--", linewidth=1.3, zorder=2)
    ax.text( # Añade el texto "Carga media: X min" arriba de la línea punteada
        len(df) - 3.5,
        carga_media - (df["carga_total_min"].max() * 0.06),
        f"Carga media: {carga_media:.0f} min",
        color="#898781",
        fontsize=9,
    )

    for barra in barras: # Le pone el número exacto (label) arriba de cada barrita azul
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
    plt.savefig(FIGURES_DIR / "carga_final_por_analista.png", dpi=200) # Lo exporta a PNG
    plt.close()


def _imprimir_encabezado() -> None:
    """Formatea la cabecera de la tablita que se imprime en la terminal (terminal output)."""
    print("=" * 126)
    print(
        f"{'Gen':>4} | {'Fitness max':>12} | {'Fitness min':>12} | {'Fitness prom':>12} | "
        f"{'Desv. std':>12} | {'Tiempo gen (s)':>15} | {'Mejor fitness':>14} | {'Backlog':>8}"
    )
    print("-" * 126)


def _imprimir_fila(stats: Dict[str, object]) -> None:
    """Imprime una fila de los logs de la terminal alineando los valores."""
    print(
        f"{stats['generacion']:>4} | {stats['fitness_max']:>12.6f} | {stats['fitness_min']:>12.6f} | "
        f"{stats['fitness_prom']:>12.6f} | {stats['desv_std']:>12.6f} | {stats['tiempo_seg']:>15.4f} | "
        f"{stats['fitness_mejor_gen']:>14.6f} | {stats['backlog_alertas']:>8}"
    )


def _imprimir_resumen(resumen: Dict[str, object]) -> None:
    """Imprime el texto final de la terminal cuando el genético concluye."""
    print("-" * 126)
    print("RESUMEN FINAL")
    print(f"Mejor fitness global          : {resumen['mejor_fitness_global']:.10f}")
    print(f"Tiempo total estimado (min)   : {resumen['tiempo_total_estimado_min']}")
    print(f"Penalizacion total            : {resumen['penalizacion_total']:.4f}")
    print(f"Espera promedio (min)         : {resumen['espera_promedio_min']:.4f}")
    print(f"Espera critica promedio (min)  : {resumen['espera_critica_promedio_min']:.4f}")
    print(f"Backlog de alertas            : {resumen['backlog_alertas']}")
    print(f"Backlog acumulado (min)       : {resumen['backlog_minutos']:.4f}")
    print(f"Desbalance de carga           : {resumen['desbalance_carga']:.6f}")
    print(f"Sobrecarga relativa           : {resumen['sobrecarga_relativa']:.6f}")
    print(f"Tiempo de ejecucion (s)       : {resumen['tiempo_ejecucion_seg']:.6f}")
    print(f"Cromosoma ganador (compacto)  : {_formatear_cromosoma(resumen['mejor_cromosoma'])}")


def main() -> None:
    """Orquesta la simulacion completa: Lee args, corre el algoritmo y genera salidas tabuladas y graficas."""
    global SEED, N_ANALISTAS, N_ALERTAS, TAM_POBLACION, N_GENERACIONES, P_CROSSOVER, P_MUTACION, HORIZONTE_MINUTOS

    # Configuramos el parser para que Streamlit o la terminal puedan enviarnos variables nuevas al vuelo
    parser = argparse.ArgumentParser(description="Algoritmo Genético Canónico aplicado a Scheduling de Alertas SOC.")
    parser.add_argument("--seed", type=int, default=SEED, help="Semilla para reproducibilidad")
    parser.add_argument("--n-analistas", type=int, default=N_ANALISTAS, help="Cantidad de analistas SOC")
    parser.add_argument("--n-alertas", type=int, default=N_ALERTAS, help="Cantidad de alertas a muestrear")
    parser.add_argument("--tam-poblacion", type=int, default=TAM_POBLACION, help="Tamano de la poblacion")
    parser.add_argument("--n-generaciones", type=int, default=N_GENERACIONES, help="Numero de generaciones")
    parser.add_argument("--p-crossover", type=float, default=P_CROSSOVER, help="Probabilidad de cruza")
    parser.add_argument("--p-mutacion", type=float, default=P_MUTACION, help="Probabilidad de mutacion")
    parser.add_argument("--horizonte-minutos", type=int, default=HORIZONTE_MINUTOS, help="Horizonte de trabajo en minutos")
    args = parser.parse_args() # Procesa los argumentos

    # Actualizamos las variables globales con lo que sea que haya enviado el Dashboard
    SEED = args.seed
    N_ANALISTAS = args.n_analistas
    N_ALERTAS = args.n_alertas
    TAM_POBLACION = args.tam_poblacion
    N_GENERACIONES = args.n_generaciones
    P_CROSSOVER = args.p_crossover
    P_MUTACION = args.p_mutacion
    HORIZONTE_MINUTOS = args.horizonte_minutos

    # Creamos los directorios de salida
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    # Inicializamos las semillas por si cambiaron
    random.seed(SEED)
    np.random.seed(SEED)

    # 1. GENERAMOS LOS DATOS (Alertas)
    alertas = derivar_alertas_desde_dataset(n_alertas=N_ALERTAS, seed=SEED)
    _guardar_alertas_derivadas(alertas) # Exportamos un CSV con las alertas puras

    # Imprimimos los settings en terminal
    print("=" * 126)
    print("ALGORITMO GENETICO CANONICO APLICADO A SCHEDULING DE ALERTAS SOC (dataset real CICIDS2017)")
    print("=" * 126)
    print(f"Dataset fuente                : {DATASET_CSV.name}")
    print(f"Analistas SOC                 : {N_ANALISTAS}")
    print(f"Alertas muestreadas            : {N_ALERTAS}")
    print(f"Poblacion inicial              : {TAM_POBLACION}")
    print(f"Generaciones                   : {N_GENERACIONES}")
    print(f"Seleccion de padres            : ruleta (proporcional al fitness)")
    print(f"Probabilidad de crossover      : {P_CROSSOVER}")
    print(f"Probabilidad de mutacion       : {P_MUTACION}")
    print(f"Horizonte de trabajo (min)     : {HORIZONTE_MINUTOS}")
    print("=" * 126)

    _imprimir_encabezado()
    # 2. DISPARAMOS EL ALGORITMO GENÉTICO (Le pasamos los parámetros que recibimos)
    df_historial, resumen = evolucionar(
        alertas,
        n_generaciones=N_GENERACIONES,
        tam_poblacion=TAM_POBLACION,
        p_crossover=P_CROSSOVER,
        p_mutacion=P_MUTACION,
        seed=SEED
    )

    # Imprimimos los logs y el resumen final
    for _, fila in df_historial.iterrows():
        _imprimir_fila(fila.to_dict())

    _imprimir_resumen(resumen)

    # 3. EXPORTAMOS LOS RESULTADOS FINALES A DISCO
    df_historial.to_csv(METRICAS_CSV, index=False) # Guardamos tabla de historial de fitness
    df_resumen = pd.DataFrame([resumen]) 
    df_resumen.to_csv(RESUMEN_CSV, index=False) # Guardamos el ganador

    distribucion_final = _resumen_distribucion(resumen["mejor_cromosoma"], alertas)
    distribucion_final.to_csv(DISTRIBUCION_FINAL_CSV, index=False) # Guardamos tabla de carga

    resumen_cargas = distribucion_final[["analista", "alertas_asignadas", "carga_total_min", "criticidad_critica"]].copy()
    resumen_cargas.to_csv(ASIGNACION_FINAL_CSV, index=False) # Guardamos otra tabla simplificada

    # 4. DISPARAMOS LOS GRÁFICOS
    graficar_metricas(df_historial) # Gráficos de líneas azules
    graficar_carga_final(distribucion_final) # Gráfico de barras

    print("\n" + "=" * 126)
    print("DISTRIBUCION FINAL DE ALERTAS EN LA MEJOR SOLUCION ENCONTRADA")
    print("=" * 126)
    print(distribucion_final.to_string(index=False))


# Boilerplate típico: arrancar main() solo si se llama a este archivo por consola
if __name__ == "__main__":
    main()
