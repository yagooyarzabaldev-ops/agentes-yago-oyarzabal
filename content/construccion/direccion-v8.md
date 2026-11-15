# V8 — cámara arriba, visuales abajo y house sutil

Yago pidió reemplazar el marco blanco y las tarjetas geométricas de V7 por una pantalla dividida arriba y abajo, manteniendo las escenas de IA. Durante la edición agregó una base musical un poco más house, de forma sutil. V8 aplica ambas correcciones.

## Composición

Durante la narración, la toma real ocupa la mitad superior completa (1080×960); la mitad inferior muestra nueve imágenes distintas y cinco secuencias técnicas animadas. El cierre ocupa toda la pantalla durante los últimos 1,8 segundos. No se usan marcos blancos, fondos de papel, tarjetas geométricas flotantes ni el teléfono simulado de V7.

Las imágenes técnicas conservadas son el busto de conexiones, el procesador, el equipo isométrico, el cerebro holográfico y el flujo de trabajo de V7. Se suman tres imágenes nuevas de desarrollo, infraestructura y producción de video, más el reloj de arena de V5. Las nueve imágenes aparecen una vez cada una. Los gráficos propios muestran conexiones, aprendizaje iterativo, un brief, una prueba y el flujo de producción. Hay 15 escenas inferiores contando el cierre y 13 transiciones durante la narración.

Los subtítulos se ubican cerca de la división central, sobre un degradado oscuro. La tipografía y las líneas de luz alternan ámbar, violeta, coral, verde y lima. Las imágenes tienen movimientos de cámara; las conexiones y los gráficos se animan de forma independiente. Se trata de ilustraciones animadas mediante composición, no de video generado de personas en movimiento.

## Referencias e imágenes

Las [referencias de Pinterest y Rawpixel](../referencias/diseno-ia/README.md) siguen guiando el detalle macro, la iluminación técnica, el contraste y la profundidad. Se mantuvo el estilo de IA que Yago indicó que le gustaba.

- [Prompts completos y procedencia de las tres imágenes nuevas](assets-v8/procedencia.json), creadas con la herramienta integrada `image_gen` y guardadas en `assets-v8/`.
- [Procedencia de las cinco imágenes de V7](assets-v7/procedencia.json).
- [Procedencia del reloj de arena de V5](assets-v5/procedencia.json).
- [Inventario del montaje](../../entregas/construccion-v8/revision-variedad.json).

## Cámara y voz

La cámara se vuelve a encuadrar desde el video original a 1080×960, usando exactamente los 36 cortes y los tiempos de `runtime/construccion-v3/edl.json`. El recorte original es 1944×1728 en x=728, y=0: da más ancho que el encuadre de V7 y llena la mitad superior. Se mantiene el desfase verificado de 2,3429 segundos entre cámara y micrófono.

La voz limpia de V3 se conserva, incluidos los cortes de repeticiones y falsos arranques. Su archivo coincide por SHA256 con el original del montaje: `6f8eb03561736aae477c7bfbdc00e6558f0a0de8c5c2596ec2a184861f8678a6`. No se acelera, clona ni sintetiza la voz. La mezcla final cambia por la nueva música.

## House sutil

Base original sintetizada a 120 BPM: bombo en los cuatro pulsos, hi-hat a contratiempo, bajo suave, acordes cálidos de novena y pads discretos. Tiene cambios de arreglo cada cuatro compases y una bajada de densidad en la parte central. No usa grabaciones musicales de terceros.

La música se normaliza a −27 LUFS antes de reducirse automáticamente durante la voz. La reducción usa ataque de 12 ms y recuperación de 220 ms. Los efectos son barridos breves y bajos en las transiciones. El máster apunta a −14 LUFS y limita los picos; la valoración auditiva y creativa de Yago queda pendiente.

## Reproducción

1. `python -X utf8 content/construccion/preparar_v8.py`
2. `python -X utf8 content/construccion/camara_v8.py`
3. `python -X utf8 content/construccion/audio_v8.py`
4. `node content/construccion/revisar_v8.mjs`
5. Renderizar `escena_v8.html` con `render_mg.mjs`, parámetros de `runtime/construccion-v8/params.json`, 30 fps, tres workers y salida `runtime/construccion-v8/graficos.mov`.
6. `python -X utf8 content/construccion/finalizar_v8.py`
7. Ejecutar `reel.py verify --dir runtime/construccion-v8` y `python -X utf8 content/construccion/revisar_exportacion_v8.py`.

La revisión previa de la plantilla pasó 102 momentos sin errores de JavaScript ni desbordamientos de texto. Se corrigió la cercanía entre una etiqueta y el usuario, y se eliminó el texto residual del cierre antes del render definitivo.

La exportación pasó todos los [controles técnicos](../../entregas/construccion-v8/Sistemas_con_IA_Yago_v8_verificacion.json): 1080×1920, 30 fps, H.264/AAC, 67,10 s, −14,1 LUFS y −1,9 dBTP; sin negros, congelados ni silencios largos detectados. Tamaño: 34.156.526 bytes.

Se inspeccionaron la hoja de contactos final de las 15 escenas, cuatro fotogramas completos y cinco momentos de la transición inferior entre código y busto de conexiones. La cámara se mantiene en la mitad superior, los textos son legibles en esas muestras y no aparece el marco blanco anterior. La revisión de audio fue técnica; no se hizo una escucha subjetiva de la nueva mezcla. No se publicó el video.
