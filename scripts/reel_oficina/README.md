# Recetas reutilizables del reel de oficina

Código extraído de la producción local V2 del 21/11/2026. Conserva las correcciones que se verificaron en esa pieza: EDL de voz real con donante grabado, reloj de audio explícito, subtítulos sin huecos internos, cuatro transiciones visibles, focos que rodean las letras y recomposición sin alterar el AAC.

No es un editor automático ni una integración nueva con la oficina. Recibe capturas directas, decisiones de montaje y recursos ya preparados. No elige frases, no inventa estados de agentes, no genera voz, no instala paquetes, no descarga modelos y no publica. La mezcla/música se entrega como audio final; su receta está fuera de esta carpeta.

## Dependencias y alcance

- Python 3.11 o posterior, FFmpeg y ffprobe existentes en PATH.
- **NumPy** para voz/energía y **Pillow** para medición de fuentes, inserts y transiciones.
- Una fuente instalada: `captions.py --font` recibe el archivo y `--font-name` el nombre que resolverá libass. Ambos deben corresponder a la misma familia/peso.
- Opcionales: `faster-whisper` instalado para `analyze --vad`/`transcribe`; transcripción requiere `--model` con un directorio local existente. No hay descarga automática.
- `focus.html` usa el runtime versionado `content/construccion/motion-runtime.js`. Su render a ProRes alfa depende del renderer de la skill motion-graphics-reels, Node y Chrome/Edge ya disponibles. La ruta del renderer se pasa en el comando, no está fijada al equipo original.

Antes de comandos directos, activar el entorno desde la raíz del proyecto:

```powershell
. ./scripts/activar-herramientas.ps1
python scripts/reel_oficina/voice.py --help
python scripts/reel_oficina/captions.py --help
python scripts/reel_oficina/assemble.py --help
```

Los scripts privados de origen quedan en `runtime/reel-agentes-v2-20261121/{voz,montaje,motion}` y no se modifican. No se copiaron sus grabaciones, transcripción, capturas, imágenes, hashes personales ni rutas de usuario. Tampoco los prototipos descartados o la estabilización de la filmación del monitor.

## Voz: seleccionar, medir, editar, volver a alinear

`voice.py analyze --source INPUT --output REPORT.json` mide RMS en ventanas de 10 ms. `--vad` agrega el Silero local si está instalado. Las zonas de baja energía son propuestas, no prueba de silencio ni cortes aplicados. Revisar respiraciones, fonemas y límites; pasar solo la lista `speech` revisada a la receta si se quieren acortar sus huecos.

La receta de `voice.py render` recibe rutas relativas a su propio JSON y tiempos en segundos desde **la primera muestra de audio decodificada**. Ejemplo estructural con tiempos ficticios que deben medirse en otra grabación:

```json
{
  "source": "grabacion.mp4",
  "ranges": [[0.2, 3.0], [4.0, 6.0]],
  "replacements": [{"target": [1.0, 1.3], "donor": [7.0, 7.4]}],
  "room_tone": [8.0, 8.12],
  "gap_threshold": 0.30,
  "speech_padding": 0.09
}
```

`audio_start_offset`, si se omite, se lee de `ffprobe` para el primer stream de audio. **No se suma al índice de muestras**; se suma a los tiempos de procedencia de la EDL. Esta separación conserva la corrección del desfase audio/video encontrada en la producción. Si un demuxer/archivo altera ese reloj, comprobarlo con una referencia audiovisual antes de editar.

`ranges` son frases elegidas; `replacements` sustituyen el intervalo objetivo por muestras de un donante del mismo archivo, sin cambiar velocidad. `room_tone` inserta ambiente propio entre rangos. También se acepta `operations` explícita: lista de `{kind,start,end}` con `kind` igual a `source`, `replacement` o `pause`; `visual_start`/`visual_end` opcionales conservan la referencia del objetivo reemplazado. Los valores finales se redondean a muestras; la EDL registra continuidad exacta y offset. Reemplazos que atraviesan un corte se rechazan.

```powershell
python -m marketing.telemetry run --agent 05-voz --task "Editando voz real con EDL revisada" --skill editar-reels -- python scripts/reel_oficina/voice.py render --recipe runtime/nueva-pieza/voz.json --output runtime/nueva-pieza/voz-editada.wav --report runtime/nueva-pieza/edl.json
```

El render usa microfades de 5 ms, high-pass de 70 Hz y loudnorm −16 LUFS/−3 dBTP como valores configurables. Mantiene voz real y velocidad 1.0. La extracción del singular a partir de un plural y los cortes de muletillas de V2 fueron decisiones fonéticas específicas: **no se generalizan ni se aceptan solo porque el código termina**. Revisar empalmes con escucha y ASR independiente. Una sustitución puede cambiar la duración y esta receta no resuelve sincronía labial ni reencuadra cámara automáticamente.

```powershell
python scripts/reel_oficina/voice.py transcribe --source runtime/nueva-pieza/voz-editada.wav --model RUTA_MODELO_LOCAL --output runtime/nueva-pieza/words.json
```

`--expect REGEX` y `--reject REGEX` permiten comprobar términos elegidos para esa pieza, sin introducir vocabulario privado en el código. ASR no equivale a escucha. No se aplican las correcciones léxicas y de timecode particulares de V2 a nuevas transcripciones.

## Subtítulos continuos y medidos

`captions.py --words words.json` recibe `{duration_seconds,words:[{w,start,end}]}` del **WAV final** y propone bloques de 2–4 palabras. `--blocks blocks.json` recibe una lista revisada de `{start,end,words:[...]}`. No corrige contenido ni infiere nuevas palabras. El archivo debe estar alineado después de los cortes y reemplazos.

```powershell
python scripts/reel_oficina/captions.py --words runtime/nueva-pieza/words.json --font RUTA_FUENTE --font-name "Segoe UI Black" --output runtime/nueva-pieza/subtitulos.ass
```

Produce ASS, SRT y reporte con el mismo basename. Por defecto: 1080×1920, 100 px, margen lateral mínimo de texto 95 px y reserva inferior 370 px, contemplando contorno/sombra. Mide glifos con Pillow, permite hasta dos líneas y falla si un bloque no cabe; no reduce la letra silenciosamente. Cada palabra activa dura hasta el inicio de la siguiente y la última hasta `block.end`. Los huecos entre bloques distintos se conservan. Las transiciones visuales deben evitar competir con los bloques de lectura especialmente breves.

## Captura directa, inserts y composición

`assemble.py` recibe un JSON con `format`, `audio`, `ass`, `scenes`, `transitions` y `overlays`. Rutas del plan y de los overrides `--audio`/`--ass`: relativas al plan. Las escenas deben cubrir desde cero, sin huecos ni solapes, y duran al menos un fotograma. Inicio/fin se cuantizan al fps de salida; el número final de frames se verifica.

```json
{
  "format": {"width":1080,"height":1920,"fps":30},
  "audio":"master.wav", "ass":"subtitulos.ass",
  "scenes":[
    {"kind":"capture","file":"captura-directa.mp4","start":0,"end":2,"source_start":4,"crop":[370,658,0,0]},
    {"kind":"image","file":"ilustracion.png","start":2,"end":3,"motion":"truck"},
    {"kind":"capture","file":"captura-directa.mp4","start":3,"end":5,"source_start":8,"crop":[370,658,400,0]}
  ],
  "transitions":[{"at":2,"duration":0.4,"type":"wipe"}],
  "overlays":[{"file":"foco.mov","start":0.2,"duration":1.5}]
}
```

Los crops del ejemplo son ilustrativos: medirlos en la captura real. `capture`/`clip` aceptan `crop:[ancho,alto,x,y]`, y opcionalmente `wide_crop`/`wide_y` para un plano amplio sobre extensión desenfocada de la misma fuente. `image` exige movimiento `push`, `pull`, `truck`, `rise` u `orbit`; varias variantes de una imagen no cuentan como originales nuevos.

Transiciones `wipe`, `iris`, `doors` y `state`: coberturas alfa visibles, centradas en `at`, conservando duración y los subtítulos encima. Los overlays externos se colocan a 0,0, deben tener las dimensiones finales y contar con transparencia verificada. Elegir la transición según el cambio que explica; el script no juzga si distrae ni certifica que la pantalla sea actividad real.

```powershell
python -m marketing.telemetry run --agent 09-montaje --task "Ensamblando captura directa y visuales" --skill editar-reels -- python scripts/reel_oficina/assemble.py --plan runtime/nueva-pieza/plan.json --work runtime/nueva-pieza/render --output entregas/nueva-pieza/reel.mp4
python scripts/reel_oficina/assemble.py --plan runtime/nueva-pieza/plan.json --work runtime/nueva-pieza/recomposicion --picture runtime/nueva-pieza/render/picture.mp4 --audio reel-anterior.mp4 --copy-audio --output entregas/nueva-pieza/reel-revisado.mp4
```

`--picture` permite reutilizar escenas ya renderizadas al cambiar subtítulos/overlays; comprueba dimensiones, fps y frames. `--copy-audio` exige AAC y evita recodificación. Debe ser la misma duración; comprobar hash del stream si se requiere identidad. El directorio `--work` es descartable y sus intermedios se sobrescriben: usar uno nuevo por revisión. Los entregables existentes requieren `--overwrite`; nunca usarlo sobre el aprobado para una prueba.

El JSON del export registra fuentes/hashes, número de imágenes distintas por hash y decodificación completa. No es aprobación de estilo ni QA perceptual. Antes de entregar, aplicar perfil vigente, comprobar imágenes efectivamente visibles, leer tareas/skills en cada crop, revisar bordes de las cuatro transiciones, medir LUFS/pico, detectar silencios/negros/congelados y escuchar el archivo exportado. Portada/copy/publicación siguen siendo responsabilidad del flujo general.

## Focos sin tapar evidencia

`focus.html` conserva anillos AGENTE/EN ESPERA y brackets TAREA/SKILL. Parámetros: `mode` 0–3, `duration`, `anchor_x/y`, `label_y`, `focus_width/height`, `leader_x`, `show_leader`, `show_pause` (apagado por defecto) y `label` opcional. La línea TAREA/SKILL pasa sobre el panel y por el margen derecho; se eliminó el barrido sobre letras. El template es 1080×1920 y el rótulo usa 94 px.

```powershell
node $motionRenderer --marca infinite-process --template scripts/reel_oficina/focus.html --params-file runtime/nueva-pieza/foco.json --workers 2 --out runtime/nueva-pieza/foco.mov
```

Las coordenadas de la toma V2 no son universales. Medir en el frame final tras crop/scale, validar el compuesto en entrada/medio/salida y comprobar alfa cero dentro del rectángulo de las letras (por ejemplo con Pillow `getchannel('A').crop(rect).getextrema() == (0,0)`). EN ESPERA se aplica solo sobre un estado real comprobado. La receta no verifica estados de la oficina.

## Comprobación pequeña y privacidad

```powershell
python scripts/reel_oficina/smoke.py --font RUTA_FUENTE --font-name "Segoe UI Black"
```

Genera una muestra sintética de **2,4 segundos**, no una grabación de agentes: donante/offset, EDL continua, cuatro transiciones alfa, insert/crop/plano amplio, ASS sostenido y recomposición con AAC idéntico por hash. Los archivos quedan bajo `.smoke/`, ignorado por Git. La prueba no ejecuta ASR/modelos ni el renderer de Chrome y no acredita escucha ni aceptación visual de una pieza nueva.

Guardar voces, capturas, palabras, planes con rutas privadas y exports reales bajo `runtime/` o `entregas/`. Esta carpeta versiona código y receta; no agregar material personal a Git. Los comandos de producción se instrumentan con el rol/skill realmente aplicados. No registrar transcripciones, rutas de grabaciones o comandos completos en la descripción de telemetría.
