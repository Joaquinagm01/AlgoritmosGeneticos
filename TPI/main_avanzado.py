"""
Versión Avanzada del Algoritmo Genético (Ideas a Futuro)
Incluye:
1. Skill-Based Routing (Tiers de Analistas)
2. Optimización Multiobjetivo (NSGA-II simplificado con Frentes de Pareto)
3. Elitismo Avanzado (Top 5% sobrevive)
4. Scheduling Dinámico (Procesamiento por ventanas temporales/lotes)
"""

import random
import statistics
import time
from dataclasses import dataclass
from typing import List, Tuple

# Reutilizamos las clases base de main.py
from main import Alerta, N_ANALISTAS

# Configuraciones Avanzadas
P_ELITISMO = 0.05
VENTANA_TIEMPO_MINUTOS = 30  # Lotes para scheduling dinámico

# 1. Skill-based Routing (Tiers de Analistas)
# Analistas 1 al 3: Senior (Tier 3)
# Analistas 4 al 7: Semi-Senior (Tier 2)
# Analistas 8 al 10: Junior (Tier 1)
def obtener_tier(analista: int) -> int:
    if 1 <= analista <= 3:
        return 3
    elif 4 <= analista <= 7:
        return 2
    else:
        return 1

def evaluar_multiobjetivo(cromosoma: List[int], alertas: List[Alerta], inicio_reloj: int = 0) -> Tuple[float, float]:
    """
    Retorna dos objetivos a MINIMIZAR:
    f1 = Tiempo Total + Penalización por SLAs y Skill-Routing
    f2 = Desbalance de Carga (Varianza)
    """
    cargas = [0] * N_ANALISTAS
    disponibilidad = [inicio_reloj] * N_ANALISTAS
    
    penalizacion_slas = 0.0
    penalizacion_skills = 0.0
    
    asignadas = [[] for _ in range(N_ANALISTAS)]
    for idx, analista in enumerate(cromosoma):
        asignadas[analista - 1].append(alertas[idx])
        
    for i in range(N_ANALISTAS):
        tier = obtener_tier(i + 1)
        asignadas[i].sort(key=lambda a: a.llegada_min)
        
        for alerta in asignadas[i]:
            inicio = max(disponibilidad[i], alerta.llegada_min)
            espera = inicio - alerta.llegada_min
            fin = inicio + alerta.tiempo_estimado_min
            
            disponibilidad[i] = fin
            cargas[i] += alerta.tiempo_estimado_min
            
            # Penalización SLA
            if espera > alerta.sla_min:
                if alerta.prioridad == "Critica":
                    penalizacion_slas += (espera - alerta.sla_min) * 10
                else:
                    penalizacion_slas += (espera - alerta.sla_min) * 2
                    
            # 1. Penalización Skill-based Routing
            if alerta.prioridad in ["Critica", "Alta"] and tier == 1:
                penalizacion_skills += 1000  # Penalización altísima por dar algo crítico a un Junior
            if alerta.prioridad == "Critica" and tier == 2:
                penalizacion_skills += 200   # Penalización media por dar crítico a un Semi-Senior

    tiempo_total = max(disponibilidad) - inicio_reloj
    f1 = tiempo_total + penalizacion_slas + penalizacion_skills
    
    carga_media = sum(cargas) / N_ANALISTAS if N_ANALISTAS else 0
    f2 = statistics.pstdev(cargas) if carga_media > 0 else 0.0
    
    return float(f1), float(f2)

def domina(objA: Tuple[float, float], objB: Tuple[float, float]) -> bool:
    """Devuelve True si la solución A domina a la B (Minimización)"""
    return (objA[0] <= objB[0] and objA[1] <= objB[1]) and (objA[0] < objB[0] or objA[1] < objB[1])

def seleccion_por_torneo(poblacion, objetivos):
    """Selección simple adaptada al multiobjetivo para el NSGA-II"""
    i1, i2 = random.sample(range(len(poblacion)), 2)
    if domina(objetivos[i1], objetivos[i2]):
        return poblacion[i1]
    elif domina(objetivos[i2], objetivos[i1]):
        return poblacion[i2]
    else:
        return poblacion[i1] if random.random() < 0.5 else poblacion[i2]

def optimizacion_nsgaii(alertas: List[Alerta], inicio_reloj: int, generaciones=15, pop_size=20) -> List[int]:
    """ 2. Optimización Multiobjetivo y 3. Elitismo """
    # Generar población
    poblacion = [[random.randint(1, N_ANALISTAS) for _ in alertas] for _ in range(pop_size)]
    
    for gen in range(generaciones):
        objetivos = [evaluar_multiobjetivo(ind, alertas, inicio_reloj) for ind in poblacion]
        
        # 3. Elitismo Avanzado: Guardar el Top 5% del Frente Pareto 1
        # (Acá hacemos un filtro simplificado para quedarnos con los no-dominados)
        frente_1 = []
        for i, obj_i in enumerate(objetivos):
            es_dominado = any(domina(obj_j, obj_i) for j, obj_j in enumerate(objetivos) if i != j)
            if not es_dominado:
                frente_1.append(poblacion[i])
        
        # Elitismo: top 5% (al menos 1)
        n_elite = max(1, int(pop_size * P_ELITISMO))
        elite = frente_1[:n_elite] if frente_1 else [poblacion[0]]
        
        nueva_pob = list(elite)
        
        while len(nueva_pob) < pop_size:
            padre1 = seleccion_por_torneo(poblacion, objetivos)
            padre2 = seleccion_por_torneo(poblacion, objetivos)
            
            # Crossover
            punto = random.randint(1, max(1, len(alertas)-1))
            hijo = padre1[:punto] + padre2[punto:]
            
            # Mutación
            if random.random() < 0.10:
                hijo[random.randint(0, len(hijo)-1)] = random.randint(1, N_ANALISTAS)
                
            nueva_pob.append(hijo)
            
        poblacion = nueva_pob[:pop_size]

    # Al finalizar, devolver el mejor del frente 1 evaluando F1 como prioridad para el SOC
    objetivos_finales = [evaluar_multiobjetivo(ind, alertas, inicio_reloj) for ind in poblacion]
    mejor_idx = min(range(len(poblacion)), key=lambda i: objetivos_finales[i][0])
    return poblacion[mejor_idx]

def scheduling_dinamico(alertas_totales: List[Alerta]) -> None:
    """ 4. Scheduling Dinámico (En tiempo real) """
    print("--- INICIANDO SCHEDULING DINÁMICO ---")
    alertas_totales.sort(key=lambda a: a.llegada_min)
    
    reloj_actual = 0
    while alertas_totales:
        # Extraer lote de la ventana de tiempo
        lote_actual = [a for a in alertas_totales if a.llegada_min <= reloj_actual + VENTANA_TIEMPO_MINUTOS]
        
        if not lote_actual:
            reloj_actual += VENTANA_TIEMPO_MINUTOS
            continue
            
        alertas_totales = [a for a in alertas_totales if a not in lote_actual]
        
        print(f"[{reloj_actual:03d} min] Lote de {len(lote_actual)} alertas recibidas. Optimizando NSGA-II...")
        
        mejor_asignacion = optimizacion_nsgaii(lote_actual, inicio_reloj=reloj_actual)
        obj1, obj2 = evaluar_multiobjetivo(mejor_asignacion, lote_actual, reloj_actual)
        
        print(f" -> Asignación lista. F1 (Tiempos): {obj1:.1f} | F2 (Desbalance): {obj2:.2f}")
        
        reloj_actual += VENTANA_TIEMPO_MINUTOS

if __name__ == "__main__":
    # Prueba del script localmente
    from main import derivar_alertas_desde_dataset
    alertas_muestra = derivar_alertas_desde_dataset()[:200]  # Probamos con 200 alertas
    scheduling_dinamico(alertas_muestra)
    print("Simulación Dinámica Completada con Éxito.")
