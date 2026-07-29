# TP2 - Problema de la mochila

Este trabajo práctico resuelve el problema de la mochila con dos enfoques:

- búsqueda exhaustiva (evalúa cada subconjunto posible);
- algoritmo greedy por relación valor/peso (o valor/volumen).

## Qué incluye

- Motor de cálculo (exhaustivo, greedy, armado del reporte) en [scripts/mochila.py](scripts/mochila.py).
- Punto de entrada único con menú interactivo por consola en [scripts/main.py](scripts/main.py).
- Resolución de los tres puntos del enunciado ([Enunciado/enunciado_text.txt](Enunciado/enunciado_text.txt)):
  - Puntos 1 y 2: lista completa de 10 objetos para una mochila de 4200 cm3 ([Enunciado/instancia_enunciado.json](Enunciado/instancia_enunciado.json)).
  - Punto 3: 3 elementos y una mochila de 3000 grs.
  - Instancia propia: se puede cargar por teclado desde el menú (opción 3), respondiendo las preguntas que va haciendo el programa.
- Reporte operativo por consola con métricas de rendimiento, inventario final, validación de restricciones y función objetivo para cada método.
- Auditoría crítica automática (tiempo y combinaciones evaluadas) comparando exhaustivo vs. greedy.
- Benchmark con repeticiones y gráficos en [scripts/run_bench.py](scripts/run_bench.py) y [scripts/generate_plots.py](scripts/generate_plots.py).
- Informe académico en [docs/informe.html](docs/informe.html).

## Ejecución

Desde la carpeta `TP2/scripts`, ejecutando el script sin argumentos se abre un **menú interactivo**:

```bash
cd scripts
python3 main.py
```

```
========================================================================
TP2 - Problema de la mochila: exhaustivo vs. greedy
========================================================================
  1) Puntos 1 y 2 del enunciado (10 objetos, mochila de 4200 cm3)
  2) Punto 3 del enunciado (3 elementos, mochila de 3000 grs.)
  3) Cargar una instancia propia (ingresar objetos por teclado)
  4) Salir
Elegí una opción escribiendo 1, 2, 3 o 4:
```

- **1** y **2** corren directamente los ejercicios del enunciado y muestran el reporte.
- **3** pide, paso a paso, la unidad, la capacidad, la cantidad de objetos y el nombre/peso/valor de cada uno (el programa indica en cada línea qué hay que ingresar).
- **4** cierra el programa.

También podés pasar un archivo JSON con una instancia propia sin pasar por el menú (corre una sola vez y termina):

```bash
python3 main.py instancia_ejemplo.json --unidad cm3
```

El JSON debe tener esta forma:

```json
{
	"capacidad": 4200,
	"items": [
		{"nombre": "A", "peso": 100, "valor": 20},
		{"nombre": "B", "peso": 250, "valor": 60}
	]
}
```

Para regenerar el benchmark y los gráficos (desde la raíz del repositorio, `AlgoritmosGeneticos/`):

```bash
python -m TP2.scripts.run_bench --reps 100
python TP2/scripts/generate_plots.py
```

## Reporte operativo

Por cada método, la ejecución imprime un panel con:

- **Métricas de rendimiento**: tiempo exacto de ejecución y cantidad de combinaciones (o candidatos) evaluados.
- **Inventario final**: los objetos seleccionados.
- **Validación de restricciones**: peso/volumen ocupado, espacio libre y si respeta la capacidad máxima.
- **Función objetivo**: valor económico total acumulado.

Al final de cada instancia se muestra una **auditoría crítica** que compara exhaustivo vs. greedy en tiempo, combinaciones evaluadas y valor obtenido.

## Resultados

### Puntos 1 y 2 — mochila de 4200 cm3 (10 objetos)

- Exhaustivo: evalúa 1024 (2¹⁰) subconjuntos y encuentra el óptimo: valor $299, 3888/4200 cm3 ocupados.
- Greedy: evalúa 10 candidatos y coincide con el óptimo en este caso: valor $299, mismo volumen ocupado, pero ~300 veces más rápido.
- La coincidencia entre ambos métodos es una propiedad de esta instancia particular, no una garantía del algoritmo (ver punto 3).

### Punto 3 — mochila de 3000 grs. (3 elementos)

Para los elementos:

- 1800 grs. y $72
- 600 grs. y $36
- 1200 grs. y $60

con una mochila de 3000 grs.:

- La solución exhaustiva óptima es tomar los elementos 1 y 3 (8 subconjuntos evaluados), valor total $132, sin desperdicio de capacidad.
- La solución greedy toma los elementos 2 y 3 (3 candidatos evaluados), valor total $96, con 1200 grs. de capacidad sin usar.

## Conclusión breve

El método exhaustivo garantiza el óptimo porque evalúa todos los subconjuntos (2ⁿ), y entre las soluciones de mayor valor conserva la de menor desperdicio de capacidad. El greedy es mucho más rápido (evalúa solo n candidatos) y simple, pero solo alcanza el óptimo cuando el orden por relación valor/peso resulta compatible con la capacidad disponible; en general es una alternativa factible, no la solución óptima absoluta.

## Informe

Abrir [docs/informe.html](docs/informe.html) en un navegador moderno. El informe incluye el marco teórico, la instancia completa del enunciado, las métricas reales de cada corrida (tiempo, combinaciones evaluadas, validación de restricciones) y la auditoría comparativa entre exhaustivo y greedy.

## Exposición

Para preparar la presentación (qué correr en vivo, mapa enunciado→código y preguntas típicas del profesor), ver [GUIA_EXPOSICION.md](GUIA_EXPOSICION.md).
