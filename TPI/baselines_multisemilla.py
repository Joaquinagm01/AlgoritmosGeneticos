"""Compara los baselines deterministas con el AG en 20 semillas.

Usa las mismas instancias y escenarios de validacion fuera de muestra que
``experimento.py`` y calcula estadisticas pareadas por escenario y semilla.
"""

from __future__ import annotations

import argparse
import importlib
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

import baseline_comparacion as baselines
import experimento


ESCENARIOS = {
    "principal": (100, "cmdb"),
    "estres": (120, "cmdb"),
    "saturacion": (500, "cmdb"),
}
METRICAS = {
    "fitness": True,
    "sla_cumplimiento_pct": True,
    "sla_cumplimiento_critica_pct": True,
    "sla_cumplimiento_activo_critico_pct": True,
    "espera_critica_promedio_min": False,
    "backlog_alertas": False,
    "desbalance_carga": False,
}
SOLUCIONES = ("Round-Robin", "Menor carga", "Urgencia balanceada", "GA")


def parsear_semillas(texto: str) -> list[int]:
    semillas: list[int] = []
    for parte in texto.split(","):
        parte = parte.strip()
        if "-" in parte:
            desde, hasta = parte.split("-", maxsplit=1)
            semillas.extend(range(int(desde), int(hasta) + 1))
        elif parte:
            semillas.append(int(parte))
    if not semillas:
        raise ValueError("Debe indicarse al menos una semilla")
    return semillas


def holm(p_values: np.ndarray) -> np.ndarray:
    orden = np.argsort(p_values)
    ajustados = np.empty(len(p_values), dtype=float)
    anterior = 0.0
    for rango, indice in enumerate(orden):
        anterior = max(anterior, min(1.0, (len(p_values) - rango) * p_values[indice]))
        ajustados[indice] = anterior
    return ajustados


def evaluar_baselines(args, modulo) -> pd.DataFrame:
    modulo.N_ANALISTAS = args.n_analistas
    dataset = Path(args.dataset)
    filas: list[dict[str, object]] = []
    for nombre, (n_alertas, modo_activo) in ESCENARIOS.items():
        for semilla in parsear_semillas(args.semillas):
            alertas = modulo.derivar_alertas_desde_dataset(
                n_alertas=n_alertas,
                seed=semilla,
                dataset_csv=dataset,
                modo_activo=modo_activo,
            )
            instancia = modulo.Instancia(alertas, usar_activos=True)
            escenarios_validacion = modulo._muestrear_duraciones(
                instancia.dur_nominal,
                args.n_validacion,
                args.cv_duracion,
                semilla + 7919,
            ).tolist()
            cromosomas = {
                "Round-Robin": baselines.asignar_round_robin(n_alertas, args.n_analistas),
                "Menor carga": baselines.asignar_menor_carga(alertas, args.n_analistas),
                "Urgencia balanceada": baselines.asignar_urgencia_balanceada(
                    alertas, args.n_analistas
                ),
            }
            for solucion, cromosoma in cromosomas.items():
                metricas = experimento.evaluar_fuera_de_muestra(
                    modulo,
                    instancia,
                    cromosoma,
                    escenarios_validacion,
                )
                filas.append(
                    {
                        "escenario": nombre,
                        "semilla": semilla,
                        "solucion": solucion,
                        **metricas,
                    }
                )
    return pd.DataFrame(filas)


def resumir(detalle: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(12345)
    pares = []
    p_values = []
    for escenario in ESCENARIOS:
        grupo = detalle[detalle["escenario"] == escenario].set_index(["solucion", "semilla"])
        for solucion in ("Round-Robin", "Menor carga", "Urgencia balanceada"):
            for metrica, mayor_es_mejor in METRICAS.items():
                izquierda = grupo.loc[solucion, metrica]
                derecha = grupo.loc["GA", metrica]
                diferencias = (izquierda - derecha).to_numpy(float)
                validas = np.isfinite(diferencias)
                diferencias = diferencias[validas]
                if not mayor_es_mejor:
                    diferencias = -diferencias
                muestras = rng.choice(
                    diferencias, size=(5000, len(diferencias)), replace=True
                ).mean(axis=1)
                ic_inf, ic_sup = np.percentile(muestras, [2.5, 97.5])
                try:
                    p = float(wilcoxon(diferencias, zero_method="wilcox").pvalue)
                except ValueError:
                    p = 1.0
                p_values.append(p)
                pares.append(
                    {
                        "escenario": escenario,
                        "comparacion": f"{solucion} vs GA",
                        "metrica": metrica,
                        "n_semillas": len(diferencias),
                        "diferencia_favorable_al_baseline": float(diferencias.mean()),
                        "ic95_inf": float(ic_inf),
                        "ic95_sup": float(ic_sup),
                        "p_wilcoxon": p,
                    }
                )
    ajustados = holm(np.asarray(p_values))
    for fila, p_holm in zip(pares, ajustados):
        fila["p_holm"] = float(p_holm)
    return pd.DataFrame(pares)


def main() -> None:
    modulo = importlib.import_module("main")
    parser = argparse.ArgumentParser(
        description="Comparacion multi-semilla de baselines deterministas contra el AG."
    )
    parser.add_argument("--semillas", default="42-61")
    parser.add_argument("--dataset", default=str(modulo.DATASET_CSV))
    parser.add_argument("--n-analistas", type=int, default=modulo.N_ANALISTAS)
    parser.add_argument("--cv-duracion", type=float, default=modulo.CV_DURACION)
    parser.add_argument("--n-validacion", type=int, default=100)
    args = parser.parse_args()

    carpeta = modulo.OUTPUTS_DIR / "baselines_multisemilla"
    carpeta.mkdir(parents=True, exist_ok=True)
    baselines_detalle = evaluar_baselines(args, modulo)
    ag_detalle = pd.read_csv(
        modulo.OUTPUTS_DIR / "experimento" / "experimento_detalle.csv"
    )
    ag_detalle = ag_detalle[ag_detalle["solucion"].eq("GA")][
        ["escenario", "semilla", "solucion", *METRICAS]
    ]
    detalle = pd.concat([baselines_detalle, ag_detalle], ignore_index=True)
    detalle.to_csv(carpeta / "baselines_detalle.csv", index=False)
    resumen = resumir(detalle)
    resumen.to_csv(carpeta / "baselines_resumen.csv", index=False)
    print(resumen.to_string(index=False))


if __name__ == "__main__":
    main()
