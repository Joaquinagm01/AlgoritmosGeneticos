import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import main
from main import (
    derivar_alertas_desde_dataset,
    _evaluar_asignacion,
    N_ANALISTAS,
    PRIORIDAD_RANK,
    OUTPUTS_DIR,
    FIGURES_DIR,
    RESUMEN_CSV
)

def asignar_round_robin(n_alertas: int, n_analistas: int) -> list:
    """Asigna las alertas de forma secuencial a los analistas (1, 2, 3... 10, 1, 2...)."""
    return [(i % n_analistas) + 1 for i in range(n_alertas)]


def asignar_menor_carga(alertas: list, n_analistas: int) -> list:
    """Asigna cada alerta al analista con menor carga acumulada."""
    cargas = [0] * n_analistas
    cromosoma = [0] * len(alertas)
    for indice, alerta in enumerate(alertas):
        analista = min(range(n_analistas), key=lambda candidato: cargas[candidato])
        cromosoma[indice] = analista + 1
        cargas[analista] += alerta.tiempo_estimado_min
    return cromosoma


def asignar_urgencia_balanceada(alertas: list, n_analistas: int) -> list:
    """Asigna primero las alertas urgentes al analista con menor carga."""
    cargas = [0] * n_analistas
    cromosoma = [0] * len(alertas)
    orden = sorted(
        range(len(alertas)),
        key=lambda indice: (
            -PRIORIDAD_RANK[alertas[indice].prioridad],
            -alertas[indice].severidad,
            alertas[indice].sla_min,
            alertas[indice].llegada_min,
        ),
    )
    for indice in orden:
        analista = min(range(n_analistas), key=lambda candidato: cargas[candidato])
        cromosoma[indice] = analista + 1
        cargas[analista] += alertas[indice].tiempo_estimado_min
    return cromosoma

def generar_comparativa() -> None:
    print("Iniciando comparación entre Baseline (Round-Robin) y Algoritmo Genético...")
    
    # 1. Obtener datos del Algoritmo Genético
    if not RESUMEN_CSV.exists():
        print(f"Error: No se encontró {RESUMEN_CSV}. Corré main.py primero.")
        return
        
    df_resumen = pd.read_csv(RESUMEN_CSV)
    mejor_cromosoma = json.loads(df_resumen.iloc[0]["mejor_cromosoma_texto"])

    # Usamos el n_analistas con el que se corrió main.py la última vez (guardado en el
    # resumen), no el valor por defecto del módulo — si alguien corrió con
    # --n-analistas distinto, esto evita comparar el AG contra un Round-Robin
    # armado para una cantidad distinta de analistas.
    if "n_analistas" in df_resumen.columns:
        n_analistas_real = int(df_resumen.iloc[0]["n_analistas"])
    else:
        n_analistas_real = N_ANALISTAS
        print(f"Aviso: el resumen no indica n_analistas, se asume el valor por defecto ({N_ANALISTAS}).")

    main.N_ANALISTAS = n_analistas_real  # Sincronizamos el global real que usa _evaluar_asignacion
    
    alertas = derivar_alertas_desde_dataset()
    eval_ag = _evaluar_asignacion(mejor_cromosoma, alertas)
    
    # 2. Generar y evaluar baselines adicionales
    cromosoma_baseline = asignar_round_robin(len(alertas), n_analistas_real)
    eval_baseline = _evaluar_asignacion(cromosoma_baseline, alertas)
    cromosoma_menor_carga = asignar_menor_carga(alertas, n_analistas_real)
    eval_menor_carga = _evaluar_asignacion(cromosoma_menor_carga, alertas)
    cromosoma_urgencia = asignar_urgencia_balanceada(alertas, n_analistas_real)
    eval_urgencia = _evaluar_asignacion(cromosoma_urgencia, alertas)

    evaluaciones = {
        "Round-Robin": eval_baseline,
        "Menor carga": eval_menor_carga,
        "Urgencia balanceada": eval_urgencia,
        "Algoritmo Genético": eval_ag,
    }
    tabla_baselines = pd.DataFrame(
        [
            {
                "metodo": metodo,
                "espera_critica_promedio_min": evaluacion["espera_critica_promedio_min"],
                "backlog_alertas": evaluacion["backlog_alertas"],
                "desbalance_carga": evaluacion["desbalance_carga"],
                "espera_promedio_min": evaluacion["espera_promedio_min"],
            }
            for metodo, evaluacion in evaluaciones.items()
        ]
    )
    tabla_baselines.to_csv(OUTPUTS_DIR / "comparativa_baselines.csv", index=False)
    
    # 3. Preparar datos para el gráfico
    metricas = [
        "Espera Crítica Promedio (min)", 
        "Backlog Total (alertas perdidas)", 
        "Desbalance de Carga (0=Perfecto)"
    ]
    
    valores_baseline = [
        eval_baseline["espera_critica_promedio_min"],
        eval_baseline["backlog_alertas"],
        eval_baseline["desbalance_carga"]
    ]
    
    valores_ag = [
        eval_ag["espera_critica_promedio_min"],
        eval_ag["backlog_alertas"],
        eval_ag["desbalance_carga"]
    ]
    
    # 4. Crear un gráfico independiente para cada métrica.
    titulos = ["A. Espera critica", "B. Backlog", "C. Desbalance de carga"]
    etiquetas_y = ["Minutos", "Alertas", "D"]
    formatos = ["{:.1f}", "{:.0f}", "{:.3f}"]
    etiquetas_x = ["Round-Robin", "AG"]
    colores = ["#cfd8dc", "#2a78d6"]

    nombres_archivo = [
        "espera_critica_comparativa.png",
        "backlog_comparativa.png",
        "desbalance_comparativa.png",
    ]
    rutas_salida = []
    for indice, (titulo, etiqueta_y, formato, nombre_archivo) in enumerate(
        zip(titulos, etiquetas_y, formatos, nombres_archivo)
    ):
        fig = plt.figure(figsize=(7, 5))
        ax = fig.add_subplot(111)
        valores = [valores_baseline[indice], valores_ag[indice]]
        barras = []
        for posicion, (etiqueta, valor, color) in enumerate(zip(etiquetas_x, valores, colores)):
            barra = ax.bar(
                posicion,
                valor,
                color=color,
                edgecolor="black",
                width=0.58,
                label=etiqueta,
            )
            barras.append(barra[0])
        ax.set_title(titulo, fontsize=11, pad=10)
        ax.set_ylabel(etiqueta_y, fontsize=10)
        ax.set_xticks(range(2))
        ax.set_xticklabels(etiquetas_x, fontsize=9, fontweight="bold")
        ax.grid(axis="y", linestyle="--", alpha=0.45)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.set_ylim(0, max(valores) * 1.2 if max(valores) else 1)
        ax.legend(frameon=False, fontsize=9)
        for barra, valor in zip(barras, valores):
            ax.annotate(formato.format(valor),
                        xy=(barra.get_x() + barra.get_width() / 2, valor),
                        xytext=(0, 4), textcoords="offset points",
                        ha="center", va="bottom", fontsize=9)

        ruta_salida = FIGURES_DIR / nombre_archivo
        fig.tight_layout()
        fig.savefig(ruta_salida, dpi=300)
        plt.close(fig)
        rutas_salida.append(ruta_salida)

    for ruta_salida in rutas_salida:
        print(f"¡Gráfico comparativo generado exitosamente en: {ruta_salida.relative_to(Path.cwd())}!")
    
    # 6. Imprimir resumen
    print("\n--- RESUMEN DE LA COMPARACIÓN ---")
    print(f"{'Métrica':<35} | {'Baseline':<12} | {'AG':<12} | Mejora")
    print("-" * 75)
    for i, m in enumerate(metricas):
        mejora = ((valores_baseline[i] - valores_ag[i]) / valores_baseline[i] * 100) if valores_baseline[i] else 0
        print(f"{m:<35} | {valores_baseline[i]:<12.3f} | {valores_ag[i]:<12.3f} | {mejora:.1f}%")

if __name__ == "__main__":
    generar_comparativa()
