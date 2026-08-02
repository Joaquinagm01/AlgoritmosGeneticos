"""
Versión Avanzada del Algoritmo Genético (Ideas a Futuro)
Incluye:
1. Skill-Based Routing (Tiers de Analistas)
2. Optimización Multiobjetivo (NSGA-II simplificado con Frentes de Pareto)
3. Elitismo Avanzado (Top 5% sobrevive)
4. Scheduling Dinámico (Procesamiento por ventanas temporales/lotes)
"""

import random # Librería estándar para generar números aleatorios (selecciones, cruzas, mutaciones)
import statistics # Librería para cálculos estadísticos rápidos (como la desviación estándar)
import time # Librería para medir el tiempo real que demora la ejecución de los algoritmos
from dataclasses import dataclass # Decorador para crear clases que solo guardan datos de forma limpia
from typing import List, Tuple # Anotaciones de tipos para que el código sea más legible y seguro

# Reutilizamos las clases base y constantes de main.py para no repetir código
from main import Alerta, N_ANALISTAS

# Configuraciones Avanzadas exclusivas de esta versión
P_ELITISMO = 0.05 # Porcentaje de los mejores individuos que pasan intactos a la siguiente generación (5%)
VENTANA_TIEMPO_MINUTOS = 30  # Tamaño del lote de tiempo para simular que las alertas llegan en tiempo real

# 1. Skill-based Routing (Tiers de Analistas)
# Se categorizan a los analistas en 3 niveles de experiencia:
# Analistas 1 al 3: Senior (Tier 3) -> Máxima experiencia
# Analistas 4 al 7: Semi-Senior (Tier 2) -> Experiencia media
# Analistas 8 al 10: Junior (Tier 1) -> Poca experiencia
def obtener_tier(analista: int) -> int: # Función que recibe el ID del analista y devuelve su nivel
    if 1 <= analista <= 3: # Si el analista es el 1, 2 o 3...
        return 3 # Le asignamos el Tier 3 (Senior)
    elif 4 <= analista <= 7: # Si es el 4, 5, 6 o 7...
        return 2 # Le asignamos el Tier 2 (Semi-Senior)
    else: # Si es el 8, 9 o 10...
        return 1 # Le asignamos el Tier 1 (Junior)

def evaluar_multiobjetivo(cromosoma: List[int], alertas: List[Alerta], inicio_reloj: int = 0) -> Tuple[float, float]:
    """
    Evalúa la asignación basándose en DOS objetivos separados a MINIMIZAR (Multi-objetivo puro):
    f1 = Tiempo Total de resolución + Penalización por romper SLAs y malas asignaciones de Skill-Routing
    f2 = Desbalance de Carga (Varianza o desviación estándar de los tiempos asignados)
    """
    cargas = [0] * N_ANALISTAS # Array para guardar cuántos minutos de trabajo acumula cada analista
    disponibilidad = [inicio_reloj] * N_ANALISTAS # Array con el minuto en que cada analista quedará libre (empieza en inicio_reloj)
    
    penalizacion_slas = 0.0 # Acumulador para penalizar si una alerta superó su tiempo límite de espera
    penalizacion_skills = 0.0 # Acumulador para penalizar si se le da una alerta crítica a un novato
    
    asignadas = [[] for _ in range(N_ANALISTAS)] # Creamos una lista de listas para agrupar qué alertas le tocaron a quién
    for idx, analista in enumerate(cromosoma): # Recorremos el cromosoma (el gen 'idx' tiene el analista asignado a la alerta 'idx')
        asignadas[analista - 1].append(alertas[idx]) # Metemos la alerta en la "caja" (lista) correspondiente a su analista
        
    for i in range(N_ANALISTAS): # Iteramos por cada analista (del 0 al 9 en el array)
        tier = obtener_tier(i + 1) # Obtenemos qué nivel de experiencia tiene el analista actual (sumamos 1 porque el ID arranca en 1)
        asignadas[i].sort(key=lambda a: a.llegada_min) # Ordenamos cronológicamente la bandeja de entrada del analista
        
        for alerta in asignadas[i]: # Procesamos una por una las alertas que le tocaron a este analista
            inicio = max(disponibilidad[i], alerta.llegada_min) # El analista empieza cuando queda libre O cuando llega la alerta (lo que pase último)
            espera = inicio - alerta.llegada_min # Calculamos cuántos minutos estuvo la alerta esperando sin ser atendida
            fin = inicio + alerta.tiempo_estimado_min # Calculamos en qué minuto termina de resolverla
            
            disponibilidad[i] = fin # Actualizamos la disponibilidad del analista a este nuevo minuto de fin
            cargas[i] += alerta.tiempo_estimado_min # Le sumamos el esfuerzo a su carga total de trabajo
            
            # Penalización por romper SLA (Service Level Agreement)
            if espera > alerta.sla_min: # Si la espera superó el tiempo máximo permitido...
                if alerta.prioridad == "Critica": # Y además la alerta era de máxima prioridad...
                    penalizacion_slas += (espera - alerta.sla_min) * 10 # Penalizamos fuertemente (multiplicado por 10)
                else: # Si era de otra prioridad menor...
                    penalizacion_slas += (espera - alerta.sla_min) * 2 # Penalizamos de forma más suave (multiplicado por 2)
                    
            # Penalización por Skill-based Routing (Routing Inteligente)
            if alerta.prioridad in ["Critica", "Alta"] and tier == 1: # Si es una alerta grave y se la dimos a un Junior (Tier 1)...
                penalizacion_skills += 1000  # Castigamos al algoritmo con 1000 puntos (muy malo para el SOC real)
            if alerta.prioridad == "Critica" and tier == 2: # Si es una alerta Crítica y se la dimos a un Semi-Senior (Tier 2)...
                penalizacion_skills += 200   # Castigamos con 200 puntos (es preferible un Senior, pero no es tan grave como dársela a un Junior)

    tiempo_total = max(disponibilidad) - inicio_reloj # El tiempo total del SOC será cuando termine el ÚLTIMO analista de trabajar
    
    # Construcción de las Funciones Objetivo
    f1 = tiempo_total + penalizacion_slas + penalizacion_skills # F1 suma el tiempo total y todas las penalizaciones. Queremos MINIMIZAR ESTO.
    
    carga_media = sum(cargas) / N_ANALISTAS if N_ANALISTAS else 0 # Calculamos el promedio de minutos asignados a los analistas
    f2 = statistics.pstdev(cargas) if carga_media > 0 else 0.0 # F2 es la Desviación Estándar poblacional. Queremos MINIMIZAR ESTO (para que todos trabajen lo mismo).
    
    return float(f1), float(f2) # Devolvemos ambos objetivos como una tupla (F1, F2)

def domina(objA: Tuple[float, float], objB: Tuple[float, float]) -> bool:
    """Devuelve True si la solución A domina a la solución B en el sentido de Pareto (Minimización)"""
    # Para que A domine a B, A debe ser menor o igual a B en AMBOS objetivos...
    condicion_menor_igual = (objA[0] <= objB[0] and objA[1] <= objB[1])
    # ... y A debe ser estrictamente menor a B en AL MENOS UN objetivo.
    condicion_estrictamente_menor = (objA[0] < objB[0] or objA[1] < objB[1])
    return condicion_menor_igual and condicion_estrictamente_menor # Retorna True solo si cumple ambas reglas

def seleccion_por_torneo(poblacion, objetivos):
    """Selección simple adaptada al multiobjetivo para el NSGA-II usando torneos binarios"""
    i1, i2 = random.sample(range(len(poblacion)), 2) # Elegimos 2 individuos al azar de la población para que "peleen"
    if domina(objetivos[i1], objetivos[i2]): # Si el individuo 1 domina (es mejor que) el individuo 2...
        return poblacion[i1] # Gana el individuo 1 y lo devolvemos como padre
    elif domina(objetivos[i2], objetivos[i1]): # Si el individuo 2 domina al individuo 1...
        return poblacion[i2] # Gana el individuo 2
    else: # Si ninguno domina al otro (son incomparables, están en el mismo frente)...
        return poblacion[i1] if random.random() < 0.5 else poblacion[i2] # Elegimos a uno de los dos tirando una moneda (50/50)

def optimizacion_nsgaii(alertas: List[Alerta], inicio_reloj: int, generaciones=15, pop_size=20) -> List[int]:
    """ Función que ejecuta la Optimización Multiobjetivo (NSGA-II) y Elitismo Avanzado """
    # Generar población inicial aleatoria (lista de listas de analistas aleatorios)
    poblacion = [[random.randint(1, N_ANALISTAS) for _ in alertas] for _ in range(pop_size)]
    
    for gen in range(generaciones): # Bucle principal que evoluciona la población generación a generación
        # Evaluamos a toda la población (obtenemos una lista de tuplas (F1, F2))
        objetivos = [evaluar_multiobjetivo(ind, alertas, inicio_reloj) for ind in poblacion]
        
        # 3. Elitismo Avanzado: Descubrir el "Frente de Pareto 1" (las mejores soluciones no dominadas)
        frente_1 = [] # Inicializamos la lista de la élite
        for i, obj_i in enumerate(objetivos): # Revisamos cada individuo de la población
            # Preguntamos: ¿Existe algún otro individuo 'j' que domine a nuestro individuo 'i'?
            es_dominado = any(domina(obj_j, obj_i) for j, obj_j in enumerate(objetivos) if i != j)
            if not es_dominado: # Si NADIE lo domina, entonces es un individuo de Élite (pertenece al Frente 1)
                frente_1.append(poblacion[i]) # Lo guardamos en el grupo de élite
        
        # Calculamos cuántos lugares le damos a la élite (top 5% de la población total, asegurando mínimo 1)
        n_elite = max(1, int(pop_size * P_ELITISMO))
        # Seleccionamos solo los primeros 'n_elite' individuos del Frente 1 (o el primero de la población si falló algo)
        elite = frente_1[:n_elite] if frente_1 else [poblacion[0]]
        
        nueva_pob = list(elite) # La nueva generación arranca teniendo ya a la élite guardada intacta (Elitismo)
        
        while len(nueva_pob) < pop_size: # Mientras no hayamos llenado la nueva generación con hijos...
            padre1 = seleccion_por_torneo(poblacion, objetivos) # Seleccionamos el primer padre por torneo
            padre2 = seleccion_por_torneo(poblacion, objetivos) # Seleccionamos el segundo padre por torneo
            
            # Operador de Crossover (Cruza de 1 punto)
            punto = random.randint(1, max(1, len(alertas)-1)) # Elegimos un punto de corte al azar en el medio del cromosoma
            hijo = padre1[:punto] + padre2[punto:] # Creamos al hijo pegando la primera mitad del padre1 y la segunda del padre2
            
            # Operador de Mutación
            if random.random() < 0.10: # Le damos un 10% de probabilidad fija a mutar
                # Elegimos un gen (alerta) al azar y le asignamos un nuevo analista al azar (del 1 al N_ANALISTAS)
                hijo[random.randint(0, len(hijo)-1)] = random.randint(1, N_ANALISTAS)
                
            nueva_pob.append(hijo) # Guardamos el nuevo hijo mutado en la nueva generación
            
        poblacion = nueva_pob[:pop_size] # Reemplazamos la población antigua por la nueva (recortando si sobraron hijos)

    # Al finalizar todas las generaciones, evaluamos a la población final
    objetivos_finales = [evaluar_multiobjetivo(ind, alertas, inicio_reloj) for ind in poblacion]
    # Elegimos al "ganador absoluto" seleccionando aquel con el menor F1 (Tiempos + Penalizaciones), dándole prioridad operativa al SOC
    mejor_idx = min(range(len(poblacion)), key=lambda i: objetivos_finales[i][0])
    return poblacion[mejor_idx] # Retornamos el mejor cromosoma

def scheduling_dinamico(alertas_totales: List[Alerta]) -> None:
    """ 4. Scheduling Dinámico (Simula la llegada de alertas en tiempo real en lotes de 30 mins) """
    print("--- INICIANDO SCHEDULING DINÁMICO ---") # Aviso de inicio en consola
    alertas_totales.sort(key=lambda a: a.llegada_min) # Ordenamos cronológicamente todas las alertas
    
    reloj_actual = 0 # Iniciamos el reloj del turno SOC en el minuto 0
    while alertas_totales: # Mientras queden alertas por procesar en la lista maestra...
        # Extraer el lote actual: filtramos las alertas que llegaron ANTES o DURANTE nuestra ventana actual de tiempo (ej. minuto 0 a 30)
        lote_actual = [a for a in alertas_totales if a.llegada_min <= reloj_actual + VENTANA_TIEMPO_MINUTOS]
        
        if not lote_actual: # Si en esta media hora no llegó ninguna alerta nueva...
            reloj_actual += VENTANA_TIEMPO_MINUTOS # Avanzamos el reloj a la siguiente media hora
            continue # Saltamos a la próxima iteración del bucle
            
        # Borramos las alertas del lote actual de la lista maestra total, para no volver a procesarlas
        alertas_totales = [a for a in alertas_totales if a not in lote_actual]
        
        # Mostramos qué está pasando en este minuto simulado
        print(f"[{reloj_actual:03d} min] Lote de {len(lote_actual)} alertas recibidas. Optimizando NSGA-II...")
        
        # Llamamos a nuestro genético multiobjetivo pero SOLO con las alertas de este pequeño lote
        mejor_asignacion = optimizacion_nsgaii(lote_actual, inicio_reloj=reloj_actual)
        # Evaluamos la asignación ganadora para obtener e imprimir sus métricas F1 y F2
        obj1, obj2 = evaluar_multiobjetivo(mejor_asignacion, lote_actual, reloj_actual)
        
        # Imprimimos los resultados del lote
        print(f" -> Asignación lista. F1 (Tiempos): {obj1:.1f} | F2 (Desbalance): {obj2:.2f}")
        
        reloj_actual += VENTANA_TIEMPO_MINUTOS # Avanzamos el reloj otra media hora para procesar el próximo bloque

# Bloque estándar para pruebas locales cuando se ejecuta este script directo
if __name__ == "__main__":
    from main import derivar_alertas_desde_dataset # Importamos la función de recolección de datos
    alertas_muestra = derivar_alertas_desde_dataset()[:200]  # Recortamos a solo 200 alertas para que la demo corra rápido
    scheduling_dinamico(alertas_muestra) # Le pasamos la muestra al simulador dinámico
    print("Simulación Dinámica Completada con Éxito.") # Aviso final

