import pandas as pd # Importamos pandas para crear un dataframe con la tabla de resultados finales
from itertools import product # Product nos sirve para crear combinaciones matemáticas (producto cartesiano) de los parámetros
import time # Importamos time para medir cuánto demora la búsqueda completa
from pathlib import Path # Path para manejar las rutas del sistema de archivos correctamente

# Importar dependencias del main
from main import (
    derivar_alertas_desde_dataset, # Función para obtener nuestra lista de alertas base
    evolucionar, # La función principal que arranca y corre el algoritmo genético entero
    SEED, # La semilla para que los resultados aleatorios sean siempre los mismos
    OUTPUTS_DIR # El directorio donde vamos a volcar nuestro CSV de resultados
)

def ejecutar_grid_search(): # Definimos la función principal que va a sintonizar los parámetros
    print("Iniciando Grid Search (Búsqueda de Hiperparámetros)...") # Aviso inicial en consola
    print("Esto puede demorar unos minutos.\n") # Advertencia al usuario porque son muchas combinaciones
    
    # 1. Definir el espacio de búsqueda (todas las combinaciones posibles)
    poblaciones = [10, 20] # Probaremos con un tamaño de población pequeño (10) y uno mediano (20)
    mutaciones = [0.01, 0.05, 0.10] # Probaremos mutar el 1%, 5% y 10% de los genes
    crossovers = [0.60, 0.75, 0.90] # Probaremos cruzar cromosomas con 60%, 75% y 90% de probabilidad
    
    # Reducimos generaciones para que no demore tanto en la demo
    N_GENERACIONES_PRUEBA = 15 # En vez de 20 o 50, usamos 15 iteraciones para cada prueba (ahorra tiempo)
    
    alertas = derivar_alertas_desde_dataset() # Obtenemos el set de datos real (las 500 alertas)
    resultados = [] # Inicializamos una lista vacía donde iremos guardando los puntajes de cada prueba
    
    total_combinaciones = len(poblaciones) * len(mutaciones) * len(crossovers) # Calculamos cuántas pruebas se van a correr (2 * 3 * 3 = 18)
    actual = 1 # Iniciamos un contador para mostrar el progreso en la consola
    
    inicio_grid = time.time() # Tomamos el tiempo exacto en que arranca la búsqueda para medir el total
    
    # 2. Iterar sobre todas las combinaciones generadas por itertools.product
    for pob, mut, cx in product(poblaciones, mutaciones, crossovers): 
        # Mostramos en qué número de iteración vamos y qué variables estamos probando (sin hacer salto de línea gracias a end="")
        print(f"[{actual}/{total_combinaciones}] Probando -> Pob: {pob}, Mut: {mut:.2f}, Cx: {cx:.2f}... ", end="", flush=True)
        
        # Ejecutar el AG con estos parámetros específicos de esta iteración
        _, resumen = evolucionar( # El guion bajo ignora el primer valor (historial), solo nos importa el 'resumen' final
            alertas=alertas, # Pasamos la lista de alertas constante
            n_generaciones=N_GENERACIONES_PRUEBA, # Pasamos la cantidad de generaciones reducida
            tam_poblacion=pob, # Usamos la población actual del bucle
            p_crossover=cx, # Usamos la probabilidad de cruza actual del bucle
            p_mutacion=mut, # Usamos la probabilidad de mutación actual del bucle
            seed=SEED # Usamos la misma semilla siempre para que la comparación sea justa
        )
        
        # Guardar resultados en nuestro diccionario de la iteración
        resultados.append({
            "poblacion": pob, # Guardamos el parámetro de población que usamos
            "mutacion": mut, # Guardamos la mutación que usamos
            "crossover": cx, # Guardamos el crossover que usamos
            "mejor_fitness": resumen["mejor_fitness_global"], # Guardamos la puntuación matemática que logró el algoritmo
            "espera_promedio": resumen["espera_promedio_min"], # Guardamos el tiempo de espera para ver si mejoró
            "backlog": resumen["backlog_alertas"] # Guardamos la cantidad de alertas que quedaron sin asignar
        })
        
        # Imprimimos el puntaje final de esta combinación al lado del texto anterior
        print(f"Fitness: {resumen['mejor_fitness_global']:.6f}")
        actual += 1 # Aumentamos el contador de progreso
    
    # 3. Guardar y mostrar el top de mejores combinaciones
    df_resultados = pd.DataFrame(resultados) # Convertimos la lista de diccionarios en un Dataframe (una tabla) de Pandas
    # Ordenar la tabla usando la columna del fitness, de mayor a menor (descendente)
    df_resultados = df_resultados.sort_values(by="mejor_fitness", ascending=False) 
    
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True) # Nos aseguramos de que exista la carpeta outputs
    ruta_csv = OUTPUTS_DIR / "grid_search_resultados.csv" # Definimos la ruta del archivo CSV
    df_resultados.to_csv(ruta_csv, index=False) # Exportamos la tabla ordenada al disco duro
    
    tiempo_total = time.time() - inicio_grid # Calculamos la diferencia de tiempo entre el final y el inicio
    print("\n" + "="*50) # Imprimimos separador decorativo
    print(f"Búsqueda finalizada en {tiempo_total:.1f} segundos.") # Mostramos cuánto tardaron las 18 pruebas
    print(f"Resultados guardados en: {ruta_csv.relative_to(Path.cwd())}") # Avisamos dónde quedó el archivo CSV
    print("="*50)
    print("\nTop 3 mejores combinaciones encontradas:") # Texto introductorio
    print(df_resultados.head(3).to_string(index=False)) # Imprimimos en consola solo las primeras 3 filas de la tabla

# Si alguien ejecuta directamente 'python hyper_tuner.py', arrancamos la función
if __name__ == "__main__":
    ejecutar_grid_search()

