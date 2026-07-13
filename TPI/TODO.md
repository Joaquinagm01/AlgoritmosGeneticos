# TODO del TPI

Checklist de trabajo para dejar el Trabajo Práctico Integrador cerrado, consistente con el material de referencia que hay dentro de `TPI`.

## 1. Revisión de material base

- [x] Leer [Diapositivas_Introducción a Investigación.pdf](Diapositivas_Introducción%20a%20Investigaci%C3%B3n.pdf) para adaptar la introducción, el encuadre académico y el tono del informe.
- [x] Revisar [UTN_Algoritmos_Genéticos_DirDeBibliotecasDigitales.pdf](UTN_Algoritmos_Gen%C3%A9ticos_DirDeBibliotecasDigitales.pdf) para chequear bibliografía, formato y criterios de presentación.
- [x] Revisar [UTN_Algoritmos_Genéticos_ProyectoInv_2020.pdf](UTN_Algoritmos_Gen%C3%A9ticos_ProyectoInv_2020.pdf) para reutilizar estructura, alcance y nivel de detalle esperado.
- [x] Abrir [EG_TP_DWeb_Chacón_GomezManna_Carrizo_Jordán.docx](EG_TP_DWeb_Chac%C3%B3n_GomezManna_Carrizo_Jord%C3%A1n.docx) como referencia de estilo, portada o formato si corresponde.

### Criterios extraídos de la presentación

- Delimitar el tema con precisión antes de plantear el problema.
- Evitar preguntas cerradas tipo sí/no para que el informe tenga valor investigativo.
- Buscar y citar literatura reciente y material técnico relevante del área.
- Presentar el problema como una exploración progresiva: tema, fuentes, acotación y formulación.
- Justificar por qué el problema del SOC es concreto, accesible y relevante para la especialidad.

### Notas de los materiales revisados

- Bibliotecas digitales: usar SciELO, Dialnet, WorldWideScience y Google Scholar como fuentes base para bibliografía académica y técnica.
- Proyecto de investigación: estructurar la entrega con carátula, índice, situación problemática, problema, objetivos, marco teórico y una segunda parte de concreción del modelo.
- Proyecto de investigación: el documento guía pide un problema formulado en un párrafo, objetivos concretos y marco teórico con referencias bibliográficas sólidas.
- Proyecto de investigación: la implementación debe documentarse de manera sintética, con especificación técnica de hardware y software.
- DOCX de referencia: sirve como guía de formato y prolijidad de presentación, pero su temática es de Desarrollo Web, así que sólo aporta estilo general.

## 2. Revisión de enunciados disponibles

- [x] Leer [UTN_AlgoritmosGen{eticos_Enunciado tema centrales fotovoltaicas_2021.pdf](UTN_AlgoritmosGen%7Beticos_Enunciado%20tema%20centrales%20fotovoltaicas_2021.pdf) para identificar qué pide un enunciado de AG bien armado.
- [x] Leer [UTN_AlgoritmosGen{eticos_Enunciado tema parque eólico_2021.pdf](UTN_AlgoritmosGen%7Beticos_Enunciado%20tema%20parque%20e%C3%B3lico_2021.pdf) para comparar restricciones, variables y métricas.
- [x] Leer [UTN_Algoritmos_Genéticos_EnunciadoTemaFractales_2021.pdf](UTN_Algoritmos_Gen%C3%A9ticos_EnunciadoTemaFractales_2021.pdf) para observar cómo se redacta un problema académico de AG.
- [x] Leer [UTN_Algoritmos_Genéticos_EnunciadoTemaMachineLearning.pdf](UTN_Algoritmos_Gen%C3%A9ticos_EnunciadoTemaMachineLearning.pdf) para rescatar estructura de evaluación y presentación.
- [x] Leer [UTN_Algoritmos_Genéticos_EnunciadoTemaTeoríaDelCaos.pdf](UTN_Algoritmos_Gen%C3%A9ticos_EnunciadoTemaTeor%C3%ADaDelCaos.pdf) para verificar criterios de desarrollo teórico y resultados. Los cinco enunciados confirman el mismo patrón: elegir tema, formular un problema (a menudo como pregunta abierta), desarrollar marco teórico y concretar un modelo codificado.

## 3. Definición del TPI

- [x] Confirmar que el tema final del TPI será Scheduling de Alertas SOC y no otro de los temas listados en los PDFs.
- [x] Redactar el problema de forma académica: contexto SOC, volumen de alertas, analistas disponibles, prioridades y SLA. Ver [docs/TPI_Documentacion_Proyecto_Investigacion.md](docs/TPI_Documentacion_Proyecto_Investigacion.md), punto 5.
- [x] Definir claramente la representación genética: gen = analista asignado, cromosoma = asignación completa.
- [x] Especificar restricciones y objetivos: tiempo total, backlog, alertas críticas, balance de carga y saturación. Ver punto 6 (objetivos específicos) del documento.
- [ ] Ajustar la función fitness para que la penalización sea coherente con el dominio y fácil de justificar en el informe.

## 4. Validación técnica del programa

- [ ] Revisar [main.py](main.py) para confirmar que todas las funciones obligatorias están presentes y bien documentadas.
- [ ] Verificar que la generación de alertas sea reproducible con semilla y que use prioridades, severidad y tiempos estimados.
- [ ] Confirmar que la selección por ruleta, por torneo y el elitismo estén implementados de forma diferenciada.
- [ ] Revisar el crossover de 1 punto y la mutación invertida para asegurar que respetan el cromosoma completo.
- [ ] Comprobar que la evolución registre por generación fitness máximo, mínimo, promedio, desvío estándar y tiempo.
- [ ] Validar que el mejor cromosoma final produzca una distribución de cargas razonable entre analistas.

## 5. Salidas y resultados

- [ ] Verificar que se generen los CSV de métricas y resúmenes en [outputs](outputs).
- [ ] Verificar que se generen los gráficos en [outputs/figures](outputs/figures).
- [ ] Revisar los valores finales obtenidos para ruleta, torneo y elitismo.
- [ ] Confirmar cuál método obtiene el mejor fitness global y si eso coincide con la interpretación académica.
- [ ] Revisar si la salida por consola necesita redacción más limpia para entrega o captura en el informe.

## 6. Informe académico

- [ ] Completar el marco teórico de algoritmos genéticos aplicado a scheduling. (Punto 7 de la guía de cátedra — fuera del alcance de la entrega hasta el punto 6; queda para la próxima etapa.)
- [x] Explicar por qué el problema de SOC se modela como un problema de asignación y balance de carga. Ver puntos 3 y 4 del documento.
- [ ] Describir cada operador genético y justificar la elección de sus parámetros en detalle (se reserva para el informe técnico de la segunda parte).
- [x] Incluir tablas por generación y tablas resumen comparativas entre métodos. Ver Tabla 1 y Tabla 2 del documento (punto 7).
- [x] Incluir los gráficos obligatorios: máximo, promedio, mínimo, desviación estándar y comparación de métodos. Referenciados en el documento, más una figura adicional de carga final por analista.
- [ ] Redactar conclusiones con foco en calidad de solución, estabilidad y costo computacional (corresponde al informe técnico de la segunda parte / concreción del modelo).

## 7. Cierre y entrega

- [ ] Releer el `README` para que explique el uso del proyecto sin ambigüedades.
- [ ] Dejar limpio el directorio `TPI` quitando archivos de referencia que no correspondan a la entrega, si el criterio de la cátedra lo exige.
- [ ] Confirmar que el proyecto corre desde cero con `python3 main.py` dentro de `TPI`.
- [ ] Revisar si conviene generar una versión final del informe en HTML o PDF para entrega.

## Orden recomendado de trabajo

1. Leer todos los PDFs y confirmar el encuadre final.
2. Ajustar el programa a ese encuadre.
3. Validar salidas, gráficos y tablas.
4. Cerrar informe académico.
5. Preparar versión final para entrega.