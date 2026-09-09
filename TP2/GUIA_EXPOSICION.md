# Guía para la exposición del TP2 (mochila)

Esta guía está pensada para exponer el TP2 con una explicación simple, pero precisa. La idea es mostrar primero qué hace el programa, después cómo está separado el código, y por último cómo defender las decisiones delante del profesor. El informe académico está en [docs/informe.html](docs/informe.html); esto es solo la guía de exposición.

## 1. Qué hay en la carpeta TP2

El trabajo está dividido en 4 partes que se conectan entre sí:

- [scripts/mochila.py](scripts/mochila.py): contiene toda la lógica del problema de la mochila.
- [scripts/main.py](scripts/main.py): maneja el menú, la lectura por teclado y la impresión en consola.
- [scripts/run_bench.py](scripts/run_bench.py): corre benchmarks y guarda resultados en `outputs/`.
- [scripts/generate_plots.py](scripts/generate_plots.py): toma el CSV del benchmark y genera gráficos.

Además, hay tres cosas de entrada/salida que conviene mencionar:

- [Enunciado/instancia_enunciado.json](Enunciado/instancia_enunciado.json): instancia usada en los puntos 1 y 2.
- [Enunciado/enunciado_text.txt](Enunciado/enunciado_text.txt): texto original del enunciado.
- `outputs/`: carpeta donde se guardan reportes, CSV y gráficos generados.

## 2. Guion corto para mostrar en vivo

La demo más clara es correr el menú interactivo desde `TP2/scripts`:

```bash
python main.py
```

El orden que conviene mostrar es este:

1. Opción 1: puntos 1 y 2 del enunciado.
   - Muestra la tabla de objetos, que es el espacio de búsqueda.
   - Explica que cada fila tiene ID, nombre, peso/volumen, valor y valor/peso.
   - Acá se ve el caso donde exhaustivo y greedy dan el mismo valor final.

2. Opción 2: punto 3 del enunciado.
   - Acá aparece el contraejemplo importante.
   - El exhaustivo llega al óptimo y el greedy queda abajo, así que sirve para justificar por qué no alcanza con una heurística codiciosa.

3. Opción 3: cargar una instancia propia por teclado.
   - Sirve para mostrar que no hay nada hardcodeado.
   - El programa pide unidad, capacidad, cantidad de objetos y luego nombre, peso y valor de cada uno.
   - Es útil para hacer una prueba chica en vivo y razonar el resultado a mano.

4. Opción 4: salir.

Si quieren correr una instancia desde un archivo sin menú, desde `TP2/scripts` pueden usar:

```bash
python main.py ../Enunciado/instancia_enunciado.json --unidad cm3
```

Si prefieren correr desde la raíz del repositorio, también funciona así:

```bash
python -m TP2.scripts.run_bench --reps 100
python TP2/scripts/generate_plots.py
```

## 3. Cómo fluye el programa

La lógica siempre sigue la misma secuencia:

1. Se carga una instancia.
2. Se imprimen los objetos disponibles y la capacidad de la mochila.
3. Se ejecutan los dos métodos: exhaustivo y greedy.
4. Se arma un reporte por método.
5. Se imprime una auditoría comparando ambos.

Ese flujo está centralizado para no duplicar lógica: `main.py` solo llama a la función que arma el reporte, y `mochila.py` devuelve los datos ya listos para imprimir.

## 4. Paso a paso de cada parte del código

### 4.1. `scripts/mochila.py`

Este archivo es el motor del TP2. Acá están los datos, los algoritmos y el armado del reporte.

#### `Item`

`Item` es una clase de datos que representa un objeto de la mochila. Guarda:

- `nombre`
- `peso`
- `valor`

Además tiene la propiedad `ratio`, que calcula `valor / peso`. Ese cociente es el criterio que usa el greedy para ordenar los objetos.

#### `valor_total()` y `peso_total()`

Son funciones auxiliares muy simples:

- `valor_total()` suma los valores de una lista de objetos.
- `peso_total()` suma los pesos de una lista de objetos.

Se usan para no repetir cuentas dentro de los algoritmos.

#### `resolver_exhaustivo()`

Este es el algoritmo exacto.

Qué hace, paso a paso:

1. Recorre todos los tamaños posibles de subconjuntos, desde 0 objetos hasta `n` objetos.
2. Para cada tamaño, usa `itertools.combinations` para generar todos los subconjuntos posibles.
3. Cuenta cuántas combinaciones evaluó.
4. Calcula el peso del subconjunto.
5. Si el peso supera la capacidad, lo descarta.
6. Si entra, calcula el valor total.
7. Se queda con el subconjunto de mayor valor.
8. Si hay empate en valor, elige el de menor peso.

Ese último criterio de desempate evita quedar con una solución que gaste más espacio sin necesidad.

#### `resolver_greedy()`

Este es el algoritmo heurístico.

Qué hace:

1. Ordena los objetos por `valor/peso`, de mayor a menor.
2. Recorre esa lista ya ordenada.
3. Si el objeto entra en la capacidad restante, lo agrega.
4. Si no entra, lo salta y sigue con el siguiente.

La idea es simple: elegir primero lo que parece más conveniente. El problema es que no mira combinaciones futuras, por eso puede fallar aunque sea rápido.

#### `medir()`

Esta función mide el tiempo de ejecución de un método usando `time.perf_counter()`.

El resultado devuelve dos cosas:

- la solución obtenida por el algoritmo,
- el tiempo exacto que tardó esa llamada.

#### `_reporte_metodo()`

Toma el resultado de un método y lo transforma en un diccionario con todo lo que hace falta imprimir:

- método usado,
- objetos seleccionados,
- peso total,
- capacidad,
- espacio libre,
- porcentaje ocupado,
- si respeta la capacidad,
- valor total,
- cantidad de combinaciones o candidatos evaluados,
- tiempo de ejecución.

#### `_auditoria()`

Compara exhaustivo contra greedy y genera un texto de conclusión.

Acá se arma la parte más importante de la defensa oral:

- diferencia de tiempo,
- diferencia de cantidad de evaluaciones,
- si greedy igualó al óptimo o no.

Si ambos dan el mismo valor y el mismo peso, la guía deja claro que fue coincidencia de esa instancia, no garantía del algoritmo.

#### `calcular_reporte()`

Es la función que une todo.

Hace tres cosas:

1. ejecuta exhaustivo,
2. ejecuta greedy,
3. arma un reporte único con la instancia, los objetos, los resultados y la auditoría.

`main.py` usa esta función para imprimir en consola, y el benchmark también usa la misma lógica base.

#### Carga de instancias

- `cargar_instancia_desde_json()` lee una instancia desde un archivo JSON.
- `instancia_ejercicios_1_y_2()` carga el JSON del enunciado.
- `instancia_ejercicio_3()` arma a mano la instancia chica del punto 3.

Esto muestra que el programa puede trabajar tanto con datos fijos como con instancias externas.

### 4.2. `scripts/main.py`

Este archivo no resuelve la mochila: solo se encarga de la interfaz con el usuario.

#### `imprimir_espacio_busqueda()`

Muestra la tabla de objetos con sus columnas:

- ID,
- nombre,
- peso/volumen,
- valor,
- valor/peso.

Esta tabla es la respuesta directa al punto del enunciado que pide describir el espacio de búsqueda.

#### `imprimir_reporte_metodo()`

Imprime el reporte de un método en secciones:

- métricas de rendimiento,
- inventario final,
- validación de restricciones,
- función objetivo.

Es la salida que conviene mostrar en la demo porque deja todo ordenado y fácil de explicar.

#### `imprimir_auditoria()`

Imprime la comparación final entre exhaustivo y greedy.

#### `imprimir_comparacion()`

Es la función que junta todo lo anterior:

1. imprime el título,
2. muestra el espacio de búsqueda,
3. ejecuta `calcular_reporte()`,
4. imprime ambos métodos,
5. imprime la auditoría.

#### `pedir_entero()` y `pedir_instancia_por_teclado()`

Estas funciones hacen la carga manual por teclado.

`pedir_entero()` valida que el dato sea un entero y que cumpla un mínimo.
`pedir_instancia_por_teclado()` va pidiendo uno por uno:

- unidad,
- capacidad,
- cantidad de objetos,
- nombre,
- peso,
- valor.

Si el usuario escribe algo inválido, el programa vuelve a pedir el dato.

#### `menu_interactivo()`

Es el bucle principal del programa.

Muestra las cuatro opciones del menú y llama a la función correcta según la elección.

#### `main()`

Hace dos modos de ejecución:

- si recibe un archivo JSON por argumento, corre una sola instancia;
- si no recibe archivo, abre el menú interactivo.

Esto es importante para la exposición porque demuestra que el programa sirve tanto en modo interactivo como en modo archivo.

### 4.3. `scripts/run_bench.py`

Este script sirve para medir varias veces la misma instancia y sacar promedios.

Qué hace:

1. carga el JSON del enunciado,
2. ejecuta exhaustivo y greedy varias veces,
3. mide tiempos con repetición interna para reducir ruido,
4. calcula media, mediana y desvío estándar,
5. guarda un TXT y un CSV en `outputs/`.

El benchmark es útil para justificar con números que el exhaustivo es más costoso, no solo más lento “a ojo”.

Para regenerarlo desde cero, lo más claro es ir a la raíz de `AlgoritmosGeneticos/` y correr:

```bash
python -m TP2.scripts.run_bench --reps 100
python TP2/scripts/generate_plots.py
```

### 4.4. `scripts/generate_plots.py`

Este script lee el CSV del benchmark y genera gráficos.

Genera cuatro imágenes:

- comparación de valores,
- comparación de tiempos en escala normal,
- comparación de tiempos en escala logarítmica,
- comparación de combinaciones evaluadas.

Estos gráficos sirven para mostrar visualmente la diferencia entre ambos métodos.

## 5. Qué decir de cada algoritmo

### Exhaustivo

Prueba todos los subconjuntos posibles de objetos. Como revisa todo, garantiza el óptimo. El problema es que su costo crece de forma exponencial: con `n` objetos hay `2^n` combinaciones.

### Greedy

Ordena por mejor relación valor/peso y mete objetos mientras entren. Es mucho más rápido, pero no garantiza el óptimo porque decide paso a paso sin revisar todas las combinaciones.

## 6. Qué mostrar si el profesor pregunta “¿dónde está X?”

| Lo que pregunta | Qué responder | Archivo |
|---|---|---|
| Dónde están los objetos y sus datos | En la clase `Item` y en las funciones que cargan instancias | [scripts/mochila.py](scripts/mochila.py) |
| Dónde está el exhaustivo | En `resolver_exhaustivo()` | [scripts/mochila.py](scripts/mochila.py) |
| Dónde está el greedy | En `resolver_greedy()` | [scripts/mochila.py](scripts/mochila.py) |
| Dónde miden el tiempo | En `medir()` con `time.perf_counter()` | [scripts/mochila.py](scripts/mochila.py) |
| Dónde arman el reporte | En `calcular_reporte()` y `_reporte_metodo()` | [scripts/mochila.py](scripts/mochila.py) |
| Dónde se imprime por consola | En las funciones `imprimir_*` | [scripts/main.py](scripts/main.py) |
| Dónde está la carga por teclado | En `pedir_instancia_por_teclado()` | [scripts/main.py](scripts/main.py) |
| Dónde está el benchmark | En `run_bench.py` | [scripts/run_bench.py](scripts/run_bench.py) |
| Dónde están los gráficos | En `generate_plots.py` | [scripts/generate_plots.py](scripts/generate_plots.py) |

## 7. Respuestas cortas para preguntas típicas

- ¿Por qué el exhaustivo es más lento? Porque evalúa todas las combinaciones posibles, y eso crece como `2^n`.
- ¿El greedy siempre es peor? No. En la instancia de 10 objetos coincide con el óptimo, pero en el punto 3 no.
- ¿Cómo eligen si hay empate en el exhaustivo? Se queda con el subconjunto de menor peso.
- ¿Qué pasa si cargo un peso inválido? El programa lo rechaza y vuelve a pedirlo.
- ¿Cómo miden el tiempo? Con `time.perf_counter()` alrededor de cada ejecución.
- ¿Por qué separaron `main.py` de `mochila.py`? Para separar interfaz y lógica, y así reutilizar el mismo motor en el menú y en el benchmark.

## 8. Orden recomendado para cerrar la exposición

Si querés cerrar con una idea clara, podés resumir así:

1. La mochila se modela con objetos que tienen nombre, peso y valor.
2. El exhaustivo prueba todo y por eso encuentra el óptimo.
3. El greedy es más rápido, pero puede equivocarse.
4. El programa compara ambos, mide tiempos y deja el resultado listo para defenderlo.
