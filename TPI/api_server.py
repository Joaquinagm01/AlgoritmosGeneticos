"""
5. Integración con SIEM/SOAR: Servidor REST API usando FastAPI.

Ejecutar con: uvicorn api_server:app --reload
Probar con: POST http://localhost:8000/asignar enviando un JSON con alertas.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List
import main_avanzado
from main import Alerta

app = FastAPI(
    title="SOC Genetic Scheduler API 🧬", 
    version="1.0",
    description="Esta API permite asignar dinámicamente alertas de ciberseguridad a analistas del SOC optimizando tiempos de espera y balance de carga usando **Algoritmos Genéticos Multiobjetivo (NSGA-II)**.",
    contact={
        "name": "Equipo UTN FRRo - Algoritmos Genéticos",
    }
)

class AlertaIn(BaseModel):
    id_alerta: int = Field(..., title="ID de la Alerta", description="Identificador único del evento en el SIEM.", example=101)
    llegada_min: int = Field(..., title="Minuto de Llegada", description="Minuto en que se originó la alerta (0 = inicio del turno).", example=15)
    prioridad: str = Field(..., title="Prioridad", description="Nivel de urgencia: Baja, Media, Alta o Critica.", example="Critica")
    severidad: int = Field(..., title="Severidad", description="Puntuación de amenaza (1 a 100).", example=85)
    tiempo_estimado_min: int = Field(..., title="Tiempo Estimado (min)", description="Minutos calculados que tomará resolver la alerta.", example=45)
    sla_min: int = Field(..., title="SLA (min)", description="Tiempo máximo permitido antes de penalización.", example=30)

class AsignacionOut(BaseModel):
    id_alerta: int = Field(..., description="ID de la alerta procesada.")
    id_analista: int = Field(..., description="Analista asignado por el algoritmo (1 a 10).")
    prioridad: str = Field(..., description="Prioridad original de la alerta.")
    tier_analista: int = Field(..., description="Nivel del analista (3=Senior, 2=Semi-Senior, 1=Junior).")

@app.get("/", tags=["Estado del Sistema"], summary="Verificar conexión")
def health_check():
    """
    Verifica si el motor de asignación genética está encendido y listo para recibir alertas.
    """
    return {"status": "ok", "message": "SOC Genetic Scheduler API en linea"}

@app.post("/asignar", response_model=List[AsignacionOut], tags=["Asignación Inteligente"], summary="Optimizar asignación de alertas")
def asignar_lote_alertas(alertas: List[AlertaIn]):
    """
    Recibe un lote de alertas y devuelve a qué analista fue asignada cada una
    usando NSGA-II y Skill-Based Routing.
    """
    if not alertas:
        raise HTTPException(status_code=400, detail="El lote de alertas está vacío.")
        
    # Convertir a objetos Alerta internos
    alertas_internas = []
    for a in alertas:
        alertas_internas.append(
            Alerta(
                id_alerta=a.id_alerta,
                llegada_min=a.llegada_min,
                prioridad=a.prioridad,
                severidad=a.severidad,
                tiempo_estimado_min=a.tiempo_estimado_min,
                sla_min=a.sla_min
            )
        )
        
    # Usamos el inicio reloj basado en la alerta más temprana del lote
    inicio_reloj = min(a.llegada_min for a in alertas_internas)
    
    # Ejecutamos la optimización NSGA-II para este lote específico (Dinámico)
    mejor_cromosoma = main_avanzado.optimizacion_nsgaii(
        alertas_internas, 
        inicio_reloj=inicio_reloj, 
        generaciones=10, 
        pop_size=20
    )
    
    # Formateamos la respuesta
    respuesta = []
    for idx, analista in enumerate(mejor_cromosoma):
        respuesta.append(
            AsignacionOut(
                id_alerta=alertas_internas[idx].id_alerta,
                id_analista=analista,
                prioridad=alertas_internas[idx].prioridad,
                tier_analista=main_avanzado.obtener_tier(analista)
            )
        )
        
    return respuesta
