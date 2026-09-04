# 🧠 Guía de Estudio y Defensa: TPI Algoritmos Genéticos

Este documento es una guía breve para la exposición oral. Resume qué problema resolvemos, cómo funciona la versión actual y qué resultados conviene explicar si los profesores hacen preguntas técnicas.

---

## 1. El Problema Central (¿Qué estamos resolviendo?)
**Problema:** En un Centro de Operaciones de Seguridad (SOC), entran alertas sin parar. Si las asignamos al azar (o al primer analista libre), terminamos con analistas sobrecargados y alertas **Críticas** esperando demasiado tiempo.
**Solución:** Modelamos este problema de asignación (*Job Shop Scheduling*) utilizando un Algoritmo Genético Canónico (AG). 
**Dataset:** No usamos alertas inventadas, usamos el dataset público **CICIDS2017** (capturas de tráfico real con ataques DDoS), al cual le aplicamos heurísticas para derivar SLAs (Tiempos máximos permitidos) y tiempos de resolución.

---

## 2. El Algoritmo Genético (El archivo `main.py`)
Este es el motor del proyecto. Implementa un AG clásico con las siguientes características:

### A. Representación (El Cromosoma)
- **Codificación:** Vector de números enteros.
- **Formato:** Cada posición del vector (índice) representa una **alerta** (del 0 al 499, porque tomamos una muestra de 500 alertas). El **valor** en esa posición es el **ID del analista** (del 1 al 10).
- **Ejemplo:** Si el cromosoma empieza con `[3, 1, 5]`, significa: la alerta 0 va al analista 3; la alerta 1 va al analista 1; la alerta 2 va al analista 5.

### B. Función de Aptitud (Fitness)
- **Diseño:** La evaluación calcula un objetivo normalizado que combina tiempo total, esperas, retraso de alertas críticas, backlog y balance de carga. Como el AG maximiza, usamos `fitness = 1 / (1 + objetivo_normalizado)`.
- **Backlog:** Se pondera por prioridad: dejar pendiente una alerta Crítica cuesta más que dejar pendiente una alerta de prioridad Baja.
- **Conclusión para los profes:** El AG no optimiza una sola métrica. Busca un compromiso entre terminar trabajo, atender antes las alertas críticas y repartir la carga.

### C. Operadores Genéticos Canónicos
- **Selección:** La configuración oficial usa **ranking**. Los individuos se ordenan por fitness y los mejores tienen más probabilidad de ser padres. La ruleta y el torneo quedan disponibles como alternativas.
- **Crossover (Cruzamiento):** De **1 punto**. Se elige un punto al azar en el vector de 500 alertas. La primera mitad se hereda del Padre 1 y la segunda mitad del Padre 2.
- **Mutación:** Por **reasignación aleatoria**. Con una probabilidad de 5% por gen, una alerta puede cambiar de analista. Esto mantiene la diversidad y ayuda a evitar óptimos locales.
- **Elitismo:** Se conservan los mejores individuos de cada generación para no perder una solución ya encontrada.
- **Semilla inicial:** La primera solución de la población es Round-Robin, lo que aporta una referencia desde la primera generación.

---

## 3. Validación y Ajuste (Las Mejoras Empíricas)

Para que el TPI tenga peso científico, agregamos dos herramientas clave:

### A. El Sintonizador de Hiperparámetros (`hyper_tuner.py`)
- **¿Qué es?** Es un script que implementa *Grid Search* (Búsqueda en grilla).
- **¿Por qué lo hicimos?** Para comparar configuraciones de forma sistemática, probamos 18 combinaciones durante 15 generaciones. La mejor configuración exploratoria fue población 20, mutación 0.05 y crossover 0.60; la corrida oficial usa población 50 y 200 generaciones.

### B. La Comparativa Baseline (`baseline_comparacion.py`)
- **¿Qué es?** Un script que compara el AG contra tres reglas deterministas.
- **Baselines:** Round-Robin reparte secuencialmente; Menor carga asigna al analista con menor carga acumulada; Urgencia balanceada prioriza alertas críticas, severidad y SLA antes de asignarlas.
- **Dato importante:** El número de analistas se lee del resumen de la corrida (`n_analistas`). Así, el baseline usa el mismo escenario que el AG aunque se haya cambiado `--n-analistas`.
- **Qué tenés que decir:** *"Round-Robin distribuye de forma simple, pero no considera la urgencia. El AG usa prioridad, SLA y carga para reducir la espera crítica, aunque no necesariamente gana en todas las métricas".*

---

## 4. El Dashboard Interactivo (`dashboard.py`)
Para no tener que mostrar una aburrida terminal negra, construimos una interfaz gráfica usando **Streamlit**.

- **¿Cómo funciona?** No procesa el algoritmo genético en vivo (tardaría mucho). Lee los archivos CSV (los *outputs*) que genera `main.py`.
- **Pestaña 1 (Evolución):** Muestra fitness máximo, mínimo, promedio y desviación estándar por generación.
- **Pestaña 2 (Distribución):** Muestra la carga final por analista, el **Diagrama de Gantt** y la tabla operativa.
- **Pestaña 3 (Comparativa):** La comparación completa se genera con `baseline_comparacion.py`. El resultado se consulta en `outputs/comparativa_baselines.csv` y en tres PNG independientes: espera crítica, backlog y desbalance.
- **Pestaña 4 (Hiperparámetros):** Muestra los resultados del grid search si existe `outputs/grid_search_resultados.csv`.

El dashboard lee los resultados guardados en `outputs/`; no ejecuta el AG en vivo. Primero ejecutá `main.py` y luego, si necesitás actualizar la comparación, `baseline_comparacion.py`.


