import json # Importamos json para poder decodificar la estructura del cromosoma guardado en texto
from pathlib import Path # Path nos ayuda a manejar las rutas de los archivos de forma compatible en cualquier SO

import matplotlib # Matplotlib es la librería estándar para generar gráficos en Python
matplotlib.use("Agg") # Configuramos el backend 'Agg' para que matplotlib no intente abrir ventanas y solo guarde archivos
import matplotlib.pyplot as plt # pyplot nos da una interfaz tipo MATLAB para dibujar las figuras
import matplotlib.patches as mpatches # mpatches nos sirve para dibujar los cuadraditos de colores en la leyenda
import pandas as pd # Pandas nos permite leer y manipular los datos CSV fácilmente

# Importamos variables y funciones globales de nuestro script principal main.py
from main import (
    derivar_alertas_desde_dataset, # Función que reconstruye las alertas desde el CSV base
    _evaluar_asignacion, # Función que calcula los tiempos de espera y finalización del genético
    HORIZONTE_MINUTOS, # El límite de minutos del turno (usualmente 480 min = 8 horas)
    N_ANALISTAS, # La cantidad total de analistas en el SOC
    OUTPUTS_DIR, # La ruta a la carpeta donde guardamos todos los resultados
    FIGURES_DIR, # La ruta a la carpeta específica para guardar las imágenes y gráficos
    RESUMEN_CSV # La ruta al archivo CSV donde guardamos el ganador del algoritmo
)

def generar_gantt() -> None: # Definimos la función principal que va a dibujar el diagrama de Gantt
    print("Generando Diagrama de Gantt de la mejor asignación...") # Avisamos al usuario por consola que arrancó el proceso
    
    # 1. Leer el mejor cromosoma encontrado
    if not RESUMEN_CSV.exists(): # Verificamos si el archivo de resultados realmente existe en el disco
        print(f"Error: No se encontró {RESUMEN_CSV}. Corré main.py primero.") # Si no existe, lanzamos un error claro
        return # Cortamos la ejecución de la función porque no tenemos datos para graficar
        
    df_resumen = pd.read_csv(RESUMEN_CSV) # Usamos Pandas para leer el archivo CSV completo en memoria
    # Extraemos el string en formato JSON y lo convertimos a una lista real de Python
    mejor_cromosoma = json.loads(df_resumen.iloc[0]["mejor_cromosoma_texto"]) 
    
    # 2. Reconstruir las alertas y evaluar el cromosoma para obtener tiempos
    alertas = derivar_alertas_desde_dataset() # Llamamos a la función que vuelve a cargar las alertas del dataset
    evaluacion = _evaluar_asignacion(mejor_cromosoma, alertas) # Simulamos la asignación ganadora para obtener a qué hora termina cada alerta
    
    finalizacion_por_alerta = evaluacion["finalizacion_por_alerta"] # Extraemos el array con el minuto exacto de fin de cada alerta
    
    # 3. Preparar datos para el gráfico
    # Creamos la figura y los ejes con un tamaño de 14x8 pulgadas
    fig, ax = plt.subplots(figsize=(14, 8)) 
    
    # Definimos un diccionario que mapea la prioridad de la alerta con un color hexadecimal específico
    colores = {
        "Critica": "#d32f2f", # Rojo oscuro para alertas Críticas (máxima atención)
        "Alta": "#f57c00",    # Naranja para las alertas de Alta prioridad
        "Media": "#fbc02d",   # Amarillo oscuro para las de Media prioridad
        "Baja": "#388e3c"     # Verde para las alertas de Baja prioridad
    }
    
    # Iteramos sobre cada gen del cromosoma (cada iteración es una alerta y a qué analista fue)
    for idx_alerta, analista in enumerate(mejor_cromosoma):
        alerta = alertas[idx_alerta] # Obtenemos el objeto de la alerta correspondiente a este índice
        fin = finalizacion_por_alerta[idx_alerta] # Obtenemos en qué minuto exactamente se terminó de resolver
        inicio = fin - alerta.tiempo_estimado_min # Calculamos el minuto de inicio restando el tiempo de resolución al tiempo de fin
        
        # Dibujamos una barra horizontal que representa esta alerta específica en la línea de tiempo del analista
        ax.barh(
            y=analista, # La posición vertical (Y) es simplemente el ID del analista (1 al 10)
            width=alerta.tiempo_estimado_min, # El ancho de la barra es lo que tardó en resolverse
            left=inicio, # La barra empieza a dibujarse en el minuto de 'inicio'
            color=colores[alerta.prioridad], # El color de relleno dependerá de su prioridad
            edgecolor="white", # Le ponemos un bordecito blanco para separarla de las alertas pegadas
            linewidth=0.5 # Grosor del bordecito blanco
        )
    
    # 4. Ajustes visuales del gráfico
    ax.set_yticks(range(1, N_ANALISTAS + 1)) # Marcamos las divisiones del eje Y (del 1 a la cantidad de analistas)
    ax.set_yticklabels([f"Analista {i}" for i in range(1, N_ANALISTAS + 1)]) # Le ponemos de etiqueta el texto "Analista X" a cada marca
    
    ax.set_xlabel("Tiempo transcurrido (Minutos)") # Etiqueta descriptiva para el eje X
    ax.set_title("Diagrama de Gantt - Asignación de Alertas SOC (Mejor Solución)", fontsize=14, pad=15) # Título del gráfico completo
    
    # Dibujamos una línea vertical punteada que simboliza la barrera de las 8 horas (Horizonte)
    ax.axvline(x=HORIZONTE_MINUTOS, color="#424242", linestyle="--", linewidth=1.5, zorder=0) 
    # Le agregamos un pequeño texto descriptivo al lado de la línea vertical
    ax.text(HORIZONTE_MINUTOS + 5, N_ANALISTAS + 0.5, "Fin del Turno (8 hs)", color="#424242", fontweight="bold")
    
    # Creamos dinámicamente los cuadraditos de colores para construir la leyenda de la derecha
    leyendas = [mpatches.Patch(color=color, label=f'Prioridad {prio}') for prio, color in colores.items()]
    ax.legend(handles=leyendas, loc="upper right") # Añadimos la leyenda al gráfico y la ubicamos arriba a la derecha
    
    ax.grid(axis='x', linestyle='--', alpha=0.6) # Activamos la grilla solo vertical (para el eje X) con un poco de transparencia
    ax.spines["top"].set_visible(False) # Ocultamos la línea de borde superior del cuadro para que quede más moderno
    ax.spines["right"].set_visible(False) # Ocultamos también la línea de borde derecha
    
    plt.tight_layout() # Auto-ajustamos los márgenes para que todo entre perfecto sin cortarse
    
    # Generamos la ruta de salida completa combinando el directorio de figuras con el nombre del archivo
    ruta_salida = FIGURES_DIR / "gantt_asignacion_final.png" 
    plt.savefig(ruta_salida, dpi=300) # Guardamos el gráfico como PNG con alta calidad (300 DPI)
    plt.close() # Cerramos el objeto de la figura para liberar la memoria RAM
    
    # Informamos al usuario que se guardó correctamente, mostrándole la ruta relativa
    print(f"¡Diagrama de Gantt generado exitosamente en: {ruta_salida.relative_to(Path.cwd())}!")

# Bloque estándar de ejecución: solo se llama a generar_gantt() si este script se ejecuta directamente
if __name__ == "__main__":
    generar_gantt() # Disparamos la función

