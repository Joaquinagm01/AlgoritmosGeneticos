# TP3 - Problema del Viajante

Trabajo práctico sobre el problema del viajante de comercio aplicado a las capitales provinciales de la República Argentina.

## Objetivos

- Analizar por qué la resolución exhaustiva no es viable para 23 ciudades.
- Resolver recorridos con la heurística de vecino más cercano.
- Resolver el problema con un algoritmo genético sobre permutaciones.
- Generar un informe HTML con el desarrollo teórico y los resultados.

## Estructura

```text
TP3/
├── main.py
├── requirements.txt
├── README.md
└── docs/
    ├── informe.html
    └── informe.css
```

## Requisitos

- Python 3.10+
- `matplotlib`
- `numpy`
- `pandas`

## Ejecución

Instalar dependencias:

```bash
python -m pip install -r TP3/requirements.txt
```

Ejecutar el programa:

```bash
python TP3/main.py
```

## Menú del programa

- Opción A: ingresar una provincia y obtener el recorrido por heurística desde esa capital.
- Opción B: buscar el mejor recorrido heurístico probando todas las capitales como inicio.
- Opción C: resolver el TSP con un algoritmo genético.

## Salidas

- Recorridos impresos por consola.
- Figuras con los recorridos generados en `TP3/outputs/figures/`.
- Copia de las figuras para el informe en `TP3/docs/assets/figures/`.
- Informe HTML en `TP3/docs/informe.html`.

## Observación sobre el método exhaustivo

Para 23 capitales, el espacio de soluciones es factorial. La cantidad de rutas posibles crece tan rápido que el enfoque exhaustivo completo no resulta práctico en tiempo razonable, por lo que en el informe se justifica teóricamente su inviabilidad y se compara con heurísticas y algoritmo genético.
