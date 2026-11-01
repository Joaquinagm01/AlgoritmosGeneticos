"""Compatibilidad para el experimento multi-semilla.

El protocolo actual vive en ``experimento.py``. Este archivo conserva el
comando histórico y lo redirige al escenario principal de 100 alertas.
"""

from __future__ import annotations

import argparse
from types import SimpleNamespace

import experimento


def ejecutar_experimentos(n_corridas: int = 20, semilla_inicial: int = 42):
    """Ejecuta el escenario principal con un rango consecutivo de semillas."""
    modulo = experimento.cargar_modulo()
    args = SimpleNamespace(
        n_analistas=modulo.N_ANALISTAS,
        dataset=str(modulo.DATASET_CSV),
        escenarios="principal",
        incluir_puerto=False,
        semillas=f"{semilla_inicial}-{semilla_inicial + n_corridas - 1}",
        modo_muestra="variable",
        seed_datos=42,
        n_escenarios=modulo.N_ESCENARIOS,
        cv_duracion=modulo.CV_DURACION,
        n_validacion=100,
        n_generaciones=modulo.N_GENERACIONES,
        tam_poblacion=modulo.TAM_POBLACION,
    )
    detalle = experimento.ejecutar(args, modulo)
    resumen = experimento.resumir(detalle)
    carpeta = modulo.OUTPUTS_DIR / "experimento"
    resumen.to_csv(carpeta / "experimento_resumen.csv", index=False)
    experimento.imprimir(detalle, resumen)
    return detalle


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compatibilidad para experimento.py.")
    parser.add_argument("--corridas", type=int, default=20)
    parser.add_argument("--seed-inicial", type=int, default=42)
    args = parser.parse_args()
    ejecutar_experimentos(args.corridas, args.seed_inicial)
