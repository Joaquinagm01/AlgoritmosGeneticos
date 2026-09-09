# Guía para exponer el TPI (SOC + Algoritmos Genéticos)

Este archivo es una guía simple para la exposición oral. La idea es saber qué mostrar, qué decir y dónde está cada parte del código sin tener que memorizar todo el proyecto. La documentación académica completa está en [docs/informe.html](docs/informe.html); esto es solo una ayuda para presentar.

## 1. Idea general del proyecto

El TPI resuelve un problema de asignación de alertas de seguridad en un SOC. En vez de repartir alertas de forma manual o secuencial, el proyecto usa un Algoritmo Genético para buscar una asignación mejor: menos espera para alertas críticas, menos backlog y mejor reparto de carga entre analistas.

La fuente de datos es el dataset CICIDS2017. De ahí se derivan alertas con prioridad, severidad, SLA y tiempo estimado de resolución.

## 2. Qué mostrar primero en la exposición

El orden más claro para presentar es este:

1. Explicar el problema del SOC y por qué una asignación simple no alcanza.
2. Mostrar el algoritmo principal en [main.py](main.py).
3. Mostrar cómo se comparó contra baselines en [baseline_comparacion.py](baseline_comparacion.py).
4. Mostrar los gráficos de evolución, carga y Gantt.
5. Cerrar con el dashboard en [dashboard.py](dashboard.py) y la API en [api_server.py](api_server.py) si quieren mostrar alcance extra.

## 3. Cómo correrlo en vivo

Todos los comandos se ejecutan desde la carpeta `TPI`.

### Algoritmo principal

```bash
python main.py
```

Eso corre el algoritmo genético, imprime las métricas por generación y genera los archivos de salida en `outputs/`.

Si quieren cambiar parámetros desde consola:

```bash
python main.py --seed 42 --n-analistas 10 --n-alertas 500 --tam-poblacion 50 --n-generaciones 200 --p-crossover 0.75 --p-mutacion 0.05 --seleccion ranking
```

### Comparación contra baselines

```bash
python baseline_comparacion.py
```

### Gráfico de Gantt

```bash
python gantt_chart.py
```

### Grid search de hiperparámetros

```bash
python hyper_tuner.py
```

### Dashboard interactivo

```bash
python -m streamlit run dashboard.py
```

### API REST

```bash
uvicorn api_server:app --reload
```

## 4. Qué hace cada archivo

| Archivo | Qué hace | Idea para explicar en voz alta |
|---|---|---|
| [main.py](main.py) | Es el motor del algoritmo genético canónico. | “Acá está la lógica principal del TPI: cómo se crean las alertas, cómo se evalúan, cómo se cruzan los cromosomas y cómo se guarda el mejor resultado.” |
| [main_avanzado.py](main_avanzado.py) | Versión avanzada con multiobjetivo, tiers de analistas y scheduling dinámico. | “Esto muestra una línea de evolución del proyecto: no es el núcleo académico, pero sí una extensión más ambiciosa.” |
| [baseline_comparacion.py](baseline_comparacion.py) | Compara el AG contra reglas simples como Round-Robin y menor carga. | “Sirve para demostrar con números que el AG mejora frente a estrategias estáticas.” |
| [gantt_chart.py](gantt_chart.py) | Genera el diagrama de Gantt de la mejor solución. | “Nos deja visualizar cuándo atiende cada analista cada alerta.” |
| [hyper_tuner.py](hyper_tuner.py) | Prueba combinaciones de parámetros y guarda el mejor resultado exploratorio. | “Acá justificamos la elección de parámetros con una búsqueda sistemática.” |
| [dashboard.py](dashboard.py) | Muestra resultados con Streamlit. | “Principalmente lee los CSV ya generados, pero también puede relanzar el algoritmo desde la barra lateral y actualizar los datos.” |
| [api_server.py](api_server.py) | Expone una API con FastAPI para asignar lotes de alertas. | “Esto conecta el proyecto con una idea de integración real con SIEM o SOAR.” |

## 5. Paso a paso del código principal

### 5.1. `main.py`

Este archivo concentra la lógica importante.

#### a) `Alerta`

`Alerta` es la clase que representa una alerta del SOC. Guarda:

- `id_alerta`
- `llegada_min`
- `prioridad`
- `severidad`
- `tiempo_estimado_min`
- `sla_min`

Ejemplo simple: una alerta crítica puede llegar al minuto 15, tener severidad 90 y un SLA de 30 minutos.

#### b) `derivar_alertas_desde_dataset()`

Toma una muestra del dataset CICIDS2017 y la transforma en alertas de SOC.

Qué hace, en simple:

1. Lee el CSV original.
2. Toma una muestra de alertas.
3. Calcula severidad y prioridad a partir del tráfico.
4. Asigna un tiempo estimado de resolución.
5. Ordena las alertas por momento de llegada.

Ejemplo para explicar: si el flujo era un DDoS y además muy intenso, la prioridad sale más alta. Si era benigno, la prioridad baja.

#### c) `generar_poblacion()`

Genera soluciones iniciales al azar. Cada cromosoma es una lista donde cada posición representa una alerta y el valor es el ID del analista que la atiende.

Ejemplo:

```text
[3, 1, 5, 5, 2]
```

Eso significa:

- alerta 1 -> analista 3
- alerta 2 -> analista 1
- alerta 3 -> analista 5
- alerta 4 -> analista 5
- alerta 5 -> analista 2

#### d) `_evaluar_asignacion()`

Esta es la parte más importante del algoritmo. Toma un cromosoma y calcula qué tan buena es esa asignación.

Evalúa:

- tiempo total estimado,
- espera promedio,
- espera de alertas críticas,
- backlog,
- desbalance de carga,
- sobrecarga relativa,
- penalizaciones por SLA,
- fitness final.

La idea clave para decir en la exposición es esta: el algoritmo no busca solo terminar rápido, sino terminar bien, respetando prioridades y repartiendo la carga.

El fitness se calcula con un objetivo normalizado y luego se convierte en una métrica a maximizar con esta lógica:

```text
fitness = 1 / (1 + objetivo_normalizado)
```

#### e) Selección de padres

El archivo trae tres formas de seleccionar padres:

- `seleccion_ruleta()`
- `seleccion_torneo()`
- `seleccion_ranking()`

La estrategia por defecto es `ranking`.

Para explicarlo fácil: los mejores individuos tienen más probabilidad de reproducirse, pero sin eliminar del todo la diversidad.

#### f) `crossover()` y `mutacion()`

`crossover()` corta dos cromosomas en un punto y mezcla sus partes.

Ejemplo:

```text
Padre 1: [1, 1, 1, 2, 2]
Padre 2: [3, 3, 3, 4, 4]
```

Si el corte es después del tercer gen:

```text
Hijo 1: [1, 1, 1, 4, 4]
Hijo 2: [3, 3, 3, 2, 2]
```

`mutacion()` cambia algunos genes al azar para no perder variedad.

#### g) `evolucionar()`

Es el bucle principal del AG.

Paso a paso:

1. Genera la población inicial.
2. Evalúa todos los individuos.
3. Elige los mejores.
4. Aplica selección, crossover y mutación.
5. Repite por varias generaciones.
6. Guarda el mejor cromosoma global.

Esto es lo que conviene explicar como “evolución”: cada generación intenta mejorar la anterior.

#### h) `graficar_metricas()` y `graficar_carga_final()`

Estas funciones crean los gráficos en `outputs/figures/`.

- `graficar_metricas()` dibuja fitness máximo, mínimo, promedio y desvío estándar.
- `graficar_carga_final()` muestra cuánto trabajó cada analista.

#### i) `main()`

Es el punto de entrada.

Hace esto:

1. Lee parámetros por consola.
2. Carga alertas desde el dataset.
3. Ejecuta el AG.
4. Imprime una tabla por generación.
5. Guarda CSVs y gráficos.

### 5.2. `baseline_comparacion.py`

Este archivo compara el AG con reglas más simples.

Los tres baselines son:

- `asignar_round_robin()`: reparte secuencialmente 1, 2, 3, 4... 10, 1, 2...
- `asignar_menor_carga()`: manda cada alerta al analista con menos carga acumulada.
- `asignar_urgencia_balanceada()`: primero prioriza alertas más urgentes y después equilibra la carga.

Después los evalúa con el mismo criterio que usa el AG y genera `comparativa_baselines.csv` más tres gráficos.

Idea simple para decir: “Acá no comparamos contra algo inventado; comparamos contra reglas razonables y deterministas.”

### 5.3. `gantt_chart.py`

Reconstruye la mejor solución guardada y la dibuja como diagrama de Gantt.

Cómo explicarlo:

1. Lee el mejor cromosoma desde `resumen_resultados_soc.csv`.
2. Reconstruye las alertas.
3. Calcula el momento de inicio y fin de cada una.
4. Dibuja una barra por alerta y por analista.

Los colores representan prioridad:

- Crítica: rojo
- Alta: naranja
- Media: amarillo
- Baja: verde

### 5.4. `hyper_tuner.py`

Hace una búsqueda en grilla de parámetros.

Prueba combinaciones de:

- tamaño de población,
- probabilidad de mutación,
- probabilidad de crossover.

La idea es justificar que los parámetros no fueron elegidos “a ojo”, sino comparando corridas.

### 5.5. `dashboard.py`

Es la interfaz visual hecha con Streamlit.

Importante para decir en la exposición:

- no ejecuta el algoritmo completo dentro de la pantalla,
- lee los CSV ya generados por `main.py`, `baseline_comparacion.py`, `gantt_chart.py` y `hyper_tuner.py`,
- muestra gráficos y tablas de forma más prolija para presentar.

### 5.6. `api_server.py`

Expone una API REST con FastAPI.

Tiene dos endpoints simples:

- `GET /`: devuelve estado OK.
- `POST /asignar`: recibe alertas y devuelve el analista asignado para cada una.

Ejemplo mental para explicar: “Si un SIEM me manda 20 alertas, esta API las recibe y responde cómo las asignaría el algoritmo.”

### 5.7. `main_avanzado.py`

Es una versión más ambiciosa y experimental.

Incluye ideas como:

- routing por nivel de analista,
- optimización multiobjetivo,
- elitismo avanzado,
- scheduling dinámico por ventanas de tiempo.

Sirve para mostrar evolución del proyecto, pero si les preguntan por el núcleo académico, el archivo principal sigue siendo [main.py](main.py).

## 6. Archivos de salida que conviene mostrar

Después de correr [main.py](main.py), lo importante queda en `outputs/`:

- `metricas_generacionales_soc.csv`: evolución generación por generación.
- `resumen_resultados_soc.csv`: mejor solución global.
- `distribucion_final_alertas_soc.csv`: carga final por analista.
- `carga_final_analistas_soc.csv`: versión resumida de la distribución.
- `alertas_derivadas_dataset.csv`: alertas derivadas desde el dataset.
- `figures/`: gráficos PNG.

Si corren [baseline_comparacion.py](baseline_comparacion.py), también aparece `comparativa_baselines.csv` y tres gráficos comparativos.

## 7. Ejemplos cortos para explicar en clase

### Ejemplo 1: cromosoma

Si un cromosoma dice `[2, 4, 4, 1]`, significa que:

- la alerta 1 la atiende el analista 2,
- la alerta 2 la atiende el 4,
- la alerta 3 la atiende el 4,
- la alerta 4 la atiende el 1.

### Ejemplo 2: por qué el AG mejora al Round-Robin

Round-Robin reparte parejo, pero no mira prioridad ni SLA. El AG sí intenta reducir espera crítica y backlog, así que puede tomar decisiones mejores para el SOC real.

### Ejemplo 3: qué hace el Gantt

Si una alerta crítica empieza en el minuto 20 y dura 40 minutos, el gráfico muestra una barra roja desde el 20 hasta el 60 en la fila del analista que la resolvió.

## 8. Preguntas típicas del profesor y respuesta corta

- ¿Qué representa el cromosoma? La asignación de cada alerta a un analista.
- ¿Qué optimiza el fitness? Un objetivo que combina tiempo, espera, backlog y balance de carga.
- ¿Por qué usan ranking? Porque mantiene presión selectiva sin depender tanto de la escala absoluta del fitness.
- ¿Cómo prueban que no es solo una heurística cualquiera? Con comparación contra baselines y con el dashboard de resultados.
- ¿Qué archivo se lleva la lógica principal? [main.py](main.py).
- ¿Dónde se ve el resultado final? En `outputs/` y en los gráficos de `outputs/figures/`.
- ¿Qué hace la API? Recibe alertas y responde la asignación optimizada.

## 9. Cierre recomendado para la exposición

Podés cerrar con esta idea:

“El proyecto modela un problema real de un SOC, usa un algoritmo genético para buscar buenas asignaciones de alertas, compara el resultado contra reglas más simples, y además deja todo documentado y visualizado para poder defenderlo con números y con gráficos.”
