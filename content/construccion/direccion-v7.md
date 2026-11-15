# V7 — sistemas con IA, profundidad y referencias visuales

Esta edición responde a la solicitud de usar los estilos de los enlaces enviados por Yago, ampliar las tres imágenes iniciales y sumar profundidad y animaciones sin volver a una paleta dominada por azul. El montaje mantiene 67,10 segundos, 21 planos y la grabación original. Se eligieron ocho ilustraciones originales y cinco secuencias gráficas diferentes; cada escena gráfica aparece una sola vez.

## Correspondencia con las referencias

Las [referencias locales](../referencias/diseno-ia/README.md) se usaron para composición, iluminación y materiales. Se conservaron sus rasgos técnicos y espaciales, adaptando los colores y el contenido al cambio de sistemas con IA.

| Referencia | Aplicación en V7 |
| --- | --- |
| [Busto de conexiones, pin 1128433250395037066](https://ar.pinterest.com/pin/1128433250395037066/) | Perfil de filamentos ámbar sobre ciruela; representa el sistema conectado. |
| [Cerebro holográfico, pin 1057008975072047609](https://ar.pinterest.com/pin/1057008975072047609/) | Holograma violeta y magenta sobre una plataforma con datos y herramientas. |
| [Equipo isométrico, pin 1035898351811759640](https://ar.pinterest.com/pin/1035898351811759640/) | Equipo de producción con luz verde esmeralda y ámbar, revisión humana y recorrido entre etapas. |
| [Pantalla macro, pin 944770828097507675](https://ar.pinterest.com/pin/944770828097507675/) | Pantalla oblicua con flujo de trabajo coral y lima, profundidad de campo y puntos luminosos. |
| [Chip de Rawpixel 17121933](https://www.rawpixel.com/video/17121933) | Circuitería de grafito con iluminación ámbar, cámara macro y procesador IA. Se tomó como referencia el póster disponible; no se incorporó el video premium. |
| [Búsqueda de diseño Claude Code](https://ar.pinterest.com/search/pins/?q=claude%20code%20design) y muestra local `search-05.jpg` | Tarjetas negras y crema sobre naranja, geometría, perspectiva y tipografía grande. |

Las ocho imágenes elegidas son `neural`, `manual_ref`, `chip_ref`, `hub_ref`, `launch`, `studio_ref`, `flow_ref` y `time`. Los [prompts completos y archivos de procedencia](assets-v7/procedencia.json) identifican cada recurso y sus referencias. Las propuestas descartadas quedan marcadas con `used_in_v7: false`.

## Movimiento y narrativa

Las tarjetas giran mediante proyección en perspectiva; los recorridos de luz, órbitas y puntos de datos se animan de forma independiente. Las ilustraciones tienen movimiento de cámara y elementos gráficos superpuestos. Son imágenes estáticas animadas mediante composición, no clips de personajes generados en movimiento.

Las 19 transiciones alternan acercamientos, barridos diagonales, apertura circular, bandas y giro de página. La cámara original aparece en ocho planos y dentro del teléfono. Los fondos alternan naranja, crema, carbón, violeta, esmeralda, ámbar y coral. Se conserva la iluminación real de la toma.

La analogía eléctrica permanece en la voz; la imagen muestra cambios de sistemas con IA: conexión entre datos, reglas y herramientas, adaptación al negocio, revisión y producción de contenido. No se atribuyen cifras de ahorro ni resultados comerciales a las escenas ilustrativas.

## Audio y sincronización

La pista AAC se copia de V6 sin recodificar. Mantiene la voz del micrófono, los recortes de muletillas y falsos arranques de V3, la música a 114 BPM y los efectos. La sincronización conserva la relación entre fuentes: tiempo de video = tiempo de micrófono + 2,3429 segundos. No se cambia la velocidad de la voz.

## Reproducción local

1. Ejecutar `python -X utf8 content/construccion/preparar_v7.py`.
2. Ejecutar `python -X utf8 content/construccion/crear_tema_v7.py` y `node content/construccion/revisar_v7.mjs`.
3. Renderizar `escena_v7.html` con `render_mg.mjs`, los parámetros de `runtime/construccion-v7/params.json`, 30 fps y tres workers, a `runtime/construccion-v7/graficos.mov`.
4. Ejecutar `python -X utf8 content/construccion/finalizar_v7.py`.
5. Ejecutar la verificación de reels sobre `runtime/construccion-v7` y `python -X utf8 content/construccion/revisar_exportacion_v7.py`.

Los scripts usan la cámara montada en V3 y el audio final de V6. Requieren las dependencias de edición y motion graphics ya instaladas en este equipo. La plantilla conserva las utilidades de V6 y sustituye sus escenas con `v7-motion.js`.

## Revisión

La revisión previa de la plantilla pasó 120 muestras sin errores de JavaScript ni desbordamientos de texto. Se inspeccionaron las 21 escenas y el encuadre compuesto de cámara. Sobre la exportación final se revisaron la hoja de contactos, cuatro fotogramas a tamaño completo y cinco momentos de la transición por bandas hacia cámara. Los textos y encuadres resultaron legibles en esas muestras.

La [verificación técnica final](../../entregas/construccion-v7/Sistemas_con_IA_Yago_v7_verificacion.json) pasó todos los controles: 1080×1920, 30 fps, H.264/AAC, 67,10 s, −14,1 LUFS y −2,0 dBTP; sin negros, congelados ni silencios largos detectados. Tamaño: 25.655.399 bytes.

La [comparación de audio](../../entregas/construccion-v7/revision-audio-identico.json) confirmó igualdad exacta con V6: SHA256 de AAC ADTS `1555eba3996d6b2061e9110334ecf224de8502bbbe5fe09e7fc60f0f839dc4bb`. No se hizo una nueva valoración subjetiva de escucha. No se publicó el video; la valoración creativa de Yago queda pendiente.
