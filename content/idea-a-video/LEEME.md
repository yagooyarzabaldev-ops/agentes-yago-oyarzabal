# De una idea a un video

## Revisión V3 — reemplazo de la pluma naranja

Yago rechazó la imagen de la pluma sobre fondo naranja. Se reemplazó por `assets/script-glass.png`, una escena de manuscritos de vidrio con luz violeta y verde, en las dos apariciones de 18–20s y 24–26s y sus transiciones. Se mantienen 14 originales distintos y 70 segundos. El rechazo corresponde a ese recurso; no es una prohibición general de usar naranja en otras escenas.

La versión vigente es `entregas/idea-a-video-v3/De_una_idea_a_un_video_V3_14_IMAGENES.mp4`. El prompt y la referencia usada con ImageGen están en `assets/prompt-v3.json`; el manifiesto de los 14 recursos vigentes está en `assets/procedencia-v3.json`. Los archivos de V2 se conservan como historial, incluyendo la imagen descartada, que ya no se carga en V3. La pieza sigue pendiente de la grabación nueva.

```powershell
python content/idea-a-video/preparar_v3.py
node content/idea-a-video/render.mjs --v3 --review
node content/idea-a-video/render.mjs --v3
python content/idea-a-video/ensamblar-preview.py --v3
```

## Revisión V2 — mínimo de imágenes

Yago corrigió la primera previsualización: cuatro imágenes eran pocas. La nueva versión adopta el perfil `infinite-process-editorial-v3` y usa **14 imágenes originales distintas**, diez generadas en esta revisión con las referencias originales aportadas como entrada de estilo. Los 35 planos y las animaciones no se contabilizan como 35 imágenes.

Las imágenes aparecen como recurso principal en 14 planos y combinadas con animación en otros nueve: **46 de los 70 segundos** de esta prueba. Los recortes, desplazamientos, zoom y cambios de color no incrementan el total de originales. `preparar_v2.py` comprueba los catorce archivos y que sus hashes sean diferentes; la hoja de contactos permite comprobar contenido y uso.

Recursos: busto de red neuronal, audiencia en plataformas isométricas, módulo del brief, equipo creativo, tarjetas de guion, revisión con lápiz, sistema de storyboard, micrófono, equipo house y sala de revisión; más las cuatro imágenes de idea, dirección, edición y export de V1. Las nuevas composiciones toman perspectiva, materiales y profundidad de los pines y de Rawpixel, con ámbar, violeta, verde y coral. Los originales de referencia se usan como entrada de estilo, no como metraje del reel.

Prompts y referencias exactas: `assets/prompts-v2.json`. Archivos y procedencia: `assets/procedencia-v2.json`. Se usó la herramienta integrada ImageGen, sin llamadas API separadas. La música y el guion se conservan; la voz y cámara nuevas siguen pendientes.

La entrega revisada queda en `entregas/idea-a-video-v2/De_una_idea_a_un_video_V2_14_IMAGENES.mp4`. V1 se conserva en su carpeta anterior. Para regenerar V2:

```powershell
python content/idea-a-video/preparar_v2.py
node content/idea-a-video/render.mjs --v2 --review
node content/idea-a-video/render.mjs --v2
python content/idea-a-video/ensamblar-preview.py --v2
```

## Primera previsualización — conservada

Producción nueva, de 70 segundos, con el perfil `infinite-process-editorial-v2`. El usuario eligió grabar el guion con su voz real. Esta entrega es una **previsualización instrumental**, pendiente de esa nueva toma; no es el reel final ni está autorizada su publicación.

## Material

- `guion-propuesto.md`: contenido propuesto y dirección. 148 palabras; duración definitiva según la toma.
- `guion-grabacion.txt`: texto limpio para grabar.
- `params.json`: 35 escenas de 2 segundos y tiempos orientativos de palabras. Los subtítulos todavía no están alineados con voz.
- `escena.html`: animaciones editables, gráficos del proceso, transiciones y composición vertical.
- `assets/`: cuatro imágenes nuevas generadas con ImageGen. Prompts, origen y hashes en `prompts.json` y `procedencia.json`.
- `musica.py`: arreglo nuevo a 122 BPM, sintetizado localmente sin samples de terceros ni instrumento de bajo. Conserva bombo corto, órgano percusivo y percusión con swing.
- `produccion.json`: estado de la pieza y tareas pendientes. No se ejecutaron llamadas API a agentes separados para esta previsualización.

La narrativa muestra una idea pasando por brief, enfoque, guion, revisión humana, storyboard, grabación, montaje, música y control final. Los gráficos son ilustrativos; no son capturas de una interfaz comercial ni acreditan generación automática de extremo a extremo.

## Previsualización

Archivo local, fuera de Git:

`entregas/idea-a-video-v1/De_una_idea_a_un_video_PREVISUALIZACION.mp4`

La prueba usa gráficos a pantalla completa porque todavía no está la nueva grabación. La versión con cámara prevé 34 segundos de presencia, aproximadamente el 49%: cámara arriba y visuales abajo, sin marco blanco. La aclaración sobre la decisión humana está prevista con cámara en blanco y negro. No se reutilizó el movimiento de labios de otra narración.

En la carpeta de entrega también quedan el texto para grabar, los subtítulos guía, la música instrumental, una portada identificada como previsualización y el informe `revision.json`. Las métricas técnicas no sustituyen la escucha ni la revisión de sincronía de la futura versión con voz.

## Regeneración local

Con Python, NumPy, FFmpeg, Chrome y Playwright ya disponibles:

```powershell
python content/idea-a-video/preparar.py
node content/idea-a-video/render.mjs --review
node content/idea-a-video/render.mjs
python content/idea-a-video/musica.py --instrumental-only
python content/idea-a-video/ensamblar-preview.py
```

`PLAYWRIGHT_MODULE` y `CHROME_PATH` permiten configurar las rutas del renderizador. Por defecto reutiliza las instalaciones locales de este equipo. `preparar.py` vuelve a generar los tiempos estimados: conservar los ajustes de la toma real en una versión nueva cuando llegue la grabación.

## Para cerrar el reel

Recibir video y audio del micrófono; limpiar errores y repeticiones preservando la voz natural; medir duración; alinear palabras; ajustar escenas; incorporar cámara y aclaración en blanco y negro; mezclar música con ducking; revisar el archivo exportado, lectura móvil, cortes, sincronía y escucha. Grabar con pausas breves entre párrafos y una palmada al principio si cámara y micrófono están separados.
