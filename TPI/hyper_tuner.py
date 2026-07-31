import pandas as pd
from itertools import product
import time
from pathlib import Path

# Importar dependencias del main
from main import (
    derivar_alertas_desde_dataset,
    evolucionar,
    SEED,
    OUTPUTS_DIR
)

def ejecutar_grid_search():
    print("Iniciando Grid Search (Búsqueda de Hiperparámetros)...")
    print("Esto puede demorar unos minutos.\n")
    
    # 1. Definir el espacio de búsqueda
    poblaciones = [10, 20]
    mutaciones = [0.01, 0.05, 0.10]
    crossovers = [0.60, 0.75, 0.90]
    
    # Reducimos generaciones para que no demore tanto en la demo
    N_GENERACIONES_PRUEBA = 15 
    
    alertas = derivar_alertas_desde_dataset()
    resultados = []
    
    total_combinaciones = len(poblaciones) * len(mutaciones) * len(crossovers)
    actual = 1
    
    inicio_grid = time.time()
    
    # 2. Iterar sobre todas las combinaciones
    for pob, mut, cx in product(poblaciones, mutaciones, crossovers):
        print(f"[{actual}/{total_combinaciones}] Probando -> Pob: {pob}, Mut: {mut:.2f}, Cx: {cx:.2f}... ", end="", flush=True)
        
        # Ejecutar el AG con estos parámetros
        _, resumen = evolucionar(
            alertas=alertas,
            n_generaciones=N_GENERACIONES_PRUEBA,
            tam_poblacion=pob,
            p_crossover=cx,
            p_mutacion=mut,
            seed=SEED
        )
        
        # Guardar resultados
        resultados.append({
            "poblacion": pob,
            "mutacion": mut,
            "crossover": cx,
            "mejor_fitness": resumen["mejor_fitness_global"],
            "espera_promedio": resumen["espera_promedio_min"],
            "backlog": resumen["backlog_alertas"]
        })
        
        print(f"Fitness: {resumen['mejor_fitness_global']:.6f}")
        actual += 1

    # 3. Guardar y mostrar el top 5
    df_resultados = pd.DataFrame(resultados)
    # Ordenar por el mejor fitness descendente
    df_resultados = df_resultados.sort_values(by="mejor_fitness", ascending=False)
    
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    ruta_csv = OUTPUTS_DIR / "grid_search_resultados.csv"
    df_resultados.to_csv(ruta_csv, index=False)
    
    tiempo_total = time.time() - inicio_grid
    print("\n" + "="*50)
    print(f"Búsqueda finalizada en {tiempo_total:.1f} segundos.")
    print(f"Resultados guardados en: {ruta_csv.relative_to(Path.cwd())}")
    print("="*50)
    print("\nTop 3 mejores combinaciones encontradas:")
    print(df_resultados.head(3).to_string(index=False))

if __name__ == "__main__":
    ejecutar_grid_search()
