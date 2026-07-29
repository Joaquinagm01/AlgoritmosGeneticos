# Guía para la exposición del TP2 (mochila)

Chuleta para la presentación: qué correr en vivo, qué mostrar del código
cuando el profesor pregunte "¿dónde/cómo hacen tal cosa?", y respuestas
cortas a las preguntas más probables. No es parte del informe académico
(eso es [docs/informe.html](docs/informe.html)); esto es solo para
ordenarnos antes de exponer.

## 1. Guion de demo en terminal (5-7 minutos)

Correr desde `TP2/scripts`:

```bash
python3 main.py
```

Se abre el menú. Orden sugerido:

1. **Opción 1** (puntos 1 y 2, 10 objetos, mochila de 4200 cm3).
   - Mostrar la tabla de objetos (espacio de búsqueda) y remarcar que tiene
     ID, peso/volumen y valor — eso responde el punto 1 del enunciado.
   - Señalar que el exhaustivo evaluó **1024 combinaciones** (2¹⁰) y el
     greedy solo **10 candidatos**, pero en esta instancia ambos llegan al
     mismo valor ($299). Es el caso "lindo" donde coinciden.

2. **Opción 2** (punto 3, 3 elementos, mochila de 3000 grs.).
   - Acá el greedy **no** llega al óptimo ($96 contra $132). Es el
     contraejemplo que demuestra que el greedy no garantiza nada — conviene
     mostrarlo después del caso 1 para que se note el contraste.

3. **Opción 3** (cargar una instancia a mano, en vivo).
   - Sirve para probar frente al profesor que el programa no tiene nada
     "hardcodeado": funciona con cualquier instancia que se cargue por
     teclado. Usar un ejemplo chico y fácil de verificar mentalmente, por
     ejemplo:
     - Unidad: `kg`
     - Capacidad: `10`
     - 2 objetos: `A` (peso `6`, valor `10`) y `B` (peso `5`, valor `9`)
     - Óptimo a mano: A+B pesa 11 (no entra); solo A o solo B entran solos,
       y A vale más → el exhaustivo debe elegir **solo A** ($10). El greedy
       ordena por ratio (A=1.67, B=1.8) así que prueba B primero (entra,
       pesa 5), después A (5+6=11, no entra) → greedy se queda con **solo
       B** ($9). Buen ejemplo chico para mostrar que también acá el greedy
       pierde por poco.

4. **Opción 4** para salir prolijo.

Si el profesor pide "corran de nuevo pero con un archivo", mostrar el modo
sin menú:

```bash
python3 main.py ../Enunciado/instancia_enunciado.json --unidad cm3
```

## 2. Mapa enunciado → código (para cuando pregunten "¿dónde está X?")

| Punto del enunciado | Qué hace | Dónde está |
|---|---|---|
| 1. Espacio de búsqueda (objetos, ID, peso/volumen, valor, capacidad) | Clase `Item` (nombre/peso/valor) + funciones que arman cada instancia | [scripts/mochila.py](scripts/mochila.py): clase `Item` (línea 20), `instancia_ejercicios_1_y_2()` (línea 184), `instancia_ejercicio_3()` (línea 190), `cargar_instancia_desde_json()` (línea 168) |
| Carga interactiva de objetos (interfaz de entrada) | Pide unidad, capacidad, cantidad de objetos y nombre/peso/valor de cada uno, con reintento si el dato es inválido | [scripts/main.py](scripts/main.py): `pedir_instancia_por_teclado()` (línea 121), `pedir_entero()` (línea 106) |
| 2. Búsqueda exhaustiva | Recorre `itertools.combinations` para cada tamaño de subconjunto (0..n), descarta los que superan la capacidad, se queda con el de mayor valor (y menor peso si hay empate) | [scripts/mochila.py](scripts/mochila.py): `resolver_exhaustivo()` (línea 43) |
| 2. Algoritmo greedy | Ordena los objetos por `valor/peso` descendente y los va cargando mientras entren | [scripts/mochila.py](scripts/mochila.py): `resolver_greedy()` (línea 70) |
| 3. Reporte operativo (métricas, inventario, validación, función objetivo) | Arma un diccionario único con los 4 bloques por método | [scripts/mochila.py](scripts/mochila.py): `_reporte_metodo()` (línea 95), `calcular_reporte()` (línea 149) — se imprime desde [scripts/main.py](scripts/main.py): `imprimir_reporte_metodo()` (línea 40) |
| Tiempo exacto de ejecución | Mide con `time.perf_counter()` alrededor de la llamada al método | [scripts/mochila.py](scripts/mochila.py): `medir()` (línea 87) |
| 4. Auditoría crítica / conclusión | Compara tiempo y combinaciones evaluadas, y arma el texto de conclusión (óptimo / factible) | [scripts/mochila.py](scripts/mochila.py): `_auditoria()` (línea 113) — se imprime desde [scripts/main.py](scripts/main.py): `imprimir_auditoria()` (línea 63) |
| Benchmark con repeticiones y gráficos | Corre cada método 100 veces y promedia tiempos; genera los PNG | [scripts/run_bench.py](scripts/run_bench.py), [scripts/generate_plots.py](scripts/generate_plots.py) |

## 3. Cómo explicar cada algoritmo en una frase

- **Exhaustivo**: prueba **todos** los subconjuntos posibles de objetos
  (2ⁿ en total), descarta los que no entran en la mochila y se queda con
  el de mayor valor. Por construcción, es imposible que exista una mejor
  combinación que se le escape — por eso es óptimo. El costo es que crece
  exponencialmente: con 10 objetos son 1024 combinaciones, con 30 objetos
  serían más de mil millones.

- **Greedy**: ordena los objetos de mejor a peor relación valor/peso y los
  va metiendo en la mochila mientras entren, sin volver atrás. Es rápido
  (crece proporcional a `n log n`, por el ordenamiento) pero es una
  decisión "codiciosa": toma lo mejor en cada paso sin ver el panorama
  completo, así que puede dejar afuera una combinación mejor (como pasa en
  el punto 3).

## 4. Preguntas típicas y respuesta corta

- **¿Por qué el exhaustivo es tan lento comparado con el greedy?**
  Porque evalúa 2ⁿ subconjuntos contra los n candidatos del greedy. Con 10
  objetos ya es 1024 contra 10 (~100x); con más objetos la diferencia
  crece exponencialmente, no linealmente.

- **¿El greedy siempre da una solución peor?**
  No necesariamente. En los puntos 1 y 2 (10 objetos) coincidió con el
  óptimo. En el punto 3 (3 elementos) no. La coincidencia depende de si el
  orden por ratio valor/peso "encaja" con la capacidad disponible; no es
  algo que se pueda garantizar de antemano sin resolver el problema.

- **¿Cómo se define qué gana si hay empate en valor?**
  En el exhaustivo, ante empate de valor se elige el subconjunto de menor
  peso (para dejar el menor espacio desperdiciado posible). Está en la
  condición `valor == mejor_valor and peso < mejor_peso` de
  `resolver_exhaustivo()`.

- **¿Qué pasa si cargan un objeto con peso 0 o negativo?**
  El programa lo rechaza y vuelve a pedirlo (`pedir_entero()` exige
  `peso >= 1`), porque un peso 0 rompería el cálculo de la relación
  valor/peso (división por cero).

- **¿Cómo miden el tiempo?**
  Con `time.perf_counter()` alrededor de la llamada a cada método
  (`medir()` en `mochila.py`), que da el tiempo real transcurrido de esa
  ejecución puntual. Para el informe también corrimos un benchmark de 100
  repeticiones (`run_bench.py`) y promediamos, para que el número no
  dependa de una sola corrida con ruido del sistema operativo.

- **¿Por qué separaron `mochila.py` de `main.py`?**
  `mochila.py` tiene solo el cálculo (los dos algoritmos y el armado del
  reporte); `main.py` tiene el menú y la impresión en consola. Así el
  mismo cálculo lo puede usar tanto el menú interactivo como el script de
  benchmark (`run_bench.py`), sin duplicar código ni arriesgarse a que los
  resultados diverjan entre uno y otro.
