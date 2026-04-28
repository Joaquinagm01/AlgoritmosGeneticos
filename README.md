# TP - Algoritmos Genéticos para Scheduling SOC

Trabajo Práctico universitario de **Inteligencia Artificial** aplicado a un problema real de **Ciberseguridad**: optimización de asignación de alertas en un **Security Operations Center (SOC)** mediante un **Algoritmo Genético Canónico**.

---

## Contexto del Problema

Un SOC recibe cientos de alertas de seguridad por día. El objetivo es optimizar automáticamente la asignación de alertas a analistas para:

- Reducir tiempo de respuesta.
- Priorizar alertas críticas.
- Balancear la carga entre analistas.
- Evitar saturación y backlog.

---

## Escenario del Modelo

- **10 analistas** SOC.
- **500 alertas** generadas aleatoriamente.
- Cada alerta posee:
  - **Prioridad**: Baja, Media, Alta, Crítica.
  - **Tiempo estimado** de resolución.
  - **Severidad**.

---

## Representación Genética

Cada **cromosoma** representa una solución completa. Cada **gen** representa la asignación de una alerta a un analista.

Ejemplo: `[3, 1, 5, 2, 2, 7, 8, 1, ...]`

- **Índice** = alerta.
- **Valor** = analista asignado (0..9).

---

## Parámetros del AG

| Parámetro | Valor |
|-----------|-------|
| Población inicial | 10 individuos |
| Generaciones (base) | 20 |
| Probabilidad de crossover | 0.75 |
| Probabilidad de mutación | 0.05 |
| Método de crossover | 1 punto |
| Método de mutación | Invertida |
| Métodos de selección | Ruleta, Torneo, Elitismo |

---

## Función Fitness

```
Fitness = 1 / (1 + (TiempoTotal + Penalización))
```

**Penalizaciones consideradas:**
- **Desbalance** de carga entre analistas (peso 2.0).
- **Sobrecarga** por encima del 120% de la carga promedio (peso 1.5).
- **Espera crítica**: demora media de alertas críticas (peso 1.2).
- **Backlog**: alertas fuera del umbral SLA (peso 30.0).

---

## Estructura del Proyecto

```
.
├── main.py                          # Punto de entrada principal (ejecutable)
├── src/main.py                      # Implementación alternativa (módulo)
├── requirements.txt                 # Dependencias de Python
├── README.md                        # Este archivo
├── docs/
│   ├── informe.html                 # Informe académico completo
│   ├── informe.css                  # Estilos del informe
│   └── assets/
│       ├── utn_rosario_logo.png     # Logo institucional
│       └── figures/                 # Gráficos embebidos en el informe
├── outputs/
│   ├── *.csv                        # Métricas y resultados exportados
│   └── figures/                     # Gráficos generados por el script
└── outputs/legacy/                  # Artefactos históricos
```

---

## Requisitos

- Python 3.10+
- `matplotlib`
- `numpy`
- `pandas`

---

## Instalación

```bash
# Crear entorno virtual (opcional pero recomendado)
python3 -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

---

## Ejecución

### Opción 1: Ejecutar desde la raíz (recomendado)
```bash
python3 main.py
```

### Opción 2: Ejecutar desde el módulo src
```bash
python3 src/main.py
```

---

## Resultados Generados

El script genera automáticamente:

### Por consola
- Tablas de métricas por generación (fitness máx, mín, promedio, desv. std, tiempo).
- Resumen final por método de selección.
- Mejor solución global encontrada.
- Resumen de variantes (20, 100, 200 generaciones).

### Archivos CSV exportados
- `metricas_generacionales_soc.csv` — métricas por generación (base).
- `resumen_resultados_soc.csv` — resumen final por método.
- `metricas_variantes_generaciones.csv` — métricas de variantes.
- `experimentos_repetidos.csv` — resultados de repeticiones por configuración.
- `resumen_variantes_generaciones.csv` — resumen de variantes.
- `tabla_mins_prom_maxs_por_configuracion.csv` — estadísticas agregadas.

### Gráficos exportados (PNG, 200 DPI)
1. `maximos_por_generacion.png` — Fitness máximo por generación.
2. `promedios_por_generacion.png` — Fitness promedio por generación.
3. `minimos_por_generacion.png` — Fitness mínimo por generación.
4. `desviacion_estandar_por_generacion.png` — Desviación estándar.
5. `comparacion_metodos.png` — Comparación global Ruleta vs Torneo vs Elitismo.
6. `comparativa_20_iteraciones.png` — Variante 20 generaciones.
7. `comparativa_100_iteraciones.png` — Variante 100 generaciones.
8. `comparativa_200_iteraciones.png` — Variante 200 generaciones.

---

## Visualización del Informe

Abrir `docs/informe.html` en cualquier navegador moderno. El informe incluye:

- Carátula institucional.
- Índice navegable.
- Marco teórico del AG.
- Descripción del problema SOC.
- Tablas de parámetros y resultados.
- **Gráficos comparativos embebidos** (ajustados para impresión y pantalla).
- Conclusiones y recomendación final.

> **Nota**: Los gráficos del informe se cargan desde `docs/assets/figures/` (copia local) para garantizar visualización offline y compatibilidad con el protocolo `file://`.

---

## Autores

- **Chacón Agustina** — aguscchacon@gmail.com
- **Gomez Manna Joaquina** — gomezmannajoaquina@gmail.com — Legajo: 47791
- **Tabini Azul** — azultabini@gmail.com

**Materia**: Inteligencia Artificial  
**Facultad**: UTN Facultad Regional Rosario  
**Profesores**: Daniela Díaz y Víctor Lombardo

