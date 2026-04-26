# TP - AG para Scheduling SOC

## Estructura del proyecto
- `src/main.py`: implementación principal del Algoritmo Genético.
- `docs/informe.html`: informe académico en HTML.
- `docs/informe.css`: estilos del informe.
- `docs/assets/`: recursos visuales del informe (logo institucional).
- `outputs/`: resultados generados automáticamente.
- `outputs/figures/`: gráficos por generación y comparación de métodos.
- `outputs/legacy/`: artefactos históricos de ejecuciones anteriores.
- `requirements.txt`: dependencias de Python.

## Ejecución
1. Crear entorno virtual (opcional):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Ejecutar:
   ```bash
   python3 src/main.py
   ```

El script genera tablas por consola y exporta métricas y gráficos en `outputs/`.
