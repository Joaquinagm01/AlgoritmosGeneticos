"""Comparación multi-semilla y pareada entre AG y Round-Robin.

Los escenarios se evalúan con las mismas alertas y los mismos escenarios de
duración para ambas soluciones. El AG se optimiza con escenarios internos y se
evalúa fuera de muestra con escenarios nuevos.

Uso:
    python experimento.py
    python experimento.py --semillas 42-61 --escenarios principal,estres,saturacion
"""

from __future__ import annotations

import argparse
import importlib
import time
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd


METRICAS: Dict[str, tuple[str, bool]] = {
    "fitness": ("Fitness", True),
    "sla_cumplimiento_pct": ("SLA cumplido, todas (%)", True),
    "sla_cumplimiento_critica_pct": ("SLA cumplido, alertas críticas (%)", True),
    "sla_cumplimiento_activo_critico_pct": ("SLA cumplido, activos críticos (%)", True),
    "espera_promedio_min": ("Espera promedio (min)", False),
    "espera_critica_promedio_min": ("Espera alertas críticas (min)", False),
    "espera_activo_critico_promedio_min": ("Espera activos críticos (min)", False),
    "backlog_alertas": ("Backlog (alertas)", False),
    "desbalance_carga": ("Desbalance de carga", False),
}

ESCENARIOS = {
    "principal": (100, "cmdb"),
    "estres": (120, "cmdb"),
    "saturacion": (500, "cmdb"),
    "principal_puerto": (100, "puerto"),
}
ESCENARIOS_DEFECTO = ("principal", "estres", "saturacion")
VARIANTES = {
    "A": (False, False),
    "B": (True, False),
    "C": (False, True),
    "D": (True, True),
}


def cargar_modulo():
    """Importa el motor del algoritmo desde main.py."""
    try:
        return importlib.import_module("main")
    except ModuleNotFoundError as error:
        raise SystemExit("No se encontró main.py junto a experimento.py") from error


def parsear_semillas(texto: str) -> List[int]:
    """Acepta rangos como 42-61 y listas como 42,43,50."""
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


def evaluar_fuera_de_muestra(m, inst, cromosoma, escenarios, peso_tiempo=0.10):
    """Promedia las métricas sobre escenarios nuevos compartidos por ambos métodos."""
    idx_g = list(range(inst.n))
    idx_arr = np.arange(inst.n)
    activo_critico = inst.criticidad == 3
    filas = []

    for duracion in escenarios:
        inicio, fin, cargas = m._simular(cromosoma, idx_g, inst, duracion)
        metricas = m._metricas(idx_arr, inicio, fin, cargas, inst)
        evaluacion = m._objetivo(metricas, inst, peso_tiempo)
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
    """Ejecuta cada escenario y semilla con comparación pareada AG/Round-Robin."""
    m.N_ANALISTAS = args.n_analistas
    m.AJUSTE_ACTIVO, m.CRITICIDAD_EN_CROMOSOMA = VARIANTES[args.variante]
    dataset = Path(args.dataset)
    if not dataset.exists():
        raise SystemExit(f"No se encontró el dataset: {dataset}")

    nombres = [nombre.strip() for nombre in args.escenarios.split(",") if nombre.strip()]
    if args.incluir_puerto and "principal_puerto" not in nombres:
        nombres.append("principal_puerto")
    desconocidos = [nombre for nombre in nombres if nombre not in ESCENARIOS]
    if desconocidos:
        opciones = ", ".join(ESCENARIOS)
        raise SystemExit(f"Escenario desconocido: {desconocidos[0]}. Opciones: {opciones}")

    semillas = parsear_semillas(args.semillas)
    carpeta = m.OUTPUTS_DIR / ("experimento" if args.variante == "D" else f"ablacion_{args.variante}")
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta_detalle = carpeta / "experimento_detalle.csv"
    filas: List[Dict[str, object]] = []
    total = len(nombres) * len(semillas)
    inicio_total = time.time()
    hecho = 0

    for nombre in nombres:
        n_alertas, modo_activo = ESCENARIOS[nombre]
        for semilla in semillas:
            seed_datos = semilla if args.modo_muestra == "variable" else args.seed_datos
            alertas = m.derivar_alertas_desde_dataset(
                n_alertas=n_alertas,
                seed=seed_datos,
                dataset_csv=dataset,
                modo_activo=modo_activo,
            )
            inst = m.Instancia(alertas, usar_activos=True)
            escenarios_ga = m.generar_escenarios_duracion(
                inst.dur_nominal, args.n_escenarios, args.cv_duracion, semilla
            )
            _, resumen = m.evolucionar(
                alertas,
                n_generaciones=args.n_generaciones,
                tam_poblacion=args.tam_poblacion,
                p_crossover=args.p_crossover,
                p_mutacion=args.p_mutacion,
                seed=semilla,
                metodo_seleccion="ranking",
                inst=inst,
                escenarios=escenarios_ga,
            )

            escenarios_validacion = m._muestrear_duraciones(
                inst.dur_nominal,
                args.n_validacion,
                args.cv_duracion,
                semilla + 7919,
            ).tolist()
            round_robin = [(indice % args.n_analistas) + 1 for indice in range(inst.n)]
            contexto = {
                "variante": args.variante,
                "escenario": nombre,
                "semilla": semilla,
                "seed_datos": seed_datos,
                "n_alertas": n_alertas,
                "n_analistas": args.n_analistas,
                "n_generaciones": args.n_generaciones,
                "tam_poblacion": args.tam_poblacion,
                "p_crossover": args.p_crossover,
                "p_mutacion": args.p_mutacion,
                "n_escenarios": args.n_escenarios,
                "cv_duracion": args.cv_duracion,
                "n_validacion": args.n_validacion,
                "criticidad_activo": modo_activo,
                "utilizacion_pct": 100.0 * float(inst.dur_nominal.sum())
                / (args.n_analistas * m.HORIZONTE_MINUTOS),
                "pct_activos_criticos": 100.0 * float((inst.criticidad == 3).mean()),
                "pct_alertas_criticas": 100.0 * float(inst.es_critica.mean()),
                "cromosoma_con_criticidad": bool(resumen.get("cromosoma_con_criticidad", False)),
                "w2_criticidad": float(resumen.get("w2_criticidad", 1.0)),
                "w3_criticidad": float(resumen.get("w3_criticidad", 1.0)),
                "n_bloques_cromosoma": int(resumen.get("n_bloques_cromosoma", 1)),
            }

            for solucion, cromosoma in (
                ("Round-Robin", round_robin),
                ("GA", resumen["mejor_cromosoma"]),
            ):
                fila = dict(contexto)
                fila["solucion"] = solucion
                fila["tiempo_ga_seg"] = resumen["tiempo_ejecucion_seg"] if solucion == "GA" else 0.0
                fila.update(evaluar_fuera_de_muestra(m, inst, cromosoma, escenarios_validacion))
                filas.append(fila)

            hecho += 1
            transcurrido = time.time() - inicio_total
            restante = transcurrido / hecho * (total - hecho)
            print(
                f"[{hecho}/{total}] {nombre:<12} semilla {semilla:<5} | "
                f"transcurrido {transcurrido / 60:5.1f} min | restante aprox. {restante / 60:5.1f} min"
            )
            pd.DataFrame(filas).to_csv(ruta_detalle, index=False)

    return pd.DataFrame(filas)


def veredicto(diferencia, inferior, superior, mas_es_mejor):
    if inferior <= 0.0 <= superior:
        return "sin diferencia clara"
    mejora = diferencia > 0 if mas_es_mejor else diferencia < 0
    return "GA mejor" if mejora else "GA peor"


def resumir(detalle: pd.DataFrame, n_bootstrap: int = 5000) -> pd.DataFrame:
    """Calcula medias, desvíos, IC bootstrap y porcentaje de mejoras por semilla."""
    rng = np.random.default_rng(12345)
    filas = []
    for escenario, grupo in detalle.groupby("escenario", sort=False):
        rr = grupo[grupo["solucion"] == "Round-Robin"].set_index("semilla")
        ga = grupo[grupo["solucion"] == "GA"].set_index("semilla")
        comunes = rr.index.intersection(ga.index)
        for columna, (etiqueta, mas_es_mejor) in METRICAS.items():
            a = ga.loc[comunes, columna].astype(float)
            b = rr.loc[comunes, columna].astype(float)
            validos = a.notna() & b.notna()
            a, b = a[validos], b[validos]
            fila = {
                "escenario": escenario,
                "metrica": columna,
                "etiqueta": etiqueta,
                "n_semillas": int(len(a)),
            }
            if len(a) == 0:
                filas.append(fila)
                continue

            diferencias = (a - b).to_numpy()
            if len(diferencias) > 1:
                muestras = diferencias[
                    rng.integers(0, len(diferencias), size=(n_bootstrap, len(diferencias)))
                ].mean(axis=1)
                inferior, superior = np.percentile(muestras, [2.5, 97.5])
            else:
                inferior = superior = float(diferencias[0])

            mejor = (diferencias > 0) if mas_es_mejor else (diferencias < 0)
            fila.update(
                {
                    "RR_media": float(b.mean()),
                    "RR_desv": float(b.std(ddof=1)) if len(b) > 1 else 0.0,
                    "GA_media": float(a.mean()),
                    "GA_desv": float(a.std(ddof=1)) if len(a) > 1 else 0.0,
                    "dif_media_GA_menos_RR": float(diferencias.mean()),
                    "IC95_inf": float(inferior),
                    "IC95_sup": float(superior),
                    "GA_mejor_en_pct_semillas": float(100.0 * mejor.mean()),
                    "veredicto": veredicto(
                        float(diferencias.mean()), float(inferior), float(superior), mas_es_mejor
                    ),
                }
            )
            filas.append(fila)
    return pd.DataFrame(filas)


def imprimir(detalle: pd.DataFrame, resumen: pd.DataFrame) -> None:
    for escenario, grupo in resumen.groupby("escenario", sort=False):
        contexto = detalle[(detalle["escenario"] == escenario) & (detalle["solucion"] == "GA")]
        print("\n" + "=" * 132)
        print(
            f"ESCENARIO {escenario.upper()}: {int(contexto['n_alertas'].iloc[0])} alertas, "
            f"criticidad '{contexto['criticidad_activo'].iloc[0]}', {len(contexto)} semillas | "
            f"demanda/capacidad {contexto['utilizacion_pct'].mean():.0f} % | "
            f"activos críticos {contexto['pct_activos_criticos'].mean():.1f} %"
        )
        print("=" * 132)
        tabla = pd.DataFrame(
            {
                "Métrica": grupo["etiqueta"],
                "Round-Robin (media ± desv)": [
                    f"{media:.3f} ± {desv:.3f}"
                    for media, desv in zip(grupo["RR_media"], grupo["RR_desv"])
                ],
                "GA (media ± desv)": [
                    f"{media:.3f} ± {desv:.3f}"
                    for media, desv in zip(grupo["GA_media"], grupo["GA_desv"])
                ],
                "Dif. GA-RR [IC 95 %]": [
                    f"{dif:+.3f} [{inferior:+.3f}, {superior:+.3f}]"
                    for dif, inferior, superior in zip(
                        grupo["dif_media_GA_menos_RR"],
                        grupo["IC95_inf"],
                        grupo["IC95_sup"],
                    )
                ],
                "GA mejor en": [
                    f"{porcentaje:.0f} % semillas"
                    for porcentaje in grupo["GA_mejor_en_pct_semillas"]
                ],
                "Veredicto": grupo["veredicto"].fillna("sin datos"),
            }
        )
        print(tabla.to_string(index=False))


def main() -> None:
    m = cargar_modulo()
    parser = argparse.ArgumentParser(description="Experimento multi-semilla AG vs Round-Robin.")
    parser.add_argument("--semillas", default="42-61", help="Rango o lista de semillas")
    parser.add_argument(
        "--escenarios",
        default=",".join(ESCENARIOS_DEFECTO),
        help=f"Escenarios separados por coma: {', '.join(ESCENARIOS)}",
    )
    parser.add_argument("--incluir-puerto", action="store_true")
    parser.add_argument("--modo-muestra", choices=("variable", "fija"), default="variable")
    parser.add_argument("--seed-datos", type=int, default=42)
    parser.add_argument("--dataset", default=str(m.DATASET_CSV))
    parser.add_argument("--n-analistas", type=int, default=m.N_ANALISTAS)
    parser.add_argument("--n-generaciones", type=int, default=m.N_GENERACIONES)
    parser.add_argument("--tam-poblacion", type=int, default=m.TAM_POBLACION)
    parser.add_argument("--p-crossover", type=float, default=m.P_CROSSOVER)
    parser.add_argument("--p-mutacion", type=float, default=m.P_MUTACION)
    parser.add_argument("--n-escenarios", type=int, default=m.N_ESCENARIOS)
    parser.add_argument("--cv-duracion", type=float, default=m.CV_DURACION)
    parser.add_argument("--n-validacion", type=int, default=100)
    parser.add_argument(
        "--variante",
        choices=tuple(VARIANTES),
        default="D",
        help="A=asignacion, B=asignacion+d_i, C=asignacion+(w2,w3), D=todos los bloques",
    )
    args = parser.parse_args()

    detalle = ejecutar(args, m)
    resumen = resumir(detalle)
    carpeta = m.OUTPUTS_DIR / ("experimento" if args.variante == "D" else f"ablacion_{args.variante}")
    detalle.to_csv(carpeta / "experimento_detalle.csv", index=False)
    resumen.to_csv(carpeta / "experimento_resumen.csv", index=False)
    imprimir(detalle, resumen)
    print(f"\nArchivos guardados en: {carpeta}")


if __name__ == "__main__":
    main()
