"""Compara el AG con una búsqueda aleatoria de igual presupuesto.

La búsqueda aleatoria evalúa exactamente tam_poblacion * n_generaciones
soluciones independientes por escenario y semilla. Usa la misma instancia,
escenarios internos y validación fuera de muestra que el AG.

Ejemplo:
    python busqueda_aleatoria.py --semillas 42 --escenarios principal --n-generaciones 3 --tam-poblacion 5
"""

from __future__ import annotations

import argparse
import importlib
import random
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd


ESCENARIOS = {
    "principal": (100, "cmdb"),
    "estres": (120, "cmdb"),
    "saturacion": (500, "cmdb"),
}
VARIANTES = {
    "A": (False, False),
    "B": (True, False),
    "C": (False, True),
    "D": (True, True),
}


def cargar_modulo():
    return importlib.import_module("main")


def parsear_semillas(texto: str) -> List[int]:
    semillas: List[int] = []
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


def cromosoma_aleatorio(
    n_alertas: int,
    n_analistas: int,
    con_ajuste: bool,
    con_criticidad: bool,
    rng: random.Random,
    m,
) -> List[float]:
    asignacion = [rng.randint(1, n_analistas) for _ in range(n_alertas)]
    ajuste = (
        [rng.uniform(-m.AJUSTE_MAX, m.AJUSTE_MAX) for _ in range(n_alertas)]
        if con_ajuste
        else []
    )
    criticidad = (
        [rng.uniform(0.0, m.WMAX_CRITICIDAD) for _ in range(2)]
        if con_criticidad
        else []
    )
    return asignacion + ajuste + criticidad


def evaluar_fuera_de_muestra(m, inst, cromosoma, escenarios):
    idx_g = list(range(inst.n))
    idx_arr = np.arange(inst.n)
    activo_critico = inst.criticidad == 3
    filas = []
    for duracion in escenarios:
        inicio, fin, cargas = m._simular(cromosoma, idx_g, inst, duracion)
        metricas = m._metricas(idx_arr, inicio, fin, cargas, inst)
        evaluacion = m._objetivo(metricas, inst, 0.10)
        espera = np.asarray(inicio) - inst.llegada
        incumplimiento = espera > inst.sla_ef
        filas.append(
            {
                "fitness": evaluacion["fitness"],
                "sla_cumplimiento_pct": 100.0 * (1.0 - incumplimiento.mean()),
                "sla_cumplimiento_critica_pct": (
                    100.0 * (1.0 - incumplimiento[inst.es_critica].mean())
                    if inst.es_critica.any()
                    else np.nan
                ),
                "sla_cumplimiento_activo_critico_pct": (
                    100.0 * (1.0 - incumplimiento[activo_critico].mean())
                    if activo_critico.any()
                    else np.nan
                ),
                "espera_promedio_min": evaluacion["espera_promedio_min"],
                "espera_critica_promedio_min": evaluacion["espera_critica_promedio_min"],
                "espera_activo_critico_promedio_min": (
                    float(espera[activo_critico].mean()) if activo_critico.any() else np.nan
                ),
                "backlog_alertas": evaluacion["backlog_alertas"],
                "desbalance_carga": evaluacion["desbalance_carga"],
            }
        )
    return {clave: float(valor) for clave, valor in pd.DataFrame(filas).mean().items()}


def ejecutar(args, m) -> pd.DataFrame:
    con_ajuste, con_criticidad = VARIANTES[args.variante]
    m.N_ANALISTAS = args.n_analistas
    m.AJUSTE_ACTIVO = con_ajuste
    m.CRITICIDAD_EN_CROMOSOMA = con_criticidad
    dataset = Path(args.dataset)
    filas: List[Dict[str, object]] = []

    for nombre in args.escenarios.split(","):
        n_alertas, modo_activo = ESCENARIOS[nombre.strip()]
        for semilla in parsear_semillas(args.semillas):
            alertas = m.derivar_alertas_desde_dataset(
                n_alertas=n_alertas,
                seed=semilla,
                dataset_csv=dataset,
                modo_activo=modo_activo,
            )
            inst = m.Instancia(alertas, usar_activos=True)
            escenarios_ga = m.generar_escenarios_duracion(
                inst.dur_nominal, args.n_escenarios, args.cv_duracion, semilla
            )
            rng = random.Random(semilla)
            mejor = None
            mejor_eval = None
            presupuesto = args.tam_poblacion * args.n_generaciones
            for _ in range(presupuesto):
                cromosoma = cromosoma_aleatorio(
                    inst.n, args.n_analistas, con_ajuste, con_criticidad, rng, m
                )
                evaluacion = m.evaluar_cromosoma(
                    cromosoma,
                    list(range(inst.n)),
                    np.arange(inst.n),
                    inst,
                    escenarios_ga,
                )
                if mejor_eval is None or evaluacion["fitness"] > mejor_eval["fitness"]:
                    mejor = cromosoma
                    mejor_eval = evaluacion

            escenarios_validacion = m._muestrear_duraciones(
                inst.dur_nominal,
                args.n_validacion,
                args.cv_duracion,
                semilla + 7919,
            ).tolist()
            fila = {
                "variante": args.variante,
                "escenario": nombre.strip(),
                "semilla": semilla,
                "n_alertas": n_alertas,
                "n_analistas": args.n_analistas,
                "n_generaciones": args.n_generaciones,
                "tam_poblacion": args.tam_poblacion,
                "presupuesto_evaluaciones": presupuesto,
                "n_escenarios": args.n_escenarios,
                "cv_duracion": args.cv_duracion,
                "n_validacion": args.n_validacion,
                "solucion": "Busqueda-aleatoria",
            }
            fila.update(evaluar_fuera_de_muestra(m, inst, mejor, escenarios_validacion))
            filas.append(fila)
            print(f"{nombre.strip():<12} semilla {semilla:<5} | {fila['fitness']:.6f}")
    return pd.DataFrame(filas)


def main() -> None:
    m = cargar_modulo()
    parser = argparse.ArgumentParser(description="Búsqueda aleatoria con presupuesto igual al AG.")
    parser.add_argument("--semillas", default="42-61")
    parser.add_argument("--escenarios", default="principal,estres,saturacion")
    parser.add_argument("--dataset", default=str(m.DATASET_CSV))
    parser.add_argument("--n-analistas", type=int, default=m.N_ANALISTAS)
    parser.add_argument("--n-generaciones", type=int, default=m.N_GENERACIONES)
    parser.add_argument("--tam-poblacion", type=int, default=m.TAM_POBLACION)
    parser.add_argument("--n-escenarios", type=int, default=m.N_ESCENARIOS)
    parser.add_argument("--cv-duracion", type=float, default=m.CV_DURACION)
    parser.add_argument("--n-validacion", type=int, default=100)
    parser.add_argument("--variante", choices=tuple(VARIANTES), default="D")
    args = parser.parse_args()
    detalle = ejecutar(args, m)
    carpeta = m.OUTPUTS_DIR / "busqueda_aleatoria"
    carpeta.mkdir(parents=True, exist_ok=True)
    detalle.to_csv(carpeta / "busqueda_aleatoria_detalle.csv", index=False)
    detalle.groupby("escenario", as_index=False).agg(
        fitness_media=("fitness", "mean"),
        fitness_desvio=("fitness", "std"),
        espera_critica_media=("espera_critica_promedio_min", "mean"),
        backlog_medio=("backlog_alertas", "mean"),
        desbalance_medio=("desbalance_carga", "mean"),
    ).to_csv(carpeta / "busqueda_aleatoria_resumen.csv", index=False)


if __name__ == "__main__":
    main()
