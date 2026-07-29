"""Trabajo Práctico 2 - Problema de la mochila. Punto de entrada único.

Sin argumentos, `main.py` levanta un menú interactivo por consola:
- Opción 1: resuelve los puntos 1 y 2 del enunciado (lista completa, mochila
  de 4200 cm3).
- Opción 2: resuelve el punto 3 (3 elementos, mochila de 3000 grs.).
- Opción 3: pide por teclado una instancia propia (capacidad, cantidad de
  objetos, y nombre/peso/valor de cada uno), indicando en cada paso qué
  ingresar.
- Opción 4: salir.

También se puede pasar una instancia en JSON como argumento para correrla
una sola vez sin pasar por el menú.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Sequence, Tuple

from mochila import (
    Item,
    cargar_instancia_desde_json,
    calcular_reporte,
    instancia_ejercicio_3,
    instancia_ejercicios_1_y_2,
)


def imprimir_espacio_busqueda(items: Sequence[Item], capacidad: int, unidad: str) -> None:
    print("Espacio de búsqueda")
    print(f"  Capacidad máxima de la mochila: {capacidad} {unidad}")
    print(f"  Objetos disponibles ({len(items)}):")
    print(f"  {'ID':<4}{'Nombre':<14}{'Peso/Volumen':>14}{'Valor':>10}{'Valor/Peso':>13}")
    for idx, item in enumerate(items, start=1):
        print(f"  {idx:<4}{item.nombre:<14}{item.peso:>14}{item.valor:>10}{item.ratio:>13.4f}")


def imprimir_reporte_metodo(reporte_metodo: dict) -> None:
    unidad = reporte_metodo["unidad"]
    nombres = ", ".join(reporte_metodo["seleccion"]) if reporte_metodo["seleccion"] else "ninguno"

    print("-" * 72)
    print(f"Método: {reporte_metodo['metodo'].upper()}")
    print("-" * 72)
    print("  [Métricas de rendimiento]")
    print(f"    Tiempo exacto de ejecución: {reporte_metodo['tiempo_s']:.9f} s")
    print(f"    Combinaciones/candidatos evaluados: {reporte_metodo['combinaciones_evaluadas']}")
    print("  [Inventario final]")
    print(f"    Objetos seleccionados: {nombres}")
    print("  [Validación de restricciones]")
    print(
        f"    {'Peso' if unidad == 'grs.' else 'Peso/volumen'} ocupado: {reporte_metodo['peso']} {unidad} de "
        f"{reporte_metodo['capacidad']} {unidad} ({reporte_metodo['porcentaje_ocupado']:.2%})"
    )
    print(f"    Espacio libre/desperdiciado: {reporte_metodo['espacio_libre']} {unidad}")
    print(f"    ¿Respeta la capacidad máxima?: {'Sí' if reporte_metodo['respeta_capacidad'] else 'No'}")
    print("  [Función objetivo]")
    print(f"    Valor económico total acumulado: ${reporte_metodo['valor']}")


def imprimir_auditoria(auditoria: dict) -> None:
    print("-" * 72)
    print("Auditoría crítica: exhaustivo vs. greedy")
    print("-" * 72)
    if auditoria["tiempo"]:
        print(f"  Tiempo: {auditoria['tiempo']}")
    if auditoria["combinaciones"]:
        print(f"  Combinaciones evaluadas: {auditoria['combinaciones']}")
    print(f"  Conclusión: {auditoria['conclusion']}")


def imprimir_comparacion(items: Sequence[Item], capacidad: int, titulo: str, unidad: str = "grs.") -> None:
    print("=" * 72)
    print(titulo)
    print("=" * 72)
    imprimir_espacio_busqueda(items, capacidad, unidad)
    print()

    reporte = calcular_reporte(items, capacidad, unidad)
    imprimir_reporte_metodo(reporte["exhaustivo"])
    imprimir_reporte_metodo(reporte["greedy"])
    imprimir_auditoria(reporte["auditoria"])
    print()


def resolver_ejercicios_1_y_2() -> None:
    items, capacidad, unidad = instancia_ejercicios_1_y_2()
    imprimir_comparacion(
        items, capacidad, "Ejercicios 1 y 2 - Mochila por volumen (lista completa del enunciado)", unidad=unidad
    )


def resolver_ejercicio_3() -> None:
    items, capacidad, unidad = instancia_ejercicio_3()
    imprimir_comparacion(items, capacidad, "Ejercicio 3 - Mochila por peso", unidad=unidad)


def leer_entrada(mensaje: str) -> str:
    """input() que además descarta un BOM UTF-8 inicial, por si la entrada
    viene redirigida desde un archivo guardado como 'UTF-8 con BOM'."""
    return input(mensaje).strip().lstrip("﻿")


def pedir_entero(mensaje: str, minimo: int) -> int:
    """Pide un entero por teclado, reintentando hasta que sea válido."""
    while True:
        crudo = leer_entrada(mensaje)
        try:
            valor = int(crudo)
        except ValueError:
            print(f"  -> Ingresá un número entero (te pedimos un valor >= {minimo}). Probá de nuevo.")
            continue
        if valor < minimo:
            print(f"  -> Tiene que ser mayor o igual a {minimo}. Probá de nuevo.")
            continue
        return valor


def pedir_instancia_por_teclado() -> Tuple[List[Item], int, str]:
    print()
    print("Vas a cargar una instancia propia. Te vamos a pedir cada dato uno por uno.")
    unidad = leer_entrada("  Unidad de peso/volumen a usar (ej: grs., cm3, kg) [u.]: ") or "u."
    capacidad = pedir_entero(f"  Capacidad máxima de la mochila (en {unidad}, número entero): ", minimo=1)
    cantidad = pedir_entero("  ¿Cuántos objetos vas a cargar? (número entero >= 1): ", minimo=1)

    items: List[Item] = []
    for i in range(1, cantidad + 1):
        print(f"\n  Objeto {i} de {cantidad}:")
        nombre = leer_entrada(f"    Nombre del objeto {i} [Objeto {i}]: ") or f"Objeto {i}"
        peso = pedir_entero(f"    Peso/Volumen de '{nombre}' (en {unidad}, entero > 0): ", minimo=1)
        valor = pedir_entero(f"    Valor económico de '{nombre}' (en $, entero >= 0): ", minimo=0)
        items.append(Item(nombre=nombre, peso=peso, valor=valor))

    return items, capacidad, unidad


def menu_interactivo() -> None:
    while True:
        print()
        print("=" * 72)
        print("TP2 - Problema de la mochila: exhaustivo vs. greedy")
        print("=" * 72)
        print("  1) Puntos 1 y 2 del enunciado (10 objetos, mochila de 4200 cm3)")
        print("  2) Punto 3 del enunciado (3 elementos, mochila de 3000 grs.)")
        print("  3) Cargar una instancia propia (ingresar objetos por teclado)")
        print("  4) Salir")
        opcion = leer_entrada("Elegí una opción escribiendo 1, 2, 3 o 4: ")

        if opcion == "1":
            resolver_ejercicios_1_y_2()
        elif opcion == "2":
            resolver_ejercicio_3()
        elif opcion == "3":
            items, capacidad, unidad = pedir_instancia_por_teclado()
            imprimir_comparacion(items, capacidad, "Mochila - instancia cargada por teclado", unidad=unidad)
        elif opcion == "4":
            print("Listo, ¡hasta la próxima!")
            return
        else:
            print(f"  -> Opción inválida: '{opcion}'. Escribí 1, 2, 3 o 4.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolver el problema de la mochila.")
    parser.add_argument(
        "archivo",
        nargs="?",
        help="Ruta a un JSON con una instancia propia. Si no se indica, se abre el menú interactivo.",
    )
    parser.add_argument(
        "--unidad",
        default="u.",
        help="Unidad de peso/volumen a mostrar cuando se pasa un archivo propio (default: u.)",
    )
    args = parser.parse_args()

    if args.archivo:
        ruta = Path(args.archivo)
        items, capacidad = cargar_instancia_desde_json(ruta)
        imprimir_comparacion(items, capacidad, f"Mochila - instancia desde {ruta.name}", unidad=args.unidad)
        return

    menu_interactivo()


if __name__ == "__main__":
    main()
