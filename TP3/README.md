# TP3 - Problema del viajante (TSP)

Tercer trabajo práctico de Algoritmos Genéticos (UTN FRRo). Resuelve el problema del viajante sobre las **capitales de provincia de la República Argentina** con la tabla de distancias que entregó la cátedra ([Matriz/TablaCapitales.xlsx](Matriz/TablaCapitales.xlsx), en kilómetros y en línea recta).

Los tres puntos del enunciado ([Enunciado/enunciado_text.txt](Enunciado/enunciado_text.txt)) están resueltos en un único programa, [main.py](main.py), y explicados en el informe ([docs/informe.html](docs/informe.html), versión PDF en [docs/informe_TP3.pdf](docs/informe_TP3.pdf)).

## Qué pide el enunciado y dónde está

| Enunciado | Programa | Informe |
|---|---|---|
| 1. Método exhaustivo: ¿se puede resolver? Justificar | opción **d** | sección 2 |
| 2a. Heurística del vecino más cercano desde la capital que ingrese el usuario, con mapa, ciudad de partida, recorrido y longitud | opción **a** | sección 3 |
| 2b. Mejor recorrido de la heurística probando todas las capitales | opción **b** | sección 4 |
| 2c. Algoritmo genético (N = 50, M = 200, permutaciones de 23 genes, crossover cíclico) | opción **c** | sección 5 |
| Conclusión que compara heurística y algoritmo genético | | sección 6 |
| Apartado final «Aportes Prácticos del TSP» (tres aplicaciones) | | sección 7 |

## Ejecución

Python 3.10 o superior (probado con 3.13, numpy 2.2, matplotlib 3.10 y openpyxl 3.1).

```bash
python -m pip install -r requirements.txt
python main.py
```

Desde la raíz del repositorio también se puede correr con `python TP3/main.py`. Al ejecutarlo sin argumentos abre el menú:

```text
  a) Heurística del vecino más cercano desde la capital que elijas (con mapa)
  b) Mejor recorrido de la heurística probando todas las capitales como inicio
  c) Algoritmo genético (N = 50, M = 200, crossover cíclico)
  d) Punto 1: justificación del método exhaustivo (cálculo y medición)
  e) Referencia: óptimo exacto por programación dinámica (tarda cerca de un minuto)
  s) Salir
```

- **a** muestra la lista de capitales, pide la capital de partida (se puede escribir el número, la provincia, la capital o parte del nombre), imprime la ciudad de partida, el recorrido completo, la longitud y abre el mapa de la República con el recorrido.
- **b** aplica la heurística desde las 23 capitales, imprime la tabla ordenada, el mejor recorrido, su longitud y el mapa.
- **c** corre el algoritmo genético con los parámetros del enunciado, imprime el mejor recorrido y su longitud, y guarda el mapa y la curva de evolución.
- **d** calcula cuántas rutas hay (N!, (N−1)! y (N−1)!/2), el tiempo que llevaría y mide la rapidez de una búsqueda por fuerza bruta en esta computadora con 5 a 10 ciudades.
- **e** calcula el recorrido óptimo con Held-Karp. No es una búsqueda exhaustiva: se usa sólo como referencia para saber a qué distancia del óptimo quedan la heurística y el algoritmo genético (usa unos 450 MB de memoria; el resultado queda guardado en `outputs/optimo_exacto.json`).

Opciones de línea de comandos:

```bash
python main.py --todo --optimo --calibrar   # regenera sin menú todos los resultados, tablas y mapas (≈ 2,5 minutos)
python main.py --todo --inicio "Santa Fe"   # igual, sin óptimo ni calibración, con otra capital para el punto 2a
python main.py --verificar                  # 9 controles de la tabla, del crossover cíclico y de las rutas
python main.py --sin-abrir                  # no abre los mapas al generarlos
python main.py --help
```

## Decisiones de diseño

- **23 ciudades y no 24.** La tabla de la cátedra trae 24 filas: las 23 capitales de provincia y la Ciudad Autónoma de Buenos Aires. El enunciado pide capitales de provincia y cromosomas de 23 genes, por lo que se excluye la Ciudad Autónoma y la provincia de Buenos Aires queda representada por La Plata. Con la Ciudad Autónoma como ciudad 24, el mejor recorrido de la heurística daría 9.335 km en lugar de 9.334 km.
- **Datos.** Las distancias se leen directamente del archivo de la cátedra (con una errata corregida: «Río Galleqos»). Las coordenadas de las capitales sólo sirven para dibujar los mapas y para controlar la tabla con la fórmula de Haversine (diferencia media 0,36 %). Los límites de provincias salen de Natural Earth 1:10m (dominio público), simplificados en [datos/argentina_provincias.json](datos/argentina_provincias.json).
- **Heurística.** Vecino más cercano, determinista (los empates se resuelven por el menor índice).
- **Algoritmo genético.** Cromosoma = permutación de las 23 ciudades; aptitud escalada (distancia del peor de la generación menos la distancia, más 1) con selección por ruleta y elitismo de 2; **crossover cíclico** como en el apunte de la cátedra; mutación por inversión de un tramo. PC = 75 % y PM = 35 %, elegidos con una calibración de 30 corridas por combinación (resultados en `outputs/calibracion_ag.csv`). Semilla 42 para que cada corrida se pueda reproducir.

## Resultados (tabla de la cátedra, 23 capitales)

| Método | Longitud (km) | Sobre el óptimo |
|---|---:|---:|
| Óptimo exacto (referencia, Held-Karp) | 9.156 | - |
| Heurística, mejor inicio (Neuquén) | 9.334 | 1,9 % |
| Heurística, desde Santa Fe | 9.905 | 8,2 % |
| Heurística, promedio de los 23 inicios | 10.065 | 9,9 % |
| Heurística, peor inicio (San Juan) | 10.660 | 16,4 % |
| Algoritmo genético, corrida con semilla 42 | 9.260 | 1,1 % |
| Algoritmo genético, mejor de 30 corridas | 9.187 | 0,3 % |
| Algoritmo genético, promedio de 30 corridas | 9.482 | 3,6 % |
| Algoritmo genético, peor de 30 corridas | 9.959 | 8,8 % |

Con M = 500 y M = 1.000 ciclos, algunas corridas encuentran el óptimo exacto. El análisis completo está en el informe.

## Estructura

```text
TP3/
├── main.py                     programa único (menú y línea de comandos)
├── requirements.txt
├── README.md
├── Enunciado/
│   └── enunciado_text.txt
├── Matriz/
│   └── TablaCapitales.xlsx     tabla de distancias de la cátedra
├── datos/
│   └── argentina_provincias.json   límites de provincias para los mapas
├── docs/
│   ├── informe.html
│   ├── informe.css
│   └── informe_TP3.pdf
├── outputs/                    resultados que genera main.py (CSV, JSON y figuras)
│   └── figures/
└── TP3_entrega_codigo.zip      código y datos para entregar
```

## Salidas

- Recorridos, tablas y mediciones por consola.
- Mapas y gráficos en `outputs/figures/` (se abren solos desde el menú).
- Tablas en CSV y resumen en JSON en `outputs/`, con los que se armó el informe.
