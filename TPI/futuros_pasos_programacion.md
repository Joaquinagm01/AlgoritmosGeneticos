# 🚀 Checklist de Futuros Pasos de Programación

A partir de la base sólida que ya tenemos en `main.py` (con el dataset CICIDS2017 procesado, la función de aptitud multifactorial funcionando y los CSVs generándose), acá detallo las opciones de programación para avanzar y darle un nivel superior al Trabajo Práctico Integrador (TPI).

## 1. Visualización Temporal Avanzada (El más recomendado)
- [ ] **Crear `gantt_chart.py`**: Escribir un script que lea la asignación final de cada analista y genere un Diagrama de Gantt.
- [ ] **Mapeo de Alertas**: Pintar bloques de tiempo por analista (ej. alertas críticas en rojo, medias en amarillo).
- [ ] **Beneficio**: Demuestra visualmente cómo el Algoritmo Genético "acomoda" las tareas tipo *Tetris* para evitar tiempos muertos y cumplir los SLA. Es el gráfico estrella para cualquier problema de *Scheduling*.

## 2. Validación Empírica (Baseline vs. Genético)
- [ ] **Crear `baseline_comparacion.py`**: Programar un algoritmo de asignación básico (First-Come-First-Serve o Round-Robin).
- [ ] **Correr métricas**: Pasar las mismas alertas derivadas del dataset por este algoritmo básico.
- [ ] **Graficar comparativa**: Hacer un gráfico de barras que compare el "Backlog final", el "Desbalance de carga" y el "Tiempo de espera crítico" entre la asignación manual/tonta vs. nuestro Algoritmo Genético.
- [ ] **Beneficio**: Justifica matemáticamente por qué se justifica la complejidad de usar Algoritmos Genéticos en un SOC.

## 3. Sintonización de Hiperparámetros (Grid Search)
- [ ] **Crear `hyper_tuner.py`**: Un script que corra automáticamente `main.py` con diferentes combinaciones de variables.
- [ ] **Variables a probar**: 
  - Tamaño de población: [10, 20, 50]
  - Probabilidad de mutación: [0.01, 0.05, 0.1]
  - Probabilidad de Crossover: [0.6, 0.75, 0.9]
- [ ] **Beneficio**: Permite decir en el paper que los parámetros elegidos (ej. 0.05 mutación) no fueron al azar, sino que se demostró que eran el óptimo global para este problema.

## 4. Presentación Interactiva (Opcional pero suma puntos)
- [ ] **Crear `dashboard.py` (con Streamlit)**: Armar una mini app web local que levante los archivos de la carpeta `outputs/`.
- [ ] **Interactividad**: Que los profes puedan ver los gráficos generacionales, buscar cómo quedó la carga de un analista en particular y ver la tabla final de alertas filtrando por "Críticas".
- [ ] **Beneficio**: Excelente para la defensa final del TPI.

---
> **Nota para el equipo:** Te sugiero empezar por el **Punto 1 (Diagrama de Gantt)** o el **Punto 2 (Baseline)**. Si querés que programemos alguno de estos ahora mismo, ¡solo decime cuál elegís!
