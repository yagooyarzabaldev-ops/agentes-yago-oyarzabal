# Base de producción aprobada

El 15 de noviembre de 2026 Yago eligió el reel **Sistemas con IA, montaje V10 + Chicago sin bajo 02** como referencia para todos los próximos videos. La aprobación de la música anterior se conserva en `content/construccion/seleccion-audio.json`; la aprobación más amplia está en `production/baseline.json`. El perfil operativo es `config/video-style.json`.

La base identifica un lenguaje audiovisual. Las próximas piezas necesitan ideas, imágenes, acciones y arreglos propios: no repetir el mismo video con otro título.

## Dirección de marca

- Voz real del micrófono, acento propio y tono cercano. Quitar muletillas y errores, sin acelerar la voz ni borrar las pausas que permiten entender.
- Hablar de cambios concretos en sistemas de trabajo con IA. Si aparece una analogía, las imágenes deben llevarla al proceso de negocio.
- Cámara aproximadamente la mitad del tiempo (rango de planificación 40–55%). Cuando aparece: arriba cámara y abajo imágenes/animaciones. En el resto, los visuales desarrollan la idea a pantalla completa.
- Aclaraciones breves pueden llevar blanco y negro y acercamiento. No es una obligación de insertar tres aclaraciones en todos los videos.
- Ámbar, violeta, verde, coral y acentos lima; materiales, luz y profundidad de las referencias. Evitar azul dominante y marco blanco.
- Planos generalmente de 1.5–2.5 segundos, con cambios de escala, objetos y acciones. Combinar animación de elementos, parallax, tipografía y desplazamientos. Cambiar imágenes a menudo no significa cambiar sin relación con la frase.
- House Chicago minimal a 122 BPM, sin línea de bajo ni subgrave sostenido. Bombo corto, órgano percusivo, madera, rim, clap y hats con swing. Voz protagonista; pausas y acentos vinculados al relato.
- Formato de partida 1080×1920, 30 fps, 60–90 segundos. La pieza aprobada dura 67.1 segundos, tiene 35 escenas y cámara en el 48.24% del tiempo.

Los números del perfil son criterios iniciales de producción, no sustituyen las decisiones de Yago ni una revisión perceptual. Cambios explícitos para una pieza se registran con su motivo; no borrar el historial de aprobación.

## Equipo bajo la gerencia

| Responsable | Entrega | Recibe de |
| --- | --- | --- |
| 00 Gerente general | Objetivo, audiencia, idea, evidencia, cierre y asignación | Yago y contexto del proyecto |
| 01 Investigación | Cinco enfoques con fundamento, sin inventar tendencias | Brief del gerente |
| 02 Guionista | Guion o selección de voz real, tres hooks, afirmaciones pendientes | Brief e investigación |
| 12 Referencias | Mapa idea/recurso, referencias, prompts y procedencia | Guion |
| 05 Voz | Plan de limpieza, EDL, tiempos y sincronía | Guion y grabaciones locales |
| 04 Dirección visual | Storyboard cronometrado, layouts, recursos, colores y acciones | Guion, referencias y voz |
| 13 Motion | Animaciones y transiciones por escena | Storyboard |
| 09 Montaje | Timeline, cámara/visuales, subtítulos, proyecto y export | Voz, storyboard y motion |
| 10 Música | Arreglo, stems, ducking, mezcla y mediciones | Narración y montaje |
| 06 Portada/copy | Portadas y textos coherentes con el contenido | Guion y arte |
| 11 Control de calidad | Defectos con timecode, evidencia, revisión pendiente o completada | Planes y luego export real |
| 08 Publicador | Paquete y envío al destino expresamente elegido | MP4 y copy revisados |
| 07 Analista | Cambios concretos basados en métricas aportadas | Resultados reales |

El gerente integra las entregas y devuelve correcciones al responsable. No le pide a Yago coordinar especialistas. Los roles son contratos persistentes: en chat el asistente ejecuta el flujo con las herramientas disponibles; en la CLI las etapas de planificación son llamadas separadas, estructuradas y recuperables. No confundir la lista de roles con agentes de fondo permanentemente activos.

## Cómo empieza el próximo video

Una frase como «Hagamos un reel sobre cómo cambia la atención de una barbería con IA» alcanza para iniciar el brief. El gerente consulta el proyecto y detecta qué material ya existe; si falta algo indispensable, pregunta eso mientras avanza el resto.

1. Definir una idea central y un cambio de proceso reconocible. Reunir evidencia de lo que realmente hace el agente.
2. Si hay grabación, transcribir y localizar frases; proponer selección y cortes conservando el sentido. Si no hay grabación, escribir guion para una toma nueva. No suponer que existe una voz grabada del guion generado.
3. Revisar el contenido de la nueva pieza; la aprobación de estilo ya está resuelta. Registrar la aprobación que exista en la conversación, no volver a pedir lo mismo.
4. Limpiar micrófono y aplicar una EDL común a cámara y voz, con offset medido. Generar subtítulos alineados y revisar palabras completas.
5. Crear storyboard con una acción concreta por escena. Seleccionar o crear recursos distintos, conservar fuente y derechos de uso. Aproximadamente mitad cámara y mitad pantalla completa.
6. Producir motion y montaje. Revisar fotogramas de cada escena y entradas/medios/salidas de transiciones antes del render largo.
7. Crear arreglo musical, escuchar con la voz, ajustar ducking y acentos; medir el master.
8. Renderizar y revisar el MP4 completo. Corregir por timecode. Entregar archivo, subtítulos, portada/copy y reporte.
9. Publicar únicamente ante la instrucción correspondiente; el comando de publicación mantiene la confirmación exacta de archivo/copy/cuenta. Analizar solo métricas reales.

## Contrato y controles del programa

`new` crea formato editorial. `draft` ejecuta gerente → investigación → guion y fija una copia del perfil con SHA256. `produce` ejecuta referencias → voz → dirección visual → motion → montaje → música → copy → revisión del plan. Cada etapa guarda su resultado y puede retomarse.

Dirección visual entrega escenas con start/end, visual_id, idea, visual, layout, palette, motion, animation, transition y aside_reason. El validador exige cobertura sin huecos ni solapes, planos de hasta tres segundos, cámara 40–55%, al menos 80% de identificadores visuales diferentes, ningún recurso consecutivo o más de dos veces, tres colores y cuatro familias de movimiento/transición. Un agente no puede ocultar un recurso repetido cambiándole el ID: el revisor debe contrastarlo con los assets.

El paquete exportado contiene `estilo.json`, `plan-de-escenas.json`, `revision-del-plan.json`, `handoff-produccion.json`, guion y salidas de especialistas. `production_ready` significa **plan preparado**, no MP4 terminado. El handoff deja render y escucha pendientes. La producción audiovisual sigue requiriendo las herramientas de montaje; `attach-video` incorpora el MP4 final para revisar/publicar.

El perfil queda fijado para no cambiar una pieza a mitad del trabajo si cambia la marca. `revise` invalida guion, audio, video y planes derivados, conserva el perfil y rehace el brief con el feedback. Para adoptar una nueva versión global, crear un trabajo nuevo; no mutar una publicación existente.

## Reutilizar la implementación aprobada

- `baseline-params.json`: tiempos, escenas, subtítulos, cámara y recursos de la base; sin rutas de grabaciones personales. Conserva el reloj visual de V10. La música final elegida es la 02 a 122 BPM.
- `content/construccion/escena_v10.html`, `v10-motion.js` y `motion-runtime.js`: plantilla visual y runtime ahora local al repositorio. El runtime se incorporó desde la skill local motion-graphics-reels; no necesita esa ruta del perfil de Windows.
- `scripts/preview-baseline.mjs`: renderiza 35 capturas y comprueba 196 muestras de texto/transiciones desde parámetros versionados. Requiere Node, playwright-core existente y Chrome/Chromium. No instala dependencias ni usa grabaciones.
- `content/construccion/audio_chicago_sin_bajo_02.py`: admite --params, --voice, --picture, --duration, --seed, --work, --output y --instrumental-only. Requiere NumPy y FFmpeg. Un seed cambia texturas de síntesis; un arreglo nuevo requiere también editar composición y patrones según el relato.
- `preparar_v10.py`, `finalizar_v10.py` y versiones anteriores son recetas históricas de esta pieza. Algunas dependen de archivos privados en runtime o rutas del equipo original. No constituyen un generador universal para cualquier guion.
- `content/referencias/diseno-ia/`: enlaces, galería y procedencia de 17 referencias. Descarga de referencia no significa licencia para incorporar esa imagen a un anuncio.

Ejemplo de revisión visual, usando dependencias ya instaladas:

```powershell
node scripts/preview-baseline.mjs --browser "C:/Program Files/Google/Chrome/Application/chrome.exe" --playwright-module "RUTA_ABSOLUTA/package.json"
```

Ejemplo de composición independiente, en carpetas nuevas para conservar la entrega aprobada:

```powershell
python content/construccion/audio_chicago_sin_bajo_02.py --instrumental-only --duration 70 --work runtime/nuevo-house --output entregas/nuevo-house
```

Para mezclar otra pieza, pasar parámetros con su duración y rangos de aclaraciones, además de --voice y --picture. Revisar los timecodes de las muestras de escucha del script si cambia la estructura. Nunca sobrescribir el master aprobado como parte de una prueba.

## Revisión y entrega

La revisión automática comprueba lo que puede medir. No escribir «escuchado», «sincronizado» o «aprobado» sin esa revisión. El informe de cada pieza registra:

- MP4 y SHA256, resolución, duración, fps, codecs y peso.
- EDL, origen de cámara/voz, prueba de sincronía y transcripción.
- Contacto de escenas, transiciones y revisión de textos en móvil.
- Detección de negros/congelados/silencios y justificación de excepciones intencionales.
- LUFS/pico, stems, instrumentos y procedencia; escucha de cortes, voz y música.
- Resultado de la revisión completa y correcciones, con evidencia y pendientes explícitos.

Versionar fuentes, perfiles y contratos. Grabaciones, voz, claves, tokens y exports personales permanecen fuera de Git. No publicar ni enviar mensajes como efecto de completar la producción.
