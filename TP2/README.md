# TP2 - Problema de la mochila

Este trabajo práctico resuelve el problema de la mochila con dos enfoques:

- búsqueda exhaustiva;
- algoritmo greedy por relación valor/peso.

## Qué incluye

- Implementación genérica en [main.py](main.py).
- Resolución del caso del punto 3 del enunciado.
- Comparación automática entre exhaustivo y greedy.
- Informe académico en [docs/informe.html](docs/informe.html).

## Ejecución

Desde la carpeta `TP2`:

```bash
python3 main.py
```

También podés pasar un archivo JSON con la instancia real del enunciado:

```bash
python3 main.py instancia_ejemplo.json
```

El JSON debe tener esta forma:

```json
{
	"capacidad": 4200,
	"items": [
		{"nombre": "A", "peso": 100, "valor": 20},
		{"nombre": "B", "peso": 250, "valor": 60}
	]
}
```

## Resultado del punto 3

Para los elementos:

- 1800 grs. y $72
- 600 grs. y $36
- 1200 grs. y $60

con una mochila de 3000 grs.:

- La solución exhaustiva óptima es tomar los elementos 1 y 3, con valor total de $132.
- La solución greedy por valor/peso toma los elementos 2 y 3, con valor total de $96.

## Observación sobre el punto 1 y 2

El enunciado menciona una lista de elementos para una mochila de 4200 cm3, pero esa lista no está visible en el texto que recibí. La implementación quedó preparada para cualquier lista: solo hay que reemplazar los ítems de ejemplo por los del enunciado completo y volver a ejecutar el script.

## Conclusión breve

El método exhaustivo garantiza el óptimo porque evalúa todos los subconjuntos. El greedy es más rápido y simple, pero solo funciona de forma óptima en ciertos casos; en general, no asegura la mejor combinación global.

## Informe

Abrir [docs/informe.html](docs/informe.html) en un navegador moderno. El informe replica la estructura académica usada en TP1, pero adaptada al problema de la mochila y al análisis del punto 3.