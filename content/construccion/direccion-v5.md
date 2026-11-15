# V5 — cambiar sistemas con IA

Dirección final solicitada por Yago: una versión más innovadora, con más transiciones y animaciones. La analogía eléctrica permanece en su voz, pero las imágenes deben explicar la transformación de sistemas con IA.

## Decisiones editoriales

La secuencia reemplaza enchufes, cables y escenas de electricidad por una transformación visual de software y procesos. Cambiar la apariencia de una pantalla da paso a revelar datos, agente, revisión y tareas conectadas. Después, archivos dispersos se integran en un flujo de marketing: brief → guion → revisión humana → video.

Se mantienen 67,10 segundos y 21 planos. Hay 13 escenas gráficas distintas, cada una aparece una sola vez. Las pantallas son representaciones animadas, identificadas como tales, no capturas de ejecución en vivo. El flujo sigue el README del proyecto; ninguna escena representa una publicación automática.

## Movimiento

- 19 transiciones adicionales: apertura por mitades, apertura circular, bandas deslizantes, giro de página y desplazamiento vertical. El paso de la interfaz al sistema también tiene su propia separación animada de capas.
- Tipografía sincronizada, cursor animado, controles que cambian, texto que se escribe, tarjetas que entran desde distintas posiciones y capas de infraestructura en perspectiva.
- Un guion se retira para revelar un teléfono que contiene la toma original de Yago, sincronizada con el micrófono. El plano conserva el instante correspondiente de la cámara; no usa otra toma de la boca ni voz sintética.
- La secuencia muestra conexión y revisión del agente, y finalmente reúne etapas dispersas en un único panel.
- Los subtítulos conservan su texto y sus tiempos, con un pequeño énfasis animado en la palabra activa.

## Audio

La pista de narración limpia de V3 se copia sin modificar; `revision-voz-identica.json` verifica la igualdad por SHA256. Se conserva la velocidad original y el desfase de 2,3429 s respecto de la cámara. La voz procede exclusivamente de `C:/Users/oyarz/Desktop/IA Experiencia.wav`.

La música original a 114 BPM se vuelve a generar sin los efectos de V3. Se incorporan tres cortes breves de la base musical y 19 efectos puntuales sintetizados localmente: clics, papel, pasos de transición, envío y cierre. La música se atenúa bajo la voz. Se normaliza la mezcla a −14 LUFS con margen de pico antes de codificar AAC.

## Recursos

Solo se usa una nueva imagen rasterizada: [reloj de arena](assets-v5/tiempo.png), como metáfora del objetivo de recuperar tiempo. Fue creada con la herramienta integrada `image_gen`. [Prompt completo y procedencia](assets-v5/procedencia.json).

Dos exploraciones visuales anteriores a la corrección de enfoque se conservan en esa carpeta, marcadas `used_in_v5: false`; no aparecen en la entrega. Los demás recursos se construyen y animan mediante Canvas, sin nuevas imágenes de electricidad.

## Archivos reproducibles

`preparar_v5.py`, `escena_v5.html`, `audio_v5.py`, `revisar_v5.mjs` y `finalizar_v5.py`. Render con `motion-graphics-reels`, marca `infinite-process`, ProRes con transparencia a 30 fps; composición final H.264/AAC en 1080×1920. V4 permanece disponible.

La revisión creativa de Yago queda pendiente. No se publicó el video.

## Verificación de la entrega

El MP4 final pasó los controles de resolución, relación de aspecto, fps, códecs, duración, sonoridad, picos y continuidad: 1080×1920, 30 fps, H.264/AAC, 67,10 s, −14,1 LUFS y −2,0 dBTP. No se detectaron negros, congelados ni silencios largos. La revisión de texto cubrió 120 momentos sin errores. Se inspeccionaron fotogramas finales, la hoja de contactos y una secuencia de cinco fotogramas consecutivos de la transición circular hacia cámara.

La igualdad SHA256 de la pista de narración limpia se conserva (`6f8eb03561736aae477c7bfbdc00e6558f0a0de8c5c2596ec2a184861f8678a6`). La mezcla final cambia por la música y los efectos nuevos. Las métricas técnicas y las inspecciones no sustituyen la valoración creativa y la escucha del usuario.
