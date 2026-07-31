# 🧬 TPI - Optimización de Asignación de Alertas SOC con Algoritmos Genéticos

Bienvenido al repositorio del Trabajo Práctico Integrador para la cátedra de Algoritmos Genéticos (UTN FRRo).
Este proyecto aborda un problema crítico de ciberseguridad en el mundo real: el *Job Shop Scheduling* de alertas en un Centro de Operaciones de Seguridad (SOC), garantizando que las amenazas más severas se atiendan a tiempo sin sobrecargar a los analistas.

![Diagrama de Gantt](outputs/figures/gantt_asignacion_final.png)

## 📌 Resumen del Proyecto

El proyecto modela la asignación de 500 alertas reales de red a un equipo de 10 analistas. A lo largo del desarrollo, hemos pasado desde un enfoque clásico hasta la integración de optimizaciones empíricas y arquitecturas modernas.

**Características Principales:**
- **Datos Reales:** Utiliza el dataset público **CICIDS2017** para las alertas (simulando ataques DDoS).
- **Core Clásico:** Implementa un **Algoritmo Genético Canónico** con Selección por Ruleta, Crossover de 1 punto y Mutación por reasignación (`main.py`).
- **Validación Empírica:** Cuenta con un Sintonizador de Hiperparámetros (Grid Search) y una comparación *Baseline* contra un asignador tradicional (Round-Robin).
- **Visualización:** Incluye un Dashboard Interactivo construido en **Streamlit** para presentar los resultados de forma visual y profesional.
- **Implementación Avanzada (Futuro):** Incluye un submódulo (`main_avanzado.py` y `api_server.py`) que eleva el proyecto utilizando **NSGA-II (Optimización Multiobjetivo)**, Scheduling Dinámico (simulación en tiempo real) y un servidor REST **FastAPI** para integración con herramientas SIEM.

---

## 🏗️ Arquitectura del Repositorio

| Archivo / Carpeta | Descripción |
|------------------|-------------|
| `main.py` | Motor del Algoritmo Genético Canónico (Requisito Académico). |
| `hyper_tuner.py` | Script de Grid Search para justificar empíricamente las tasas de mutación y crossover. |
| `baseline_comparacion.py` | Script que compara nuestro AG contra un asignador tradicional (Round-Robin). |
| `dashboard.py` | Interfaz gráfica interactiva hecha en Streamlit para exponer resultados. |
| `main_avanzado.py` | **(Extra)** Módulo con optimización Multiobjetivo NSGA-II y Skill-based Routing. |
| `api_server.py` | **(Extra)** API REST con FastAPI para emular integración con un SIEM real. |
| `docs/` | Documentación académica: `informe.html`, `articulo.tex` y guía de defensa. |
| `outputs/` | Archivos CSV generados y gráficos (`figures/`). |

---

## 🚀 Guía de Instalación y Uso

### 1. Requisitos Previos
Asegurate de tener Python 3 instalado. Posicionate en la carpeta del proyecto y ejecutá:
```bash
python3 -m pip install -r requirements.txt
```

### 2. Ejecutar el Algoritmo Principal
Para generar la asignación óptima de alertas (Algoritmo Canónico):
```bash
python3 main.py
```
*Esto generará los gráficos de aptitud y el Gantt en la carpeta `outputs/figures/`.*

### 3. Visualizar el Dashboard Interactivo
Para una exposición visual de los datos y la tabla de métricas:
```bash
python3 -m streamlit run dashboard.py
```

### 4. Modo Avanzado (NSGA-II y API REST)
Si querés probar la versión de "Próxima Generación" (Scheduling Dinámico y Multiobjetivo):
```bash
# Simulación por consola
python3 main_avanzado.py

# Servidor API para recibir alertas externas en formato JSON
uvicorn api_server:app --reload
```
Una vez levantada el API, podés ver la documentación Swagger en `http://localhost:8000/docs`.

---

## 🎓 Documentación Académica

La documentación requerida por la cátedra se encuentra en la carpeta `docs/`:
1. **Documento Guía de Investigación**: Informe principal en HTML con la situación problemática, modelo y objetivos (`docs/informe.html`).
2. **Artículo Científico**: Formato de paper IEEE (`docs/articulo.tex`).
3. **Machete de Defensa**: Guía estructurada para estudiar de cara a la exposición oral (`docs/guia_estudio_defensa.md`).

---
**Universidad Tecnológica Nacional — Facultad Regional Rosario**  
Cátedra Algoritmos Genéticos · Ciclo lectivo 2026