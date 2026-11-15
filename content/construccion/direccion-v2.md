# V2 — IA: de la idea a la práctica

El usuario aportó su grabación y eligió alternar cámara con gráficos. Confirmó expresamente usar el audio del micrófono y enfocar el reel en su experiencia y su enfoque de la IA, con el agente de marketing como ejemplo visual.

## Fuentes

- Imagen: `D:/PRODUCCION VIDEO/VID_20261114_190637138.mp4`.
- Única fuente de narración del montaje final: `C:/Users/oyarz/Desktop/IA Experiencia.wav`.
- El audio de la cámara se usa solo para calcular sincronización. No se mezcla en la entrega.
- La voz es original, sin clonación, síntesis ni cambio de velocidad.
- Transcripción local con un modelo ya instalado. No se subió el material a un servicio externo.

## Edición

74,53 segundos, 1080×1920 y 30 fps. La edición tiene 26 planos; aproximadamente 41,57 segundos son de cámara y 32,97 de gráficos. La comparación del enchufe y el cableado se adelanta como gancho. Después siguen la presentación, el aprendizaje, la infraestructura, la dificultad de implementar una idea y el objetivo de resolver necesidades concretas.

Se quitan muletillas, una explicación redundante y parte de las pausas largas. En las pausas comprimidas se conservan unos 280 ms para que la dicción respire. Los cortes y correspondencias al original quedan en `runtime/construccion-v2/edl.json`. Los originales no se modifican.

El desfase cámara-micrófono se calculó por correlación y se comprobó en cinco ventanas entre los segundos 8 y 102. El promedio fue 2,3429 s y la variación máxima entre ventanas fue 3,75 ms. La relación usada es `tiempo de cámara = tiempo del WAV + 2,3429 s`.

Las escenas del enchufe y del cableado son analogías gráficas. Las escenas Python/SQLite/FFmpeg, flujo de producción y código se basan en los archivos reales del proyecto. Los gráficos no representan una publicación en directo ni resultados comerciales. Los dos fragmentos de código de la escena de guardado omiten instrucciones intermedias y se identifican como fragmentos.

La música y los efectos son síntesis local original con semilla fija. La música se atenúa bajo la voz. La mezcla se normaliza con medición posterior del archivo AAC exportado.

## Reproducción

1. `python content/construccion/preparar_v2.py`
2. `python content/construccion/montar_v2.py`
3. Renderizar `escena_v2.html` con `render_mg.mjs --marca infinite-process --params-file runtime/construccion-v2/params.json --fps 30 --out runtime/construccion-v2/graficos.mov`.
4. `python content/construccion/finalizar_v2.py`
5. `python <skill-editar-reels>/scripts/reel.py verify --dir runtime/construccion-v2`

Las fuentes audiovisuales, alineación y renders se conservan en rutas excluidas de Git. La V1 con voz sintética queda como prototipo anterior y no es la entrega de esta revisión. La aprobación creativa del usuario y cualquier publicación son posteriores a la entrega.
