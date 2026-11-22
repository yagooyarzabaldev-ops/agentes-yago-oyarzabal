# Base de producción aprobada

El 15 de noviembre de 2026 Yago eligió el reel **Sistemas con IA, montaje V10 + Chicago sin bajo 02** como referencia para todos los próximos videos. La aprobación de la música anterior se conserva en `content/construccion/seleccion-audio.json`; la aprobación más amplia está en `production/baseline.json`. El perfil operativo es `config/video-style.json`.

La base identifica un lenguaje audiovisual. Las próximas piezas necesitan ideas, imágenes y acciones propias: no repetir el mismo video con otro título.

**Actualización musical del 21/11/2026 — perfil v4:** Yago seleccionó su track «Yago Oyarzabal - chatgpt» para usarlo siempre desde el principio hasta la duración del video, con sidechain suave mientras habla. Reemplaza las selecciones musicales anteriores como default. La fuente dura aproximadamente 2:05; la copia privada está en `content/material/music/yago-chatgpt.mp3`, con procedencia en `production/music-default.json`. Conservar velocidad, timbre y estructura; no crear otro arreglo, buscar otra entrada ni hacer loop. Si falta o no alcanza, informar el límite antes de mezclar. La autoría y autorización fueron declaradas por Yago. Se conservan la base visual, las duraciones editoriales y las aprobaciones históricas.

Música entrega el fragmento desde cero, el stem con ducking, el master y una envolvente verificable de reducción y recuperación. Montaje copia el video en revisiones exclusivamente musicales y Calidad contrasta fuente, inicio, duración y ganancia, además del AAC final. La escucha y la medición son comprobaciones diferentes. La herramienta `scripts/musica_opciones/usar_track.py` puede usar directamente el track del perfil.

## Dirección de marca

- Voz real del micrófono, acento propio y tono cercano. Quitar muletillas y errores, sin acelerar la voz ni borrar las pausas que permiten entender.
- Hablar de cambios concretos en sistemas de trabajo con IA. Si aparece una analogía, las imágenes deben llevarla al proceso de negocio.
- Cámara aproximadamente la mitad del tiempo (rango de planificación 40–55%). Cuando aparece: arriba cámara y abajo imágenes/animaciones. En el resto, los visuales desarrollan la idea a pantalla completa.
- Aclaraciones breves pueden llevar blanco y negro y acercamiento. No es una obligación de insertar tres aclaraciones en todos los videos.
- Ámbar, violeta, verde, coral y acentos lima; materiales, luz y profundidad de las referencias. Evitar azul dominante y marco blanco.
- Mínimo 10 imágenes de origen distintas por video (corrección de Yago, perfil v3). Motion nativo, tipografía, crops, zoom, reencuadres y variantes de color no suman originales. Guiar composición y materiales por las referencias aportadas; cada imagen desarrolla una idea del relato.
- Planos generalmente de 1.5–2.5 segundos, con cambios de escala, objetos y acciones. Combinar animación de elementos, parallax, tipografía y desplazamientos. Cambiar imágenes a menudo no significa cambiar sin relación con la frase.
- Track propio de Yago desde cero, recortado a la duración del video. Voz protagonista, música atenuada suavemente por sidechain durante el habla y recuperación en pausas; conservar el sonido y tempo originales.
- Formato de partida 1080×1920, 30 fps, **60–75 segundos para Reels y Shorts**. La pieza aprobada dura 67.1 segundos, tiene 35 escenas y cámara en el 48.24% del tiempo.

Los números del perfil son criterios iniciales de producción, no sustituyen las decisiones de Yago ni una revisión perceptual. Cambios explícitos para una pieza se registran con su motivo; no borrar el historial de aprobación.

## Duración según el contenido — perfil v2

Yago pidió usar 60–75 segundos como base para las próximas piezas y que los agentes ajusten según el contenido. Gerencia propone la duración; guion la concreta y registra `duration_reason` fuera de la base. El ajuste editorial ya está autorizado: se presenta junto con el guion, sin una consulta adicional de estilo.

Como orientación: 20–35s para un consejo o idea puntual; 40–60s para un problema y solución; 60–90s para desarrollar un cambio de sistema; 90–180s para un tutorial o caso cuyos pasos lo necesiten. Estos rangos no son cuotas ni garantías de rendimiento. Priorizar claridad y ritmo, sin relleno ni voz acelerada. El margen técnico del programa es 20–180s; la base habitual sigue siendo 60–75s.

Dirección visual y motion ajustan la cantidad de escenas; montaje conserva pausas útiles y palabras completas; música crea un cierre para la duración elegida; calidad comprueba que el motivo y el resultado sean coherentes. Un cambio de duración que altera el guion se revisa como nueva versión del contenido.

El video base y la etiqueta `video-base-v1` conservan su aprobación histórica. El perfil vigente v4 conserva esta política de duración y el mínimo de imágenes incorporado en v3; los trabajos existentes mantienen su perfil y duración anteriores.

## Cantidad de imágenes — perfil v3

Yago corrigió la primera prueba de «idea a video»: cuatro imágenes y numerosos gráficos no alcanzaban. Desde el perfil v3, `minimum_distinct_images` vale 10 por video, además de la variedad de escenas y animaciones. No es un conteo de planos: varios encuadres, colorizaciones o movimientos sobre el mismo original cuentan como una imagen.

Dirección visual distingue `asset_type` (`image` o `native`) e `image_id` del origen, vacío para gráficos nativos. El validador cuenta IDs de imagen distintos y bloquea menos de diez antes de motion/montaje. Su informe registra `planned_distinct_images` e `image_asset_review: pending`: no ha inspeccionado archivos. Referencias y montaje conservan procedencia y timecodes; calidad contrasta archivos/hashes y escenas del export para detectar alias del mismo recurso y asegurar que las imágenes realmente se vean. Ninguna miniatura imperceptible cumple el requisito.

Los trabajos v1/v2 conservan el esquema de escenas anterior y no se migran silenciosamente al cargar el perfil actual. La revisión explícita de una pieza con esta corrección puede adoptar v3 como una nueva versión local, conservando su entrega previa.

## Equipo bajo la gerencia

### Correcciones incorporadas de la oficina — 21/11/2026

- **Voz y subtítulos:** llamar agente/agentes a los especialistas. Cuando se corrige una toma que dice bot/bots, corregir el audio además del texto, reutilizar material compatible de la propia voz, registrar el origen del empalme y mantener la EDL y la sincronía. Detectar silencios no autoriza cortar respiraciones útiles ni palabras. Retranscribir ayuda a verificar términos; escuchar sigue siendo una comprobación distinta.
- **Demostración real:** asignar trabajo concreto a especialistas, registrar eventos de ejecución y capturar directamente la oficina mientras trabajan. Relacionar cada escena con tarea, responsable y evidencia de skill. Distinguir captura real, ilustración y recreación; una animación no demuestra que se ejecutó un agente.
- **Imágenes y movimiento:** crear recursos nuevos para el contenido hablado, con contexto y procedencia. Revisar clip y fotogramas de transiciones; comprobar movimiento de los elementos, lectura móvil, rótulos TAREA/SKILL y subtítulos sin solapes o huecos dentro de las frases. Los cambios de cámara sobre una sola imagen no cumplen el mínimo de originales.
- **Música alternativa:** conservar la selección vigente y comparar propuestas nuevas usando la misma voz, fragmento y nivel. Variar composición, patrón e instrumentación; no solamente semilla o volumen. Entregar muestras escuchables y versiones del reel, medir formatos codificados y declarar si la escucha está pendiente. Las exploraciones de 118/114/124 BPM y la electrónica de V3 quedan como historial tras la elección expresa del track propio para V4.
- **Persistencia:** llevar las reglas a los contratos y rescatar el código reutilizable en `scripts/reel_oficina/` y `scripts/musica_opciones/`. Conservar los archivos personales, EDL de tomas reales, comprobantes de publicación y actividad histórica en carpetas privadas. Versionar fuentes y pruebas; no presentar un script como mejora automática de una skill externa que no se modificó.

Estas reglas corrigen el flujo y no cambian la aprobación histórica de `production/baseline.json`. Las revisiones técnicas, visuales y de escucha se registran por separado. Una demostración breve puede conservar su duración justificada, sin forzarla a la base de una nueva pieza.

En la siguiente revisión de la oficina, Yago pidió apreciar más las imágenes: cada original pasa de 0,8 a 1,6 s y suma una segunda acción visual independiente. La receta versionada `production/office-reel-v3.json` fija 48 frames visibles por imagen, las ventanas de evidencia real y la nueva dirección musical, basada en el audio oficial de Hey Boy Hey Girl a partir de 0:40. No confundir aumentar la permanencia con alargar una transición que tapa el recurso; más animación ocurre dentro del plano. La base global de estilo y música conserva su aprobación histórica.

El recorte MP3 aportado luego por Yago dura 19 s y reemplaza la URL como material de referencia disponible. Se analiza completo, sin buscar de nuevo 0:40 dentro del recorte. El pedido de un buen sinte con filtro se prueba mediante una composición propia y muestras separadas de sintetizador, instrumental y voz. Una comparación espectral no acredita similitud perceptual ni aprobación musical; conservar ese límite en la entrega.

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
7. Aplicar la selección musical del perfil. En v4, tomar el track desde cero hasta el final, ajustar sidechain con la voz y medir el master y el audio codificado; registrar la escucha cuando se realice.
8. Renderizar y revisar el MP4 completo. Corregir por timecode. Entregar archivo, subtítulos, portada/copy y reporte.
9. Publicar únicamente ante la instrucción correspondiente; el comando de publicación mantiene la confirmación exacta de archivo/copy/cuenta. Analizar solo métricas reales.

## Contrato y controles del programa

`new` crea formato editorial. `draft` ejecuta gerente → investigación → guion y fija una copia del perfil con SHA256. `produce` ejecuta referencias → voz → dirección visual → motion → montaje → música → copy → revisión del plan. Cada etapa guarda su resultado y puede retomarse.

Dirección visual entrega escenas con start/end, visual_id, idea, visual, layout, palette, motion, animation, transition y aside_reason; v3 agrega asset_type e image_id. El validador exige cobertura sin huecos ni solapes, planos de hasta tres segundos, cámara 40–55%, al menos 80% de identificadores visuales diferentes, ningún recurso consecutivo o más de dos veces, tres colores y cuatro familias de movimiento/transición. En v3, también al menos 10 image_id de origen distintos. Un agente no puede ocultar un recurso repetido cambiándole el ID: el revisor debe contrastarlo con los assets.

El paquete exportado contiene `estilo.json`, `plan-de-escenas.json`, `revision-del-plan.json`, `handoff-produccion.json`, guion y salidas de especialistas. `production_ready` significa **plan preparado**, no MP4 terminado. El handoff deja render y escucha pendientes. La producción audiovisual sigue requiriendo las herramientas de montaje; `attach-video` incorpora el MP4 final para revisar/publicar.

El guion v2 incluye `duration_reason` (puede estar vacío dentro de 60–75s, debe justificar decisiones fuera de la base). La duración calculada y su motivo quedan visibles en `produccion.md` y `handoff-produccion.json`; el storyboard debe cubrir exactamente ese tiempo.

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
