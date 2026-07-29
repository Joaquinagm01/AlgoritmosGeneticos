"""Genera gráficos a partir de `outputs/instancia_enunciado_bench.csv`.
Genera:
- `value_comparison.png`: comparación de valores por método
- `time_comparison.png`: comparación de tiempos (media ± std) en µs
- `time_comparison_log.png`: misma información en escala log
- `combinaciones_comparison.png`: combinaciones/candidatos evaluados por método (escala log)
"""
from pathlib import Path
import csv
import matplotlib.pyplot as plt


def read_csv(path: Path):
    rows = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def main():
    base = Path(__file__).parent.parent
    csv_path = base / "outputs" / "instancia_enunciado_bench.csv"
    out_dir = base / "outputs" / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)

    data = read_csv(csv_path)
    methods = [r["metodo"] for r in data]
    valores = [int(r["valor"]) for r in data]

    # Valores (igual que antes)
    plt.figure(figsize=(6, 4))
    bars = plt.bar(methods, valores, color=["#2b8cbe", "#f16913"])
    plt.title("Comparación de valor total por método")
    plt.ylabel("Valor total ($)")
    for bar, val in zip(bars, valores):
        plt.text(bar.get_x() + bar.get_width() / 2, val + 1, str(val), ha="center")
    plt.tight_layout()
    plt.savefig(out_dir / "value_comparison.png", dpi=150)
    plt.close()

    # Tiempos: leer medias y std desde CSV (están en segundos). Convertir a µs para mostrar.
    mean_s = [float(r.get("mean_s", 0.0)) for r in data]
    std_s = [float(r.get("std_s", 0.0)) for r in data]
    mean_us = [m * 1e6 for m in mean_s]
    std_us = [s * 1e6 for s in std_s]

    # Barra con error (linear)
    plt.figure(figsize=(6, 4))
    x = range(len(methods))
    plt.bar(x, mean_us, yerr=std_us, color=["#4daf4a", "#984ea3"], capsize=6)
    plt.xticks(x, methods)
    plt.title("Comparación de tiempo de ejecución (media ± std, µs)")
    plt.ylabel("Tiempo (µs)")
    for xi, val in zip(x, mean_us):
        plt.text(xi, val + max(mean_us) * 0.02 if max(mean_us) > 0 else val + 1, f"{val:.2f}", ha='center')
    plt.tight_layout()
    plt.savefig(out_dir / "time_comparison.png", dpi=150)
    plt.close()

    # Barra con error (log scale)
    plt.figure(figsize=(6, 4))
    plt.bar(x, mean_us, yerr=std_us, color=["#4daf4a", "#984ea3"], capsize=6)
    plt.yscale("log")
    plt.xticks(x, methods)
    plt.title("Comparación de tiempo de ejecución (media ± std, µs, escala log)")
    plt.ylabel("Tiempo (µs), escala log")
    # Etiquetas encima (usar log-friendly placement)
    for xi, val in zip(x, mean_us):
        ypos = val * (1.2 if val > 0 else 1.0)
        plt.text(xi, ypos, f"{val:.2f}", ha='center')
    plt.tight_layout()
    plt.savefig(out_dir / "time_comparison_log.png", dpi=150)
    plt.close()

    # Combinaciones/candidatos evaluados por método (escala log: 2^n vs n)
    combinaciones = [int(r["combinaciones_evaluadas"]) for r in data]
    plt.figure(figsize=(6, 4))
    bars = plt.bar(methods, combinaciones, color=["#e41a1c", "#377eb8"])
    plt.yscale("log")
    plt.title("Combinaciones/candidatos evaluados por método (escala log)")
    plt.ylabel("Cantidad evaluada")
    for bar, val in zip(bars, combinaciones):
        plt.text(bar.get_x() + bar.get_width() / 2, val * 1.1, str(val), ha="center")
    plt.tight_layout()
    plt.savefig(out_dir / "combinaciones_comparison.png", dpi=150)
    plt.close()

    print("Plots generated in outputs/figures/")


if __name__ == '__main__':
    main()
