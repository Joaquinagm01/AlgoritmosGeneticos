# TP 1 - Algoritmo Genético Canónico

Trabajo Práctico universitario de **Inteligencia Artificial** para implementar un **Algoritmo Genético Canónico** que maximiza la función:

f(x) = (x / coef)^2

Dentro del dominio [0, 2^30 - 1], donde `coef = 2^30 - 1`.

---

## Contexto del Problema

Se busca encontrar el máximo de una función mediante un AG canónico con:

- Codificación binaria de 30 bits.
- Población inicial de 10 individuos.
- Probabilidad de crossover de 0.75.
- Probabilidad de mutación de 0.05.
- Crossover de 1 punto.
- Mutación invertida.
- Selección por ruleta, torneo y elitismo.

---

## Escenario del Modelo

- Dominio de búsqueda: enteros entre `0` y `2^30 - 1`.
- Cromosoma: 30 bits.
- Objetivo: maximizar el valor de la función objetivo.

---

## Representación Genética

Cada cromosoma representa un número entero codificado en binario.

Ejemplo: `010101001011...` (30 bits)

- Índice = posición del gen.
- Valor = `0` o `1`.

---

## Parámetros del AG

| Parámetro | Valor |
|-----------|-------|
| Población inicial | 10 individuos |
| Generaciones base | 20 |
| Probabilidad de crossover | 0.75 |
| Probabilidad de mutación | 0.05 |
| Método de crossover | 1 punto |
| Método de mutación | Invertida |
| Métodos de selección | Ruleta, Torneo, Elitismo |

---

## Función Fitness

La aptitud coincide con la función objetivo:

f(x) = (x / coef)^2

Cuanto mayor es `x`, mayor es el fitness, y el óptimo se encuentra en el extremo superior del dominio.

---

## Estructura del Proyecto

```text
.
├── main.py
├── src/main.py
├── requirements.txt
├── README.md
├── docs/
│   ├── informe.html
│   ├── informe.css
│   └── assets/
│       ├── utn_rosario_logo.png
│       └── figures/
└── outputs/
    ├── *.csv
    └── figures/
```

---

## Requisitos

- Python 3.10+
- `matplotlib`
- `numpy`
- `pandas`

---

## Ejecución

### Opción 1: Ejecutar desde la raíz
```bash
python main.py
```

### Opción 2: Ejecutar desde el módulo `src`
```bash
python src/main.py
```

---

## Resultados Generados

### Por consola
- Tablas de métricas por generación.
- Resumen final por método de selección.
- Mejor cromosoma y valor máximo encontrado.
- Resumen de variantes para 20, 100 y 200 corridas.

### Archivos CSV exportados
- `metricas_generacionales.csv`
- `resumen_resultados.csv`
- `metricas_variantes_generaciones.csv`
- `experimentos_repetidos.csv`
- `resumen_variantes_generaciones.csv`
- `tabla_mins_prom_maxs_por_configuracion.csv`
- `tabla_estabilidad_tiempos.csv`
- `experimentos_adicionales.csv`

### Gráficos exportados
- `maximos_por_generacion.png`
- `promedios_por_generacion.png`
- `minimos_por_generacion.png`
- `desviacion_estandar_por_generacion.png`
- `comparacion_metodos.png`
- `comparativa_20_iteraciones.png`
- `comparativa_100_iteraciones.png`
- `comparativa_200_iteraciones.png`

---

## Informe

Abrir `docs/informe.html` en un navegador moderno. El informe incluye:

- Marco teórico del AG canónico.
- Descripción del problema y función objetivo.
- Parámetros fijos y variables.
- Resultados para ruleta, torneo y elitismo.
- Experimentos adicionales.
- Gráficas comparativas.
- Tabla de estabilidad y tiempos.
- Conclusiones.

> El script copia automáticamente los gráficos de `outputs/figures/` a `docs/assets/figures/` para que el informe se vea correctamente en local.

---

## Autores

- **Chacón Agustina** — aguscchacon@gmail.com 
- **Gomez Manna Joaquina**  gomezmannajoaquina@gmail.com
- **Tabini Azul** — azultabini@gmail.com 
- **Carloni, Nahuel Iván** — nahuelcarloni25@gmail.com
- **Mierez, Joaquin** — joakomierez1@hotmail.com


**Materia**: Algoritmo Genético
**Facultad**: UTN Facultad Regional Rosario  
**Profesores**: Daniela Díaz y Víctor Lombardo

