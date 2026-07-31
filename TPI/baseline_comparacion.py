import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from main import (
    derivar_alertas_desde_dataset,
    _evaluar_asignacion,
    N_ANALISTAS,
    OUTPUTS_DIR,
    FIGURES_DIR,
    RESUMEN_CSV
)

def asignar_round_robin(n_alertas: int, n_analistas: int) -> list:
    """Asigna las alertas de forma secuencial a los analistas (1, 2, 3... 10, 1, 2...)."""
    return [(i % n_analistas) + 1 for i in range(n_alertas)]

def generar_comparativa() -> None:
    print("Iniciando comparación entre Baseline (Round-Robin) y Algoritmo Genético...")
    
    # 1. Obtener datos del Algoritmo Genético
    if not RESUMEN_CSV.exists():
        print(f"Error: No se encontró {RESUMEN_CSV}. Corré main.py primero.")
        return
        
    df_resumen = pd.read_csv(RESUMEN_CSV)
    mejor_cromosoma = json.loads(df_resumen.iloc[0]["mejor_cromosoma_texto"])
    
    alertas = derivar_alertas_desde_dataset()
    eval_ag = _evaluar_asignacion(mejor_cromosoma, alertas)
    
    # 2. Generar y evaluar Baseline
    cromosoma_baseline = asignar_round_robin(len(alertas), N_ANALISTAS)
    eval_baseline = _evaluar_asignacion(cromosoma_baseline, alertas)
    
    # 3. Preparar datos para el gráfico
    metricas = [
        "Espera Crítica Promedio (min)", 
        "Backlog Total (alertas perdidas)", 
        "Desbalance de Carga (0=Perfecto)"
    ]
    
    valores_baseline = [
        eval_baseline["espera_critica_promedio_min"],
        eval_baseline["backlog_alertas"],
        eval_baseline["desbalance_carga"] * 100 # Multiplicado para escala visual
    ]
    
    valores_ag = [
        eval_ag["espera_critica_promedio_min"],
        eval_ag["backlog_alertas"],
        eval_ag["desbalance_carga"] * 100
    ]
    
    # 4. Crear el gráfico de barras
    x = np.arange(len(metricas))
    ancho = 0.35
    
    fig, ax = plt.subplots(figsize=(12, 7))
    rects1 = ax.bar(x - ancho/2, valores_baseline, ancho, label='Baseline (Round-Robin)', color='#cfd8dc', edgecolor='black')
    rects2 = ax.bar(x + ancho/2, valores_ag, ancho, label='Algoritmo Genético', color='#2a78d6', edgecolor='black')
    
    # Títulos y etiquetas
    ax.set_ylabel('Valor (Menor es mejor)', fontsize=12)
    ax.set_title('Comparativa de Rendimiento Operativo del SOC', fontsize=15, pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(metricas, fontsize=11)
    ax.legend(fontsize=12)
    
    # Anotaciones numéricas
    def auto_label(rects):
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f'{height:.1f}',
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=10)
                        
    auto_label(rects1)
    auto_label(rects2)
    
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    
    # 5. Guardar el gráfico
    ruta_salida = FIGURES_DIR / "comparativa_baseline_ag.png"
    plt.savefig(ruta_salida, dpi=300)
    plt.close()
    
    print(f"¡Gráfico comparativo generado exitosamente en: {ruta_salida.relative_to(Path.cwd())}!")
    
    # 6. Imprimir resumen
    print("\n--- RESUMEN DE LA COMPARACIÓN ---")
    print(f"{'Métrica':<35} | {'Baseline':<12} | {'AG':<12} | Mejora")
    print("-" * 75)
    for i, m in enumerate(metricas):
        mejora = ((valores_baseline[i] - valores_ag[i]) / valores_baseline[i] * 100) if valores_baseline[i] else 0
        print(f"{m:<35} | {valores_baseline[i]:<12.2f} | {valores_ag[i]:<12.2f} | {mejora:.1f}%")

if __name__ == "__main__":
    generar_comparativa()
