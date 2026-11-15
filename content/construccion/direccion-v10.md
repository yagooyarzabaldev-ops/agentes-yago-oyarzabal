> Base aprobada el 15/11/2026: V10 con Chicago sin bajo 02 (122 BPM). El estándar vigente para próximas piezas está en [Estilo y flujo](../../production/ESTILO-Y-FLUJO.md); las mezclas anteriores se conservan como historia. La aprobación de estilo no implica publicación.

# V10 — variedad visual, aclaraciones en blanco y negro y música ligada al montaje

Yago pidió apariciones puntuales en blanco y negro cuando hace una aclaración, más imágenes y animaciones, transiciones menos repetitivas y una música que acompañe la explicación. La narración conserva la voz limpia original del micrófono, sus cortes y su velocidad.

## Cámara y aclaraciones

La cámara aparece 32,37 segundos de un total de 67,10: el 48,24 %. Se mantiene arriba con visuales abajo. En los demás tramos, las imágenes y animaciones ocupan la pantalla completa.

Hay tres intervenciones de cámara en blanco y negro: 18,50–21,20 s, 37,50–39,73 s y 47,80–48,73 s. Se vinculan con las frases sobre creer saber, las limitaciones de implementación y «sería lo ideal». La cámara tiene un acercamiento del 8 % aproximadamente y un contraste moderado en esas apariciones. El rótulo «OJO CON ESTO.» y un tratamiento monocromático del apoyo visual señalan el cambio de tono.

La cámara mantiene la sincronización original: tiempo del video fuente = tiempo del micrófono + 2,3429 segundos. El audio de cámara no se utiliza.

## Imágenes y animación

Se generan doce imágenes originales con la herramienta integrada `image_gen`, guardadas en [assets-v10](assets-v10/procedencia.json). La procedencia incluye cada prompt, archivo original, copia local y SHA256. Se observó la biblioteca de referencias del usuario y se aplicó su lenguaje de macros técnicos, cristales, conexiones luminosas y composición espacial, con ámbar, violeta, verde y coral.

Los temas nuevos son tareas aisladas, arquitectura del sistema, conocimiento compartido, aprendizaje práctico, bases técnicas, paso de idea a implementación, adaptación al negocio, bloqueos, producción audiovisual, revisión, automatización y tiempo recuperado. Cada imagen aparece una sola vez. Solo se reutilizan dos imágenes anteriores, también una vez cada una: figura neuronal e infraestructura.

Hay 35 escenas sin repetir identificadores: 14 planos de imagen y 21 escenas gráficas, incluido el cierre. Los planos durante la narración duran 1,92 segundos en promedio. Los gráficos muestran conexiones que se dibujan, paquetes que avanzan, una red giratoria, módulos que se apilan y encajan, pruebas, revisiones y ciclos de trabajo. Las imágenes raster se animan con desplazamiento, acercamiento y giro de cámara, además de capas de luz; no se presentan como videos generados de personas en movimiento.

Las transiciones combinan cortes directos, apertura elíptica, paneles que giran, acercamiento por correspondencia, disolución en partículas, ranuras y revelado por trazado. Las aclaraciones entran con un corte directo. Los movimientos no introducen pantallas blancas ni destellos de fotograma completo.

## Música y diseño sonoro

La nueva base original mantiene 120 BPM y una instrumentación contenida, con bajo sincopado, percusión desplazada para dar swing, palmas secas, acentos armónicos breves y ecos. El arreglo cambia por secciones y suma pequeños remates de frase. No se usaron grabaciones de terceros.

La percusión baja durante las tres aclaraciones, con un retorno marcado al terminar. Trece cambios visuales principales tienen acentos sonoros programados en su mismo instante; las transiciones de paneles, partículas y ranuras añaden clics breves. La base se normaliza a −24,5 LUFS antes de la reducción automática bajo la voz, frente a −28 LUFS en V9.

El máster apunta a −14 LUFS con margen de pico para AAC. La revisión de audio es técnica; no se realizó una escucha subjetiva.

## Reproducción y revisión

Ejecutar `preparar_v10.py`, `crear_tema_v10.py`, `audio_v10.py` y `revisar_v10.mjs`; renderizar `escena_v10.html` con `render_mg.mjs`, los parámetros de `runtime/construccion-v10/params.json`, 30 fps y tres workers; ejecutar `finalizar_v10.py`, la verificación de reels y `revisar_exportacion_v10.py`.

La revisión de plantilla comprobó 196 momentos sin errores de JavaScript ni desbordamientos de títulos y subtítulos. Se inspeccionaron los 35 planos del MP4 final, seis fotogramas completos y tres secuencias de transición. La medición de los píxeles confirmó las tres apariciones monocromáticas y el color del plano de control. La cámara queda cubierta en los visuales completos según las 35 muestras de transparencia.

El archivo final ocupa 43.771.767 bytes y pasó la verificación: 1080×1920, 30 fps, H.264/AAC, duración de 67,10 segundos, sonoridad de −14,1 LUFS y pico verdadero de −0,5 dBTP. No se detectaron negros, congelados mayores a 1,5 segundos ni silencios mayores a 1,2 segundos. Los resultados se guardan junto al MP4. El video no se publicó.
