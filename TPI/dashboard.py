import streamlit as st
import pandas as pd
from pathlib import Path
from PIL import Image
import subprocess
import sys

# Configuración de página
st.set_page_config(
    page_title="TPI Algoritmos Genéticos - SOC",
    page_icon="🧬",
    layout="wide"
)

# Constantes
OUTPUTS_DIR = Path("outputs")
FIGURES_DIR = OUTPUTS_DIR / "figures"

# --- Sidebar para configurar parámetros ---
st.sidebar.header("⚙️ Parámetros del Algoritmo")
st.sidebar.markdown("Ajusta los parámetros y presiona **Ejecutar** para correr el algoritmo.")

with st.sidebar.form("config_form"):
    seed_val = st.number_input("SEED", value=42, step=1)
    n_analistas = st.number_input("N_ANALISTAS", value=10, min_value=1, step=1)
    n_alertas = st.number_input("N_ALERTAS", value=500, min_value=10, step=10)
    tam_pob = st.number_input("TAM_POBLACION", value=10, min_value=2, step=2)
    n_gen = st.number_input("N_GENERACIONES", value=20, min_value=1, step=1)
    p_cross = st.slider("P_CROSSOVER", min_value=0.0, max_value=1.0, value=0.75, step=0.05)
    p_mut = st.slider("P_MUTACION", min_value=0.0, max_value=1.0, value=0.05, step=0.01)
    horiz = st.number_input("HORIZONTE_MINUTOS", value=480, min_value=60, step=60)
    
    submitted = st.form_submit_button("🚀 Ejecutar Algoritmo")

if submitted:
    with st.spinner("Ejecutando algoritmo genético... (esto puede tardar unos segundos)"):
        cmd = [
            sys.executable, "main.py",
            "--seed", str(seed_val),
            "--n-analistas", str(n_analistas),
            "--n-alertas", str(n_alertas),
            "--tam-poblacion", str(tam_pob),
            "--n-generaciones", str(n_gen),
            "--p-crossover", str(p_cross),
            "--p-mutacion", str(p_mut),
            "--horizonte-minutos", str(horiz)
        ]
        try:
            subprocess.run(cmd, check=True)
            st.cache_data.clear()
            st.success("¡Algoritmo finalizado! Los gráficos y tablas han sido actualizados.")
        except subprocess.CalledProcessError as e:
            st.error(f"Error ejecutando main.py: {e}")

# --- Funciones de carga de datos ---
@st.cache_data
def load_data():
    metricas_gen = pd.read_csv(OUTPUTS_DIR / "metricas_generacionales_soc.csv")
    resumen = pd.read_csv(OUTPUTS_DIR / "resumen_resultados_soc.csv")
    distribucion = pd.read_csv(OUTPUTS_DIR / "distribucion_final_alertas_soc.csv")
    grid_search = pd.read_csv(OUTPUTS_DIR / "grid_search_resultados.csv") if (OUTPUTS_DIR / "grid_search_resultados.csv").exists() else None
    return metricas_gen, resumen, distribucion, grid_search

try:
    metricas_gen, resumen, distribucion, grid_search = load_data()
except Exception as e:
    st.error(f"Error cargando los datos. Asegurate de haber corrido `main.py` y los scripts de evaluación. Detalles: {e}")
    st.stop()

# --- Interfaz Principal ---
st.title("🧬 Optimización SOC mediante Algoritmos Genéticos")
st.markdown("**Trabajo Práctico Integrador** - Cátedra de Algoritmos Genéticos (UTN FRRo)")
st.markdown("---")

# Métricas Globales
mejor_fitness = resumen.iloc[0]['mejor_fitness_global']
espera_critica = resumen.iloc[0]['espera_critica_promedio_min']
desbalance = resumen.iloc[0]['desbalance_carga']
tiempo_total = resumen.iloc[0]['tiempo_total_estimado_min']

col1, col2, col3, col4 = st.columns(4)
col1.metric("Mejor Fitness Global", f"{mejor_fitness:.6f}")
col2.metric("Espera Crítica Prom.", f"{espera_critica:.1f} min")
col3.metric("Desbalance Carga", f"{desbalance:.4f}")
col4.metric("Tiempo Total Asignado", f"{tiempo_total} min")

st.markdown("---")

# --- Pestañas ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Evolución del Algoritmo", 
    "📊 Distribución y Gantt", 
    "⚖️ Comparativa (Baseline)", 
    "⚙️ Hiperparámetros"
])

with tab1:
    st.header("Convergencia Generacional")
    st.markdown("Evolución del Fitness (Máximo, Mínimo y Promedio) a lo largo de las generaciones.")
    st.line_chart(metricas_gen.set_index("generacion")[["fitness_max", "fitness_prom", "fitness_min"]])
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Datos Tabulares (Últimas generaciones)")
        st.dataframe(metricas_gen.tail(), use_container_width=True)
    with col_b:
        st.subheader("Desviación Estándar")
        st.line_chart(metricas_gen.set_index("generacion")[["desv_std"]], color="#d32f2f")

with tab2:
    st.header("Asignación Final a Analistas")
    
    st.subheader("1. Carga Total por Analista")
    img_path_carga = FIGURES_DIR / "carga_final_por_analista.png"
    if img_path_carga.exists():
        st.image(Image.open(img_path_carga), use_container_width=True)
    
    st.subheader("2. Diagrama de Gantt Temporal")
    st.markdown("Visualización tipo *Scheduling* de cómo cada analista atiende las alertas en su turno de 8hs. (Rojo = Crítico).")
    img_path_gantt = FIGURES_DIR / "gantt_asignacion_final.png"
    if img_path_gantt.exists():
        st.image(Image.open(img_path_gantt), use_container_width=True)
    else:
        st.warning("Diagrama de Gantt no encontrado. Ejecutá `gantt_chart.py`.")
        
    st.subheader("3. Detalle Operativo")
    st.dataframe(distribucion, use_container_width=True)

with tab3:
    st.header("Validación Empírica (AG vs Round-Robin)")
    st.markdown("Demostración de la mejora introducida por el Algoritmo Genético frente a una heurística de asignación secuencial clásica.")
    
    img_path_comp = FIGURES_DIR / "comparativa_baseline_ag.png"
    if img_path_comp.exists():
        st.image(Image.open(img_path_comp), use_container_width=True)
    else:
        st.warning("Comparativa no encontrada. Ejecutá `baseline_comparacion.py`.")

with tab4:
    st.header("Sintonización de Parámetros (Grid Search)")
    if grid_search is not None:
        st.markdown("Resultados de probar 18 combinaciones distintas para encontrar el óptimo matemático.")
        st.dataframe(grid_search, use_container_width=True)
        st.info(f"**Mejor configuración encontrada:** Población {grid_search.iloc[0]['poblacion']}, Mutación {grid_search.iloc[0]['mutacion']}, Crossover {grid_search.iloc[0]['crossover']}")
    else:
        st.warning("Resultados de Grid Search no encontrados. Ejecutá `hyper_tuner.py`.")

# Footer
st.markdown("---")
st.markdown("### 📊 Detalles Técnicos de la Última Ejecución del Algoritmo")

col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    st.markdown("**Desempeño y Penalizaciones**")
    st.markdown(f"- **Penalización Total:** `{resumen.iloc[0]['penalizacion_total']:.2f}`")
    st.markdown(f"- **Sobrecarga Relativa:** `{resumen.iloc[0]['sobrecarga_relativa']:.4f}`")
    st.markdown(f"- **Retraso Crítico Promedio:** `{resumen.iloc[0]['retraso_critico_promedio_min']:.2f} min`")
    
with col_f2:
    st.markdown("**Métricas de Backlog (Fuera del Horizonte)**")
    st.markdown(f"- **Alertas en Backlog:** `{resumen.iloc[0]['backlog_alertas']}` alertas")
    st.markdown(f"- **Backlog Acumulado:** `{resumen.iloc[0]['backlog_minutos']:.2f} min`")

with col_f3:
    st.markdown("**Tiempos y Eficiencia Computacional**")
    st.markdown(f"- **Espera Promedio Global:** `{resumen.iloc[0]['espera_promedio_min']:.2f} min`")
    st.markdown(f"- **Tiempo de Ejecución (CPU):** `{resumen.iloc[0]['tiempo_ejecucion_seg']:.4f} seg`")

