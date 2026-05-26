"""Trabajo Práctico 2 - Problema de la mochila.

Este script implementa dos estrategias:
- búsqueda exhaustiva
- algoritmo greedy por relación valor/peso

Además resuelve el caso de ejemplo del enunciado con 3 elementos y una
capacidad de 3000 grs.

Para el punto 1 y 2 del enunciado completo, basta con reemplazar la lista de
elementos de ejemplo por la lista real de la consigna.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import List, Sequence, Tuple


@dataclass(frozen=True)
class Item:
    nombre: str
    peso: int
    valor: int


def valor_total(items: Sequence[Item]) -> int:
    return sum(item.valor for item in items)


def peso_total(items: Sequence[Item]) -> int:
    return sum(item.peso for item in items)


def resolver_exhaustivo(items: Sequence[Item], capacidad: int) -> Tuple[List[Item], int, int]:
    """Evalúa todos los subconjuntos y devuelve la mejor combinación factible."""
    mejor_subconjunto: List[Item] = []
    mejor_valor = 0
    mejor_peso = 0

    for cantidad in range(len(items) + 1):
        for subconjunto in combinations(items, cantidad):
            peso = peso_total(subconjunto)
            if peso > capacidad:
                continue

            valor = valor_total(subconjunto)
            if valor > mejor_valor or (valor == mejor_valor and peso < mejor_peso):
                mejor_subconjunto = list(subconjunto)
                mejor_valor = valor
                mejor_peso = peso

    return mejor_subconjunto, mejor_peso, mejor_valor


def resolver_greedy(items: Sequence[Item], capacidad: int) -> Tuple[List[Item], int, int]:
    """Selecciona items por mayor relación valor/peso hasta completar la capacidad."""
    seleccionados: List[Item] = []
    peso_acumulado = 0

    for item in sorted(items, key=lambda item: (item.valor / item.peso), reverse=True):
        if peso_acumulado + item.peso <= capacidad:
            seleccionados.append(item)
            peso_acumulado += item.peso

    return seleccionados, peso_acumulado, valor_total(seleccionados)


def formatear_solucion(items: Sequence[Item], peso: int, valor: int) -> str:
    nombres = ", ".join(item.nombre for item in items) if items else "ninguno"
    return f"Items: {nombres}\nPeso total: {peso} grs.\nValor total: ${valor}"


def imprimir_comparacion(items: Sequence[Item], capacidad: int, titulo: str) -> None:
    print("=" * 72)
    print(titulo)
    print(f"Capacidad de la mochila: {capacidad} grs.")
    print("Items disponibles:")
    for item in items:
        ratio = item.valor / item.peso
        print(f"- {item.nombre}: peso={item.peso} grs., valor=${item.valor}, valor/peso={ratio:.4f}")

    solucion_exhaustiva, peso_exhaustivo, valor_exhaustivo = resolver_exhaustivo(items, capacidad)
    solucion_greedy, peso_greedy, valor_greedy = resolver_greedy(items, capacidad)

    print("\nSolución exhaustiva:")
    print(formatear_solucion(solucion_exhaustiva, peso_exhaustivo, valor_exhaustivo))

    print("\nSolución greedy:")
    print(formatear_solucion(solucion_greedy, peso_greedy, valor_greedy))

    if valor_greedy == valor_exhaustivo and peso_greedy == peso_exhaustivo:
        comentario = "Ambos métodos coinciden en la solución óptima para este conjunto."
    elif valor_greedy == valor_exhaustivo:
        comentario = (
            "El greedy alcanzó el mismo valor óptimo que el exhaustivo, "
            "aunque puede elegir una combinación distinta."
        )
    else:
        comentario = (
            "El greedy no garantiza optimalidad: en este caso obtuvo un valor menor "
            "que la búsqueda exhaustiva."
        )

    print("\nConclusión:")
    print(comentario)


def resolver_caso_ejercicio_3() -> None:
    items = [
        Item("Elemento 1", peso=1800, valor=72),
        Item("Elemento 2", peso=600, valor=36),
        Item("Elemento 3", peso=1200, valor=60),
    ]
    capacidad = 3000
    imprimir_comparacion(items, capacidad, "Ejercicio 3 - Mochila por peso")

    print("\nRespuesta esperada para el análisis del punto 3:")
    print("- Exhaustivo: el mejor subconjunto es {Elemento 1, Elemento 3} con valor $132 y peso 3000 grs.")
    print("- Greedy por valor/peso: elige {Elemento 2, Elemento 3} con valor $96 y peso 1800 grs.")
    print("- Conclusión: el greedy es más simple y rápido, pero no siempre encuentra el óptimo global.")


def cargar_instancia_desde_json(ruta: Path) -> Tuple[List[Item], int]:
    with ruta.open("r", encoding="utf-8") as archivo:
        data = json.load(archivo)

    capacidad = int(data["capacidad"])
    items = [
        Item(
            nombre=str(item["nombre"]),
            peso=int(item["peso"]),
            valor=int(item["valor"]),
        )
        for item in data["items"]
    ]
    return items, capacidad


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolver el problema de la mochila.")
    parser.add_argument(
        "archivo",
        nargs="?",
        help="Ruta a un JSON con la instancia. Si no se indica, se usa el caso del punto 3.",
    )
    args = parser.parse_args()

    if args.archivo:
        ruta = Path(args.archivo)
        items, capacidad = cargar_instancia_desde_json(ruta)
        imprimir_comparacion(items, capacidad, f"Mochila - instancia desde {ruta.name}")
        return

    resolver_caso_ejercicio_3()


if __name__ == "__main__":
    main()