# 🧬 TPI - Optimización de Asignación de Alertas SOC con Algoritmos Genéticos

Bienvenido al repositorio del Trabajo Práctico Integrador para la cátedra de Algoritmos Genéticos (UTN FRRo).
Este proyecto aborda un problema de asignación y scheduling en máquinas paralelas para alertas de un Centro de Operaciones de Seguridad (SOC). El modelo sirve como caso particular relacionado con el *Job Shop Scheduling* estocástico, y busca priorizar amenazas severas sin sobrecargar a los analistas.

![Diagrama de Gantt](outputs/figures/gantt_asignacion_final.png)

## 📌 Resumen del Proyecto

El escenario oficial modela la asignación de 100 alertas derivadas de tráfico real a un equipo de 10 analistas. También se incluyen escenarios de estrés de 120 alertas y de saturación de 500 alertas para estudiar cómo cambia el comportamiento del algoritmo cuando la demanda supera la capacidad.

**Características Principales:**
- **Datos derivados:** Utiliza el dataset público **CICIDS2017** como fuente de eventos y complementa las alertas con atributos operativos sintéticos.
- **Algoritmo Genético:** Implementa selección por ranking, crossover, mutación por bloques y elitismo (`main.py`).
- **Validación Empírica:** Cuenta con un Sintonizador de Hiperparámetros y una comparación con Round-Robin, Menor carga y Urgencia balanceada.
- **Evaluación reproducible:** `experimento.py` compara AG y Round-Robin sobre las mismas alertas y escenarios de duración en 20 semillas.
- **Extensiones:** Incluye incertidumbre en los tiempos, flujo continuo y criticidad de activos mediante un catálogo CMDB simulado.
- **Visualización:** Incluye un Dashboard Interactivo construido en **Streamlit** para presentar los resultados de forma visual y profesional.

---

## 🏗️ Arquitectura del Repositorio

| Archivo / Carpeta | Descripción |
|------------------|-------------|
| `main.py` | Motor del Algoritmo Genético y simulador de asignación. |
| `hyper_tuner.py` | Script de Grid Search para justificar empíricamente las tasas de mutación y crossover. |
| `baseline_comparacion.py` | Script que compara nuestro AG contra un asignador tradicional (Round-Robin). |
| `experimento.py` | Comparación pareada multi-semilla para los escenarios principal, de estrés y de saturación. |
| `dashboard.py` | Interfaz gráfica interactiva hecha en Streamlit para exponer resultados. |
| `docs/` | Documentación académica: `informe.html` y `articulo_v2.tex`. |
| `outputs/` | Archivos CSV generados y gráficos (`figures/`). |

---

## Guía rápida de instalación y uso

Todos los comandos de esta sección se ejecutan desde la carpeta `TPI`.

### 1. Instalar dependencias
Requiere Python 3. Instalá las dependencias con:
```bash
python -m pip install -r requirements.txt
```

### 2. Ejecutar el algoritmo
Para ejecutar la corrida completa:
```bash
python main.py
```
Esto genera el resumen, las métricas generacionales, la distribución final y los gráficos en `outputs/`.

Para probar rápidamente que todo funciona:
```bash
python main.py --tam-poblacion 5 --n-generaciones 3
```

El escenario oficial usa 100 alertas y criticidad de activos `cmdb`. Para ejecutar
el escenario de estrés:
```bash
python main.py --n-alertas 120 --criticidad-activo cmdb
```

Por defecto, el cromosoma tiene tres bloques: asignación de analista, ajuste
evolucionado de prioridad de despacho y dos pesos globales de criticidad (`w2`,
`w3`). Estos pesos no cambian la criticidad observada: aprenden cuánto debe
influir cada nivel en el orden de despacho. Para ejecutar las variantes de
ablación:
```bash
# A: solo asignación
python main.py --sin-ajuste --sin-criticidad
# B: asignación + ajuste individual
python main.py --sin-criticidad
# C: asignación + política global de criticidad
python main.py --sin-ajuste
# D: asignación + ajuste + política de criticidad (por defecto)
python main.py
```

Para reproducir el escenario de saturación:
```bash
python main.py --n-alertas 500 --criticidad-activo cmdb
```

### Semilla aleatoria y reproducibilidad

Para sortear una semilla distinta en cada corrida:
```bash
python main.py --seed-aleatoria
```

El flag se puede combinar con otras opciones:
```bash
python main.py --seed-aleatoria --flujo-continuo
```

Al comenzar, el programa informa la semilla utilizada para repetir exactamente
la corrida. Para repetirla, ejecutá:
```bash
python main.py --seed <semilla-informada>
```

El flag no lleva ningún valor. Si el comando se arma desde un dashboard o
script, alcanza con agregar `--seed-aleatoria` a la lista de argumentos.

### 3. Comparar con los baselines
Después de ejecutar `main.py`, generá la comparación:
```bash
python baseline_comparacion.py
```
El script actualiza `outputs/comparativa_baselines.csv` y genera tres gráficos en `outputs/figures/`.

### 4. Ejecutar la comparación multi-semilla

La comparación recomendada usa las semillas 42 a 61, las mismas alertas para
cada par AG/Round-Robin y escenarios nuevos de validación:
```bash
python experimento.py
```

Para comparar las variantes del cromosoma usando las corridas ya guardadas,
sin volver a ejecutar el algoritmo:
```bash
python comparar_ablacion.py
```
El resultado pareado queda en `outputs/comparacion_ablacion.csv` e incluye
diferencias contra A, comparaciones D-B y D-C, IC bootstrap, Wilcoxon con
corrección de Holm, victorias/empates/derrotas y estadísticas de `w2`, `w3` y
`w3-w2`.

Para ejecutar el control de búsqueda aleatoria con el mismo presupuesto del AG
(10.000 evaluaciones por escenario y semilla):
```bash
python busqueda_aleatoria.py --variante D --semillas 42-61
```
Los resultados se guardan en `outputs/busqueda_aleatoria/`. Este control usa
las mismas instancias, escenarios de duración y validación fuera de muestra que
el experimento del AG.

Genera tablas en `outputs/experimento/` con media, desvío estándar, intervalos
de confianza bootstrap y porcentaje de semillas en las que el AG mejora.
Para mantener fijas las alertas entre semillas:
```bash
python experimento.py --modo-muestra fija --seed-datos 42
```

### 5. Ver los resultados
Los archivos más importantes son:
- `outputs/resumen_resultados_soc.csv`: mejor solución y métricas globales.
- `outputs/metricas_generacionales_soc.csv`: evolución por generación.
- `outputs/distribucion_final_alertas_soc.csv`: carga final por analista.
- `outputs/comparativa_baselines.csv`: comparación entre baselines y AG.
- `outputs/figures/`: gráficos PNG de evolución, carga, Gantt y comparación.

Los gráficos de comparación actuales son:
- `espera_critica_comparativa.png`
- `backlog_comparativa.png`
- `desbalance_comparativa.png`

### 6. Abrir el dashboard
El dashboard lee los archivos de `outputs/`; no ejecuta el algoritmo en vivo. Para actualizar los datos antes de abrirlo, ejecutá primero `main.py` y, opcionalmente, `gantt_chart.py` y `baseline_comparacion.py`.

Para iniciar Streamlit:
```bash
python -m streamlit run dashboard.py
```
Después abrí la dirección que muestra Streamlit, normalmente `http://localhost:8501`. Para detenerlo, presioná `Ctrl+C` en la terminal.

### 7. Regenerar el PDF del paper
Requiere tener `pdflatex` disponible. Desde `TPI`:
```bash
cd docs
pdflatex -interaction=nonstopmode -halt-on-error articulo_v2.tex
pdflatex -interaction=nonstopmode -halt-on-error articulo_v2.tex
```
El PDF actualizado queda en `docs/articulo_v2.pdf`. Los archivos `.aux`, `.log` y `.out` son regenerables y están ignorados por `TPI/.gitignore`.

---

## 🎓 Documentación Académica

La documentación académica disponible se encuentra en la carpeta `docs/`:
1. **Documento Guía de Investigación**: Informe principal en HTML con la situación problemática, modelo y objetivos (`docs/informe.html`).
2. **Artículo Científico**: Formato de paper IEEE (`docs/articulo_v2.tex`).

---
**Universidad Tecnológica Nacional — Facultad Regional Rosario**  
Cátedra Algoritmos Genéticos · Ciclo lectivo 2026