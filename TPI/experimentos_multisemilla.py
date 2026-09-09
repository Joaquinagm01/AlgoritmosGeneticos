"""Evalua la estabilidad del AG sobre varias semillas reproducibles."""

import argparse

import pandas as pd
from scipy.stats import wilcoxon

from baseline_comparacion import asignar_round_robin
from main import OUTPUTS_DIR, SEED, _evaluar_asignacion, derivar_alertas_desde_dataset, evolucionar, N_ANALISTAS


def ejecutar_experimentos(n_corridas: int = 20, peso_tiempo_objetivo: float = 0.10) -> pd.DataFrame:
    alertas = derivar_alertas_desde_dataset()
    evaluacion_rr = _evaluar_asignacion(asignar_round_robin(len(alertas), N_ANALISTAS), alertas)
    resultados = []

    for indice in range(n_corridas):
        semilla = SEED + indice
        _, resumen = evolucionar(
            alertas,
            seed=semilla,
            peso_tiempo_objetivo=peso_tiempo_objetivo,
        )
        resultados.append(
            {
                "corrida": indice + 1,
                "seed": semilla,
                "peso_tiempo_objetivo": peso_tiempo_objetivo,
                "fitness": resumen["mejor_fitness_global"],
                "tiempo_total_min": resumen["tiempo_total_estimado_min"],
                "espera_promedio_min": resumen["espera_promedio_min"],
                "espera_critica_promedio_min": resumen["espera_critica_promedio_min"],
                "backlog_alertas": resumen["backlog_alertas"],
                "backlog_ponderado": resumen["backlog_ponderado"],
                "backlog_baja": resumen["backlog_baja"],
                "backlog_media": resumen["backlog_media"],
                "backlog_alta": resumen["backlog_alta"],
                "backlog_critica": resumen["backlog_critica"],
                "desbalance_carga": resumen["desbalance_carga"],
                "sobrecarga_relativa": resumen["sobrecarga_relativa"],
                "tiempo_ejecucion_seg": resumen["tiempo_ejecucion_seg"],
                "rr_backlog_alertas": evaluacion_rr["backlog_alertas"],
                "rr_espera_critica_promedio_min": evaluacion_rr["espera_critica_promedio_min"],
                "rr_desbalance_carga": evaluacion_rr["desbalance_carga"],
                "ag_mejora_backlog_alertas": evaluacion_rr["backlog_alertas"] - resumen["backlog_alertas"],
                "ag_mejora_espera_critica_min": evaluacion_rr["espera_critica_promedio_min"] - resumen["espera_critica_promedio_min"],
                "ag_mejora_desbalance": evaluacion_rr["desbalance_carga"] - resumen["desbalance_carga"],
            }
        )

    datos = pd.DataFrame(resultados)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    ruta = OUTPUTS_DIR / "experimentos_multisemilla.csv"
    datos.to_csv(ruta, index=False)

    resumen = datos.drop(columns=["corrida", "seed"]).agg(["mean", "std", "min", "max"])
    resumen.to_csv(OUTPUTS_DIR / "resumen_multisemilla.csv")
    pruebas = {
        "espera_critica": wilcoxon(
            datos["rr_espera_critica_promedio_min"],
            datos["espera_critica_promedio_min"],
            alternative="greater",
        ),
        "desbalance": wilcoxon(
            datos["rr_desbalance_carga"],
            datos["desbalance_carga"],
            alternative="greater",
        ),
        "backlog_total": wilcoxon(
            datos["rr_backlog_alertas"],
            datos["backlog_alertas"],
            alternative="greater",
        ),
    }
    pruebas_df = pd.DataFrame(
        [
            {"metrica": nombre, "estadistico": resultado.statistic, "p_valor": resultado.pvalue}
            for nombre, resultado in pruebas.items()
        ]
    )
    pruebas_df.to_csv(OUTPUTS_DIR / "pruebas_wilcoxon.csv", index=False)
    print("\nPruebas de Wilcoxon pareadas (RR > AG):")
    print(pruebas_df.to_string(index=False))
    print(f"Resultados guardados en: {ruta}")
    print(resumen.to_string())
    return datos


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evalua estabilidad del AG con varias semillas.")
    parser.add_argument("--corridas", type=int, default=20, help="Cantidad de semillas a evaluar")
    parser.add_argument("--peso-tiempo", type=float, default=0.10, help="Peso del makespan en el objetivo")
    args = parser.parse_args()
    ejecutar_experimentos(args.corridas, args.peso_tiempo)