# Presentación del TPI: asignación de alertas en un SOC

Guion de diapositivas para una exposición de aproximadamente 20 minutos, dividida entre cuatro integrantes. Cada diapositiva incluye qué mostrar, qué explicar y dónde respaldarlo en el código.

## Reparto sugerido

| Integrante | Diapositivas | Tema |
|---|---:|---|
| 1 | 1 a 4 | Problema, SOC y datos |
| 2 | 5 a 7 | Cromosoma, simulación y fitness |
| 3 | 8 a 10 | Evolución, parámetros y visualización |
| 4 | 11 a 14 | Resultados, límites y cierre |

---

## Diapositiva 1 - Problema y objetivo

**Responsable:** Integrante 1

### En pantalla

- Título: *Optimización de la asignación de alertas de seguridad en un SOC*.
- Un esquema simple: alertas entrantes -> analistas -> alertas atendidas o pendientes.
- Objetivo: priorizar alertas críticas y distribuir la carga.

### Qué decir

“Un SOC es un equipo que controla alertas de seguridad. Recibe muchas alertas, pero tiene pocos analistas para atenderlas. No alcanza con repartirlas en orden: también debemos mirar qué tan urgente es cada una, cuánto puede tardar y cuánto tiempo tenemos para empezar a atenderla. Para buscar un buen reparto usamos un Algoritmo Genético, que prueba muchas opciones y conserva las mejores.”

### Conceptos clave

- **SOC:** equipo que monitorea eventos de seguridad y responde a incidentes.
- **SLA:** tiempo máximo de espera acordado para comenzar a atender una alerta.
- **Scheduling:** planificación de quién atiende cada tarea y cuándo.

### Código relacionado

- Modelo de configuración: [`N_ANALISTAS`, `N_ALERTAS` y `HORIZONTE_MINUTOS`](main.py#L35-L42).
- Modelo de alerta: [`Alerta`](main.py#L66).

---

## Diapositiva 2 - Por qué la asignación es difícil

**Responsable:** Integrante 1

### En pantalla

- Comparación entre una regla secuencial y una asignación que considera prioridad.
- Relación entre demanda y capacidad:

```text
Demanda aproximada: 20.600 minutos-analista
Capacidad del turno: 4.800 minutos-analista
Relación: 4,3 veces más demanda que capacidad
```

### Qué decir

“El ejemplo tiene más trabajo del que el equipo puede terminar. Diez analistas trabajando 480 minutos no alcanzan para resolver 500 alertas que duran, en promedio, 41,2 minutos. Por eso algunas van a quedar pendientes. A esas alertas pendientes las llamamos backlog. Lo importante no es solo contar cuántas quedan, sino cuidar primero las más urgentes.”

### Conceptos clave

- **Backlog:** alertas que terminan después del minuto 480.
- **Carga:** minutos de trabajo asignados a un analista.
- **NP-hard:** problema para el que no se conoce un método eficiente que garantice el óptimo en instancias grandes.

### Código relacionado

- Horizonte del turno: [`HORIZONTE_MINUTOS`](main.py#L42).
- Cálculo de backlog y capacidad dentro de [`_evaluar_asignacion()`](main.py#L179).

---

## Diapositiva 3 - Datos: CICIDS2017 y atributos derivados

**Responsable:** Integrante 1

### En pantalla

| Viene del dataset | Se deriva para el modelo SOC |
|---|---|
| Flujo de red | Severidad |
| Etiqueta `DDoS` o `BENIGN` | Prioridad |
| Bytes y paquetes por segundo | Duración estimada |
| Orden de captura | SLA |

### Qué decir

“El dataset CICIDS2017 nos da registros de tráfico de red, pero no nos dice qué prioridad tiene cada alerta ni cuánto debería tardar un analista. La función `derivar_alertas_desde_dataset()` toma 500 registros, mide la intensidad del tráfico y agrega prioridad, severidad, duración y tiempo máximo de espera. Por eso decimos que son alertas derivadas: parten de datos reales, pero esos datos operativos los construye nuestro modelo.”

### Reglas principales

- DDoS con severidad alta -> prioridad `Critica` o `Alta`.
- Tráfico benigno -> prioridad `Media` o `Baja`.
- SLA: Crítica 30 min, Alta 60, Media 120, Baja 240.
- Duración: base según prioridad + componente de severidad + ruido reproducible.

### Código relacionado

- Transformación completa: [`derivar_alertas_desde_dataset()`](main.py#L82).
- Clasificación: [`_clasificar_prioridad()`](main.py#L75).
- SLA por prioridad: [`SLA_POR_PRIORIDAD`](main.py#L47).
- Archivo generado: `outputs/alertas_derivadas_dataset.csv`.

---

## Diapositiva 4 - Instancia de estudio

**Responsable:** Integrante 1

### En pantalla

| Prioridad | Cantidad |
|---|---:|
| Crítica | 85 |
| Alta | 207 |
| Media | 111 |
| Baja | 97 |
| **Total** | **500** |

También mostrar las primeras filas de `outputs/alertas_derivadas_dataset.csv`.

### Qué decir

“En nuestra prueba usamos 500 alertas. Su severidad promedio es 53,5 y cada una tarda, en promedio, 41,2 minutos en resolverse. Estos números describen la prueba que armamos; no vienen directamente del dataset original.”

### Frase puente

“Ya tenemos las alertas y sabemos que la capacidad no alcanza. Ahora vemos cómo se representa una posible asignación y cómo se decide si es buena.”

### Código relacionado

- Estructura de cada registro: [`Alerta`](main.py#L66).
- Exportación de la instancia: [`_guardar_alertas_derivadas()`](main.py#L156).

---

## Diapositiva 5 - Representación cromosómica

**Responsable:** Integrante 2

### En pantalla

```text
[2, 4, 4, 1]

alerta 1 -> analista 2
alerta 2 -> analista 4
alerta 3 -> analista 4
alerta 4 -> analista 1
```

Con 500 alertas, el cromosoma tiene 500 genes. Cada valor está entre 1 y 10.

### Qué decir

“Representamos cada solución como una lista. Cada lugar de la lista corresponde a una alerta y el número que aparece allí indica qué analista la atiende. Por ejemplo, el 2 significa analista 2. Como solo usamos números del 1 al 10, las soluciones que generamos siempre son válidas y no tenemos que corregirlas después.”

### Conceptos clave

- **Cromosoma:** asignación completa.
- **Gen:** posición que representa una alerta.
- **Alelo:** valor que identifica al analista.

### Código relacionado

- Generación de cromosomas: [`generar_poblacion()`](main.py#L163).
- Primera solución Round-Robin: bloque inicial de [`generar_poblacion()`](main.py#L163).

---

## Diapositiva 6 - Simulación de una asignación

**Responsable:** Integrante 2

### En pantalla

Diagrama simple por analista:

```text
Analista 1: [alerta] [alerta crítica]     [alerta]
Analista 2:       [alerta] [alerta alta]
Tiempo:       llegada -> espera -> inicio -> fin
```

### Qué decir

“Para saber si una solución sirve, simulamos el turno completo. Cada analista trabaja con su propia cola. Cuando queda libre, elige primero la alerta de mayor prioridad; si hay empate, mira la severidad y después cuál está más cerca de superar su tiempo máximo de espera, llamado SLA. Con esta simulación podemos medir cuánto espera cada alerta y cuánto trabaja cada analista.”

### Métricas calculadas

- Espera promedio.
- Espera crítica.
- Retraso crítico frente al SLA.
- Makespan.
- Backlog total y ponderado.
- Desbalance y sobrecarga.

### Conceptos clave

- **Makespan:** momento en que termina la última alerta.
- **Desbalance:** desvío estándar de las cargas dividido por la carga media.
- **Espera crítica:** tiempo en cola de las alertas `Critica`.

### Código relacionado

- Motor de simulación: [`_evaluar_asignacion()`](main.py#L179).
- Resumen de cargas: [`_resumen_distribucion()`](main.py#L423).

---

## Diapositiva 7 - Función objetivo y fitness

**Responsable:** Integrante 2

### En pantalla

```text
J = 0,10*T + 0,10*W + 0,20*Wc + 0,25*Rc
    + 0,10*Bp + 0,05*Bm + 0,15*D + 0,05*O

fitness = 1 / (1 + J)
```

### Qué decir

“La fórmula `J` junta varios problemas que queremos reducir: esperas, retrasos, alertas pendientes y diferencias de carga. Como esas medidas usan unidades distintas, primero las llevamos a una escala comparable. Después convertimos `J` en un puntaje llamado fitness. Si `J` es más chico, el fitness es más alto y la solución es mejor. Le damos mucha importancia a las alertas críticas.”

### Aclaración importante

La variable `penalizacion` que aparece en algunos reportes no es exactamente el `J` normalizado que optimiza el AG. Para explicar la función objetivo conviene usar `J` y la fórmula del paper.

### Código relacionado

- Contribuciones del objetivo: [`_evaluar_asignacion()`](main.py#L179).
- Atajo que devuelve el fitness: [`calcular_fitness()`](main.py#L322).

---

## Diapositiva 8 - Ciclo del algoritmo genético

**Responsable:** Integrante 3

### En pantalla

```text
Población inicial
       |
    Evaluar
       |
 Seleccionar padres
       |
 Cruzar y mutar
       |
 Nueva generación
       |
 Repetir 200 veces
```

### Qué decir

“El algoritmo empieza con varias soluciones posibles. En cada vuelta las evalúa, conserva las mejores, combina algunas entre sí y cambia pequeños datos al azar para probar alternativas nuevas. Cada vuelta se llama generación. Repetimos el proceso 200 veces y guardamos la mejor solución encontrada.”

### Código relacionado

- Bucle principal: [`evolucionar()`](main.py#L450).
- Estadísticas por generación: [`calcular_estadisticas()`](main.py#L403).

---

## Diapositiva 9 - Operadores y parámetros

**Responsable:** Integrante 3

### En pantalla

| Parámetro | Valor oficial |
|---|---:|
| Analistas | 10 |
| Alertas | 500 |
| Población | 50 |
| Generaciones | 200 |
| Crossover `Pc` | 0,75 |
| Mutación `Pm` | 0,05 |
| Elitismo | 3 individuos |
| Semilla base | 42 |

### Qué decir

“La prueba principal usa 50 soluciones en cada generación y repite el proceso 200 veces. En el 75 % de los casos combinamos dos soluciones para crear nuevas. Cada alerta tiene un 5 % de probabilidad de cambiar de analista. Además, conservamos las tres mejores soluciones para no perder un buen resultado.”

### Operadores

- [`seleccion_ranking()`](main.py#L354): favorece a los mejores por posición.
- [`crossover()`](main.py#L380): intercambia segmentos de dos padres.
- [`mutacion()`](main.py#L394): reasigna genes al azar.
- Ruleta y torneo: alternativas no usadas oficialmente.

### Nota

Con poblaciones menores, el elitismo cambia porque el código usa `min(3, N // 10)`.

---

## Diapositiva 10 - Grid search, dashboard y Gantt

**Responsable:** Integrante 3

### En pantalla

Mostrar:

- curva de fitness por generación;
- distribución de carga por analista;
- diagrama de Gantt;
- dashboard de Streamlit.

### Qué decir

“También probamos distintas combinaciones de parámetros en una búsqueda corta llamada grid search. Sirvió para explorar opciones, pero no demuestra cuál es la solución perfecta ni reemplaza la configuración principal. El gráfico de Gantt muestra el resultado como una línea de tiempo: cada fila es un analista y cada barra es una alerta que atiende.”

### Código y comandos

- Grid search: [`ejecutar_grid_search()`](hyper_tuner.py#L14).
- Gantt: [`generar_gantt()`](gantt_chart.py#L21).
- Dashboard: [`load_data()`](dashboard.py#L57).

```bash
python hyper_tuner.py
python gantt_chart.py
python -m streamlit run dashboard.py
```

### Precaución

Antes de mostrar el dashboard, cargar población `50` y generaciones `200` si se relanza el algoritmo desde la interfaz. Sus valores por defecto pueden ser menores que la configuración oficial.

---

## Diapositiva 11 - Baselines

**Responsable:** Integrante 4

### En pantalla

| Método | Idea |
|---|---|
| Round-Robin | Reparte en rotación |
| Menor carga | Elige al analista con menos minutos |
| Urgencia balanceada | Prioriza urgencia y luego balancea |
| AG | Busca mediante evolución |

### Qué decir

“Para saber si el algoritmo realmente aporta algo, lo comparamos con reglas simples llamadas baselines. Un baseline es una forma fija de repartir las alertas. Usamos las mismas medidas para todos: así la comparación es justa.”

### Código relacionado

- Round-Robin: [`asignar_round_robin()`](baseline_comparacion.py#L20).
- Menor carga: [`asignar_menor_carga()`](baseline_comparacion.py#L25).
- Urgencia balanceada: [`asignar_urgencia_balanceada()`](baseline_comparacion.py#L36).
- Comparación completa: [`generar_comparativa()`](baseline_comparacion.py#L55).

---

## Diapositiva 12 - Resultados principales

**Responsable:** Integrante 4

### En pantalla

| Métrica | Round-Robin | AG, media de 20 semillas |
|---|---:|---:|
| Espera crítica | 179,0 min | 136,1 min |
| Desbalance `D` | 0,045 | 0,0271 |
| Backlog total | 421 | 425,1 |
| Fitness | - | 0,5282 |
| Tiempo por corrida | - | aproximadamente 34,9 s |

### Qué decir

“Cuando miramos 20 corridas, el algoritmo baja la espera de las alertas críticas de 179 a 136,1 minutos: es una mejora cercana al 24 %. También reparte mejor los minutos de trabajo. El backlog total queda apenas más alto, porque el equipo no tiene capacidad para terminar todo. Por eso no podemos decir que un método gane en todas las medidas.”

### Aclaración

La corrida puntual con semilla 42 muestra 136,0 minutos de espera crítica, 426 alertas de backlog y `D=0,043`. Para las conclusiones conviene usar las 20 semillas, no solamente esa corrida.

### Código y archivos

- Experimento multisemilla: [`ejecutar_experimentos()`](experimentos_multisemilla.py#L12).
- Resultados: `outputs/resumen_multisemilla.csv`.
- Comparación: `outputs/comparativa_baselines.csv`.

---

## Diapositiva 13 - Ablación del makespan

**Responsable:** Integrante 4

### En pantalla

| Configuración | Makespan medio |
|---|---:|
| Peso oficial `w_T=0,10` | 2138,4 min |
| Sin makespan `w_T=0` | 2180,4 min |

### Qué decir

“Para medir la importancia del tiempo total, hicimos una prueba quitando esa parte de la fórmula. A esta prueba la llamamos ablación: significa sacar una pieza y comparar. Sin esa pieza, el tiempo hasta terminar la última alerta aumenta 42 minutos, cerca de un 1,9 %. El cambio es consistente, pero no modifica de manera clara el backlog total ni el reparto de carga.”

### Conceptos clave

- **Ablación:** quitar una parte del modelo para medir su efecto.
- **Wilcoxon:** prueba pareada no paramétrica.
- **Bonferroni:** corrección por realizar varias pruebas.

### Código y archivos

- Ejecución multisemilla: [`ejecutar_experimentos()`](experimentos_multisemilla.py#L12).
- Resultados estadísticos: `outputs/pruebas_wilcoxon.csv`.

### Precaución

La ablación puede sobrescribir los mismos archivos de salida. Guardar la corrida oficial antes de ejecutarla.

---

## Diapositiva 14 - Límites, API y cierre

**Responsable:** Integrante 4

### En pantalla

- El modelo actual es determinista.
- Los atributos operativos son derivados.
- El backlog total está limitado por la capacidad.
- La API es una extensión de integración.
- Trabajo futuro: activos, colaboración Humano-IA y tiempos estocásticos.

### Qué decir

“El algoritmo no reemplaza la decisión del analista ni puede crear más horas de trabajo. Sirve para ordenar y repartir mejor las alertas al comienzo. También tenemos una API, que es una forma de recibir alertas desde otro sistema y devolver una asignación. Esa API usa otra versión del algoritmo, llamada NSGA-II, por lo que no es la misma versión con la que obtuvimos los resultados del paper.”

### Código relacionado

- Estado de la API: [`health_check()`](api_server.py#L37).
- Asignación por lote: [`asignar_lote_alertas()`](api_server.py#L44).
- Trabajo futuro y límites: sección 10 de [`GUIA_EXPOSICION.md`](GUIA_EXPOSICION.md#L580).

### Cierre sugerido

“En resumen, buscamos una mejor forma de repartir alertas entre un grupo limitado de analistas. El algoritmo reduce la espera de las alertas críticas y reparte mejor el trabajo que Round-Robin. Pero no puede eliminar las alertas pendientes porque hay 4,3 veces más trabajo que capacidad. Por eso lo probamos varias veces y lo comparamos con reglas simples: la mejora existe, pero se da sobre todo en las métricas más importantes para las alertas críticas.”

---

## Orden recomendado para la demo

```bash
# Desde la carpeta TPI
python main.py
python baseline_comparacion.py
python gantt_chart.py
python experimentos_multisemilla.py --corridas 20 --peso-tiempo 0.10
python -m streamlit run dashboard.py
```

La API se puede mostrar aparte:

```bash
uvicorn api_server:app --reload
```

Antes de exponer, verificar que `main.py` se haya ejecutado con la configuración oficial y que los archivos de `outputs/` correspondan a esa corrida.
