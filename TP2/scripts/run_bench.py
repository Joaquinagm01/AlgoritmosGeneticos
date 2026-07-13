"""Ejecutor de benchmarks para TP2.

Carga una instancia JSON, ejecuta `resolver_exhaustivo` y `resolver_greedy`, mide tiempos
y guarda los resultados en `outputs/` en formato TXT y CSV.
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path
from typing import List

from TP2.scripts.main import Item, resolver_exhaustivo, resolver_greedy


def cargar_instancia(path: Path):
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    capacidad = int(data["capacidad"])
    items: List[Item] = [
        Item(nombre=str(it["nombre"]), peso=int(it["peso"]), valor=int(it["valor"]))
        for it in data["items"]
    ]
    return items, capacidad


def nombres(items: List[Item]) -> str:
    return ", ".join(it.nombre for it in items) if items else "ninguno"


def main():
    parser = argparse.ArgumentParser(description="Ejecutar benchmark (con repeticiones) sobre la instancia del enunciado.")
    parser.add_argument("--reps", type=int, default=1, help="Número de repeticiones por método (default=1)")
    args = parser.parse_args()

    base = Path(__file__).parent
    instancia = base / "instancia_enunciado.json"
    out_dir = base / "outputs"
    out_dir.mkdir(exist_ok=True)

    items, capacidad = cargar_instancia(instancia)

    results = []

    # Parámetros de medición: asegurar tiempo mínimo acumulado por medición para reducir ruido
    MIN_MEASURE_TIME = 0.02  # segundos por medición (20 ms)

    def measure_with_scaling(func, *fargs):
        """Mide `func(*fargs)` repitiéndolo internamente hasta alcanzar MIN_MEASURE_TIME.
        Devuelve (time_per_call, last_result, iterations, total_time).
        """
        iterations = 1
        last_result = None
        while True:
            t0 = time.perf_counter()
            for _ in range(iterations):
                last_result = func(*fargs)
            total = time.perf_counter() - t0
            if total >= MIN_MEASURE_TIME:
                return total / iterations, last_result, iterations, total
            iterations *= 2

    # Ejecutar y medir repetidamente cada método (con auto-escalado interno)
    for nombre_metodo, funcion in ("exhaustivo", resolver_exhaustivo), ("greedy", resolver_greedy):
        tiempos = []
        sol_final = None
        peso_final = None
        valor_final = None
        iters_used = []

        for i in range(args.reps):
            per_call, last_res, iterations, total = measure_with_scaling(funcion, items, capacidad)
            # per_call en segundos
            tiempos.append(per_call)
            iters_used.append(iterations)

            # last_res es la última tupla (sol, peso, valor)
            sol, peso, valor = last_res
            sol_final = sol
            peso_final = peso
            valor_final = valor

        mean_t = statistics.mean(tiempos)
        median_t = statistics.median(tiempos)
        stdev_t = statistics.pstdev(tiempos) if args.reps > 1 else 0.0
        mean_iters = int(statistics.mean(iters_used))

        results.append(
            {
                "metodo": nombre_metodo,
                "seleccion": nombres(sol_final),
                "peso": peso_final,
                "valor": valor_final,
                "reps": args.reps,
                "mean_s": mean_t,
                "median_s": median_t,
                "std_s": stdev_t,
                "mean_iters": mean_iters,
            }
        )

    # Guardar TXT con resumen
    txt = []
    txt.append(f"Instancia: {instancia.name} (capacidad={capacidad})")
    txt.append(f"Items: {nombres(items)}")
    txt.append("")
    for r in results:
        txt.append(f"{r['metodo'].capitalize()}:")
        txt.append(f"  Selección: {r['seleccion']}")
        txt.append(f"  Peso: {r['peso']} | Valor: ${r['valor']}")
        txt.append(f"  Repeticiones: {r['reps']} | Iteraciones internas (media): {r.get('mean_iters',1)}")
        txt.append(f"  Tiempo medio por llamada: {r['mean_s']:.9f} s | mediana: {r['median_s']:.9f} s | std: {r['std_s']:.9f} s")
        txt.append("")

    (out_dir / "instancia_enunciado_bench.txt").write_text("\n".join(txt), encoding="utf-8")

    # Guardar CSV resumen (campos: metodo,seleccion,peso,valor,reps,mean_s,median_s,std_s,mean_iters)
    csv_lines = ["metodo,seleccion,peso,valor,reps,mean_s,median_s,std_s,mean_iters"]
    for r in results:
        csv_lines.append(
            f"{r['metodo']},\"{r['seleccion']}\",{r['peso']},{r['valor']},{r['reps']},{r['mean_s']:.9f},{r['median_s']:.9f},{r['std_s']:.9f},{r.get('mean_iters',1)}"
        )
    (out_dir / "instancia_enunciado_bench.csv").write_text("\n".join(csv_lines), encoding="utf-8")

    print(f"Bench completed ({args.reps} reps). Results saved to outputs/")


if __name__ == "__main__":
    main()
