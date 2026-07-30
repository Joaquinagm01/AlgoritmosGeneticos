import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd

# Importar funciones clave del main
from main import (
    derivar_alertas_desde_dataset,
    _evaluar_asignacion,
    HORIZONTE_MINUTOS,
    N_ANALISTAS,
    OUTPUTS_DIR,
    FIGURES_DIR,
    RESUMEN_CSV
)

def generar_gantt() -> None:
    print("Generando Diagrama de Gantt de la mejor asignación...")
    
    # 1. Leer el mejor cromosoma encontrado
    if not RESUMEN_CSV.exists():
        print(f"Error: No se encontró {RESUMEN_CSV}. Corré main.py primero.")
        return
        
    df_resumen = pd.read_csv(RESUMEN_CSV)
    # Extraer la lista del string json guardado en la columna
    mejor_cromosoma = json.loads(df_resumen.iloc[0]["mejor_cromosoma_texto"])
    
    # 2. Reconstruir las alertas y evaluar el cromosoma para obtener tiempos
    alertas = derivar_alertas_desde_dataset()
    evaluacion = _evaluar_asignacion(mejor_cromosoma, alertas)
    
    finalizacion_por_alerta = evaluacion["finalizacion_por_alerta"]
    
    # 3. Preparar datos para el gráfico
    # Cada fila del gráfico será un analista (de 1 a N_ANALISTAS)
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Colores por prioridad
    colores = {
        "Critica": "#d32f2f", # Rojo
        "Alta": "#f57c00",    # Naranja
        "Media": "#fbc02d",   # Amarillo oscuro
        "Baja": "#388e3c"     # Verde
    }
    
    # Dibujar las barras de tareas
    for idx_alerta, analista in enumerate(mejor_cromosoma):
        alerta = alertas[idx_alerta]
        fin = finalizacion_por_alerta[idx_alerta]
        inicio = fin - alerta.tiempo_estimado_min
        
        # Bloque de la tarea
        ax.barh(
            y=analista,
            width=alerta.tiempo_estimado_min,
            left=inicio,
            color=colores[alerta.prioridad],
            edgecolor="white",
            linewidth=0.5
        )
    
    # 4. Ajustes visuales del gráfico
    ax.set_yticks(range(1, N_ANALISTAS + 1))
    ax.set_yticklabels([f"Analista {i}" for i in range(1, N_ANALISTAS + 1)])
    
    ax.set_xlabel("Tiempo transcurrido (Minutos)")
    ax.set_title("Diagrama de Gantt - Asignación de Alertas SOC (Mejor Solución)", fontsize=14, pad=15)
    
    # Línea vertical marcando el fin del turno (Horizonte)
    ax.axvline(x=HORIZONTE_MINUTOS, color="#424242", linestyle="--", linewidth=1.5, zorder=0)
    ax.text(HORIZONTE_MINUTOS + 5, N_ANALISTAS + 0.5, "Fin del Turno (8 hs)", color="#424242", fontweight="bold")
    
    # Leyenda
    leyendas = [mpatches.Patch(color=color, label=f'Prioridad {prio}') for prio, color in colores.items()]
    ax.legend(handles=leyendas, loc="upper right")
    
    ax.grid(axis='x', linestyle='--', alpha=0.6)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    
    plt.tight_layout()
    
    # Guardar gráfico
    ruta_salida = FIGURES_DIR / "gantt_asignacion_final.png"
    plt.savefig(ruta_salida, dpi=300)
    plt.close()
    
    print(f"¡Diagrama de Gantt generado exitosamente en: {ruta_salida.relative_to(Path.cwd())}!")

if __name__ == "__main__":
    generar_gantt()
