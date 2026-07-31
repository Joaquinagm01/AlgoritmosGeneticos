# 🚀 Guía de Ejecución: Dashboard Interactivo SOC

Esta guía te muestra cómo levantar la aplicación web interactiva desarrollada con **Streamlit** en tu propia computadora o durante la presentación del Trabajo Práctico Integrador.

## 📋 Requisitos Previos y Ubicación

Primero que nada, abrí la terminal y asegurate de entrar a la carpeta correcta pegando este comando:

```bash
cd /Users/joa/AlgoritmosGeneticos/TPI
```

Si es la primera vez que vas a correr el dashboard, instalá las dependencias (Pandas, Streamlit, etc) con:

```bash
python3 -m pip install -r requirements.txt
```

*(Esto instalará Pandas, NumPy, Matplotlib y Streamlit).*

---

## ▶️ Paso 1: Generar los Datos (Opcional pero Recomendado)

El Dashboard no calcula el algoritmo en vivo porque demoraría mucho. Lo que hace es **leer los archivos generados en la carpeta `outputs/`**. 

Si querés asegurarte de que los gráficos estén actualizados con tu última versión del código, ejecutá primero los scripts principales:

```bash
# 1. Corre el algoritmo genético y genera la mejor asignación
python3 main.py

# 2. (Opcional) Genera la imagen del diagrama temporal
python3 gantt_chart.py

# 3. (Opcional) Genera la comparativa contra Round-Robin
python3 baseline_comparacion.py
```

---

## 🌐 Paso 2: Ejecutar la Aplicación Web (Streamlit)

Para levantar el servidor local y ver la interfaz, usá el siguiente comando desde la carpeta `TPI/`:

```bash
python3 -m streamlit run dashboard.py
```

### ¿Qué va a pasar?
1. Se abrirá una pequeña terminal local (servidor).
2. Automáticamente se abrirá una nueva pestaña en tu navegador web predeterminado apuntando a `http://localhost:8501`.
3. ¡Ya podés navegar por las pestañas e interactuar con tu proyecto!

---

## 🛑 Paso 3: Apagar la Aplicación

Cuando termines de usar el Dashboard o finalices tu exposición, volvé a la terminal donde ejecutaste el comando del Paso 2 y presioná:

**`Ctrl + C`** (Control + C)

Esto detendrá el servidor web y cerrará la aplicación de forma segura.
