"""Compara pareadamente las variantes A/B/C/D usando los outputs existentes.

No ejecuta el algoritmo. Requiere que cada carpeta contenga
``experimento_detalle.csv`` con las mismas semillas y escenarios.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon


CARPETAS = {"A": "ablacion_A", "B": "ablacion_B", "C": "ablacion_C", "D": "experimento"}
METRICAS = {
    "fitness": True,
    "sla_cumplimiento_pct": True,
    "sla_cumplimiento_critica_pct": True,
    "sla_cumplimiento_activo_critico_pct": True,
    "espera_critica_promedio_min": False,
    "backlog_alertas": False,
    "desbalance_carga": False,
}
PARES = [("B", "A"), ("C", "A"), ("D", "A"), ("D", "B"), ("D", "C")]


def holm(p_values: np.ndarray) -> np.ndarray:
    orden = np.argsort(p_values)
    ajustados = np.empty(len(p_values), dtype=float)
    anterior = 0.0
    for rango, indice in enumerate(orden):
        anterior = max(anterior, min(1.0, (len(p_values) - rango) * p_values[indice]))
        ajustados[indice] = anterior
    return ajustados


def bootstrap_ic(diferencias: np.ndarray, rng: np.random.Generator) -> tuple[float, float]:
    muestras = rng.choice(diferencias, size=(5000, len(diferencias)), replace=True).mean(axis=1)
    return tuple(np.percentile(muestras, [2.5, 97.5]))


def cargar(base: Path, variante: str, semilla_col: str) -> pd.DataFrame:
    ruta = base / CARPETAS[variante] / "experimento_detalle.csv"
    if not ruta.exists():
        raise SystemExit(f"No existe el output de {variante}: {ruta}")
    df = pd.read_csv(ruta, encoding="utf-8-sig")
    requeridas = {"escenario", "solucion", semilla_col, *METRICAS}
    faltantes = requeridas.difference(df.columns)
    if faltantes:
        raise SystemExit(f"{ruta} no contiene: {', '.join(sorted(faltantes))}")
    return df[df["solucion"].eq("GA")].set_index(["escenario", semilla_col])


def comparar(datos: dict[str, pd.DataFrame], semilla_col: str) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    filas: list[dict[str, object]] = []
    escenarios = sorted(set(datos["A"].index.get_level_values("escenario")))

    for escenario in escenarios:
        for primero, segundo in PARES:
            izquierda = datos[primero].loc[escenario]
            derecha = datos[segundo].loc[escenario].reindex(izquierda.index)
            for metrica, mayor_es_mejor in METRICAS.items():
                valido = izquierda[metrica].notna() & derecha[metrica].notna()
                diferencia = (izquierda.loc[valido, metrica] - derecha.loc[valido, metrica]).to_numpy(float)
                if not mayor_es_mejor:
                    diferencia = -diferencia
                if diferencia.size == 0:
                    continue
                ic_inf, ic_sup = bootstrap_ic(diferencia, rng)
                try:
                    p = float(wilcoxon(diferencia, zero_method="wilcox").pvalue)
                except ValueError:
                    p = 1.0
                filas.append(
                    {
                        "tipo": "comparacion",
                        "escenario": escenario,
                        "comparacion": f"{primero} vs {segundo}",
                        "metrica": metrica,
                        "n_semillas": len(diferencia),
                        "mejora_media": float(diferencia.mean()),
                        "ic95_inf": float(ic_inf),
                        "ic95_sup": float(ic_sup),
                        "p_wilcoxon": p,
                        "gana": int((diferencia > 0).sum()),
                        "empata": int((diferencia == 0).sum()),
                        "pierde": int((diferencia < 0).sum()),
                    }
                )

    resultado = pd.DataFrame(filas)
    resultado["p_holm"] = np.nan
    for escenario, indices in resultado.groupby("escenario").groups.items():
        resultado.loc[indices, "p_holm"] = holm(resultado.loc[indices, "p_wilcoxon"].to_numpy())
    return resultado


def resumir_pesos(datos: dict[str, pd.DataFrame], semilla_col: str) -> pd.DataFrame:
    filas: list[dict[str, object]] = []
    for variante in ("C", "D"):
        if not {"w2_criticidad", "w3_criticidad"}.issubset(datos[variante].columns):
            continue
        tabla = datos[variante].reset_index()
        tabla["w3_menos_w2"] = tabla["w3_criticidad"] - tabla["w2_criticidad"]
        for _, fila in tabla.iterrows():
            filas.append(
                {
                    "tipo": "peso_semilla",
                    "escenario": fila["escenario"],
                    "comparacion": variante,
                    semilla_col: fila[semilla_col],
                    "w2_criticidad": fila["w2_criticidad"],
                    "w3_criticidad": fila["w3_criticidad"],
                    "w3_menos_w2": fila["w3_menos_w2"],
                    "w3_menor_que_w2": int(fila["w3_menos_w2"] < 0),
                    "w2_pegado_techo": int(fila["w2_criticidad"] >= 0.98),
                    "w3_pegado_techo": int(fila["w3_criticidad"] >= 0.98),
                }
            )
        for escenario, grupo in tabla.groupby("escenario", sort=True):
            delta = grupo["w3_menos_w2"]
            filas.extend(
                [
                    {
                        "tipo": "pesos",
                        "escenario": escenario,
                        "comparacion": variante,
                        "metrica": "w2_criticidad",
                        "n_semillas": len(grupo),
                        "media": grupo["w2_criticidad"].mean(),
                        "desvio": grupo["w2_criticidad"].std(ddof=1),
                        "min": grupo["w2_criticidad"].min(),
                        "max": grupo["w2_criticidad"].max(),
                        "pegado_techo_>=0.98": int((grupo["w2_criticidad"] >= 0.98).sum()),
                    },
                    {
                        "tipo": "pesos",
                        "escenario": escenario,
                        "comparacion": variante,
                        "metrica": "w3_criticidad",
                        "n_semillas": len(grupo),
                        "media": grupo["w3_criticidad"].mean(),
                        "desvio": grupo["w3_criticidad"].std(ddof=1),
                        "min": grupo["w3_criticidad"].min(),
                        "max": grupo["w3_criticidad"].max(),
                        "pegado_techo_>=0.98": int((grupo["w3_criticidad"] >= 0.98).sum()),
                    },
                    {
                        "tipo": "pesos",
                        "escenario": escenario,
                        "comparacion": variante,
                        "metrica": "w3_menos_w2",
                        "n_semillas": len(grupo),
                        "media": delta.mean(),
                        "desvio": delta.std(ddof=1),
                        "min": delta.min(),
                        "max": delta.max(),
                        "w3_menor_que_w2": int((delta < 0).sum()),
                    },
                ]
            )
    return pd.DataFrame(filas)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="TPI/outputs")
    parser.add_argument("--semilla-col", default="semilla")
    args = parser.parse_args()

    base = Path(args.base)
    datos = {variante: cargar(base, variante, args.semilla_col) for variante in CARPETAS}
    comparaciones = comparar(datos, args.semilla_col)
    pesos = resumir_pesos(datos, args.semilla_col)
    salida = base / "comparacion_ablacion.csv"
    pd.concat([comparaciones, pesos], ignore_index=True, sort=False).to_csv(salida, index=False)
    pd.set_option("display.max_columns", None)
    print(comparaciones.round(4).to_string(index=False))
    print("\nResumen de pesos globales:")
    print(pesos.round(4).to_string(index=False))
    print(f"\nArchivo guardado: {salida.resolve()}")


if __name__ == "__main__":
    main()
