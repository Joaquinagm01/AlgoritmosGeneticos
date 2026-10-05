# Guía para exponer el TPI: asignación de alertas en un SOC

Esta guía resume el paper y lo traduce a una explicación oral para **cuatro expositores**. Cada parte es autónoma: tiene su propio recuadro de **palabras clave** (con la explicación en lenguaje simple), un guion, qué archivo mostrar y una frase para pasarle la palabra al siguiente. Así, quien exponga puede explicar cada término sin depender de lo que dijo el compañero anterior.

La documentación académica completa está en [docs/informe.html](docs/informe.html) y el artículo en [docs/articulo_v2.tex](docs/articulo_v2.tex). La idea no es memorizar cada línea, sino poder explicar qué problema se modeló, cómo se toma la decisión de asignación y qué muestran realmente los experimentos.

> **Revisión de esta versión:** todas las cifras y los enlaces a líneas de código fueron contrastados con el paper (`articulo_v2.pdf`) y con los scripts `.py`. Al final (sección 9) hay un listado de lo que se corrigió y de los puntos del proyecto que conviene verificar o evitar decir en voz alta.

---

## 0. Reparto entre los 4 integrantes

Tiempos sugeridos para ~20 minutos en total (escalar proporcionalmente si la cátedra da más o menos). Completar los nombres.

| Parte | Integrante | Tiempo | Tema | Qué se muestra |
|---|---|---|---|---|
| **1** | _(nombre)_ | ~5 min | Problema, contexto y datos | `derivar_alertas_desde_dataset()`, `alertas_derivadas_dataset.csv` |
| **2** | _(nombre)_ | ~5 min | Cómo se modela una solución y cómo se evalúa (cromosoma + fitness) | `generar_poblacion()`, `_evaluar_asignacion()` |
| **3** | _(nombre)_ | ~5 min | Cómo evoluciona la población, parámetros y demo en vivo | `evolucionar()`, operadores, `grid_search`, dashboard, Gantt |
| **4** | _(nombre)_ | ~5 min | Resultados, límites y cierre | baselines, 20 semillas, ablación, API (extensión) |

**Reglas para que se note que es un solo trabajo:**

- Cada parte termina con una **frase puente** que anticipa lo que sigue.
- Si alguien usa un término de otra parte, lo vuelve a aclarar en una frase (los recuadros de palabras clave están para eso).
- Las preguntas del público se contestan por quien tenga la parte correspondiente (hay una etiqueta `[P1]`…`[P4]` en la sección 8). Si la pregunta cruza partes, contesta quien la recibió y completa quien corresponda.

---

## 1. Mensaje central (lo tienen que saber los cuatro)

Un **Centro de Operaciones de Seguridad (SOC)** (el equipo que vigila eventos de seguridad informática, investiga alertas y responde a incidentes) recibe más alertas de las que un equipo limitado puede investigar dentro de un turno. Repartirlas de manera pareja no alcanza: también importan la **prioridad**, la **severidad**, el **tiempo estimado de resolución** y el **SLA** de cada alerta.

El proyecto formula esa decisión como un problema de **asignación y scheduling** (planificar quién atiende qué y cuándo) y usa un **Algoritmo Genético Canónico** (una técnica de búsqueda inspirada en la evolución biológica) para encontrar una distribución que:

- reduzca la espera, especialmente para las alertas críticas;
- reduzca los retrasos respecto del SLA;
- mantenga razonablemente equilibrada la carga entre analistas;
- reduzca el tiempo total hasta terminar el lote;
- priorice mejor qué alertas quedan pendientes cuando la capacidad no alcanza.

**La conclusión correcta del paper es matizada:** el AG mejora la espera crítica y el desbalance promedio frente a Round-Robin, pero no domina todas las métricas. En esta instancia el backlog total está determinado principalmente por una demanda mucho mayor que la capacidad del turno. Además, una regla simple como "urgencia balanceada" reparte mejor la carga que el AG; el AG, en cambio, obtiene una espera crítica menor. No existe un ganador en todas las métricas a la vez.

---

## 2. Glosario general

Los términos están agrupados por tema. En cada parte de la exposición se repiten los que se necesitan.

### 2.1 Mundo SOC

| Término | Explicación sencilla |
|---|---|
| **SOC** | *Security Operations Center*. Equipo que monitorea eventos de seguridad, investiga alertas y responde a incidentes. |
| **Alerta** | Aviso automático de que algo podría ser un problema de seguridad. En el modelo tiene: minuto de llegada, prioridad, severidad, duración estimada y SLA. |
| **Alert fatigue (fatiga de alertas)** | Cansancio de los analistas por recibir demasiadas alertas, muchas de ellas falsas. Provoca que ignoren o posterguen alertas que sí importan. |
| **Falso positivo** | Alerta que parece un ataque pero no lo es. |
| **Triaje** | Ordenar y decidir qué atender primero (como en una guardia médica). |
| **Prioridad** | Nivel de urgencia de una alerta: Baja, Media, Alta o Crítica. |
| **Severidad** | Puntaje de 1 a 100 de qué tan dañina parece la alerta. |
| **SLA** | *Service Level Agreement*. Tiempo máximo acordado para empezar a atender una alerta. En el código se mide sobre la **espera en cola** (desde que llega hasta que un analista la empieza), no sobre el tiempo de resolución. |
| **Analista** | Persona del SOC que investiga una alerta. En el modelo son 10 por defecto. |
| **Turno / horizonte** | Ventana de trabajo: 480 minutos (8 horas). |
| **SIEM / SOAR** | Herramientas que centralizan las alertas (SIEM) y automatizan respuestas (SOAR). Solo aparecen en la demo de la API. |

### 2.2 Problema de optimización

| Término | Explicación sencilla |
|---|---|
| **Scheduling** | Planificar quién hace cada tarea y en qué momento. |
| **JSP** | *Job Shop Scheduling Problem*: asignar tareas con duraciones a recursos limitados (acá, alertas a analistas). |
| **SJSP** | Versión estocástica del JSP, donde las duraciones son inciertas. El paper la menciona como **extensión futura**; el modelo actual usa tiempos estimados fijos. |
| **NP-hard** | Clase de problemas para los que no se conoce un método eficiente que garantice la solución óptima cuando el problema es grande. Por eso se usan métodos que buscan *buenas* soluciones sin garantizar la óptima. |
| **Determinista / estocástico** | Determinista: mismo dato de entrada, mismo resultado. Estocástico: incluye azar o incertidumbre. |
| **Heurística** | Regla práctica y simple que da una solución razonable sin garantizar que sea la mejor. |
| **Backlog** | Alertas que no terminaron de resolverse al llegar el minuto 480 (en el código: las que **finalizan después** del minuto 480). |
| **Backlog ponderado** | Backlog que cuenta más una alerta pendiente cuanto más prioritaria es (pesos: Baja 0,5 / Media 1 / Alta 2 / Crítica 4). |
| **Carga** | Minutos de trabajo asignados a un analista. |
| **Desbalance de carga (D)** | Qué tan desparejo es el reparto: desvío estándar de las cargas dividido la carga media. 0 = reparto perfecto. |
| **Sobrecarga relativa (O)** | Proporción del trabajo total que está por encima de la carga media de los analistas que más trabajan. |
| **Makespan** | Minuto en que termina la **última** alerta. No es un promedio: es el final del cronograma. |
| **Espera** | Minutos que una alerta espera en cola antes de que alguien empiece a trabajarla. |
| **Espera / retraso crítico** | Espera de las alertas Críticas, y cuánto se pasa esa espera del SLA (30 min). |

### 2.3 Algoritmo genético

| Término | Explicación sencilla |
|---|---|
| **Algoritmo Genético (AG)** | Método de búsqueda que imita la evolución: se parte de muchas soluciones, se quedan las mejores, se combinan y se modifican un poco, y se repite muchas veces. |
| **Canónico** | Versión clásica del AG (la de Holland): selección, cruzamiento, mutación y elitismo, sin variantes sofisticadas. |
| **Cromosoma** | Una solución completa. Acá: la lista que dice qué analista atiende cada alerta. |
| **Gen / alelo** | Cada posición del cromosoma es un gen (una alerta); el valor guardado es el alelo (el analista asignado). |
| **Población** | Conjunto de cromosomas (soluciones) que compiten en cada vuelta. |
| **Generación** | Una vuelta completa del ciclo evolutivo. |
| **Fitness (aptitud)** | Puntaje de calidad de una solución. Acá, cuanto **más alto, mejor**. |
| **Selección** | Elegir qué soluciones se "reproducen". Más chances para las mejores. |
| **Selección por ranking** | Se ordenan las soluciones de peor a mejor y la probabilidad depende de la **posición**, no del valor exacto del fitness. Evita que pequeñas diferencias de puntaje dominen la elección. |
| **Ruleta / torneo** | Otras formas de selección implementadas: ruleta (chances proporcionales al fitness) y torneo (se sortea un grupo de 3 y gana el mejor). No se usan en la configuración oficial. |
| **Cruzamiento (crossover) de un punto** | Se corta el cromosoma de dos padres en un punto y se intercambian las colas para generar dos hijos. |
| **Mutación** | Cambio al azar de algunos genes (acá: reasignar una alerta a un analista sorteado). Aporta variedad. |
| **Elitismo** | Las mejores soluciones pasan intactas a la generación siguiente para no perder lo ya logrado. |
| **Semilla (seed)** | Número que fija el azar de la computadora: misma semilla, mismo resultado. Permite **reproducir** corridas. |
| **Normalizar** | Pasar magnitudes con unidades distintas (minutos, alertas, proporciones) a una escala comparable, para poder sumarlas. |
| **Hiperparámetro** | Ajuste del algoritmo que se elige a mano (tamaño de población, probabilidades, generaciones). |
| **Grid search** | Probar todas las combinaciones de una grilla de hiperparámetros. |

### 2.4 Evaluación y estadística

| Término | Explicación sencilla |
|---|---|
| **Baseline** | Regla simple de referencia contra la que se compara el AG. |
| **Round-Robin** | Repartir las alertas en rotación (1, 2, 3 … 10, 1, 2 …) sin mirar prioridad ni carga. |
| **Ablación** | Experimento donde se **quita una parte** del modelo para medir cuánto aporta. Acá se quita el peso del makespan (`w_T = 0`). |
| **Wilcoxon (pareado)** | Prueba estadística que compara dos mediciones emparejadas sin suponer que siguen una distribución normal. |
| **p-valor** | Si en realidad no hubiera diferencia, qué tan raro sería ver un resultado como el obtenido. Muy chico (por ejemplo < 0,05) = la diferencia difícilmente sea casualidad. |
| **Significativo** | Diferencia cuyo p-valor está por debajo del umbral elegido. No dice que sea *grande*, solo que no parece azar. |
| **Corrección de Bonferroni** | Cuando se hacen varias pruebas a la vez aumenta la chance de "falsos descubrimientos". Se corrige exigiendo un umbral más estricto: 0,05 / 5 pruebas = 0,01. |
| **Desvío estándar (σ)** | Cuánto se alejan los resultados de su promedio. Chico = resultados estables. |

### 2.5 Datos y herramientas

| Término | Explicación sencilla |
|---|---|
| **CICIDS2017** | Dataset público de tráfico de red con ataques reales y tráfico normal, etiquetados. No trae prioridad, SLA ni duración de análisis. |
| **DDoS** | Ataque que satura un servicio con un volumen enorme de tráfico desde muchos orígenes. |
| **Flujo de red** | Resumen de una comunicación entre dos equipos (bytes, paquetes por segundo, etiqueta, etc.). |
| **Percentil** | Posición relativa: estar en el percentil 90 significa superar al 90 % del resto. |
| **Gantt** | Gráfico de barras en el tiempo: cada barra es una tarea, cada fila un recurso (acá, un analista). |
| **Dashboard** | Panel visual para mirar resultados (hecho con Streamlit). |
| **API REST** | Interfaz para que otro programa le envíe datos por internet y reciba una respuesta. |

---

## 3. Parte 1 — Problema, contexto y datos

**Integrante 1 · ~5 min**

> **Palabras clave de esta parte**
> - **SOC:** equipo que vigila y responde a incidentes de seguridad informática.
> - **Alerta / alert fatigue:** aviso de posible incidente; la fatiga es el cansancio por recibir demasiadas.
> - **SLA:** tiempo máximo de espera acordado antes de empezar a atender una alerta.
> - **Backlog:** alertas que quedan sin terminar al cierre del turno.
> - **JSP / NP-hard:** problema de asignar tareas a recursos limitados, y clase de problemas sin método exacto eficiente para casos grandes.
> - **CICIDS2017 / DDoS / flujo de red:** dataset público de tráfico de red; un DDoS es un ataque por saturación; un flujo es el resumen de una comunicación.
> - **Percentil:** posición relativa dentro del conjunto (el 90 supera al 90 %).

### Guion

1. **El problema.** Un SOC recibe más alertas de las que puede atender. El paper cita un relevamiento (Jalalvand et al.) según el cual la mayoría de las organizaciones recibe más de 10.000 alertas diarias y más del 50 % son falsos positivos. Eso produce fatiga de alertas: se ignoran, se desactivan o se delegan, y sube el riesgo de que una intrusión avance sin ser contenida.
2. **Por qué repartir bien es difícil.** Las prácticas habituales (turnos fijos, reglas estáticas, asignación manual) no consideran a la vez prioridad, SLA, duración estimada y carga ya acumulada de cada analista. El resultado típico: algunos analistas acumulan backlog y otros quedan subutilizados.
3. **Cómo se formaliza.** Asignar tareas con duraciones y recursos limitados es una variante del Job Shop Scheduling (JSP), un problema NP-hard. Por eso se busca una buena solución con un algoritmo genético en lugar de una solución exacta. *(El SJSP —duraciones inciertas— queda como extensión futura; el modelo actual es determinista.)*
4. **Los datos: qué viene del dataset y qué se deriva.** CICIDS2017 contiene flujos de red etiquetados (`DDoS` o `BENIGN`) pero **no** campos de un SOC. El proyecto usa el archivo del viernes por la tarde (DDoS) y le agrega una capa operativa con reglas explícitas, implementada en [`derivar_alertas_desde_dataset()`](main.py#L82):
   1. Toma una muestra aleatoria de 500 flujos (reproducible con la semilla).
   2. Limpia `Flow Bytes/s` y `Flow Packets/s` (valores infinitos o faltantes).
   3. Calcula una **intensidad** del tráfico en escala logarítmica (para que los valores gigantes no aplasten a los chicos) y su **percentil**.
   4. Convierte etiqueta + intensidad en **severidad**: un DDoS queda entre 45 y 100; un flujo benigno, entre 5 y 50.
   5. Asigna **prioridad**: un DDoS con severidad ≥ 80 es `Critica`, si no `Alta`; un benigno con severidad ≥ 30 es `Media`, si no `Baja`.
   6. Reparte las llegadas a lo largo del turno de 480 minutos, respetando el **orden de captura** original.
   7. Estima la **duración de resolución**: base por prioridad (Baja 8, Media 15, Alta 25, Crítica 40 min) + 35 % de la severidad + un ruido reproducible entre −3 y +4 min (mínimo 5 min).
   8. Asigna un **SLA fijo** por prioridad: 30 min `Critica`, 60 `Alta`, 120 `Media`, 240 `Baja` ([`SLA_POR_PRIORIDAD`](main.py#L47)).
5. **La instancia concreta.** 500 alertas: 85 Críticas, 207 Altas, 111 Medias y 97 Bajas. Severidad media 53,5 y duración media 41,2 minutos.
6. **La clave de la instancia: está sobredimensionada a propósito.** 500 alertas × 41,2 min ≈ **20.600 minutos-analista de demanda**; 10 analistas × 480 min = **4.800 de capacidad**. La demanda es ≈ **4,3 veces** la capacidad. Por eso es inevitable que mucha gente "quede fuera del turno", y por eso el backlog total no sirve por sí solo para juzgar el algoritmo (lo retoma la Parte 4).

> **Frase útil:** "El dataset aporta el comportamiento del tráfico; nosotros agregamos una capa operativa explícita para poder estudiar asignación de alertas. Por eso los resultados describen la instancia derivada y no propiedades originales de CICIDS2017."

### Qué mostrar

- [`derivar_alertas_desde_dataset()`](main.py#L82) y la clase [`Alerta`](main.py#L66) (los 6 datos de cada alerta).
- `outputs/alertas_derivadas_dataset.csv` (las primeras filas, para que se vea una alerta concreta).

### Cuidado con el vocabulario

- Decir **"alertas derivadas"** o "construidas a partir del dataset", no "alertas reales". El docstring de `main.py` dice "reales", y el paper dice "simular de forma fiel y rigurosa"; ambas expresiones sobreactúan: los atributos operativos son **sintéticos**.
- Aclarar que 292 de las 500 alertas (Altas + Críticas) provienen de flujos DDoS y 208 (Medias + Bajas) de tráfico benigno; es una consecuencia directa de la regla de prioridad de arriba.

> **Frase puente → Parte 2:** "Ya tenemos las alertas y sabemos que no alcanza la capacidad. Ahora: ¿cómo representamos una posible forma de repartirlas y cómo decidimos si es buena o mala?"

---

## 4. Parte 2 — Cómo se modela una solución y cómo se evalúa

**Integrante 2 · ~5 min**

> **Palabras clave de esta parte**
> - **Cromosoma:** una solución completa, o sea la lista "alerta → analista".
> - **Gen / alelo:** una posición de la lista (una alerta) y el valor que contiene (el analista).
> - **Población inicial:** el primer conjunto de soluciones, antes de evolucionar.
> - **Round-Robin:** repartir en rotación sin mirar nada más.
> - **Espera, retraso crítico, makespan, backlog, desbalance, sobrecarga:** ver glosario (sección 2.2).
> - **Normalizar:** pasar todo a una escala comparable para poder sumarlo.
> - **Fitness:** puntaje de calidad (más alto = mejor).

### Guion

1. **Representación.** Con 500 alertas, un cromosoma tiene 500 genes. Cada gen es un número entre 1 y 10: el analista responsable. Ejemplo corto:

   ```text
   [2, 4, 4, 1]
   ```

   - alerta 1 → analista 2;
   - alerta 2 → analista 4;
   - alerta 3 → analista 4;
   - alerta 4 → analista 1.

   Es una **codificación directa**: la decisión principal (qué analista recibe cada alerta) queda visible en el propio cromosoma, sin capas de traducción. Los valores están acotados al conjunto de analistas disponibles, así que toda solución generada es válida (no hace falta "repararla").

2. **Población inicial.** Se genera en [`generar_poblacion()`](main.py#L163): todo aleatorio, salvo el primer individuo, que es la asignación **Round-Robin**. Eso da una referencia válida desde la primera generación.

3. **Cómo se simula una solución.** [`_evaluar_asignacion()`](main.py#L179) "juega" el turno: cada analista tiene su bandeja de alertas y trabaja una por vez. **Política de atención dinámica:** cuando un analista se libera, elige entre las alertas que **ya llegaron** la de mayor prioridad; si empatan, la de mayor severidad; si vuelve a haber empate, la que tiene menos margen antes de romper el SLA. Si no hay ninguna disponible, espera a la próxima que llegue. De esa simulación salen las métricas:
   - **espera promedio:** cuánto esperan las alertas antes de empezar;
   - **espera crítica:** espera promedio de las `Critica`;
   - **retraso crítico:** cuánto se pasa la espera de las críticas por encima de su SLA (si cumplió, 0);
   - **makespan:** minuto en que termina la última alerta;
   - **backlog:** alertas que terminan después del minuto 480;
   - **backlog ponderado:** igual, pero una crítica pendiente pesa 4 y una baja 0,5;
   - **desbalance:** desvío estándar de las cargas ÷ carga media;
   - **sobrecarga relativa:** parte del trabajo que está por encima de la carga media.

4. **Del conjunto de métricas a un solo puntaje.** El AG necesita un número único por solución. El objetivo normalizado `J` (a minimizar) se transforma en fitness (a maximizar):

   ```text
   J = 0.10*T + 0.10*W + 0.20*Wc + 0.25*Rc
       + 0.10*Bp + 0.05*Bm + 0.15*D + 0.05*O
   fitness = 1 / (1 + J)
   ```

   Si `J` baja, el fitness sube. En el paper las variables llevan un **sombrero (^)** que indica que están **normalizadas**:

   | Símbolo | Qué es | Cómo se normaliza en el código | Peso |
   |---|---|---|---|
   | `T` | Makespan | tiempo total ÷ 480 | 0,10 (0 en la ablación) |
   | `W` | Espera promedio | espera ÷ 480 | 0,10 |
   | `Wc` | Espera crítica | espera crítica ÷ 480 | 0,20 |
   | `Rc` | Retraso crítico frente al SLA | retraso ÷ 480 | 0,25 |
   | `Bp` | Backlog ponderado por prioridad | backlog ponderado ÷ (4 × n.º de alertas) | 0,10 |
   | `Bm` | Minutos de backlog | minutos ÷ (n.º de alertas × 480) | 0,05 |
   | `D` | Desbalance de carga | ya es relativo (σ ÷ media) | 0,15 |
   | `O` | Sobrecarga relativa | ya es relativa | 0,05 |

   Los pesos suman 1. Casi la mitad (0,45) está puesta en las alertas críticas (`Wc` + `Rc`): esa es la prioridad operativa que expresa el modelo.

5. **Qué NO decir.** El AG no "minimiza el backlog total a cualquier costo". Los pesos expresan prioridades: puede convenir dejar más alertas de prioridad Alta pendientes si así se atienden antes las Críticas.

### Qué mostrar

- [`generar_poblacion()`](main.py#L163), [`_evaluar_asignacion()`](main.py#L179) (el bloque de `contribuciones_objetivo` con los pesos) y [`calcular_fitness()`](main.py#L322) (el atajo que devuelve solo el fitness).

### Cuidado con el vocabulario

- La función `_evaluar_asignacion()` calcula también una **`penalizacion`** sin normalizar (con coeficientes tipo 40 × desbalance, 1,8 × espera crítica…). Es la que muestra el dashboard como "Penalización total", pero **no es lo que optimiza el AG**: el AG optimiza `J` (el objetivo normalizado). El paper usa la letra `J`; si aparece "P" o "penalización", aclarar que es la misma idea general pero otra escala.

> **Frase puente → Parte 3:** "Sabemos cómo se escribe una solución y cómo se le pone nota. Falta responder: ¿cómo se pasa de una población al azar a soluciones buenas?"

---

## 5. Parte 3 — Evolución, parámetros y demo en vivo

**Integrante 3 · ~5 min**

> **Palabras clave de esta parte**
> - **Generación:** una vuelta completa del ciclo evolutivo.
> - **Selección por ranking:** los padres se eligen según su posición ordenada por fitness, no por el valor exacto.
> - **Cruzamiento de un punto:** cortar dos cromosomas en un punto e intercambiar las colas.
> - **Mutación:** cambiar genes al azar para introducir variedad.
> - **Elitismo:** las mejores soluciones pasan sin cambios a la próxima generación.
> - **Semilla:** número que fija el azar para poder repetir una corrida idéntica.
> - **Hiperparámetro / grid search:** ajustes del algoritmo y prueba sistemática de combinaciones.
> - **Gantt:** barras en el tiempo, una fila por analista.

### Guion

1. **El ciclo.** [`evolucionar()`](main.py#L450) repite lo siguiente durante `G = 200` generaciones:
   1. **Evalúa** cada cromosoma (calcula su fitness).
   2. **Elitismo:** conserva a los mejores. Con la configuración oficial (`N = 50`) son **3** (el código usa `min(3, N // 10)`; con poblaciones más chicas son menos: 2 con `N = 20`, 1 con `N = 10`).
   3. **Selección de padres:** por defecto [`seleccion_ranking()`](main.py#L354). Cada individuo recibe un peso igual a su posición en el ranking (el peor 1, el mejor `N`), así que los mejores se eligen más seguido sin que diferencias minúsculas de fitness decidan todo.
   4. **Cruzamiento** ([`crossover()`](main.py#L380)) de un punto con probabilidad `Pc = 0,75`: se elige un punto de corte al azar y se combinan las partes de ambos padres. Si no toca cruzar, los hijos son copias de los padres.
   5. **Mutación** ([`mutacion()`](main.py#L394)) gen por gen con probabilidad `Pm = 0,05`: la alerta se reasigna a un analista sorteado entre los 10 (puede salir el mismo).
   6. **Se completa la nueva población** y se repite.
2. **Parámetros oficiales** (los que usa el paper): población `N = 50`, `G = 200` generaciones (= **10.000 evaluaciones** por corrida), `Pc = 0,75`, `Pm = 0,05`, selección por ranking, horizonte 480 min, 10 analistas, 500 alertas, semilla base 42. Están declarados en [`main.py`](main.py#L35-L42).
3. **Otras selecciones.** También están implementadas [`seleccion_ruleta()`](main.py#L327) y [`seleccion_torneo()`](main.py#L342) (se activan con `--seleccion`), pero la configuración oficial usa ranking.
4. **Grid search (solo exploración).** [`ejecutar_grid_search()`](hyper_tuner.py#L14) probó 18 combinaciones (población 10 o 20 × mutación 0,01/0,05/0,10 × cruzamiento 0,60/0,75/0,90) con **15 generaciones** y **una sola semilla**. La mejor combinación exploratoria fue `N = 20`, `Pm = 0,05`, `Pc = 0,60`. **No reemplaza** la configuración oficial `N = 50`, `G = 200`, porque:
   - se probó con muchas menos generaciones (15 vs 200);
   - no incluyó `N = 50`;
   - se corrió con una sola semilla, que es ruidosa.
5. **Demo en vivo (si hay tiempo):** correr `python main.py` y mostrar el dashboard y el Gantt (ver sección 6 para el orden correcto de ejecución).

### Qué mostrar

- [`evolucionar()`](main.py#L450) (el bucle) y los tres operadores.
- Gráficos de convergencia en `outputs/figures/` (`maximos_por_generacion.png`, `promedios_por_generacion.png`, etc.): sube el fitness y baja la dispersión, o sea la población "se pone de acuerdo".
- [`generar_gantt()`](gantt_chart.py#L21): cada barra es una alerta atendida por un analista; el color es la prioridad (rojo = Crítica) y la línea punteada marca el fin del turno en el minuto 480.
- [`load_data()`](dashboard.py#L57) / `python -m streamlit run dashboard.py`.

### Cuidado con el vocabulario y la demo

- Los valores por defecto del **formulario del dashboard** son población 10 y 20 generaciones: **no son la configuración oficial**. Si se corre desde el dashboard sin cambiarlos, se pisa `outputs/` con resultados más débiles y los scripts que leen `resumen_resultados_soc.csv` (baselines, Gantt) quedan con esa corrida. Antes de la demo, o bien cargar `N = 50` y `G = 200` en la barra lateral, o bien correr `python main.py` en consola.
- El dashboard dice que el grid search busca "el óptimo matemático". Es una expresión exagerada: es una **exploración de hiperparámetros**. No repetirla.
- "Semilla" no es una pieza del algoritmo: es una forma de que el azar sea repetible.

> **Frase puente → Parte 4:** "Con el algoritmo funcionando, la pregunta que importa es si sirve: ¿le gana a las reglas simples?"

---

## 6. Cómo correr el proyecto (para quien haga la demo)

Todos los comandos se ejecutan desde la carpeta `TPI`. El archivo del dataset debe estar en `dataset/Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv` (ruta declarada en [`main.py`](main.py#L53)).

### Orden recomendado (los scripts se leen entre sí)

```bash
python main.py                      # 1) corrida principal, config oficial
python baseline_comparacion.py      # 2) compara contra heurísticas (lee el resumen del paso 1)
python gantt_chart.py               # 3) cronograma (lee el resumen del paso 1)
python hyper_tuner.py               # 4) grid search (opcional, tarda unos minutos)
python experimentos_multisemilla.py # 5) 20 semillas + pruebas de Wilcoxon (tarda: ~36 s por semilla)
python -m streamlit run dashboard.py
uvicorn api_server:app --reload     # solo demo de la API (ver Parte 4)
```

`baseline_comparacion.py` y `gantt_chart.py` **leen `outputs/resumen_resultados_soc.csv`**, que escribe la última corrida de `main.py`. Si esa última corrida fue con otros parámetros, los gráficos reflejarán esa corrida.

### Corrida principal

```bash
python main.py
```

Usa por defecto la semilla `42`, diez analistas, 500 alertas, población de 50 individuos, 200 generaciones, `Pc = 0,75`, `Pm = 0,05` y horizonte de 480 minutos. El punto de entrada que procesa los argumentos es [`main()`](main.py#L664). Para cambiar parámetros:

```bash
python main.py --seed 42 --n-analistas 10 --n-alertas 500 --tam-poblacion 50 --n-generaciones 200 --p-crossover 0.75 --p-mutacion 0.05 --seleccion ranking --horizonte-minutos 480
```

### Experimento multisemilla

```bash
python experimentos_multisemilla.py --corridas 20 --peso-tiempo 0.10
```

Ejecuta el AG con las semillas `42` a `61` (`SEED + índice`), compara cada corrida contra Round-Robin con pruebas de Wilcoxon y guarda los resultados en `outputs/`. **Atención:** las 20 semillas cambian el azar **del algoritmo**, pero la instancia de 500 alertas es la misma en todas. Con `--peso-tiempo 0` se reproduce la ablación, pero **escribe sobre los mismos CSV**: copiar los archivos de la corrida oficial antes de correr la ablación.

---

## 7. Parte 4 — Resultados, límites y cierre

**Integrante 4 · ~5 min**

> **Palabras clave de esta parte**
> - **Baseline:** regla simple de referencia para comparar.
> - **Round-Robin / Menor carga / Urgencia balanceada:** tres reglas simples de reparto (ver más abajo).
> - **Backlog:** alertas que terminan después del minuto 480.
> - **Desbalance (D):** qué tan desparejo es el reparto de trabajo; 0 = perfecto.
> - **Ablación:** quitar una parte del modelo para medir cuánto aportaba.
> - **Wilcoxon / p-valor / significativo:** prueba estadística pareada; el p-valor chico indica que la diferencia difícilmente sea casualidad.
> - **Bonferroni:** corrección por hacer varias pruebas juntas.
> - **Desvío estándar (σ):** qué tan dispersos son los resultados entre corridas.

### Guion

1. **Contra qué se compara.** Un baseline es una regla de referencia, no una solución aprendida. Sirve para preguntar si el AG aporta algo frente a estrategias simples y razonables. Los tres implementados:
   - **Round-Robin** ([`asignar_round_robin()`](baseline_comparacion.py#L20)): reparte en rotación. Parejo en cantidad de alertas, pero no mira prioridad, SLA ni carga real.
   - **Menor carga** ([`asignar_menor_carga()`](baseline_comparacion.py#L25)): cada alerta va al analista con menos minutos acumulados.
   - **Urgencia balanceada** ([`asignar_urgencia_balanceada()`](baseline_comparacion.py#L36)): ordena por prioridad, severidad y SLA, y luego asigna al analista con menos carga. Incorpora urgencia **sin** búsqueda evolutiva.

   Todas se evalúan con **la misma función** [`_evaluar_asignacion()`](main.py#L179) que el AG: no se compara con una métrica inventada para favorecerlo. Ninguna forma parte del entrenamiento del AG. El resumen del paper usa **Round-Robin como comparación principal**; la tabla completa de los cuatro métodos queda en `outputs/comparativa_baselines.csv` ([`generar_comparativa()`](baseline_comparacion.py#L55)).

2. **Una corrida puntual (semilla 42, Figuras 1 a 3 del paper).**

   | Métrica | Round-Robin | AG |
   |---|---|---|
   | Espera crítica (min) | 179,0 | 136,0 |
   | Backlog (alertas) | 421 | 426 |
   | Desbalance D | 0,045 | 0,043 |

   Ojo: el propio paper aclara que el desbalance de la semilla 42 es **mayor que la media** de las 20 semillas, así que esa corrida no es representativa del balance típico. Y en esa corrida el backlog del AG es **ligeramente peor**: hay que decirlo.

3. **Los resultados que importan: 20 semillas** (42–61), no una sola corrida. Ver tabla en la sección 7.1.

4. **Por qué el backlog es tan alto.** Demanda ≈ 20.600 minutos-analista vs. capacidad 4.800: razón ≈ 4,3. Con esa sobrecarga, una fracción enorme de alertas queda fuera del turno **cualquiera sea el método**. Por eso el backlog total es un efecto **estructural de capacidad** y no un diferenciador del algoritmo. La métrica informativa es **qué prioridades quedan pendientes**.
   - Para dimensionarlo (cuenta propia, a partir de las cifras del paper): para que la capacidad igualara a la demanda harían falta ≈ 43 analistas (20.600 ÷ 480).

5. **Ablación del makespan.** Se quita el peso `w_T = 0,10` y se fija en `0`:
   - makespan medio con el peso oficial: **2138,4 min**; sin ese peso: **2180,4 min**;
   - diferencia pareada: **42,0 min** (≈ 1,9 %), estadísticamente significativa (p = 8,2 × 10⁻⁵);
   - desbalance (p = 0,189) y backlog total (p = 0,832): **sin diferencia significativa**.

   Lectura: el makespan aporta una mejora temporal **modesta pero consistente**; no explica por sí solo el balance de carga. Detalle por prioridad: sin makespan, el backlog de Alta sube de 203,55 a 205,85 y el de Crítica baja de 34,15 a 31,95; es decir, la configuración sin makespan protege algo mejor a las críticas, a costa de las Altas.

6. **Corrección de Bonferroni.** Con 5 comparaciones pareadas (espera crítica, desbalance, backlog total, backlog ponderado y makespan) el umbral ajustado es α = 0,01. Después de corregir siguen siendo significativas la espera crítica (p ajustado = 9,5 × 10⁻⁶) y el makespan (4,1 × 10⁻⁴); **no** lo son desbalance (0,947), backlog total (1,000) y backlog ponderado (0,121).

7. **Costo computacional.** ≈ 34,9 s dentro del motor por corrida de 10.000 evaluaciones (36,4 s con medición externa). Es compatible con reevaluaciones **por lote**, no con una respuesta instantánea por alerta. No decir que "es rápido" ni "en milisegundos".

8. **Límites y trabajo futuro** (ver sección 10).

### 7.1 Cifras de referencia (20 semillas, configuración oficial)

| Indicador | Round-Robin | AG (media de 20 semillas) |
|---|---|---|
| Espera crítica media | 179,0 min | 136,1 min (σ = 7,7) → mejora ≈ 24 % |
| Desbalance relativo medio (D) | 0,045 | 0,0271 |
| Backlog total medio | 421 alertas | 425,1 alertas (≈ 425,05) |
| Fitness | — | media 0,5282 (σ = 0,00171); mejor corrida 0,5319 |
| Makespan | — | 2138,4 min (2180,4 sin el término de makespan) |
| Tiempo por corrida | — | ≈ 34,9 s (motor) / 36,4 s (externo) |

Round-Robin es **determinista** (siempre da el mismo reparto), por eso tiene un único valor, mientras que el AG tiene uno por semilla.

**Lectura correcta:** el AG protege mejor las alertas críticas y distribuye mejor la carga en promedio, pero no reduce automáticamente la cantidad total de alertas pendientes (la aumenta levemente). Además, la regla de **urgencia balanceada** puede repartir mejor la carga que el AG; el AG obtiene menor espera crítica. No hay dominancia simultánea.

### Qué mostrar

- Gráficos `espera_critica_comparativa.png`, `backlog_comparativa.png` y `desbalance_comparativa.png` (solo Round-Robin vs AG) y la tabla `comparativa_baselines.csv` (los cuatro métodos).
- `pruebas_wilcoxon.csv` y `resumen_multisemilla.csv` para respaldar las 20 semillas ([`ejecutar_experimentos()`](experimentos_multisemilla.py#L12)).
- Opcional: [`health_check()` y `asignar_lote_alertas()`](api_server.py#L37) para mostrar integración con SIEM/SOAR (ver advertencia abajo).

### Cuidado con el vocabulario y los datos

- En el gráfico de backlog el eje dice "alertas perdidas". **No se pierden**: quedan **pendientes** al final del turno. Decir "pendientes".
- La palabra "significativamente" en la conclusión del paper para la comparación AG vs. Round-Robin: el script `experimentos_multisemilla.py` sí calcula esas pruebas (`pruebas_wilcoxon.csv`), pero el paper no informa sus p-valores; los p-valores que reporta son de la comparación **oficial vs. ablación**. Si preguntan, mostrar el CSV en vez de citar un número de memoria.
- La afirmación de que el AG reduce las críticas pendientes respecto de Round-Robin no tiene en el paper una tabla de respaldo por prioridad para Round-Robin; sí hay backlog por prioridad para AG oficial vs. ablación. Presentarla con prudencia o respaldarla con datos propios.
- **La API no ejecuta el algoritmo del paper.** [`api_server.py`](api_server.py) llama a `main_avanzado.optimizacion_nsgaii(...)`: una variante **multiobjetivo (NSGA-II)** con *skill-based routing* (los analistas tienen niveles: Senior, Semi-Senior, Junior), población 20 y 10 generaciones. Es distinta del AG canónico evaluado en el paper, y `main_avanzado.py` no forma parte de lo que se revisó para esta guía. Presentarla como **demostración de integración / extensión**, nunca como la forma en que se obtuvieron los resultados.

> **Frase puente → cierre:** "En resumen, ¿qué nos llevamos de todo esto?" (ver sección 11).

---

## 8. Preguntas típicas y respuestas

Etiqueta `[P1]`…`[P4]` = quién responde por defecto.

**[P1] ¿El dataset ya trae prioridad y SLA?**
No. CICIDS2017 trae flujos de red y etiquetas de tráfico. El proyecto deriva esos atributos operativos con reglas explícitas para construir una instancia reproducible de SOC.

**[P1] ¿Entonces son alertas "reales"?**
Son alertas **derivadas** de tráfico real. El tráfico y su etiqueta son del dataset; prioridad, SLA y duración son sintéticos. Por eso los resultados describen esta instancia y no propiedades de CICIDS2017.

**[P1] ¿Qué significa que el problema sea NP-hard?**
Que no se conoce un método eficiente que garantice la solución óptima en instancias grandes. El AG busca buenas soluciones explorando muchas combinaciones; no promete el óptimo exacto.

**[P1] ¿Por qué hay tanto backlog?**
Porque la demanda (~20.600 minutos-analista) es ~4,3 veces la capacidad (4.800). Es una instancia sobredimensionada a propósito.

**[P2] ¿Qué representa el cromosoma?**
Una asignación completa: cada posición es una alerta y el valor indica el analista responsable.

**[P2] ¿Qué optimiza el fitness?**
Un objetivo ponderado y normalizado que combina makespan, espera general, espera crítica, retraso respecto del SLA, backlog ponderado, minutos de backlog, desbalance y sobrecarga. El fitness es `1/(1+J)`: si el objetivo baja, el fitness sube.

**[P2] ¿Por qué esos pesos?**
Expresan prioridades operativas del modelo (la mayor parte del peso está en las alertas críticas). Un SOC con otras prioridades podría cambiarlos; el paper propone justamente que los analistas ajusten los pesos como trabajo futuro.

**[P2] ¿El modelo es estocástico?**
No en su evaluación actual: usa tiempos estimados fijos una vez generada la instancia. El SJSP aparece como motivación para extender el modelo a duraciones inciertas.

**[P3] ¿Por qué selección por ranking y no ruleta?**
Porque el ranking usa la posición ordenada y no el valor exacto del fitness: evita que pequeñas diferencias de puntaje dominen la elección. Ruleta y torneo están implementados, pero la configuración oficial usa ranking.

**[P3] ¿Por qué no usaron la mejor combinación del grid search (`N = 20`, `Pc = 0,60`)?**
Porque el grid se corrió con solo 15 generaciones, una única semilla y poblaciones de 10 o 20; es una exploración, no una comparación justa contra la configuración de 50 individuos y 200 generaciones.

**[P3] ¿Qué es una semilla y por qué importa?**
Fija el azar: misma semilla, mismo resultado. Permite reproducir una corrida y, usando semillas distintas, medir qué tan estable es el algoritmo.

**[P3] ¿Qué muestra el Gantt?**
El cronograma real de la mejor solución: una fila por analista, una barra por alerta (largo = duración, color = prioridad) y la línea del fin de turno en el minuto 480.

**[P4] ¿El AG gana en todas las métricas?**
No. Mejora la espera crítica y el desbalance promedio frente a Round-Robin, pero aumenta levemente el backlog total, y la regla de urgencia balanceada reparte mejor la carga. La conclusión depende de qué riesgo operativo se considera más importante.

**[P4] ¿Por qué el backlog del AG puede ser mayor?**
Porque la capacidad del turno es muy inferior a la demanda y la función objetivo prioriza proteger las alertas críticas; según la ablación, parte del costo se traslada a las alertas de prioridad **Alta**.

**[P4] ¿Qué demuestra la comparación de 20 semillas?**
Que el comportamiento no depende de una corrida afortunada y que se pueden medir variabilidad y significancia estadística. Aclarar que las semillas cambian el azar del algoritmo, no la instancia de alertas.

**[P4] ¿Qué es la ablación y para qué sirve?**
Quitar una pieza (el término de makespan) y comparar. Mostró que el makespan reduce el tiempo total de finalización de forma modesta (~1,9 %) y consistente, sin mejorar significativamente el balance.

**[P4] ¿Por qué tarda 35 segundos? ¿Sirve en tiempo real?**
Cada corrida evalúa 10.000 soluciones simulando 500 alertas. Sirve para reasignar por lotes, no para responder alerta por alerta al instante.

**[P4] ¿Qué hace la API?**
Expone un endpoint REST para recibir un lote de alertas y devolver una asignación. Es una demostración de integración, y usa una variante NSGA-II multiobjetivo con niveles de analista; no es el procedimiento experimental del paper.

**[P4] ¿Con cuántos analistas se absorbería la demanda?**
Con la aritmética del modelo, ≈ 43 (20.600 ÷ 480). Es una cuenta de orden de magnitud, no un resultado experimental.

---

## 9. Qué se corrigió y qué verificar antes de exponer

### 9.1 Correcciones respecto de la versión anterior

- **Reparto en 4 partes** con tiempos, recuadros de vocabulario propios, frases puente y respuestas etiquetadas por expositor.
- **"Letras con tilde"** → en el paper son variables con **sombrero** (^), que indican magnitudes normalizadas. Se agregó la tabla de cómo se normaliza cada una según el código.
- **Elitismo:** no son siempre 3: el código usa `min(3, N // 10)` (3 con `N = 50`; 2 con 20; 1 con 10).
- **Mutación:** reasigna a un analista sorteado entre los 10, no necesariamente "a otro".
- **Retraso crítico y SLA:** el SLA se compara con la **espera en cola**, no con el tiempo de resolución.
- **Parámetros del dataset:** se agregaron los rangos de severidad (DDoS 45–100, benigno 5–50), los umbrales de prioridad (80 y 30), la fórmula de duración y el hecho de que se usa un único archivo (viernes por la tarde, DDoS).
- **Q&A:** "postergar Altas o Bajas" → según el paper, el costo adicional se traslada a las **Altas**.
- **Faltaba el experimento multisemilla** (`experimentos_multisemilla.py`): es de donde salen los resultados principales del paper; ahora figura en comandos, tabla de archivos y partes 3 y 4.
- **Aclaración sobre las 20 semillas:** cambian el azar del AG, no la instancia.
- **Resultados de la semilla 42** (Figuras 1–3 del paper) y el hecho de que no es representativa del balance.
- **La API:** pasó de "devuelve una asignación" a aclarar que usa NSGA-II (una variante distinta) y que `main_avanzado.py` no se revisó.
- **Urgencia balanceada** reparte mejor la carga que el AG (dato del paper): faltaba decirlo explícitamente.
- **Grid search:** por qué no reemplaza la configuración oficial (15 generaciones, una semilla, solo `N` = 10 o 20).
- **Salidas completas** (sección 12) y orden de ejecución de los scripts.

### 9.2 Inconsistencias del proyecto (para no pisarse en la exposición)

| Dónde | Qué pasa | Qué hacer |
|---|---|---|
| `dashboard.py` | Los defaults del formulario son población 10 y 20 generaciones (no los oficiales). | Cargar 50 y 200, o correr `main.py` por consola antes de la demo. |
| `dashboard.py` | Dice "encontrar el óptimo matemático" en la pestaña de hiperparámetros. | No repetirlo; el grid search es exploratorio. |
| `dashboard.py` | "Penalización total" no es el objetivo que optimiza el AG (`J`). | Aclarar si se muestra ese panel. |
| `dashboard.py` | La pestaña "Comparativa" muestra solo Round-Robin vs AG, aunque el CSV tiene cuatro métodos. | Mostrar también `comparativa_baselines.csv`. |
| `baseline_comparacion.py` | El gráfico de backlog dice "alertas perdidas". | Decir "pendientes". |
| `main.py` (docstring) | "Alertas SOC reales". | Decir "derivadas". |
| `gantt_chart.py` | Importa `N_ANALISTAS` de `main.py` por valor; no lee el resumen como hace `baseline_comparacion.py`. | Si se corrió `main.py` con otro `--n-analistas`, el Gantt no es consistente. Usar la configuración oficial. |
| `experimentos_multisemilla.py` | La ablación (`--peso-tiempo 0`) sobrescribe los mismos CSV. Además, entre los scripts revisados no hay uno que calcule la comparación pareada oficial vs. ablación ni la corrección de Bonferroni (que sí aparecen en el paper). | Guardar los CSV de la corrida oficial antes de la ablación y tener claro de dónde salieron esos números del paper. |
| `api_server.py` | Depende de `main_avanzado.py` (NSGA-II), que no está entre los archivos revisados. | No presentarlo como el algoritmo del paper; verificar que el archivo esté en el repo si se va a correr. |
| Paper | Menciona "penalización operativa P" y luego usa `J` en la fórmula. | Usar `J` al presentar. |

---

## 10. Límites y trabajo futuro

El modelo actual es una instancia determinista con atributos operativos derivados. No reemplaza el criterio experto ni modela todavía disponibilidad variable, niveles de experiencia, activos afectados, falsos positivos o duraciones estocásticas. Se interpreta como una forma de **priorización de alertas automatizada** para el triaje y la asignación inicial, no como reemplazo de la validación experta ante incidentes nuevos o ambiguos.

El paper propone como siguientes pasos:

- incorporar criticidad, vulnerabilidad y dependencia de los **activos** afectados (los sistemas que se protegen) en la representación;
- permitir que los analistas revisen las asignaciones y ajusten los pesos (colaboración Humano-IA);
- evaluar cronogramas **robustos** frente a variaciones en los tiempos de resolución;
- extender el modelo hacia un scheduling estocástico (SJSP) más realista.

---

## 11. Cierre sugerido (lo dice el Integrante 4)

"Modelamos la asignación de alertas de un SOC como un problema de scheduling con recursos limitados. El Algoritmo Genético representa cada asignación como un cromosoma y evalúa no solo el tiempo total, sino también la espera crítica, el SLA, el backlog y el balance de carga. Sobre una instancia derivada de CICIDS2017, el AG reduce en promedio un 24 % la espera de las alertas críticas y mejora el balance promedio frente a Round-Robin. Como la demanda supera unas 4,3 veces la capacidad del turno, no prometemos eliminar el backlog: mostramos cómo decidir qué trabajo conviene priorizar, y dejamos el proceso reproducible mediante múltiples semillas, métricas y gráficos."

---

## 12. Archivos de salida importantes

Después de ejecutar [`main.py`](main.py):

- `outputs/metricas_generacionales_soc.csv`: evolución por generación;
- `outputs/resumen_resultados_soc.csv`: mejor solución (incluye el cromosoma) y sus métricas;
- `outputs/distribucion_final_alertas_soc.csv`: carga final por analista;
- `outputs/carga_final_analistas_soc.csv`: resumen simplificado de cargas;
- `outputs/alertas_derivadas_dataset.csv`: instancia derivada, útil para trazabilidad;
- `outputs/figures/`: gráficos del AG (máximo, promedio, mínimo y desvío estándar por generación) y `carga_final_por_analista.png`.

Los otros scripts generan:

- `baseline_comparacion.py` → `outputs/comparativa_baselines.csv` y tres gráficos en `outputs/figures/` (`espera_critica_comparativa.png`, `backlog_comparativa.png`, `desbalance_comparativa.png`);
- `gantt_chart.py` → `outputs/figures/gantt_asignacion_final.png`;
- `hyper_tuner.py` → `outputs/grid_search_resultados.csv`;
- `experimentos_multisemilla.py` → `outputs/experimentos_multisemilla.csv`, `outputs/resumen_multisemilla.csv` y `outputs/pruebas_wilcoxon.csv`.

---

## 13. Qué archivo mostrar en cada momento

| Archivo | Parte | Qué mostrar | Cómo explicarlo |
|---|---|---|---|
| [`derivar_alertas_desde_dataset()`](main.py#L82) | P1 | Construcción de la instancia | "Acá le agregamos prioridad, SLA y duración al tráfico del dataset." |
| [`Alerta`](main.py#L66) | P1 | Los 6 datos de cada alerta | "Esto es lo que sabe el sistema de cada alerta." |
| [`generar_poblacion()`](main.py#L163) / [`_evaluar_asignacion()`](main.py#L179) | P2 | Cromosoma, simulación y fitness | "Acá se define qué es una solución y cómo se le pone nota." |
| [`evolucionar()`](main.py#L450) | P3 | Ciclo evolutivo | "Este bucle repite evaluar, seleccionar, cruzar y mutar." |
| [`ejecutar_grid_search()`](hyper_tuner.py#L14) | P3 | Exploración de parámetros | "Probamos 18 combinaciones, pero no reemplazó la configuración oficial." |
| [`generar_gantt()`](gantt_chart.py#L21) | P3 | Cronograma de atención | "Cada barra muestra cuándo trabaja un analista sobre una alerta." |
| [`load_data()`](dashboard.py#L57) | P3 | Carga de tablas y gráficos | "Es una capa visual para inspeccionar resultados ya generados." |
| [`generar_comparativa()`](baseline_comparacion.py#L55) | P4 | Reglas de referencia y tabla comparativa | "Medimos el AG con el mismo criterio que las heurísticas." |
| [`ejecutar_experimentos()`](experimentos_multisemilla.py#L12) | P4 | 20 semillas y Wilcoxon | "De acá salen los resultados agregados." |
| [`health_check()` y `asignar_lote_alertas()`](api_server.py#L37) | P4 | Endpoints REST | "Es una demostración de integración con un SIEM o SOAR, con una variante del algoritmo (NSGA-II)." |

---

## 14. Orden sugerido de diapositivas

Este orden permite que cada integrante tenga un recorrido claro sin repetir explicaciones:

1. **Problema del SOC:** volumen de alertas, fatiga y capacidad limitada.
2. **Formalización:** asignación y scheduling como problema JSP/NP-hard.
3. **Datos:** CICIDS2017, atributos derivados y aclaración de qué es sintético.
4. **Instancia:** 500 alertas, composición por prioridad y relación demanda/capacidad.
5. **Cromosoma:** ejemplo `[2, 4, 4, 1]` y codificación directa.
6. **Simulación:** cola por analista y política prioridad > severidad > urgencia del SLA.
7. **Fitness:** objetivo `J`, normalización y transformación `f = 1/(1+J)`.
8. **Ciclo evolutivo:** selección, crossover, mutación y elitismo.
9. **Configuración:** `N=50`, `G=200`, `Pc=0,75`, `Pm=0,05` y 10.000 evaluaciones.
10. **Visualización:** curvas generacionales, dashboard y Gantt.
11. **Baselines:** Round-Robin, menor carga y urgencia balanceada.
12. **Resultados:** comparación puntual y resultados agregados de 20 semillas.
13. **Ablación:** efecto de quitar el peso del makespan.
14. **Integración y cierre:** API como extensión, límites y trabajo futuro.

## 15. Preguntas técnicas adicionales

**¿Por qué usan codificación directa y no permutaciones?**

Porque cada posición representa una alerta y su valor es un analista válido entre 1 y 10. El crossover y la mutación siguen produciendo asignaciones válidas, sin necesitar un algoritmo adicional de reparación.

**¿Por qué el backlog total es parecido entre Round-Robin y el AG?**

Porque el backlog está limitado principalmente por la capacidad: aproximadamente 20.600 minutos-analista de demanda frente a 4.800 disponibles. El AG reorganiza qué se atiende primero, pero no puede crear capacidad adicional.

**¿Cómo se evaluó la estabilidad?**

Se ejecutó la configuración con 20 semillas, de `42` a `61`, y se analizaron media, desvío estándar y pruebas pareadas. Las semillas cambian el azar del algoritmo, no la instancia de alertas.

**¿Cuál es la diferencia entre `main.py` y `api_server.py`?**

`main.py` implementa el AG canónico monocriterio usado en el paper. `api_server.py` es una extensión de integración que utiliza una variante multiobjetivo NSGA-II; no es el procedimiento que produjo los resultados académicos.

**¿Qué significa que el AG sea canónico?**

Que utiliza los operadores clásicos de un algoritmo genético: selección, cruzamiento, mutación y elitismo, con una función objetivo ponderada. No implica que garantice el óptimo exacto.

## 16. Frase central para los cuatro integrantes

“El proyecto modela la asignación de alertas de un SOC como un problema de scheduling con recursos limitados. El Algoritmo Genético busca reducir la espera de las alertas críticas y mejorar el balance de carga, pero no puede eliminar un backlog provocado por una demanda 4,3 veces mayor que la capacidad del turno. Por eso la evaluación se hace con múltiples semillas, baselines y métricas operativas, y la conclusión es una mejora focalizada, no una victoria en todas las métricas.”
