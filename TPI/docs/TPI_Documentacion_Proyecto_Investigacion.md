## 1. Carátula

**Universidad Tecnológica Nacional — Facultad Regional Rosario**
**Cátedra:** Algoritmos Genéticos
**Docentes:** Daniela Díaz y Víctor Lombardo
**Ciclo lectivo:** 2026

### Temática abordada

Algoritmos Genéticos vinculados a los problemas de Scheduling ¿En qué medida la aplicación de algoritmos genéticos para la optimización de la asignación de alertas en un Centro de Operaciones de Seguridad (SOC) permite minimizar los tiempos de respuesta, reducir la saturación de analistas y mejorar la eficiencia operativa mediante una distribución inteligente de la carga de trabajo durante la gestión de incidentes de ciberseguridad?

### Integrantes del grupo

| Integrante | Legajo | Correo electrónico |
|---|---|---|
| Chacón, Agustina | 50980 | aguscchacon@gmail.com |
| Gomez Manna, Joaquina | 47791 | gomezmannajoaquina@gmail.com |
| Tabini, Azul | 48038 | azultabini@gmail.com |
| Carloni, Nahuel Iván | 51095 | nahuelcarloni25@gmail.com |
| Mierez, Joaquin | 49938 | joakomierez1@hotmail.com |

---

## 2. Índice de Contenidos

1. Carátula
2. Índice de Contenidos
3. Denominación del futuro proyecto de investigación
4. Situación Problemática
5. Problema
6. Objetivos de la investigación
   - 6.a. Objetivo general
   - 6.b. Objetivos específicos
7. Marco Teórico
8. Evidencia preliminar del modelo implementado (tablas y figuras)
9. Referencias bibliográficas

---

## 3. Denominación del futuro proyecto de investigación

**Optimización mediante Algoritmos Genéticos de la asignación y el balance de carga de alertas de seguridad en Centros de Operaciones de Seguridad (SOC).**

Esta denominación delimita con precisión el alcance del proyecto en tres ejes: la técnica a emplear (algoritmos genéticos, dentro de la familia de los algoritmos evolutivos), el problema de optimización combinatoria abordado (asignación de tareas — *scheduling* — y balance de carga entre recursos humanos limitados) y el dominio de aplicación (la operación de un SOC, entendido como el equipo y la infraestructura responsables de detectar, triar y responder a alertas de seguridad informática).

---

## 4. Situación Problemática

Los Centros de Operaciones de Seguridad (SOC) son la primera línea de defensa de las organizaciones frente a incidentes de ciberseguridad: reciben, triean y resuelven alertas generadas por sistemas de detección de intrusiones, antivirus, firewalls y plataformas de gestión de eventos (SIEM). La literatura reciente coincide en que el volumen de alertas que procesa un SOC moderno ha crecido a un ritmo muy superior a la disponibilidad de analistas capacitados para atenderlas. Jalalvand et al. (2025) [1] sistematizan decenas de criterios y métodos propuestos en la última década para priorizar alertas, y señalan que la sobrecarga de alertas (*alert overload*) es uno de los problemas estructurales más persistentes de la operación de un SOC, ya que obliga a los analistas a decidir, con información incompleta y bajo presión de tiempo, qué atender primero.

Esa sobrecarga tiene un correlato humano documentado: la fatiga de alertas (*alert fatigue*). Tariq et al. (2025) [2] identifican cuatro causas principales de este fenómeno —el volumen de alertas, la proporción de falsos positivos, la falta de contexto en cada alerta y el diseño de las herramientas— y advierten que la fatiga degrada la calidad de las decisiones de triage, incrementa el tiempo de respuesta y favorece la rotación de personal capacitado, lo que a su vez reduce aún más la capacidad operativa disponible. Este ciclo (más alertas, menos analistas efectivos, peores tiempos de respuesta) es especialmente crítico cuando las alertas retrasadas son de alta severidad, dado que la demora en su atención incrementa directamente el riesgo de que una intrusión progrese sin ser contenida.

A esta escasez estructural de analistas se suma un problema de coordinación: aun cuando el equipo de analistas es suficiente en promedio, la forma en que las alertas se reparten entre ellos rara vez es óptima. Las prácticas habituales de asignación —turnos fijos, reglas estáticas por tipo de alerta, o asignación manual según disponibilidad aparente— no consideran de forma simultánea la prioridad de cada alerta, su plazo de resolución comprometido (SLA), el tiempo estimado que insumirá resolverla y la carga ya acumulada por cada analista. El resultado observado en la práctica es un desbalance de carga: algunos analistas acumulan alertas pendientes mientras otros permanecen subutilizados, y las alertas críticas no siempre son atendidas por quien está en condiciones de resolverlas dentro del plazo comprometido. Investigaciones sobre priorización adaptativa de alertas exploran, desde el aprendizaje automático, mecanismos que involucran retroalimentación humana para mejorar estas decisiones (arXiv:2506.18462, 2025) [3], lo que confirma que la asignación de alertas a analistas es, en esencia, un problema de optimización combinatoria bajo restricciones y no una tarea que pueda resolverse satisfactoriamente con reglas fijas.

Los algoritmos genéticos son una familia de metaheurísticas particularmente adecuada para este tipo de problemas, porque permiten explorar de manera eficiente un espacio de soluciones combinatorio —en este caso, todas las formas posibles de repartir *n* alertas entre *m* analistas— sin necesidad de enumerar exhaustivamente las alternativas, algo inviable incluso para instancias moderadas del problema. Su aplicación a problemas de *scheduling* y balance de carga está ampliamente documentada: existen antecedentes concretos de algoritmos genéticos aplicados a la programación de tareas en entornos de manufactura (problema de *Job Shop Scheduling*) (SciELO Chile, 2018) [4], y al balanceo dinámico de carga entre recursos computacionales en sistemas distribuidos (Luna Rosas, Tristán Ávila y Martínez Pedroza, 2003) [5]. Ambos antecedentes comparten con el problema del SOC la misma estructura de fondo: unidades de trabajo heterogéneas que deben repartirse entre recursos limitados minimizando tiempo total y desbalance, lo que respalda la pertinencia de adaptar un algoritmo genético canónico al dominio de la asignación de alertas en un SOC.

En síntesis, la situación problemática identificada combina tres factores que se retroalimentan: (a) un volumen de alertas que excede la capacidad de análisis manual eficiente, (b) el riesgo de incumplir plazos de atención en alertas críticas cuando la asignación no prioriza correctamente, y (c) la ausencia de mecanismos de asignación que balanceen la carga entre analistas de forma sistemática y verificable. Estos tres factores configuran un escenario donde una técnica de optimización combinatoria como los algoritmos genéticos puede aportar un modelo formal, medible y comparable frente a las heurísticas manuales actualmente en uso.

---

## 5. Problema

La asignación manual o basada en reglas fijas de alertas de seguridad a los analistas de un Centro de Operaciones de Seguridad no logra, de manera consistente, minimizar simultáneamente el makespan de finalización, el incumplimiento de los plazos de atención (SLA) de las alertas críticas y el desbalance de carga entre analistas, por lo que resulta necesario investigar y modelar mediante Algoritmos Genéticos una estrategia de asignación que, a partir de un conjunto de alertas caracterizadas por su prioridad, severidad, tiempo estimado de resolución y SLA, distribuya dichas alertas entre un número limitado de analistas optimizando de forma conjunta esos objetivos operativos.

---

## 6. Objetivos de la investigación

### 6.a. Objetivo general

Diseñar, implementar y evaluar un modelo de Algoritmo Genético Canónico que optimice la asignación de alertas de seguridad a los analistas de un Centro de Operaciones de Seguridad, minimizando de forma conjunta el makespan de finalización, el incumplimiento de los SLA en alertas críticas, las alertas pendientes y el desbalance de carga entre analistas.

### 6.b. Objetivos específicos

1. Diseñar una representación cromosómica que codifique una asignación completa de alertas a analistas, donde cada gen indique el analista responsable de resolver la alerta correspondiente.
2. Formular una función de fitness compuesta que integre el makespan de finalización junto con penalizaciones por espera promedio, espera y retraso de alertas críticas respecto del SLA, alertas pendientes y desbalance de carga, de modo que un fitness mayor represente siempre una asignación operativamente mejor.
3. Implementar y comparar, bajo idénticas condiciones iniciales (semilla aleatoria, tamaño de población y número de generaciones), tres estrategias de selección y preservación de individuos —ruleta, torneo y ruleta con preservación elitista— a fin de determinar cuál produce el mejor fitness global y la convergencia más estable.
4. Registrar y cuantificar, generación a generación, el fitness máximo, mínimo, promedio y su desvío estándar para cada operador de selección, documentando la velocidad y la estabilidad con la que cada estrategia converge hacia una solución de buena calidad.
5. Cuantificar, a partir del mejor cromosoma hallado, la distribución final de alertas y de carga horaria entre los analistas del SOC, verificando el grado de equilibrio efectivamente alcanzado por el modelo.
6. Medir el tiempo de ejecución de cada estrategia evolutiva, para poder contrastar la calidad de la solución obtenida por cada operador de selección frente a su costo computacional.

---

## 7. Marco Teórico

El presente proyecto se apoya en tres ejes conceptuales: la teoría de algoritmos genéticos, la formulación del problema como un caso de optimización combinatoria tipo *scheduling* y el contexto operativo de los Centros de Operaciones de Seguridad (SOC). Estos ejes permiten justificar las decisiones de modelado, interpretar los resultados obtenidos y delimitar el aporte del prototipo frente a heurísticas manuales o reglas estáticas de asignación.

### 7.1. Algoritmos genéticos y optimización evolutiva

Los algoritmos genéticos son metaheurísticas inspiradas en la evolución biológica y formalizadas originalmente por Holland como un mecanismo de búsqueda adaptativa sobre poblaciones de soluciones [6]. Su funcionamiento parte de una población inicial de cromosomas, una función de aptitud que evalúa la calidad de cada individuo, y operadores de selección, cruza y mutación que inducen exploración y explotación del espacio de búsqueda [6][7]. La utilidad de este enfoque en problemas reales surge de una idea central: no se intenta enumerar todas las soluciones posibles, sino mejorar iterativamente una población de candidatos hasta encontrar soluciones de alta calidad en tiempos computacionales razonables [8].

Desde el punto de vista teórico, el valor del algoritmo genético no radica en garantizar el óptimo global, sino en ofrecer un equilibrio práctico entre diversidad y convergencia. Goldberg destaca que la presión selectiva debe ser suficiente para conservar buenos individuos, pero no tan fuerte como para destruir la variabilidad necesaria para seguir explorando [7]. Mitchell, por su parte, remarca que la mutación y la cruza no son simples accesorios: cumplen la función de evitar convergencia prematura y de recombinar bloques útiles de información presentes en distintos individuos [8].

En este trabajo, esa lógica se refleja directamente en la representación del problema: cada cromosoma codifica una asignación completa de alertas a analistas, por lo que el espacio de soluciones crece combinatoriamente con el número de alertas y analistas. En ese escenario, la búsqueda exhaustiva deja de ser viable y la heurística evolutiva se vuelve una estrategia apropiada.

### 7.2. Representación cromosómica y operadores genéticos

La codificación elegida corresponde a una representación directa de asignación, donde cada gen identifica al analista responsable de una alerta. Formalmente, si hay $n$ alertas y $m$ analistas, el cromosoma puede escribirse como el vector

$$
x = (x_1, x_2, \dots, x_n), \qquad x_i \in \{1, 2, \dots, m\}
$$

donde $x_i = a$ indica que la alerta $i$ queda asignada al analista $a$. Esta forma de cromosoma es adecuada cuando la unidad de decisión es discreta y el objetivo es asignar ítems heterogéneos a recursos limitados, porque simplifica la interpretación del individuo y hace más transparente la evaluación del fitness [7][9].

La selección define qué individuos contribuyen a la siguiente generación y, por lo tanto, condiciona la dirección de la búsqueda. La ruleta favorece individuos con mejor aptitud proporcional, el torneo introduce una presión selectiva controlable mediante el tamaño del torneo, y la preservación elitista asegura la supervivencia de los mejores cromosomas encontrados [7][10]. En términos teóricos, estas variantes representan distintos compromisos entre exploración, explotación y estabilidad de la convergencia.

La cruza de un punto permite recombinar segmentos del cromosoma preservando bloques de asignación contiguos, mientras que la mutación introduce pequeñas perturbaciones aleatorias que ayudan a escapar de óptimos locales [6][8]. Dado que el cromosoma modela asignaciones, una mutación semánticamente coherente debe modificar la asignación de una alerta concreta, y no simplemente permutar posiciones sin significado operativo. Esa decisión es coherente con la literatura de algoritmos evolutivos aplicada a problemas de programación y asignación [9][11].

### 7.3. Función de fitness y criterios de calidad

La función de fitness traduce los objetivos operativos en una métrica cuantificable. En este proyecto, la calidad de una solución no depende de un único factor, sino de una combinación de makespan de finalización, espera promedio, penalizaciones por alertas críticas, alertas pendientes y desbalance de carga. Esta formulación no implementa un enfoque multiobjetivo en sentido estricto: el código resume todas las dimensiones en un único valor escalar, de modo que una asignación puede ser más conveniente que otra solo por su menor penalización total [8][12].

La literatura de optimización multiobjetivo sugiere que, cuando no existe una única medida natural de calidad, conviene incorporar penalizaciones para forzar el cumplimiento de restricciones operativas relevantes [12]. En el contexto de este trabajo, las alertas críticas y sus SLA funcionan como restricciones de negocio, porque su incumplimiento tiene más impacto que el retraso de alertas de menor severidad. Por ese motivo, el fitness se construye para favorecer soluciones con menor penalización total y mejor distribución de la carga, de modo que un valor mayor represente siempre una solución más conveniente desde el punto de vista operativo.

Los pesos de cada componente de la penalización se calibraron para reflejar las prioridades operativas de un SOC real, donde el incumplimiento de un SLA crítico es el evento más perjudicial, seguido por la saturación de analistas y la demora en la atención de alertas de alta prioridad. La siguiente tabla resume la justificación de los pesos principales utilizados en el modelo:

| Penalización | Peso | Justificación del impacto operativo |
|---|---|---|
| **Retraso crítico (SLA)** | 20.0 | **Impacto muy alto.** Penaliza severamente cada minuto que una alerta crítica excede su SLA. Es el factor más importante porque un retraso aquí implica un riesgo de seguridad materializado y un posible incumplimiento contractual. |
| **Desbalance de carga** | 10.0 | **Impacto alto.** Fomenta una distribución equitativa del trabajo para evitar la saturación de ciertos analistas y la subutilización de otros. Un equipo balanceado es más resiliente y menos propenso a la fatiga (*alert fatigue*). |
| **Espera de alertas críticas** | 5.0 | **Impacto medio-alto.** Penaliza el tiempo que una alerta crítica pasa en cola antes de ser atendida, incluso si no llega a violar su SLA. El objetivo es minimizar la ventana de riesgo desde que la alerta llega. |
| **Backlog de alertas** | 2.0 | **Impacto medio.** Penaliza las alertas que no se completan dentro del horizonte de simulación (el turno de trabajo). Un backlog excesivo indica una planificación deficiente o falta de capacidad. |
| **Makespan (tiempo total)** | 2.0 | **Impacto medio.** Incentiva la finalización de todas las tareas en el menor tiempo posible, optimizando la eficiencia global del equipo. |
| **Espera promedio general** | 1.0 | **Impacto bajo.** Actúa como un optimizador secundario para reducir la latencia general del sistema una vez que las restricciones más importantes están bajo control. |

Esta jerarquía de pesos asegura que el algoritmo genético priorice la búsqueda de soluciones que resuelvan primero los problemas más urgentes desde una perspectiva operativa.

### 7.4. Problema de asignación de alertas en un SOC

Un SOC procesa alertas provenientes de herramientas diversas y debe decidir qué analista las atiende y con qué urgencia. La investigación reciente sobre priorización de alertas muestra que el volumen, los falsos positivos y la falta de contexto generan fatiga de alertas y degradan la calidad del triage [1][2][3]. Esto convierte la asignación en un problema donde no basta con clasificar severidades: también es necesario distribuir la carga y reducir demoras de finalización.

Teóricamente, la asignación de alertas en un SOC puede asimilarse a un problema de asignación con recursos paralelos, tiempos de servicio heterogéneos y una regla fija de ordenamiento de atención. Esa estructura es análoga a problemas bien estudiados de programación de tareas y balance de carga, donde se usan metaheurísticas para minimizar el makespan, los retrasos y el desbalance entre recursos [4][5]. Por eso, el aporte del presente proyecto no es solo implementar un algoritmo genético, sino adaptarlo a una función de decisión que represente con fidelidad el contexto de operación de un SOC.

### 7.5. Base para la interpretación de resultados

Este marco teórico permite interpretar los resultados experimentales con un criterio claro. Si una estrategia logra buen fitness promedio pero alta variabilidad, la literatura de algoritmos genéticos sugiere que probablemente esté explorando más que explotando; si conserva buen fitness máximo y baja dispersión, la presión selectiva y la preservación elitista están actuando de forma más estable [7][8]. Del mismo modo, una distribución final de carga equilibrada entre analistas es teóricamente consistente con una función de fitness que penaliza el desbalance y con una representación cromosómica orientada a la asignación [9][11].

### 7.6. Medición de la diversidad genética

Un aspecto clave para evaluar el comportamiento de un algoritmo genético es su capacidad para mantener la diversidad en la población y así evitar la convergencia prematura a óptimos locales. Medir únicamente la desviación estándar del fitness es insuficiente, ya que una población puede converger genotípicamente (todos los individuos son muy parecidos) mientras mantiene una baja dispersión de aptitud. Para abordar esto, el modelo implementa una métrica de diversidad genética que se calcula en cada generación. Para cada gen (locus), se mide la frecuencia del alelo más común. La diversidad para ese gen se define como `1 - frecuencia_max`. El valor de diversidad de la población es el promedio de esta métrica sobre todos los genes. Un valor cercano a 0 indica una población homogénea (convergencia), mientras que un valor cercano a 1 indica una alta variabilidad de alelos, lo que sugiere que el algoritmo sigue explorando activamente el espacio de búsqueda. Esta métrica permite un diagnóstico más preciso del equilibrio entre exploración y explotación de cada estrategia de selección.

En consecuencia, el marco teórico no solo fundamenta la elección metodológica, sino también la discusión de los resultados que se muestran en la sección siguiente. La evidencia experimental se entiende mejor si se la lee como un caso aplicado de búsqueda evolutiva sobre un problema real de asignación y balance de carga en un SOC.

## 8. Evidencia preliminar del modelo implementado (tablas y figuras)

Esta sección no forma parte de los seis apartados exigidos, pero se incorpora porque el grupo ya cuenta con un prototipo funcional (`TPI/main.py`) que instrumenta exactamente lo descripto en los objetivos específicos, y sus resultados reales permiten anticipar y justificar con datos concretos varias de las afirmaciones anteriores.

### Configuración utilizada

Por criterio de accesibilidad y para mantener un tiempo de ejecución manejable, el modelo utiliza **250 alertas sintéticas** generadas localmente con semilla fija (semilla = 42), sobre un **horizonte de simulación de llegada de alertas de 8 horas (480 minutos)**. Sobre ese mismo conjunto de alertas, el script ejecuta **30 repeticiones** independientes por método de selección, variando la semilla del algoritmo genético en cada corrida (semillas 1001 a 1030). La configuración del algoritmo genético utilizada es de **100 individuos** por población, evolucionando durante **200 generaciones**, con una probabilidad de cruza de 0.8 y una tasa de mutación adaptativa que oscila entre 0.005 y 0.05.

### Tabla 1. Resumen estadístico agregado por método de selección

| Método | Fitness medio | Fitness mínimo | Fitness máximo | Makespan medio (min) | Desbalance medio | Tiempo de ejecución medio (s) |
|---|---|---|---|---|---|---|
| Ruleta | 7,5191 × 10⁻⁵ | 7,3723 × 10⁻⁵ | 7,6139 × 10⁻⁵ | 1993,8 | 0,0821 | 0,0592 |
| Torneo | 7,4910 × 10⁻⁵ | 7,3215 × 10⁻⁵ | 7,6178 × 10⁻⁵ | 1999,4 | 0,0873 | 0,0593 |
| Ruleta con preservación elitista | 7,5190 × 10⁻⁵ | 7,4196 × 10⁻⁵ | 7,6892 × 10⁻⁵ | 1996,6 | 0,0795 | 0,0596 |

*Fuente: `TPI/outputs/resumen_resultados_agrupados_soc.csv`, consolidado de 30 repeticiones por método.*

En términos promedio, las diferencias entre métodos fueron pequeñas. Ruleta y ruleta con preservación elitista quedaron apenas por encima de torneo en fitness medio, mientras que esta última alcanzó el mayor fitness máximo puntual de toda la experimentación. Bajo el criterio de selección de mejor solución que implementa `main.py`, el escenario global ganador corresponde a esa mejor corrida puntual con preservación elitista.

### Comparación contra baselines simples

| Referencia | Fitness | Makespan (min) | Penalización total | Desbalance |
|---|---|---|---|---|
| Aleatorio | 6,8139 × 10⁻⁵ | 2618 | 12057,0 | 0,2017 |
| Round robin | 7,3497 × 10⁻⁵ | 2140 | 11465,0 | 0,0827 |
| Least loaded | 7,6502 × 10⁻⁵ | 1810 | 11260,6 | 0,0063 |
| Mejor GA (ruleta con preservación elitista) | 7,6892 × 10⁻⁵ | 1836 | 11168,2 | 0,0286 |

La comparación agrega una referencia simple al experimento: la mejor corrida del algoritmo genético supera a la asignación aleatoria, al round robin y a una heurística greedy de menor carga.

### Tabla 2. Carga final por analista en la mejor solución global (método Ruleta con preservación elitista)

| Analista | Alertas asignadas | Carga total (min) | Alertas críticas | Severidad promedio |
|---|---|---|---|---|
| 1 | 46 | 1799 | 9 | 51,9 |
| 2 | 55 | 1900 | 6 | 47,1 |
| 3 | 48 | 1827 | 8 | 51,0 |
| 4 | 50 | 1871 | 8 | 51,5 |
| 5 | 44 | 1712 | 8 | 51,7 |
| 6 | 46 | 1698 | 7 | 51,2 |
| 7 | 49 | 1784 | 8 | 49,4 |
| 8 | 55 | 1721 | 3 | 43,1 |
| 9 | 57 | 1766 | 7 | 42,5 |
| 10 | 50 | 1682 | 6 | 45,4 |

*Fuente: `TPI/outputs/distribucion_final_alertas_soc.csv`, calculado a partir de la mejor corrida global entre las 30 repeticiones.*

La carga total osciló entre 1682 y 1900 minutos (media de 1776 minutos), es decir, una dispersión relativa moderada dado que ningún analista quedó ni ampliamente ocioso ni saturado muy por encima del resto. Ese reparto corresponde a la mejor solución global puntual obtenida por el script, no al promedio de las 30 repeticiones.

### Figuras

- **Figura 1 — Fitness máximo por generación** ([`outputs/figures/maximos_por_generacion.png`](../outputs/figures/maximos_por_generacion.png)): se exporta a partir del histórico generacional acumulado de las 30 repeticiones por método y funciona como una referencia visual de la variabilidad de la corrida masiva.
- **Figura 2 — Comparación entre Ruleta, Torneo y Ruleta con preservación elitista (fitness promedio)** ([`outputs/figures/comparacion_metodos.png`](../outputs/figures/comparacion_metodos.png)): resume la evolución de las 30 repeticiones acumuladas para cada método y permite contrastar el comportamiento global de las tres estrategias.
- **Figura 3 — Desviación estándar por generación** ([`outputs/figures/desviacion_estandar_por_generacion.png`](../outputs/figures/desviacion_estandar_por_generacion.png)): muestra la dispersión generacional registrada por el experimento masivo; en conjunto con la tabla agregada, aporta una lectura complementaria de la estabilidad de cada estrategia.
- **Figura 4 — Carga final por analista** ([`outputs/figures/carga_final_por_analista.png`](../outputs/figures/carga_final_por_analista.png), generada especialmente para este documento a partir de `distribucion_final_alertas_soc.csv`): visualiza la Tabla 2 y permite apreciar de un vistazo que la mejor solución hallada reparte la carga sin picos extremos, con todos los analistas dentro de un rango de ±120 minutos respecto de la media.
- **Figura 5 — Evolución de la diversidad genética** (`outputs/figures/evolucion_diversidad_genetica.png`): muestra cómo decae la diversidad genética en la población para cada método, permitiendo evaluar visualmente el riesgo de convergencia prematura.

Estas figuras y tablas no reemplazan el marco teórico ni la concreción del modelo (punto 7 y segunda parte de la guía de cátedra), que quedan fuera del alcance de esta entrega, pero constituyen el avance de programación ya disponible para mostrar durante la clase, ejecutable de punta a punta con `python3 main.py` desde la carpeta `TPI`.

### A. Introducción de la tecnología al medio

El entorno que se modela en este trabajo es el flujo operativo de un Centro de Operaciones de Seguridad, en particular la recepción, priorización y asignación de alertas o *tickets* provenientes del SIEM y de otras fuentes de monitoreo. En ese sentido, el "medio" no es un espacio abstracto sino el sistema real de atención de incidencias del SOC, donde cada alerta compite por recursos humanos limitados y debe ser derivada al analista más conveniente según su severidad, su tiempo estimado de resolución y su plazo de atención comprometido.

La tecnología introducida en ese medio es un motor evolutivo programado en Python, basado en un Algoritmo Genético Canónico, que simula el criterio de asignación óptima de las alertas. El script funciona como un módulo de decisión en segundo plano: toma las alertas generadas por el sistema, evalúa múltiples distribuciones posibles entre analistas y devuelve una matriz de asignación que busca equilibrar carga, reducir esperas y evitar incumplimientos de SLA. De esta manera, la propuesta no reemplaza al SOC, sino que actúa como una capa de optimización que podría integrarse sobre el flujo habitual de tickets para asistir al analista de turno.

### B. Especificación técnica del Hardware y Software

El experimento se ejecutó de forma local sobre un entorno Windows 11, utilizando Python 3.13.7 desde el workspace de VS Code. El hardware disponible para la corrida fue un equipo con procesador Intel Core i7 (arquitectura x64), sin requerir aceleración por GPU ni infraestructura externa, ya que el modelo se apoya únicamente en procesamiento secuencial y en operaciones de cálculo livianas sobre estructuras de datos en memoria.

En cuanto al software, el prototipo se implementó en `TPI/main.py` y emplea las bibliotecas `numpy`, `pandas` y `matplotlib` para el cálculo numérico, el manejo de resultados y la generación de gráficos. Las dependencias mínimas del proyecto se encuentran listadas en `TPI/requirements.txt`, con `matplotlib>=3.7`, `numpy>=1.24` y `pandas>=2.0`. Esta configuración fue suficiente para ejecutar tanto la simulación evolutiva como la exportación de tablas CSV y figuras PNG generadas por el experimento.

---

## 9. Referencias bibliográficas

[1] Jalalvand, F.; Baruwal Chhetri, M.; Nepal, S.; Paris, C. (2025). "Alert Prioritisation in Security Operations Centres: A Systematic Survey on Criteria and Methods". *ACM Computing Surveys*, 57(2). https://dl.acm.org/doi/10.1145/3695462

[2] Tariq, S.; Baruwal Chhetri, M.; Nepal, S.; Paris, C. (2025). "Alert Fatigue in Security Operations Centres: Research Challenges and Opportunities". *ACM Computing Surveys*, 57(9), art. 224. https://dl.acm.org/doi/10.1145/3723158

[3] "Adaptive Alert Prioritisation in Security Operations Centres via Learning to Defer with Human Feedback" (2025). arXiv:2506.18462. https://arxiv.org/abs/2506.18462

[4] "Algoritmo Genético Simple para Resolver el Problema de Programación de la Tienda de Trabajo (Job Shop Scheduling)" (2018). SciELO Chile. https://www.scielo.cl/scielo.php?script=sci_arttext&pid=S0718-07642018000500299

[5] Luna Rosas, F. J.; Tristán Ávila, R.; Martínez Pedroza, J. de J. (2003). "Aplicando un algoritmo genético para balancear carga dinámicamente en ambientes distribuidos orientados a objetos (CORBA)". *ConCiencia Tecnológica*, N.º 23. https://dialnet.unirioja.es/servlet/articulo?codigo=6482681

[6] Holland, J. H. (1975). *Adaptation in Natural and Artificial Systems*. University of Michigan Press.

[7] Goldberg, D. E. (1989). *Genetic Algorithms in Search, Optimization, and Machine Learning*. Addison-Wesley.

[8] Mitchell, M. (1998). *An Introduction to Genetic Algorithms*. MIT Press.

[9] Deb, K. (2001). *Multi-Objective Optimization Using Evolutionary Algorithms*. Wiley.

[10] Bäck, T. (1996). *Evolutionary Algorithms in Theory and Practice*. Oxford University Press.

[11] Haupt, R. L.; Haupt, S. E. (2004). *Practical Genetic Algorithms* (2nd ed.). Wiley.

[12] Coello Coello, C. A.; Lamont, G. B.; Van Veldhuizen, D. A. (2007). *Evolutionary Algorithms for Solving Multi-Objective Problems* (2nd ed.). Springer.
