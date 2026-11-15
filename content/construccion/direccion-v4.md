# V4 — variedad visual por idea

Corrección pedida por Yago: V3 mejoró, pero las imágenes resultaron repetitivas.

## Montaje

Se reemplazó la secuencia de 37 planos por 21 planos con 13 escenas visuales distintas y ocho intervenciones de cámara. Cada escena visual aparece una sola vez. La cámara ocupa 23,90 segundos y los recursos visuales 43,20 segundos; el reel conserva 67,10 segundos.

Las siete imágenes de fondo son diferentes. El cableado y la mesa de V3 se usan una sola vez, en sus momentos correspondientes. Se incorporaron cinco imágenes nuevas: manos compartiendo ideas, un cuaderno de aprendizaje, una base de infraestructura, una pieza que no encaja y un reloj. Las imágenes tienen movimientos de cámara distintos, sin reaparecer como fondo de cierre.

Las otras seis escenas son mecanismos gráficos diferentes: un interruptor, una lista de arranque, una visualización de la edición con la onda del micrófono real, el flujo del agente, la simplificación conceptual de un recorrido y el cierre. No se utilizan la diana, el anillo de aprendizaje ni la placa de interrogación repetida de V3.

Se redujo el texto sobre las imágenes para que el recurso pueda verse. Las ilustraciones están identificadas como creadas con IA. El flujo del agente es una representación visual del proceso documentado en el proyecto; los gráficos no muestran resultados económicos ni clientes reales.

## Audio y sincronización

La narración sigue procediendo exclusivamente del WAV original del micrófono. Se mantiene la limpieza, la música, las pausas y la velocidad de V3. El montaje V4 copia la pista AAC de V3 sin recodificarla. `revision-audio-identico.json` compara el SHA256 de ambas pistas extraídas como ADTS y exige igualdad.

Los subtítulos y los cortes de voz no se modifican. La base de cámara sigue siendo `runtime/construccion-v3/camara.mp4`, con el mismo desfase de 2,3429 segundos respecto del WAV original.

## Imágenes y procedencia

Las cinco imágenes nuevas fueron generadas con la herramienta integrada `image_gen`, sin CLI ni carga de la grabación personal. Se conservaron los originales y se copiaron los recursos al proyecto:

- [Comunidad](assets-v4/comunidad.png)
- [Aprendizaje](assets-v4/aprendizaje.png)
- [Infraestructura](assets-v4/base.png)
- [Encaje](assets-v4/encaje.png)
- [Tiempo](assets-v4/tiempo.png)
- [Prompts completos, método y rutas de origen](assets-v4/procedencia.json)

Las otras dos imágenes y sus prompts se conservan en [assets-v3](assets-v3/procedencia.json).

## Archivos reproducibles

`preparar_v4.py` prepara la secuencia sin alterar V3. `escena_v4.html` genera los movimientos deterministas, `revisar_v4.mjs` revisa texto e imágenes y `finalizar_v4.py` compone la exportación manteniendo la pista de audio. El render se ejecuta con la skill `motion-graphics-reels`, marca `infinite-process`, 30 fps; la verificación final utiliza la skill `editar-reels-Codex`.

La revisión creativa del usuario permanece pendiente. No se publicó el video; V3 se conserva para comparación.

## Verificación de la entrega

El MP4 final pasó la verificación de formato, duración, audio y continuidad: 1080×1920, 30 fps, H.264/AAC, 67,10 s, −14,1 LUFS, −2,0 dBTP, sin negros, congelados ni silencios largos detectados. Se inspeccionaron la hoja de contactos y cuatro fotogramas finales. La revisión de texto pasó 78 momentos y 57 grupos de subtítulos. La pista de audio de V4 es idéntica a V3: ambas tienen SHA256 ADTS `569e944c283550287131590a980f335ba2f82b39445b7b278579096856715086`.
