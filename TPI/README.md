# TPI - Algoritmo Genético Canónico para Scheduling de Alertas SOC

Este trabajo práctico implementa un Algoritmo Genético Canónico aplicado a un problema realista de un SOC (Security Operations Center): asignar 500 alertas a 10 analistas minimizando tiempo total de resolución, backlog, espera de alertas críticas y desbalance de carga.

## Dataset

Las alertas ya no son sintéticas: se derivan de una muestra real de **CICIDS2017** (Sharafaldin, Lashkari y Ghorbani, 2018), un dataset público de 225.745 flujos de red de una captura con ataque DDoS, en `dataset/Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv`. Ese dataset no trae campos operativos de SOC (prioridad, severidad, SLA, tiempo de resolución, analista, timestamp), así que `main.py` los deriva con una regla explícita, documentada en `derivar_alertas_desde_dataset()`:

- **Prioridad y severidad**: se derivan combinando la columna `Label` (`DDoS`/`BENIGN`) con la intensidad del tráfico (`Flow Bytes/s`, `Flow Packets/s`), normalizada a una escala 0-100.
- **SLA**: tabla de política fija por prioridad (Baja=240, Media=120, Alta=60, Crítica=30 minutos).
- **Tiempo estimado de resolución**: fórmula en función de la prioridad y la severidad, con ruido acotado.
- **Llegada de la alerta**: se deriva del orden real de las filas en el archivo (que preserva el orden cronológico de la captura), reescalado al horizonte de trabajo de 8 horas.

## Modelo del problema

- 10 analistas SOC.
- 500 alertas muestreadas del dataset real (semilla 42).
- Cada alerta incluye prioridad, severidad, tiempo estimado de resolución y SLA asociado.
- Cada cromosoma representa una solución completa: el gen en la posición i indica a qué analista se asigna la alerta i.

### Representación genética

Ejemplo:

```text
[3, 1, 5, 2, 2, 7, 8, 1, ...]
```

- Índice: alerta.
- Valor: analista asignado, numerado del 1 al 10.

## Función fitness

La evaluación combina el tiempo total estimado con penalizaciones por:

- espera promedio,
- espera de alertas críticas,
- retrasos respecto del SLA,
- backlog,
- desbalance extremo de carga,
- sobrecarga relativa.

La forma general utilizada es:

```text
fitness = 1 / (1 + tiempo_total_estimado + penalizacion)
```

Cuanto menor es el tiempo total y menores son las penalizaciones, mayor es el fitness.

## Operadores implementados

- Selección por ruleta.
- Selección por torneo.
- Elitismo con preservación de individuos de mayor fitness.
- Crossover de 1 punto.
- Mutación por reasignación (cambia el analista de una alerta aleatoria).

## Estructura del programa

El archivo principal es `main.py` y contiene las funciones pedidas para el TP:

- `derivar_alertas_desde_dataset()`
- `generar_poblacion()`
- `calcular_fitness()`
- `seleccion_ruleta()`
- `seleccion_torneo()`
- `crossover()`
- `mutacion()`
- `evolucionar()`
- `calcular_estadisticas()`

## Ejecución

Desde la carpeta raíz del proyecto:

```bash
cd TPI
python3 -m pip install -r requirements.txt
python3 main.py
```

Si ya tenés las dependencias instaladas, alcanza con:

```bash
cd TPI
python3 main.py
```

## Salidas generadas

Al ejecutar el programa se crean:

- `outputs/alertas_derivadas_dataset.csv` (trazabilidad: alertas derivadas del dataset real)
- `outputs/metricas_generacionales_soc.csv`
- `outputs/resumen_resultados_soc.csv`
- `outputs/distribucion_final_alertas_soc.csv`
- `outputs/carga_final_analistas_soc.csv`
- `outputs/figures/` (incluye `carga_final_por_analista.png`)

Y se imprimen por consola:

- fitness máximo, mínimo, promedio y desvío estándar por generación,
- tiempo de ejecución por generación,
- mejor cromosoma encontrado,
- distribución final de alertas,
- carga por analista,
- fitness global final.

## Lectura académica

El problema modela una decisión de scheduling donde cada alerta debe asignarse a un recurso humano limitado. El algoritmo genético explora soluciones distribuyendo la carga entre analistas y privilegiando las alertas críticas. El elitismo protege soluciones prometedoras, mientras que ruleta y torneo permiten comparar presión selectiva y diversidad.

La salida gráfica incluye:

- máximo por generación,
- promedio por generación,
- mínimo por generación,
- desviación estándar por generación,
- comparación entre ruleta, torneo y elitismo.

## Documentación de cátedra

La cátedra exige dos documentos:

1. **Documento Guía de Investigación** (carátula, índice, denominación, situación problemática, problema, objetivos y marco teórico): [docs/informe.html](docs/informe.html), con el mismo formato que los informes de TP1, TP2 y TP3.
2. **Artículo científico** (máximo 8 páginas: abstract, palabras clave, introducción, metodología, resultados, discusión, conclusiones, referencias y datos de contacto): [docs/articulo.tex](docs/articulo.tex) / [docs/articulo.pdf](docs/articulo.pdf), en formato LaTeX (compilar con `xelatex articulo.tex`, dos veces, para resolver las referencias cruzadas).

## Nota

El directorio `TPI` también contiene PDFs y material de referencia que ya venía en el workspace. El programa nuevo convive con ese material sin modificarlo.