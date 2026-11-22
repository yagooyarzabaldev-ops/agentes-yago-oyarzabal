# Instagram por Composio

Yago corrigió el 22/11/2026 que las publicaciones de Instagram deben hacerse por Composio, sin interfaz gráfica. La conexión hosted de Instagram está autorizada; usar el navegador para completar la publicación no satisface esa preferencia. No recurrir automáticamente a CUA, cookies ni tokens del navegador.

## Componentes y estado

- **Conexión Instagram:** verificada mediante Composio como cuenta de creador `yago.oyarzabal`. Verificar de nuevo su estado y la identidad antes de publicar; no inferirlos solo del alias.
- **CLI local:** versión oficial 0.6.3 de Windows x64, instalada en `D:/Herramientas/marketing/composio/composio-windows-x64/`. ZIP contrastado con el checksum del release oficial. Windows tiene soporte experimental según el proveedor.
- **Autenticación y archivos de sesión:** `D:/Herramientas/marketing/composio/config/` y `D:/Herramientas/marketing/composio/sessions/`, fuera de Git. `scripts/composio.ps1` configura estas rutas por proceso y conserva el código de salida de la CLI.
- **Autenticación local:** autorizada por Yago y verificada el 22/11/2026. La CLI devuelve la conexión Instagram activa y `GET_USER_INFO` confirma la misma cuenta de creador. El permiso del conector hosted no inicia por sí solo esta sesión local; no crear una cuenta de agente alternativa para eludir la vinculación.
- **API sin interfaz gráfica:** verificada por el proxy autenticado de Composio contra Instagram. Recuperó la V4 ya existente, su cuenta, permalink, tipo Reel, etiqueta IA y presencia en el feed. El `--dry-run` también acepta el archivo local como `video_file`, pero no lo transfiere.
- **Carga real de archivos:** verificada el 22/11/2026 por `marketing.composio_files`: MP4 de 7.975.513 bytes y portada JPEG de 78.430 bytes. Ambos se reconstruyeron en Composio y se descargaron por HTTPS sin autenticación adicional, con tamaño y SHA-256 idénticos. La transferencia del MP4 utilizó 31 bloques y tardó aproximadamente tres minutos. Los comprobantes y URLs están en `runtime/composio-staging-20261122/`, fuera de Git.
- **Comprobación del paquete:** `marketing.composio_instagram check` validó video e identidad y devolvió `already_published` para la V4, con su permalink y `publication_performed: false`. Las pruebas locales cubren cambios del paquete, cuenta equivocada, respuestas perdidas, estados compartidos y conservación de portada, música y etiqueta IA.
- **Publicación nueva por esta ruta:** no ejecutada como prueba. La V4 conserva su publicación previa; una consulta de lectura o una carga de archivos no demuestra una publicación nueva.

Validación local de esta entrega: **133 pruebas aprobadas** con `python -m unittest discover -s tests -v`; `python -m marketing style` conserva el perfil v4, el track propio desde cero y el sidechain. Las pruebas de escritura usan respuestas simuladas; la conexión, consulta de identidad, lectura de la V4, transferencia y descarga de archivos se comprobaron contra los servicios reales.

La V4 de la oficina ya se publicó antes de esta corrección. Su comprobante privado está en la entrega. No volver a crearla ni publicarla para probar el cambio de transporte.

## Entrada local

```powershell
./scripts/composio.ps1 --version
./scripts/composio.ps1 whoami
./scripts/composio.ps1 login --no-browser --no-wait --no-skill-install --yes
# Después de que el usuario complete el enlace:
./scripts/composio.ps1 login --poll --timeout 30 --no-skill-install --yes
./scripts/composio.ps1 connections list --toolkit instagram
./scripts/composio.ps1 execute INSTAGRAM_GET_USER_INFO --account yago.oyarzabal --data '{"ig_user_id":"me","fields":"id,user_id,username,account_type"}'
```

La autenticación inicial puede requerir que el usuario complete el enlace de Composio; la ejecución de las publicaciones debe continuar por API/CLI. No imprimir credenciales ni guardar el enlace temporal en documentación versionada.

## Paquetes y comandos

El JSON del paquete vive en `runtime/` o en la entrega privada. Las rutas de medios se resuelven desde ese JSON. Debe contener `video` (MP4), `cover` (JPEG), `caption_file`, `account` (selector explícito de Composio), `instagram_user_id`, `username`, `is_ai_generated` y `share_to_feed`. `audio_name` y `api_version` son opcionales; la versión usada en esta integración es `v21.0`. Los archivos ya deben contar con revisión editorial y técnica y con la autorización de publicación del usuario.

```powershell
# Comprueba identidad, video y huella; no carga archivos ni crea contenedores.
python -m marketing.composio_instagram check runtime/publicaciones/pieza/paquete.json --state runtime/publicaciones/pieza/estado.json

# Solo para un paquete cuya publicación esté autorizada. Usar la huella exacta de check.
python -m marketing.composio_instagram publish runtime/publicaciones/pieza/paquete.json --state runtime/publicaciones/pieza/estado.json --confirm HUELLA_SHA256

# Consulta de lectura; conservar siempre el mismo archivo de estado.
python -m marketing.composio_instagram status runtime/publicaciones/pieza/paquete.json --state runtime/publicaciones/pieza/estado.json
```

La primera ejecución de `publish` prepara los medios y crea un contenedor. Si devuelve `processing`, consultar su estado con una pausa de al menos 30 segundos entre lecturas. Cuando esté `FINISHED`, el mismo comando `publish`, con la misma huella y estado, realiza el envío una vez y verifica el medio. Los estados `create_unknown` o `publish_unknown` impiden repetir la escritura; `status --media-id ID` permite reconciliar por lectura un ID conocido y contrastar su metadata. No borrar estados para sortear un bloqueo.

`--state` debe apuntar dentro de `runtime/`. En una reconciliación manual, comprobar que el ID corresponde a esa edición: la coincidencia de cuenta, copy y etiquetas no distingue por sí sola dos versiones con esos mismos datos. Los hashes acreditan los archivos locales y preparados; Instagram recodifica el medio y la consulta de metadata no acredita identidad binaria del video publicado.

El programa comprueba también `publicacion-instagram.json` junto al MP4 y el comprobante opcional `existing_receipt`. Una entrega ya publicada devuelve `already_published`. Para una nueva versión editorial se conserva la entrega y el comprobante anteriores.

Un registro y bloqueo compartidos en `runtime/composio-instagram/` conservan los intentos por archivo y cuenta aunque cambie la ruta de `--state`. El registro se guarda antes de cada escritura de Instagram. Conservarlo junto con los comprobantes de las entregas.

## Puente de archivos

`marketing/composio_files.py` usa la CLI autenticada para enviar bloques de 256 KiB al workbench de Composio. El sandbox reconstruye el archivo, comprueba tamaño y SHA-256 y llama a su helper `upload_local_file`. El programa descarga la URL HTTPS resultante y vuelve a comprobar el archivo completo. Los datos base64, respuestas y URLs temporales permanecen en `runtime/`, fuera de Git y de la salida de consola. No lee credenciales de la CLI ni crea un contenedor de Instagram.

```powershell
python -m marketing.composio_files --file entregas/mi-pieza/video.mp4 --runtime runtime/composio/mi-pieza/video
python -m marketing.composio_files --file entregas/mi-pieza/portada.jpg --runtime runtime/composio/mi-pieza/portada
```

El resultado indica la ruta del comprobante privado. Para reutilizar esas cargas, agregar `video_stage_receipt` y `cover_stage_receipt` al JSON del paquete. Sin ellos, el publicador llama al puente al preparar una publicación autorizada. Las URLs son temporales: el publicador vuelve a descargar y comparar sus bytes antes de crear el contenedor. Una URL vencida necesita una carga nueva, no una publicación nueva.

## Flujo requerido

1. Leer el comprobante de la entrega. Si ya está publicada, devolver su enlace; si el estado es incierto, reconciliar antes de otra acción.
2. Verificar identidad de la conexión y registrar el paquete exacto: hashes de MP4, portada y copy, cuenta, visibilidad, audio y etiqueta IA.
3. Consultar los schemas actuales. La CLI admite archivos locales en entradas `file_uploadable`; `--file` solo sirve cuando el schema tiene una única entrada de ese tipo. No asumir que una herramienta con varias entradas de archivo acepta esa opción sin especificar el campo.
4. Cargar por Composio, obteniendo un archivo preparado o URL temporal con procedencia. Una ruta local no es un `s3key`. Mantener la fuente exacta y comprobar la transferencia.
5. Crear el contenedor de Reel una vez, guardar su ID y esperar el estado final de procesamiento. Conservar audio, duración, portada y etiquetas del paquete.
6. Publicar el contenedor una sola vez. Guardar el ID antes de cualquier paso posterior; ante timeout o respuesta perdida consultar el estado, sin repetir el envío.
7. Recuperar el medio publicado por Composio y contrastar cuenta, caption, tipo Reel, etiquetas y permalink. Guardar el comprobante privado y entregar el enlace.

## Brecha de schemas observada

El schema hosted consultado de `INSTAGRAM_POST_IG_USER_MEDIA` admite `video_file`, `video_url`, `cover_url` y `audio_name`, pero no `is_ai_generated`. Meta documenta ese campo al crear el contenedor. Cuando sea necesario, debe usarse el proxy autenticado de Composio contra el endpoint oficial o una herramienta que lo exponga; no añadir campos rechazados ni eliminar la etiqueta para completar el envío.

El helper hosted `upload_local_file` trabaja sobre archivos del sandbox remoto. Por eso el puente local primero transporta los bloques mediante `COMPOSIO_REMOTE_WORKBENCH`; no le pasa una ruta de Windows como si fuera un archivo remoto. El binario no pasa por el contexto del modelo ni se sube a Git.

## Fuentes oficiales

- [Composio CLI y Windows](https://docs.composio.dev/docs/cli).
- [Referencia y configuración de la CLI](https://github.com/ComposioHQ/composio/blob/next/ts/packages/cli/README.md).
- [Manejo de archivos al ejecutar herramientas](https://docs.composio.dev/docs/tools-direct/executing-tools).
- [Diferencia entre rutas de sesión y archivos preparados](https://docs.composio.dev/kb/guide/mcp-tool-router-files).
- [Publicación y etiqueta AI Content de Instagram](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/content-publishing/).
