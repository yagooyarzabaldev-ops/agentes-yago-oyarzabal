# Agentes de marketing — Infinite Process

**Base audiovisual aprobada por Yago el 15/11/2026:** reel Sistemas con IA, montaje V10. **Música vigente desde el 21/11/2026:** su track «Yago Oyarzabal - chatgpt», desde el inicio hasta la duración del video, con sidechain suave bajo la voz. El asistente principal actúa como **gerente general de marketing** y coordina guion, referencias, voz, arte, animación, montaje, música, revisión y entrega.

El estándar es voz real y tono natural; cámara cerca de la mitad del tiempo, arriba y visuales abajo; el resto a pantalla completa; imágenes variadas, profundidad, animaciones y transiciones dinámicas; paleta ámbar/violeta/verde/coral, con aclaraciones puntuales en blanco y negro. El perfil v4 conserva el track seleccionado a velocidad original y baja suavemente la música cuando habla Yago. La selección musical anterior queda como historial.

**Duración base para próximos Reels y Shorts: 60–75 segundos.** El perfil v3 conserva el ajuste de gerencia y guion según el contenido; fuera de la base registran un motivo concreto. Las ideas puntuales pueden ser más breves y los tutoriales necesitar más desarrollo. No rellenar ni acelerar la voz para alcanzar un número.

**Mínimo 10 imágenes distintas por video**, siguiendo las referencias aportadas por Yago. Los gráficos nativos y las variantes de recorte, zoom o color de una imagen no aumentan ese conteo. El plan v3 distingue `asset_type` e `image_id`; la revisión del export debe comprobar los archivos originales y su uso real. Los trabajos con perfil anterior conservan su contrato fijado.

- [Reglas para el asistente y futuros chats](AGENTS.md).
- [Estilo y flujo completo de producción](production/ESTILO-Y-FLUJO.md).
- [Perfil operativo versionado](config/video-style.json).
- [Selección y procedencia de la música vigente](production/music-default.json).
- [Publicación de Instagram por Composio, sin navegador](production/COMPOSIO-INSTAGRAM.md).
- [Registro de aprobación y huella del video base](production/baseline.json).
- [Brief para la próxima pieza](production/BRIEF-PROXIMO-VIDEO.md).
- [Biblioteca de las 17 referencias y enlaces originales](content/referencias/diseno-ia/README.md).
- [Montaje aprobado, assets, código e historial](content/construccion/LEEME.md).

El video aprobado dura **67.1 segundos**, tiene **35 escenas** y cámara durante **48.24%** del tiempo. Su MP4 se conserva localmente en `entregas/chicago-sin-bajo-02/Sistemas_con_IA_Yago_Chicago_sin_bajo_02.mp4`. GitHub guarda código, configuración, contratos, imágenes de diseño y procedencia; las grabaciones originales, la voz y los exports personales no se suben. Los enlaces a entregas locales funcionan en la instalación original, no desde un clon sin esos archivos.

## Operación

Python 3.11+; la CLI usa la biblioteca estándar. Montaje: FFmpeg/FFprobe. Síntesis musical: NumPy. Revisión de motion: Node, playwright-core y Chrome/Chromium. Las herramientas no instalan dependencias ni realizan llamadas de pago automáticamente.

En el equipo de Yago, las herramientas están en `D:\Herramientas\marketing`: Python, su lanzador, Node.js, FFmpeg/FFprobe, paquetes globales de npm, cachés de pip/npm y las dos skills audiovisuales. Las rutas anteriores de C: son enlaces de compatibilidad hacia D:, para que los otros proyectos sigan funcionando. El PATH y el registro de Python también apuntan a D:. No reinstalar copias completas en C:.

El registro local del traslado está en `D:\Herramientas\marketing\migracion`. Incluye verificación SHA256, destinos y estado de limpieza. Los binarios antiguos que Windows mantenga en uso se eliminan en el próximo reinicio mediante una operación registrada; no confundirlos con una segunda instalación activa ni borrarlos forzando el cierre del bot.

`iniciar.ps1` aplica la configuración privada `runtime/herramientas-locales.json` para usar las herramientas, temporales y cachés de pip/npm en D:. Para ejecutar directamente los scripts de producción o los comandos de abajo, activá primero el mismo entorno en esa terminal:

```powershell
. ./scripts/activar-herramientas.ps1
```

La activación afecta solo a esa terminal y sus procesos hijos; no vuelve a modificar el PATH global configurado durante la migración. En otro equipo, sin ese archivo local, se conserva el entorno existente. Para instalar paquetes, usá `python -m pip`; los lanzadores que conservan rutas antiguas siguen funcionando mediante los enlaces de compatibilidad.

```powershell
python -m marketing doctor
python -m marketing style
python -m marketing new "Cómo cambia la atención de una barbería con IA"
python -m marketing draft ID
python -m marketing show ID
python -m marketing approve ID --hash HUELLA_DEL_GUION
python -m marketing produce ID
python -m marketing export ID
```

Reemplazar ID y HUELLA por los valores mostrados. También existen `python -m marketing menu` e `./iniciar.ps1`. `new`, `style` y `export` no consumen API. `draft`, `produce` y `analyze` llaman a la API configurada; `check-openai` hace una comprobación real que puede consumir cuota. No se consultan tendencias actuales: investigación trabaja en modo evergreen.

`draft` ejecuta gerente → investigación → guion. `produce` ejecuta referencias → voz → dirección visual → motion → montaje → música → copy → control del plan. SQLite conserva cada etapa para retomar sin repetir las completadas. Cada trabajo fija el perfil de estilo con una huella.

El director visual entrega escenas cronometradas. Se comprueban cobertura, cámara 40–55%, variedad de recursos, al menos tres colores y cuatro familias de movimiento y transición. Un plan inválido se detiene antes de pasar a motion y mezcla. El paquete incluye guion, estilo, plan de escenas, revisión del plan y handoff de producción.

**produce prepara el plan; no genera automáticamente el MP4 editorial.** El gerente usa las herramientas y scripts de producción para crear los recursos, montar voz/cámara, animar, mezclar y revisar el export. Luego se incorpora el archivo:

```powershell
python -m marketing attach-video ID "D:/mis-materiales/reel-final.mp4"
```

Se valida 1080×1920, H.264/AAC, 20–180 segundos y hasta 100 MiB. La base editorial es 60–75 s; el margen técnico admite ajustes según el contenido y piezas históricas. El guion registra `duration_reason` cuando sale de la base, y el plan de escenas y la música se adaptan a su duración. La validación de formato no sustituye revisión visual, escucha ni sincronía. `--synthetic-voice` declara una voz sintética si fue solicitada para esa pieza; la voz real es el estándar.

Para corregir el contenido:

```powershell
python -m marketing revise ID "Usá un caso concreto y un cierre más cercano"
python -m marketing draft ID
```

Se invalidan aprobación, audio, video y planes derivados, preservando el perfil. Afirmaciones pendientes requieren corregirse o comprobarse antes de aprobar con `--claims-reviewed`. La aprobación del estilo no autoriza nuevos hechos ni publicar en redes.

## Base visual y musical reutilizable

La plantilla V10 ya carga su runtime desde el repo y sus parámetros están versionados. Ver comandos y dependencias en [el flujo](production/ESTILO-Y-FLUJO.md). La previsualización no requiere grabaciones privadas:

```powershell
node scripts/preview-baseline.mjs --help
python content/construccion/audio_chicago_sin_bajo_02.py --help
```

El sintetizador anterior se conserva como herramienta histórica; no genera la música predeterminada v4. Para usar el track seleccionado, consultar `python scripts/musica_opciones/usar_track.py --help`: sin `--track`, toma la fuente privada y su hash del perfil. Siempre empieza en cero, recorta al video y aplica sidechain con la voz. Si el archivo falta o es demasiado corto, se detiene; no lo repite automáticamente. Ver [la receta de mezcla](scripts/musica_opciones/README.md).

## Material histórico

La [V4 del Día 1](content/dia-1/LEEME.md), de 38 segundos, sigue pendiente de revisión de montaje; no se convierte en aprobada por esta decisión. Las versiones anteriores del reel se conservan como historia, no como defaults.

`new --format roulette`, `import-week` y `demo` mantienen el formato anterior de ruleta para pedidos explícitos y ejemplos. `render --winner 0` es exclusivamente ese render histórico de 35–55 s; no intenta reproducir el estilo editorial aprobado. La demo es local y no publicable. `voice` es una acción opcional explícita de síntesis, no una etapa automática.

## Publicar en YouTube Shorts

Con el canal conectado, revisá primero el paquete final. La confirmación incluye el hash del video, guion, copy, canal y visibilidad:

```powershell
python -m marketing preview ID youtube --privacy private
python -m marketing publish ID youtube --privacy private --confirm HUELLA_DEL_PAQUETE
```

Para hacerlo público, usá `--privacy public` **en ambos comandos** y revisá la nueva huella. El destino es YouTube: la clasificación como Short depende de la plataforma. Una respuesta `uploaded` significa que YouTube recibió el archivo; el procesamiento puede continuar. La implementación usa [sesiones de subida reanudables](https://developers.google.com/youtube/data/guides/using_resumable_upload_protocol), y conserva la misma sesión después de una respuesta perdida.

## Publicar en Instagram Reels

Instagram se opera por **Composio API/CLI, sin navegador ni clics**, según la corrección de Yago del 22/11/2026. El login local ya fue autorizado y la cuenta de creador verificada. La receta, el estado comprobado y sus límites están en [COMPOSIO-INSTAGRAM.md](production/COMPOSIO-INSTAGRAM.md).

```powershell
./scripts/composio.ps1 connections list --toolkit instagram
python -m marketing.composio_files --help
python -m marketing.composio_instagram --help
```

El archivo local y la portada se preparan en Composio con comprobación de SHA-256. El proxy autenticado permite conservar el campo `is_ai_generated`, ausente en el schema de la herramienta tipada consultada. Cuenta, MP4, portada, copy, música y visibilidad pertenecen a una misma huella revisada. No cambiar el paquete ni crear otra publicación ante un resultado incierto.

Las entradas antiguas `marketing preview/publish … instagram` redirigen al módulo de Composio. El adaptador directo se conserva para el historial y la reconciliación de sus registros previos. La V4 de la oficina ya publicada no se vuelve a publicar para probar esta integración.

## Conexiones

`.env.local`, `credentials/`, `runtime/`, tokens y material audiovisual están excluidos de Git. **No pegues claves o tokens en el chat ni los incluyas en commits.** `.env.example` documenta los nombres de las variables, sin valores privados. Si `.env.local` ya existe, conservá sus valores al agregar otras conexiones; no lo reemplaces con el ejemplo.

| Conexión | Preparación |
| --- | --- |
| OpenAI | Guardado seguro de `OPENAI_API_KEY` en `.env.local`. `OPENAI_MODEL` permite elegir un modelo disponible para el proyecto. Probar con `python -m marketing check-openai`. |
| YouTube | Activar YouTube Data API y obtener un cliente OAuth de tipo Desktop. Guardar el JSON privado en `credentials/youtube-client.json`. Ejecutar `python -m marketing youtube-login`, elegir la cuenta en el navegador y configurar `YOUTUBE_CHANNEL_ID` con el ID mostrado. |
| Instagram | Cuenta profesional conectada en Composio y CLI local autenticada en la misma cuenta. Usar `scripts/composio.ps1`, comprobar la conexión y la identidad por API. Autenticación y sesiones en D:, fuera de Git. No necesita copiar un token de Instagram al proyecto. |
| ElevenLabs, opcional | Configurar `ELEVENLABS_API_KEY` y el `ELEVENLABS_VOICE_ID` de una voz que tengas derecho a usar. El adaptador solicita [audio con tiempos](https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps). |
| Telegram, opcional | Configurar `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` y `TELEGRAM_USER_ID`. Iniciar una conversación con el bot antes de enviarle aprobaciones. |

El flujo [OAuth Desktop de Google](https://developers.google.com/identity/protocols/oauth2/native-app) usa un callback temporal en `127.0.0.1`, estado aleatorio y PKCE. El navegador se abre únicamente al ejecutar `youtube-login`. Los tokens persistentes se guardan en `runtime/youtube-token.json`.

El error 429 se distingue por su código específico, según la [documentación de OpenAI](https://developers.openai.com/api/docs/guides/error-codes):

| Código | Acción |
| --- | --- |
| `credit_balance_exhausted` | La organización no tiene créditos de API. Activar un beneficio elegible o agregar créditos en [facturación](https://platform.openai.com/settings/organization/billing). |
| `organization_spend_limit_exceeded` | Revisar el límite de gasto de la organización. |
| `project_spend_limit_exceeded` | Revisar el límite de gasto del proyecto. |
| `organization_usage_limit_exceeded` | Revisar el límite de uso asignado por OpenAI. |
| `rate_limit_exceeded` / `slow_down` | Espaciar las solicitudes y respetar `Retry-After` si está presente. |
| `insufficient_quota` sin un código más específico | Revisar saldo y [límites](https://platform.openai.com/settings/organization/limits). |

Los errores de saldo o límites de gasto requieren resolver esa condición antes de volver a generar. Esperar o crear otra clave no repone el saldo. El programa conserva la clave y no reintenta automáticamente. Tras resolverlo, ejecutá `python -m marketing check-openai` y retomá `draft` con el ID existente: las etapas completadas se conservan.

## Aprobación por Telegram

```powershell
python -m marketing telegram-request ID
python -m marketing telegram-poll --watch
```

El bot envía el guion y botones SI/NO. Solo acepta la respuesta del usuario, chat, mensaje y versión configurados. Un SI aprueba el guion; no publica. Un NO invalida la versión y deja feedback para `draft`. Si hay afirmaciones pendientes de revisar, se usa la aprobación local con revisión explícita. `Ctrl+C` detiene la recepción; no se instala ninguna tarea programada. Las llamadas siguen la [Bot API de Telegram](https://core.telegram.org/bots/api).

## Recuperación y análisis

Los estados inciertos después de una interrupción bloquean una nueva publicación de Instagram. Para las operaciones de Composio, usar el estado privado y la consulta del módulo `marketing.composio_instagram`; no repetir una escritura perdida. Los siguientes comandos corresponden a los registros del adaptador histórico y a YouTube:

```powershell
python -m marketing reconcile ID instagram --remote-id ID_REAL
python -m marketing reconcile ID youtube --remote-id ID_REAL
```

La reconciliación verifica la cuenta propietaria. El operador debe comprobar que el ID corresponde al video en cuestión. No hay un botón de reintento ciego ni una limpieza automática del historial. Un trabajo con publicación iniciada no se puede reescribir: se crea otro para una nueva versión editorial.

Para analizar métricas aportadas por vos:

```powershell
python -m marketing analyze ID --metrics "D:\mis-datos\metricas.json"
```

El formato de referencia es `examples/metrics.json`; sus números son ilustrativos. El Analista devuelve cambios concretos y la siguiente generación incorpora su feedback. No hay descarga automática de estadísticas.

## Pruebas y alcance

```powershell
python -m unittest discover -s tests -v
python -m marketing demo
```

Las pruebas de agentes y publicaciones que usan dobles de red no prueban credenciales, OAuth en un navegador, revisión de apps ni comportamiento real de los proveedores. La demo sí ejecuta FFmpeg localmente. Antes de operar cuentas reales hay que completar sus conexiones y comprobar el primer envío supervisado.

El control de producción se realiza por consola y menú de PowerShell. La [oficina de agentes](sites/oficina-agentes/MONITOR.md) agrega un panel de observación local y un espejo privado: muestra actividad real, tareas, skills y animación ligada a las señales del proyecto. No inicia trabajos desde la web. Esta versión no incluye scheduler, descarga de tendencias, publicación de comentarios ni métricas automáticas. El MP4 también puede subirse manualmente a TikTok, pero el publicador implementa únicamente YouTube e Instagram.

## Mejoras de los agentes guardadas en Git

Los contratos de `agents/` y [el flujo de producción](production/ESTILO-Y-FLUJO.md) incorporan las correcciones de voz y subtítulos, captura directa de actividad real, imágenes contextuales, motion perceptible y comparación de alternativas musicales. El perfil v3 valida al menos diez originales declarados y mantiene pendiente su comprobación en el export.

Las herramientas extraídas de las producciones están en `scripts/reel_oficina/` y `scripts/musica_opciones/`. Reciben rutas y parámetros explícitos; consultar su ayuda antes de usarlas. No incluyen las grabaciones, transcripciones personales ni las entregas que originaron las mejoras. `content/idea-a-video/` conserva las plantillas y la procedencia de una previsualización anterior; sus imágenes generadas permanecen locales.

El código completo de la oficina vive en `sites/oficina-agentes/`, con Three.js y su licencia. La configuración del alojamiento, el worker compilado y `dist/snapshot.json` con actividad real quedan fuera del repositorio público. Para trabajar localmente, iniciar `./scripts/oficina-agentes.ps1`; el backend entrega el estado en vivo. La exportación de snapshots y el despliegue se documentan en `MONITOR.md` y requieren mantener la privacidad del destino.
