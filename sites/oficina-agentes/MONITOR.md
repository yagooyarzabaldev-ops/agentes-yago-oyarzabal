# Oficina de agentes de Infinite Process

La oficina permite recorrer los 14 contratos del proyecto, consultar sus responsabilidades y observar actividad real de la CLI, comandos instrumentados y sesiones Codex del proyecto. La vista usa eventos en vivo y animación ligada al estado observado.

## Actividad real y animación

- La CLI registra inicio, heartbeat cada 2 segundos y fin de cada `Agents.run`, con el ID del trabajo. No guarda prompts ni respuestas. La base de eventos es independiente: `runtime/office-activity.sqlite3`.
- El observador Codex lee incrementalmente eventos de sesiones cuyo proyecto coincide con este repositorio y de sus especialistas reconocidos. Solo exporta etiquetas de tareas y metadatos permitidos; no exporta mensajes, razonamiento ni argumentos.
- El descubrimiento de sesiones recientes se revisa cada 10 segundos. Al iniciar y como máximo una vez por minuto, se revisan rutas y fechas del historial para detectar chats antiguos retomados (hasta 120 candidatos recientes), sin volver a leer todo su contenido en cada consulta. Una sesión antigua aún no indexada puede tardar hasta 60 segundos en aparecer. Si el primer registro estaba incompleto, se vuelve a intentar cuando cambia el archivo.
- Los nombres de especialistas como `13_motion` o `11_control_calidad` corresponden a los IDs de contratos. Los alias usados para construir esta oficina también están registrados.
- La animación suave y el parpadeo representan espera. Tipeo, pantalla activa y luz verde corresponden exclusivamente a actividad observada. El botón **Animación** permite pausarla y se respeta movimiento reducido.
- Un proceso de la CLI necesita PID vivo, identidad de proceso coincidente y heartbeat de hasta 10 segundos. Codex usa señales recientes de turno y queda sin señal tras 90 segundos sin eventos. Son coberturas diferentes, identificadas por su fuente.
- La ficha distingue **skill consultada** (instrucciones leídas), **herramienta ejecutándose** (invocación observada) y **skill declarada por el ejecutor**. El contrato de la CLI no carga automáticamente una skill externa.

Para instrumentar una tarea de producción externa sin guardar el comando en la telemetría:

```powershell
python -m marketing.telemetry run --agent 13-motion --task "Render de las escenas del reel" -- node content/idea-a-video/render.mjs
```

El comando debe ser una operación real ya autorizada. Agregar `--skill motion-graphics` solo si esa skill se está aplicando realmente; la oficina conserva que fue una declaración del ejecutor.

## Abrir el monitor local

Desde la raíz de `agente-marketing`, ejecutar en PowerShell:

```powershell
./scripts/oficina-agentes.ps1
```

Abrir `http://127.0.0.1:4178`. La consola debe permanecer abierta mientras se usa el monitor. `Ctrl+C` detiene únicamente este servidor.

Para elegir otro puerto:

```powershell
./scripts/oficina-agentes.ps1 -Port 4180
```

El lanzador activa las herramientas audiovisuales instaladas en D:. También se puede ejecutar directamente:

```powershell
. ./scripts/activar-herramientas.ps1
python -m marketing.office --host 127.0.0.1 --port 4178 --site-dir sites/oficina-agentes/dist
```

El endpoint `GET /api/office` consulta el estado actual. `GET /api/events` transmite cambios mediante Server-Sent Events, con resolución local de aproximadamente un segundo. El monitor no ejecuta agentes ni genera contenido y no requiere instalar dependencias.

## Copia alojada y actualización local

El Site privado recibe el resumen minimizado del monitor local cada 3 segundos y lo conserva en almacenamiento R2 privado. El navegador consulta ese espejo cada 2 segundos. La conexión de servicio existente queda únicamente en `runtime/office-relay.private.json`, fuera de Git; no se incluye en el sitio ni en su JavaScript. El monitor activa el envío cuando existe esa configuración.

Si el monitor pierde conexión o la PC se apaga, después de 20 segundos el Site marca **sin señal** y detiene las animaciones de trabajo. El sitio nunca considera una copia vieja prueba de ejecución actual. La copia `snapshot.json` queda como respaldo expresamente fechado.

Para generar una nueva copia resumida:

```powershell
./scripts/oficina-agentes.ps1 -ExportPath sites/oficina-agentes/dist/snapshot.json
```

Este comando solamente escribe el JSON de respaldo; no despliega el Site. La actividad en vivo se transmite automáticamente desde el monitor. La fecha `generated_at` indica cuándo se hizo la lectura; cada ejecución nueva tiene sus propias marcas de inicio, señal y fin.

## Cómo interpretar la información

- **Contrato disponible:** el rol está definido en `agents/`. Esto no demuestra que haya un proceso ejecutándose.
- **Sin registro de ejecución:** no se encontró una etapa de ese rol en los trabajos de SQLite.
- **Etapa guardada · sin telemetría:** un trabajo conserva una respuesta de ese rol. No demuestra actividad actual ni que se haya renderizado un video.
- **Fecha del trabajo:** corresponde a `updated_at` o `created_at` del trabajo completo. La base no guarda un timestamp individual para cada etapa; el historial no debe presentarse como hora exacta de ejecución.
- **Demo histórica:** los trabajos con estado `demo` o marca `demo` se identifican expresamente como demostraciones no publicables. No equivalen a una producción real.
- **Skill disponible:** se comprobó la existencia de su archivo local y se relacionó por pertinencia con el rol. La CLI no carga ni asigna automáticamente esas skills a los contratos. Tampoco se afirma que se hayan ejecutado.

Los registros históricos de SQLite se conservan separados de los eventos nuevos. `active_verified` cuenta puestos con actividad observada mediante la instrumentación o el ciclo del turno Codex. Un cero no prueba que no existan procesos ajenos a estas fuentes. Los archivos `.lock` no se usan para inferir ejecución.

Los estados de producción manual se obtienen únicamente de manifiestos conocidos. El indicador de presencia del MP4 comprueba que existe el archivo, no vuelve a verificar su contenido ni declara una nueva aprobación audiovisual.

## Lectura y privacidad

El backend abre SQLite con `mode=ro` y `query_only=ON`; no inicializa el almacén de marketing ni crea su base. Si faltan registros o no puede leerlos, informa la limitación sin reparar ni modificar el proyecto.

El servidor escucha únicamente en loopback y rechaza orígenes externos. Solo sirve la carpeta `dist/` y el endpoint de resumen; no expone el árbol completo del proyecto ni permite escribir mediante HTTP.

La exportación utiliza una lista explícita de campos: nombres y responsabilidades de agentes, metadatos de skills, títulos breves de trabajos, estados, IDs de etapas y fechas del trabajo. Excluye credenciales, variables de entorno, respuestas completas de agentes, feedback privado, grabaciones, muestras de voz y contenido de los videos. Las etiquetas se limitan y se ocultan patrones evidentes de claves o tokens. Los títulos de trabajos siguen siendo información del proyecto: la copia alojada debe conservar el acceso privado previsto para esta oficina.

El monitor no modifica autorizaciones de publicación ni reintenta operaciones inciertas.

El repositorio público conserva fuentes, pruebas y la licencia de Three.js. No incluye `dist/snapshot.json` de la actividad real, `.openai/` con configuración del alojamiento, `dist/server/` compilado ni conexiones privadas. En un checkout nuevo, el backend local entrega los datos; para preparar una copia de respaldo usar el comando de exportación anterior y mantener privado su destino. El historial Git local del Site es independiente: el repositorio principal guarda sus archivos fuente completos, no un gitlink que dependa de ese historial local.

## Verificación

Desde la raíz del proyecto:

```powershell
. ./scripts/activar-herramientas.ps1
python -m unittest discover -s tests -v
python -m marketing style
```

`tests/test_office.py` comprueba lectura sin modificar SQLite, ausencia de campos privados, comportamiento sin base, estados sin actividad inventada, skills sin asignación automática, exportación y restricciones del servidor HTTP.
