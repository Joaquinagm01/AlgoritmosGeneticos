# 🧠 Guía de Estudio y Defensa: TPI Algoritmos Genéticos

Este documento es tu "machete" o guía de estudio completa para la exposición oral. Aquí explicamos, a nivel de código y diseño, todo lo que construimos, por qué lo hicimos y cómo funciona. El objetivo es que tengas las respuestas claras si los profesores te hacen preguntas técnicas.

---

## 1. El Problema Central (¿Qué estamos resolviendo?)
**Problema:** En un Centro de Operaciones de Seguridad (SOC), entran alertas sin parar. Si las asignamos al azar (o al primer analista libre), terminamos con analistas sobrecargados y alertas **Críticas** esperando demasiado tiempo.
**Solución:** Modelamos este problema de asignación (*Job Shop Scheduling*) utilizando un Algoritmo Genético Canónico. 
**Dataset:** No usamos alertas inventadas, usamos el dataset público **CICIDS2017** (capturas de tráfico real con ataques DDoS), al cual le aplicamos heurísticas para derivar SLAs (Tiempos máximos permitidos) y tiempos de resolución.

---

## 2. El Algoritmo Genético (El archivo `main.py`)
Este es el motor del proyecto. Implementa un AG clásico con las siguientes características:

### A. Representación (El Cromosoma)
- **Codificación:** Vector de números enteros.
- **Formato:** Cada posición del vector (índice) representa una **alerta** (del 0 al 499, porque tomamos una muestra de 500 alertas). El **valor** en esa posición es el **ID del analista** (del 1 al 10).
- **Ejemplo:** Si el cromosoma empieza con `[3, 1, 5]`, significa: la alerta 0 va al analista 3; la alerta 1 va al analista 1; la alerta 2 va al analista 5.

### B. Función de Aptitud (Fitness)
- **Diseño:** Es una función de *minimización* convertida a *maximización*. La fórmula es: `1 / (1 + tiempo_total_estimado + penalizaciones)`.
- **Las Penalizaciones:** Aquí está el secreto. El algoritmo suma castigos altísimos si se incumple el SLA de una alerta Crítica o si un analista queda con mucha más carga que los demás (desbalance).
- **Conclusión para los profes:** El algoritmo es inteligente porque sabe *sacrificar* un poco el balance de carga si eso significa atender más rápido una alerta roja.

### C. Operadores Genéticos Canónicos
- **Selección:** Usamos **Ruleta**. Los cromosomas con mayor fitness tienen una "porción" más grande en la ruleta, por lo tanto, mayor probabilidad de reproducirse.
- **Crossover (Cruzamiento):** De **1 punto**. Se elige un punto al azar en el vector de 500 alertas. La primera mitad se hereda del Padre 1 y la segunda mitad del Padre 2.
- **Mutación:** Por **reasignación aleatoria**. Con una probabilidad baja (ej: 5%), se agarra una alerta al azar y se le cambia el analista por otro aleatorio. Esto mantiene la diversidad en la población e impide caer en óptimos locales.

---

## 3. Validación y Ajuste (Las Mejoras Empíricas)

Para que el TPI tenga peso científico, agregamos dos herramientas clave:

### A. El Sintonizador de Hiperparámetros (`hyper_tuner.py`)
- **¿Qué es?** Es un script que implementa *Grid Search* (Búsqueda en grilla).
- **¿Por qué lo hicimos?** Si en la defensa te preguntan *"¿Por qué eligieron una mutación del 10%?"*, en lugar de decir "porque sí", podés responder: *"Programamos un script que probó 18 combinaciones diferentes iterando variables. El Grid Search nos demostró estadísticamente que Población=10, Mutación=0.10 y Crossover=0.75 maximizaba el fitness global (0.000061)"*.

### B. La Comparativa Baseline (`baseline_comparacion.py`)
- **¿Qué es?** Un script que compara nuestro AG contra un asignador tradicional (Round-Robin).
- **El Round-Robin:** Asigna las alertas "una para vos, una para mí". (Analista 1, 2, 3... 10, y repite).
- **El resultado (Lo que tenés que decir):** *"El Round-Robin es casi matemáticamente perfecto en balancear la cantidad de alertas... pero es tonto. No mira la criticidad. Nuestro Algoritmo Genético, como prioriza los SLA críticos, logra reducir el tiempo de espera promedio de los incidentes más graves de la red. Sacrifica la simetría numérica para ganar eficiencia operativa".*

---

## 4. El Dashboard Interactivo (`dashboard.py`)
Para no tener que mostrar una aburrida terminal negra, construimos una interfaz gráfica usando **Streamlit**.

- **¿Cómo funciona?** No procesa el algoritmo genético en vivo (tardaría mucho). Lee los archivos CSV (los *outputs*) que genera `main.py`.
- **Pestaña 1 (Evolución):** Muestra el típico gráfico que pide la cátedra (Fitness Máximo, Mínimo y Promedio) para demostrar que nuestra población converge con el paso de las generaciones.
- **Pestaña 2 (Distribución):** Aquí está la estrella del TP: el **Diagrama de Gantt**. Demuestra de manera visual (como si fuera un calendario) cómo se organizó el trabajo a lo largo del turno de 8 horas.
- **Pestaña 3 y 4:** Muestran los gráficos generados por el Baseline y la tabla del Grid Search.

---

## 💡 Tips Finales para la Exposición
1. **Puntualidad Conceptual:** No leas el código línea por línea. Los profes quieren saber si entendés **qué** hace la Selección por Ruleta y **qué** representa tu función de Fitness.
2. **Impacto:** Hacé mucho hincapié en que usaron un **Dataset Real (CICIDS2017)**. Eso eleva la calidad del trabajo muy por encima del promedio que suele usar datos sintéticos.
3. **Muestra el Dashboard:** Cerrá tu presentación abriendo el Streamlit. Eso da una impresión de profesionalismo (frontend, gráficas interactivas) que suele garantizar la promoción directa.
