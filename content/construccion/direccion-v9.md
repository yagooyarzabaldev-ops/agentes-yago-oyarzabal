# V9 — cámara la mitad del tiempo, visuales dinámicos y minimal house

Yago pidió más movimiento, cambios más frecuentes, transiciones más dinámicas y música un poco más minimal. También indicó que su cara debía aparecer solo la mitad del tiempo, para desarrollar la idea con imágenes. V9 alterna **32,67 segundos con cámara** y **34,43 segundos de visuales a pantalla completa**, incluido el cierre. La cámara ocupa el 48,68 % de los 67,1 segundos totales.

## Ritmo y animación

La narración tiene **30 planos visuales**, frente a 14 en V8: cambian cada **2,18 segundos en promedio**, con duraciones entre 1,33 y 3,07 segundos. Se añade el cierre de 1,8 segundos, para un total de 31 planos y 67,1 segundos. Hay 29 transiciones entre los planos de la narración.

Se reutilizan las nueve imágenes de V8 y se intercalan los gráficos técnicos con encuadres distintos. Los movimientos de cámara incluyen acercamiento, alejamiento, desplazamiento lateral, elevación y giro suave. Cada nueva aparición cambia el encuadre y el movimiento; no se generaron nuevas imágenes. Las imágenes siguen siendo ilustraciones estáticas animadas mediante composición, con reflejos y puntos luminosos independientes.

Las transiciones duran aproximadamente 0,3 segundos y alternan barrido lateral con desenfoque, acercamiento, diagonal, bandas, apertura circular y desplazamiento vertical con giro. Actúan sobre la zona visual: mitad inferior cuando aparece Yago, pantalla completa en los demás tramos. Los títulos siguen los capítulos de la explicación y permanecen sobre los cambios de imágenes, lo que permite acelerar el montaje sin acortar su lectura. Los subtítulos se ubican junto a la división durante la cámara y en la parte inferior durante los visuales completos.

El cierre también se anima: luces cálidas y violetas se desplazan por el fondo, dos órbitas giran y la frase final asciende suavemente mientras se dibuja la línea de cierre.

La toma de cámara se copia de V8 sin modificar el archivo, los cortes, el encuadre ni la velocidad. Se muestra en siete bloques; en los demás, los gráficos la cubren completamente. Los tramos de infraestructura, contexto del negocio y tareas conectadas ocupan toda la pantalla. La voz limpia sigue coincidiendo con V3 por SHA256. Se conserva la sincronización entre originales: tiempo de cámara = tiempo de micrófono + 2,3429 segundos.

## Música más minimal

Se mantiene el tempo de 120 BPM y el bombo regular. El nuevo arreglo elimina pads, progresión de acordes y palmas; reduce el bajo de seis a tres notas por compás y los hi-hats de doce a cuatro golpes. Quedan golpes secos y un acento breve de dos notas cada cuatro compases. Los efectos de transición se usan solo en una de cada cuatro transiciones.

La base se normaliza a −28 LUFS antes de la reducción automática durante la voz, un decibelio por debajo de V8. Se vuelve a mezclar con la voz del micrófono y se normaliza el máster a −14 LUFS. La música es original, sintetizada localmente y sin grabaciones de terceros.

## Archivos y reproducción

- [Inventario de planos y movimientos](../../entregas/construccion-v9/revision-variedad.json).
- [Procedencia de imágenes reutilizadas](assets-v8/procedencia.json), con enlaces a los prompts y referencias originales.
- [Audio y arreglo](../../entregas/construccion-v9/audio-procedencia.json).
- [Comprobación de cámara idéntica](../../entregas/construccion-v9/revision-camara-identica.json).
- [Duración y visibilidad de la cámara](../../entregas/construccion-v9/revision-visibilidad.json).
- [Comprobación de voz conservada](../../entregas/construccion-v9/revision-voz-identica.json).

Para reproducir: ejecutar `preparar_v9.py`, `crear_tema_v9.py`, `audio_v9.py` y `revisar_v9.mjs`; renderizar `escena_v9.html` con `render_mg.mjs`, los parámetros de `runtime/construccion-v9/params.json`, 30 fps y tres workers; ejecutar `finalizar_v9.py`, la verificación de reels y `revisar_exportacion_v9.py`. La plantilla reutiliza las funciones de V8 y las sustituye con `v9-motion.js`.

## Revisión

La revisión de la plantilla final pasó 179 momentos sin errores de JavaScript ni desbordamientos de texto. La comprobación de transparencia en 31 muestras confirmó que la cámara queda cubierta durante los visuales completos y visible en los bloques previstos. Se inspeccionaron los 31 planos del MP4, cuatro fotogramas completos y tres secuencias de transiciones. El cierre se ajustó para mantener el movimiento hasta el final.

El MP4 final dura 67,10 segundos, ocupa 42.177.349 bytes y está exportado en 1080×1920, 30 fps, H.264 y AAC. La verificación completa pasó: −14,1 LUFS, pico verdadero −2,1 dBTP, sin negros, congelados mayores a 1,5 segundos ni silencios mayores a 1,2 segundos. El audio fue medido técnicamente; no se realizó una escucha subjetiva. Los informes quedan junto al MP4. No se publica automáticamente.
