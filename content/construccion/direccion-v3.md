# V3 — IA, sin tantas vueltas

Revisión solicitada por Yago: mantener la base de V2, bajar la formalidad, mejorar el atractivo de las imágenes, quitar las «yyy» y los arranques repetidos, y usar música más entretenida.

## Cambios editoriales

- 67,10 segundos, 37 planos. 34,77 segundos de cámara y 32,33 segundos de recursos visuales. Se conserva la velocidad original de la voz.
- Textos más cortos, tipografía grande, acentos lima/cobalto/naranja y recursos visuales concretos en lugar de pantallas de código y placas técnicas.
- Dos imágenes ilustrativas creadas con la herramienta integrada `image_gen`: el enchufe con la red de cables detrás de la pared, y una mesa de trabajo que transforma una idea en una pieza terminada. Se animan con reencuadres; no se presentan como instalaciones ni ejecuciones reales.
- Fuentes guardadas en [electricidad.png](assets-v3/electricidad.png) y [mesa.png](assets-v3/mesa.png). [Prompts completos y procedencia](assets-v3/procedencia.json). Los originales generados también se conservan en la carpeta de imágenes de Codex.
- El ejemplo del agente mantiene la idea → guion → video y la revisión humana, con una presentación gráfica más breve.

## Limpieza de voz

La única fuente hablada sigue siendo `C:/Users/oyarz/Desktop/IA Experiencia.wav`. No se emplea el audio de cámara, ni clonación, ni voz sintética.

La nueva revisión de fragmentos cortos encontró repeticiones que la primera transcripción completa había absorbido dentro de una sola palabra. La edición incluye:

- Repeticiones de «y» entre 77,18 y 78,70 s, antes de «teclas»; queda una conjunción breve.
- La vacilación previa a la toma clara de «implementar», entre 49,59 y 51,13 s.
- El arranque «de la primera…», entre 66,80 y 67,65 s; se conserva «desde el primer momento».
- La vacilación antes de «agregar», entre 91,00 y 92,20 s.
- Se conservan las palabras completas de las frases válidas; la limpieza se concentra en las vacilaciones y los intentos repetidos.
- Pausas largas reducidas con unos 180 ms de respiración total conservada.

Los tiempos se refieren al WAV original. La lista exacta de cortes está en `runtime/construccion-v3/edl.json`. Imagen y micrófono conservan la misma correspondencia temporal, con el desfase verificado de 2,3429 s.

## Música

Nueva composición original con bajo sincopado, piano eléctrico, batería, palmas y percusión a 114 BPM. La música objetivo antes de la mezcla pasa de −31 a −26,5 LUFS; la atenuación durante la voz conserva su protagonismo. El volumen final se comprueba después de codificar AAC.

## Fuentes reproducibles

`preparar_v3.py`, `montar_v3.py`, `escena_v3.html`, `musica_v3.py` y `finalizar_v3.py`. La revisión de cajas de texto se ejecuta con `node content/construccion/revisar.mjs --v3`.

V2 se conserva. V3 queda para revisión creativa del usuario; no se publica automáticamente.
