"""Motor de cálculo del problema de la mochila (TP2).

Contiene la representación de los objetos y las dos estrategias de
resolución (exhaustiva y greedy), además de las funciones que arman el
reporte estructurado que consume `main.py` (menú interactivo y modo
archivo) y que también usa `run_bench.py` para el benchmark.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Dict, List, Sequence, Tuple


@dataclass(frozen=True)
class Item:
    nombre: str
    peso: int
    valor: int

    @property
    def ratio(self) -> float:
        return self.valor / self.peso


# (seleccion, peso_total, valor_total, combinaciones_evaluadas)
ResultadoMetodo = Tuple[List[Item], int, int, int]


def valor_total(items: Sequence[Item]) -> int:
    return sum(item.valor for item in items)


def peso_total(items: Sequence[Item]) -> int:
    return sum(item.peso for item in items)


def resolver_exhaustivo(items: Sequence[Item], capacidad: int) -> ResultadoMetodo:
    """Evalúa cada subconjunto posible (2^n) y devuelve el de mayor valor.

    Entre subconjuntos con el mismo valor, se queda con el de menor peso
    (menor volumen/espacio desperdiciado).
    """
    mejor_subconjunto: List[Item] = []
    mejor_valor = 0
    mejor_peso = 0
    combinaciones_evaluadas = 0

    for cantidad in range(len(items) + 1):
        for subconjunto in combinations(items, cantidad):
            combinaciones_evaluadas += 1
            peso = peso_total(subconjunto)
            if peso > capacidad:
                continue

            valor = valor_total(subconjunto)
            if valor > mejor_valor or (valor == mejor_valor and peso < mejor_peso):
                mejor_subconjunto = list(subconjunto)
                mejor_valor = valor
                mejor_peso = peso

    return mejor_subconjunto, mejor_peso, mejor_valor, combinaciones_evaluadas


def resolver_greedy(items: Sequence[Item], capacidad: int) -> ResultadoMetodo:
    """Ordena los items por relación valor/peso descendente y los carga
    mientras haya capacidad disponible. Cada item candidato cuenta como una
    evaluación (no evalúa combinaciones, sino candidatos individuales)."""
    seleccionados: List[Item] = []
    peso_acumulado = 0
    combinaciones_evaluadas = 0

    for item in sorted(items, key=lambda item: item.ratio, reverse=True):
        combinaciones_evaluadas += 1
        if peso_acumulado + item.peso <= capacidad:
            seleccionados.append(item)
            peso_acumulado += item.peso

    return seleccionados, peso_acumulado, valor_total(seleccionados), combinaciones_evaluadas


def medir(func, items: Sequence[Item], capacidad: int):
    """Ejecuta `func` y devuelve el resultado junto con el tiempo exacto (s)."""
    inicio = time.perf_counter()
    resultado = func(items, capacidad)
    fin = time.perf_counter()
    return resultado, fin - inicio


def _reporte_metodo(nombre: str, func, items: Sequence[Item], capacidad: int, unidad: str) -> Dict:
    resultado, tiempo_s = medir(func, items, capacidad)
    seleccion, peso, valor, combinaciones = resultado
    return {
        "metodo": nombre,
        "seleccion": [item.nombre for item in seleccion],
        "peso": peso,
        "capacidad": capacidad,
        "unidad": unidad,
        "espacio_libre": capacidad - peso,
        "porcentaje_ocupado": (peso / capacidad) if capacidad else 0.0,
        "respeta_capacidad": peso <= capacidad,
        "valor": valor,
        "combinaciones_evaluadas": combinaciones,
        "tiempo_s": tiempo_s,
    }


def _auditoria(exhaustivo: Dict, greedy: Dict) -> Dict:
    texto_tiempo = None
    if greedy["tiempo_s"] > 0:
        texto_tiempo = (
            f"El exhaustivo tardó {exhaustivo['tiempo_s'] / greedy['tiempo_s']:.1f}x más que el greedy "
            f"({exhaustivo['tiempo_s']:.9f} s vs. {greedy['tiempo_s']:.9f} s)."
        )

    texto_combinaciones = None
    if greedy["combinaciones_evaluadas"] > 0:
        texto_combinaciones = (
            f"El exhaustivo evaluó {exhaustivo['combinaciones_evaluadas'] / greedy['combinaciones_evaluadas']:.1f}x "
            f"más candidatos que el greedy ({exhaustivo['combinaciones_evaluadas']} vs. "
            f"{greedy['combinaciones_evaluadas']})."
        )

    if greedy["valor"] == exhaustivo["valor"] and greedy["peso"] == exhaustivo["peso"]:
        conclusion = (
            "El greedy coincidió exactamente con la solución óptima (mismo valor y mismo peso). "
            "No es garantía general: en esta instancia particular la heurística no perdió valor."
        )
    elif greedy["valor"] == exhaustivo["valor"]:
        conclusion = (
            "El greedy alcanzó el mismo valor óptimo que el exhaustivo, aunque con una combinación "
            "de elementos distinta."
        )
    else:
        diferencia = exhaustivo["valor"] - greedy["valor"]
        conclusion = (
            f"El greedy NO alcanzó el óptimo: obtuvo ${greedy['valor']} contra ${exhaustivo['valor']} del "
            f"exhaustivo (diferencia de ${diferencia}). Es una solución factible, pero no la óptima absoluta."
        )

    return {"tiempo": texto_tiempo, "combinaciones": texto_combinaciones, "conclusion": conclusion}


def calcular_reporte(items: Sequence[Item], capacidad: int, unidad: str = "u.") -> Dict:
    """Corre ambos métodos sobre la misma instancia y arma un reporte único
    (espacio de búsqueda + resultado de cada método + auditoría crítica)
    que consumen por igual la consola y la interfaz web."""
    exhaustivo = _reporte_metodo("exhaustivo", resolver_exhaustivo, items, capacidad, unidad)
    greedy = _reporte_metodo("greedy", resolver_greedy, items, capacidad, unidad)
    return {
        "capacidad": capacidad,
        "unidad": unidad,
        "items": [
            {"id": idx, "nombre": item.nombre, "peso": item.peso, "valor": item.valor, "ratio": round(item.ratio, 4)}
            for idx, item in enumerate(items, start=1)
        ],
        "exhaustivo": exhaustivo,
        "greedy": greedy,
        "auditoria": _auditoria(exhaustivo, greedy),
    }


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


def instancia_ejercicios_1_y_2() -> Tuple[List[Item], int, str]:
    ruta = Path(__file__).resolve().parent.parent / "Enunciado" / "instancia_enunciado.json"
    items, capacidad = cargar_instancia_desde_json(ruta)
    return items, capacidad, "cm3"


def instancia_ejercicio_3() -> Tuple[List[Item], int, str]:
    items = [
        Item("Elemento 1", peso=1800, valor=72),
        Item("Elemento 2", peso=600, valor=36),
        Item("Elemento 3", peso=1200, valor=60),
    ]
    return items, 3000, "grs."
