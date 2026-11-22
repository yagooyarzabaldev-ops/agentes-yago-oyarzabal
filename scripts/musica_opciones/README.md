# Música autorizada desde el inicio

`usar_track.py` aplica el track privado seleccionado por el usuario desde su primera muestra decodificada hasta el final del video, a velocidad 1×. Conserva la voz suministrada y copia los paquetes del video; exporta audio AAC a 192 kb/s. No publica ni usa servicios externos.

Activar primero las herramientas del proyecto:

```powershell
. ./scripts/activar-herramientas.ps1
python scripts/musica_opciones/usar_track.py --help
```

## Fuente predeterminada

Sin `--track`, lee `config/video-style.json` —o el archivo indicado con `--profile`— y exige:

- `music.mode = "user_track"`.
- `music.asset_path`, relativo a la raíz del repositorio o absoluto.
- `music.source_sha256`, coincidente con el archivo privado.

Si falta la fuente, cambia su hash o el perfil usa otro modo, termina con error. `--track RUTA` selecciona una fuente explícita para esa invocación. No modifica el perfil.

```powershell
python scripts/musica_opciones/usar_track.py `
  --voice content/material/voz.wav `
  --video entregas/version-anterior/video.mp4 `
  --output-dir entregas/nueva-version `
  --work-dir runtime/nueva-mezcla `
  --source-assets-dir entregas/version-anterior `
  --video-name video.mp4 `
  --rights-note "Fuente propia y uso autorizado por el usuario"
```

`--output-dir` y `--work-dir` deben estar vacíos o no existir. El primero contiene MP4, `musica/master.wav`, `musica/master.mp3` y procedencia. El segundo conserva extracto desde cero, voz alineada, música antes/después del ducking, envolvente y mediciones. Grabaciones y exports permanecen fuera de Git.

Para archivar una fuente explícita sin cambiar el original, añadir `--track RUTA_ORIGINAL --archive-track content/material/music/archivo.mp3`. La copia conserva exactamente los bytes y se verifica por SHA256; una copia existente con otro hash se rechaza.

Con `--source-assets-dir` se copian `portada.jpg`, `copy.txt`, `subtitulos.srt` y `subtitulos-renderizados.ass` sin cambios. Si existe `plan-y-procedencia.json`, conserva la planificación visual, reemplaza la información de audio actual y marca la música anterior como histórica.

## Mezcla y controles

La música recibe una ganancia constante para alcanzar el nivel previo al ducking, predeterminado en `--music-lufs -23.5`. No se ecualiza ni se rehace su timbre. El detector utiliza RMS de la voz por bloques de 10 ms, rodilla suave de 8 dB, ratio 2:1, ataque de 20 ms y recuperación de 280 ms. La reducción máxima es 6 dB y se interpola por muestra. Los argumentos correspondientes permiten ajustes explícitos; los rangos de ataque y recuperación se limitan a 15–25 ms y 220–320 ms.

Se mide la reducción real entre la música previa y posterior, separando ventanas con voz y pausas. El fade final predeterminado dura 0,4 segundos (`--fade-out`). El master apunta a −14 LUFS con margen de pico para el AAC; el export se rechaza si supera −2 dBTP o se aparta más de 0,8 LU del objetivo. Se verifica decodificación completa, fuentes intactas y hash de paquetes de video idéntico.

Si el track no alcanza o la voz excede el video, termina antes de producir: no crea loops, saltos, cambios de velocidad ni truncamientos de narración. Las mediciones no reemplazan escuchar claridad, recuperación y posibles bombeos.

Pruebas específicas:

```powershell
python -m unittest discover -s tests -p test_music_track.py -v
```

Las recetas `componer.py`, `comparar.py`, `revisar.py` y `bigbeat.py` conservan las exploraciones anteriores. `analizar_referencia.py` sirve para medir un fragmento local completo sin convertirlo en un sample. Su existencia no modifica la fuente predeterminada seleccionada en el perfil.
