# Agentes de marketing — Infinite Process

**Base aprobada por Yago el 15/11/2026:** reel Sistemas con IA, montaje V10 + Chicago house sin bajo 02. El asistente principal actúa como **gerente general de marketing** y coordina guion, referencias, voz, arte, animación, montaje, música, revisión y entrega.

El estándar es voz real y tono natural; cámara cerca de la mitad del tiempo, arriba y visuales abajo; el resto a pantalla completa; imágenes variadas, profundidad, animaciones y transiciones dinámicas; paleta ámbar/violeta/verde/coral, con aclaraciones puntuales en blanco y negro. Música Chicago house minimal a 122 BPM, sin línea de bajo y con la voz al frente.

- [Reglas para el asistente y futuros chats](AGENTS.md).
- [Estilo y flujo completo de producción](production/ESTILO-Y-FLUJO.md).
- [Perfil operativo versionado](config/video-style.json).
- [Registro de aprobación y huella del video base](production/baseline.json).
- [Brief para la próxima pieza](production/BRIEF-PROXIMO-VIDEO.md).
- [Biblioteca de las 17 referencias y enlaces originales](content/referencias/diseno-ia/README.md).
- [Montaje aprobado, assets, código e historial](content/construccion/LEEME.md).

El video aprobado dura **67.1 segundos**, tiene **35 escenas** y cámara durante **48.24%** del tiempo. Su MP4 se conserva localmente en `entregas/chicago-sin-bajo-02/Sistemas_con_IA_Yago_Chicago_sin_bajo_02.mp4`. GitHub guarda código, configuración, contratos, imágenes de diseño y procedencia; las grabaciones originales, la voz y los exports personales no se suben. Los enlaces a entregas locales funcionan en la instalación original, no desde un clon sin esos archivos.

## Operación

Python 3.11+; la CLI usa la biblioteca estándar. Montaje: FFmpeg/FFprobe. Síntesis musical: NumPy. Revisión de motion: Node, playwright-core y Chrome/Chromium. Las herramientas no instalan dependencias ni realizan llamadas de pago automáticamente.

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

Se valida 1080×1920, H.264/AAC, 35–90 segundos y hasta 100 MiB. La base editorial es 60–90 s; el rango corto conserva compatibilidad con piezas anteriores. La validación de formato no sustituye revisión visual, escucha ni sincronía. `--synthetic-voice` declara una voz sintética si fue solicitada para esa pieza; la voz real es el estándar.

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

El script musical admite duración, parámetros, fuentes locales y directorios de salida propios. Con `--instrumental-only` genera música sin voz ni video. La base de estilo se reutiliza con nuevos recursos y arreglos; cambiar una semilla no reemplaza la composición de un arreglo nuevo.

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

Subí el MP4 final a un alojamiento bajo tu control que permita una descarga HTTPS directa. El programa compara su SHA-256 con el archivo revisado antes de crear el contenedor. No incluye un alojamiento público de archivos.

```powershell
python -m marketing preview ID instagram --video-url "https://tu-dominio.example/reel.mp4"
python -m marketing publish ID instagram --video-url "https://tu-dominio.example/reel.mp4" --confirm HUELLA_DEL_PAQUETE
```

La primera llamada crea un contenedor y devuelve `processing`. Esperá al menos un minuto y repetí **el mismo comando**: consulta ese contenedor y lo publica cuando está listo. Las llamadas anticipadas no crean otros contenedores. Instagram publica en la cuenta profesional confirmada; `--privacy` corresponde solo a YouTube.

Este adaptador sigue [Instagram Login y Content Publishing](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/content-publishing). No sirve un token de Facebook Login en esta integración. Si el contenedor vence o la API rechaza el contenido, se informa el fallo.

## Conexiones

`.env.local`, `credentials/`, `runtime/`, tokens y material audiovisual están excluidos de Git. **No pegues claves o tokens en el chat ni los incluyas en commits.** `.env.example` documenta los nombres de las variables, sin valores privados. Si `.env.local` ya existe, conservá sus valores al agregar otras conexiones; no lo reemplaces con el ejemplo.

| Conexión | Preparación |
| --- | --- |
| OpenAI | Guardado seguro de `OPENAI_API_KEY` en `.env.local`. `OPENAI_MODEL` permite elegir un modelo disponible para el proyecto. Probar con `python -m marketing check-openai`. |
| YouTube | Activar YouTube Data API y obtener un cliente OAuth de tipo Desktop. Guardar el JSON privado en `credentials/youtube-client.json`. Ejecutar `python -m marketing youtube-login`, elegir la cuenta en el navegador y configurar `YOUTUBE_CHANNEL_ID` con el ID mostrado. |
| Instagram | App de Meta con Instagram Login, cuenta profesional y permisos `instagram_business_basic` / `instagram_business_content_publish`. Configurar `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_USER_ID` e `INSTAGRAM_API_VERSION` según la versión admitida por esa app. |
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

Los estados `unknown` o `publishing` después de una interrupción bloquean una nueva publicación de Instagram. Comprobá el resultado en la cuenta y, si existe, vinculá su ID:

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

El control se realiza por consola y menú de PowerShell. Esta versión no incluye panel web, scheduler, hosting público, descarga de tendencias, publicación de comentarios ni métricas automáticas. El MP4 también puede subirse manualmente a TikTok, pero el publicador implementa únicamente YouTube e Instagram.
