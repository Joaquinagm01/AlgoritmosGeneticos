# TODO del TPI — checklist contra la guía oficial de la cátedra

Este checklist sigue textualmente la "GUIA de la Estructura y contenido del perfil del proyecto de
investigación" de la cátedra (Algoritmos Genéticos). Reemplaza cualquier versión anterior de este
archivo. El objetivo del documento guía es dejar establecido qué se puede investigar sobre la
temática elegida y servir de guía para el proyecto que permite la aprobación directa de la materia.

## PRIMERA PARTE: Marco contextual y teórico

Entregable: [docs/informe.html](docs/informe.html) (Documento Guía de la Investigación).

- [x] **1. Carátula**
  - [x] a. Nombre de la temática abordada
  - [x] b. Nombre de los integrantes del grupo
  - [x] c. Legajo de los integrantes del grupo
  - [x] d. Ciclo lectivo
- [x] **2. Índice de Contenidos**
- [x] **3. Denominación del futuro proyecto de investigación**
- [x] **4. Situación Problemática** — problemas identificados a partir del material bibliográfico que conforma el marco teórico.
- [x] **5. Problema** — síntesis de la situación problemática en un párrafo, formulado con claridad y sin ambigüedades.
- [x] **6. Objetivos de la investigación**
  - [x] a. Objetivo general (meta global)
  - [x] b. Objetivos específicos (concretos, comprobables, verificables, medibles, realizables; determinan el alcance)
- [x] **7. Marco Teórico** — conceptos teóricos (AG, optimización, metaheurísticas, scheduling, componentes canónicos del AG, SOC/SIEM/alert fatigue), con referencias bibliográficas reales (6 citas: 5 sobre el dominio + 1 sobre el dataset usado).

### Trabajo de Cátedra (máximo 8 páginas, formato de la guía)

Entregable: [docs/articulo.tex](docs/articulo.tex) / [docs/articulo.pdf](docs/articulo.pdf), formato Times New Roman, A4, dos columnas, sin numeración de página.

- [x] Título, Autores, Institución
- [x] Abstract (<250 palabras: objetivo, metodología, resultados, conclusión)
- [x] Palabras Clave (8)
- [x] Introducción
- [x] Elementos del trabajo y metodología
- [x] Resultados (con datos reales de la corrida sobre CICIDS2017)
- [x] Discusión (ruleta vs. torneo vs. elitismo, con hallazgo empírico real)
- [x] Conclusión
- [x] Referencias (numeradas, formato homogéneo)
- [x] Datos de Contacto (con dirección postal real de la institución)
- [x] Tabla en Times New Roman 10 real (sin escalado), con título "Tabla 1..." en 10 cursiva
- [x] Figura numerada ("Figura 1..."), en blanco y negro (líneas punteada/rayada/sólida en vez de color) para impresión monocromática
- [x] Discusión relacionada con la bibliografía citada ([1]-[5]) e indicando aplicaciones posibles

### Entrega de la Primera Parte

- [ ] Subir **ambos documentos** (Documento Guía + Trabajo de Cátedra) al campus virtual de la asignatura, una semana antes de la exposición oral. *(Acción del equipo, no de este repositorio.)*

## SEGUNDA PARTE: Concreción del modelo

- [x] Describir la introducción de la tecnología al medio para la situación problemática abordada.
- [x] Desarrollar un prototipo/modelo/software que describa, analice y verifique los resultados: [main.py](main.py), corriendo sobre datos reales de CICIDS2017 (ver [docs/informe.html](docs/informe.html), sección 9, y `outputs/`).
- [x] Experimentar con el software y verificar si se alcanzaron los objetivos propuestos (comparación ruleta/torneo/elitismo con métricas reales).
- [x] Implementación en Python, documentada de manera sintética (README.md + docstrings de `main.py`).
- [x] **Especificación técnica de hardware, software e infraestructura utilizada.** Ver [docs/informe.html](docs/informe.html), sección 9 ("Especificación técnica"): Python 3.13.3, pandas/numpy/matplotlib con versiones exactas, SO, infraestructura de ejecución (local, sin GPU) y tamaños de dataset/salidas.
- [ ] Compartir esta segunda etapa (documentación + código) a través de una **carpeta de Google Drive** con la cátedra. *(Acción del equipo: crear la carpeta, subir el contenido y compartirla.)*
- [ ] Subir al campus el **enlace** a esa carpeta de Drive. *(Acción del equipo.)*

## Exposición

- [ ] Preparar la charla: cada integrante del grupo debe hablar como máximo 30 minutos.
- [ ] Armar las diapositivas (PowerPoint, Prezi u otra herramienta, a elección del grupo).
- [ ] Exponer en la fecha definida por la cátedra. Si falta algún integrante, el resto debe exponer igual y quien faltó recupera la instancia evaluativa después.
- [ ] Subir la exposición (diapositivas o grabación, según pida la cátedra) al campus virtual.

## Entrega general

- [x] Plantilla del **documento con los enlaces a cada parte del trabajo**: [ENLACES_ENTREGA.md](ENLACES_ENTREGA.md). Falta completar los campos `[COMPLETAR]` con los enlaces reales de campus/Drive y subirlo.
- [ ] Subir al campus virtual **todos** los archivos generados: Marco Contextual y Teórico, Concreción del modelo con el código, y la Presentación.

## Estado actual del repositorio (resumen técnico)

- `main.py`: deriva 500 alertas de una muestra real de `dataset/Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv` (CICIDS2017) y corre el AG canónico (ruleta, torneo, elitismo) sobre esos datos.
- `outputs/`: CSV y figuras generados por la corrida real (semilla 42). Ganador por fitness global: elitismo; mejor balance de carga: torneo.
- `docs/informe.html`: Documento Guía de Investigación completo, estrictamente los 7 puntos exigidos (Carátula a Marco Teórico) en el índice numerado, más "Referencias bibliográficas" (soporte del punto 7) y "Material complementario — Evidencia del modelo implementado" (Segunda Parte) claramente separados y sin numerar, para no dar a entender que son puntos oficiales adicionales de la guía.
- `docs/articulo.tex` / `docs/articulo.pdf`: Trabajo de Cátedra en el formato exigido, con resultados reales, 4 páginas (dentro del límite de 8).
- Pendiente y fuera del alcance de este repositorio: especificación técnica de hardware/infraestructura, carpeta de Drive, diapositivas de exposición, y las subidas al campus virtual.
