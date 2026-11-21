# V6 — sistemas con IA, con otra dirección visual

Corrección solicitada por Yago: el video seguía resultando aburrido y demasiado azul. La V6 conserva la historia de cambio de sistemas con IA, el ejemplo del agente de marketing, los cortes de voz y el movimiento de V5. Cambia la dirección visual completa.

## Paleta y materiales

Fondos crema, amarillo, coral, verde claro, rosa y lila alternan según la idea. Los acentos son borgoña, verde oscuro, ciruela y terracota, con texto oscuro sobre las superficies claras. La toma original aparece dentro de un marco de papel con bordes irregulares y cinta. El azul de las interfaces y los degradados oscuros deja de dominar la composición. La luz real de la cámara se conserva.

La escena de trabajo manual muestra papeles y notas sobre una mesa cálida. La escena del flujo conectado usa una miniatura de producción de contenido: idea, guion, revisión y video. La escena del tiempo recupera el temporizador naranja de V4. Las tres imágenes tienen movimiento de cámara y textos animados. Las demás escenas mantienen interfaces, capas y tipografía animadas, con la nueva paleta y textura de papel.

Son 67,10 segundos, 21 planos y 19 transiciones. Los trece planos gráficos aparecen una sola vez. La electricidad permanece como analogía en la grabación, mientras la narración visual sigue mostrando datos, reglas, herramientas y tareas conectadas con IA.

## Audio y sincronización

La pista AAC de V5 se copia sin recodificar. Se mantienen exactamente la voz del micrófono, los recortes de muletillas y falsos arranques, la música a 114 BPM y sus efectos. Se comprueba la igualdad del audio final mediante SHA256 de los bytes AAC demultiplexados.

La cámara sigue el montaje de V3 y mantiene la relación verificada entre originales: tiempo de video = tiempo de micrófono + 2,3429 segundos. Se cambia únicamente el encuadre espacial de la imagen para adaptarlo al marco claro. El teléfono sigue mostrando la toma real correspondiente a ese instante.

## Recursos y reproducción

- [Trabajo manual](assets-v6/manual.png) y [flujo de contenido](assets-v6/flujo.png), creados con la herramienta integrada de generación de imágenes; [prompts y procedencia](assets-v6/procedencia.json).
- [Temporizador cálido reutilizado de V4](assets-v4/tiempo.png).
- `preparar_v6.py`, `crear_tema_v6.py`, `escena_v6.html`, `revisar_v6.mjs` y `finalizar_v6.py`.
- Render de gráficos con `motion-graphics-reels`, marca `infinite-process`, 30 fps y transparencia; composición final H.264/AAC en 1080×1920.

## Revisión

La plantilla pasó la revisión de textos en 120 momentos sin errores ni desbordamientos. Se inspeccionó la hoja de contactos de las 21 escenas y el encuadre compuesto de cámara. La verificación final de la exportación queda registrada junto al MP4. No se publicó el video.


### Resultado de la exportación

El archivo final pasó todos los controles: 1080×1920, 30 fps, H.264/AAC, 67,10 s, −14,1 LUFS y −2,0 dBTP; sin negros, congelados ni silencios largos detectados. Se inspeccionaron la hoja de contactos final, cuatro fotogramas del MP4 y cinco momentos de la transición circular hacia cámara. Los encuadres y textos resultaron legibles en las muestras inspeccionadas.

La pista AAC es idéntica a la de V5, sin recodificación: SHA256 `1555eba3996d6b2061e9110334ecf224de8502bbbe5fe09e7fc60f0f839dc4bb`. No se hizo una nueva valoración subjetiva de escucha; la pista anterior se conserva exactamente.
