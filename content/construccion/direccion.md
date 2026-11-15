# Cómo se construyó el agente de marketing

Reel encargado por el usuario el 14 de noviembre de 2026: 60–90 segundos, voz en off y gráficos. Primera versión para revisión creativa; no autoriza publicación.

La narración explica la arquitectura comprobable del proyecto, sin inventar fechas, horas de trabajo, resultados comerciales ni conexiones activas. La secuencia es explicativa: el repositorio no conserva un historial detallado de cada paso de implementación.

## Dirección

- Formato vertical 1080×1920, 30 fps. Nueve capítulos sincronizados con la narración.
- Voz argentina sintética es-AR-TomasNeural; no es un clon de Yago. No se usan planos de personas hablando.
- Diseño Infinite Process: azul cobalto, naranja cálido y blanco; diagramas animados, detalle de código real y representaciones del flujo. Etiqueta «Visualización del proyecto» para distinguir gráficos de una captura operativa en vivo.
- Subtítulos por palabra, texto grande y composición con margen para los controles de Reels.
- Música y efectos generados localmente, de volumen bajo durante la voz.
- Cierre editorial «Seguí la construcción», sin prometer envío automático de materiales ni resultados.

## Fundamento de las escenas

1. Objetivo y flujo: `README.md`, `marketing/agents.py`.
2. Marca: `config/brand-guidelines.json`, `Agents.run` incorpora la marca al contexto.
3. Roles: `agents/`, `Workflow.draft` y `Workflow.produce`. La coordinación y publicación son código; no se presentan nueve modelos autónomos simultáneos.
4. Aprobación/versionado: `Workflow.approve`, `Workflow.revise` y `approved`. Los gráficos de aprobación son una explicación, no una aprobación del trabajo real.
5. Producción: `Workflow.produce` ejecuta ruleta, dirección visual, voz y portada/copy. Las instrucciones editoriales no se ejecutan todas automáticamente.
6. Tecnología: Python, SQLite en `marketing/store.py`, FFmpeg en `marketing/media.py`. La duración de este reel es una edición externa encargada expresamente; no altera el límite 35–55 s del generador del producto.
7. Pruebas: `tests/test_workflow.py`. Dobles de red no verifican cuentas ni publicaciones reales. Recuperación por etapa guardada en `Workflow.produce`.
8. Publicación: `marketing/publish.py`; las integraciones requieren configuración y validación real. No se muestra una publicación exitosa simulada.
9. Resultado: flujo local con revisión humana, sin promesas de autonomía total ni viralidad.

Los archivos de código y los trabajos existentes se conservan; los renders nuevos viven en `runtime/construccion-v1/` y `entregas/construccion-v1/`.
