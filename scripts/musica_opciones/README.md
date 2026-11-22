# Música autorizada desde el inicio

`usar_track.py` aplica el track privado seleccionado por el usuario desde su primera muestra decodificada hasta el final del video, a velocidad 1×. Conserva la voz suministrada y copia los paquetes del video; exporta audio AAC a 192 kb/s. No publica ni usa servicios externos.

Ejecutarlo como última etapa de mezcla, con los cortes de montaje, voz y silencios y la duración ya cerrados. `--voice` debe ser la voz limpia sin fondo musical; conservarla separada del master. Si luego cambia la línea de tiempo o la voz, preparar la nueva versión sin música y ejecutar otra mezcla desde el track original con la nueva voz. No cortar el MP4 final para aplicar esos cambios ni pasar su audio mezclado como `--voice`: eso genera saltos o duplica la música. El script crea el fragmento continuo y el sidechain, pero no puede acreditar por sí solo que el operador haya cerrado la edición ni que la voz aportada esté libre de música; Montaje y Calidad deben comprobarlo.

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

Para estabilizar la música dentro de una frase, `--hold-ms` mantiene durante 0–250 ms el máximo reciente del detector antes de recuperar. Solo modifica la envolvente de volumen: no desplaza muestras del track ni de la voz. El valor predeterminado 0 conserva la receta anterior. Un hold corto evita subir y bajar el fondo entre sílabas; las pausas más largas siguen recuperando. La procedencia registra el hold y la variación real de ganancia, además de la profundidad.

`--mastering fixed-limiter` utiliza una ganancia constante calculada por LUFS y limita únicamente los picos con sobremuestreo a 192 kHz, techo de −2,8 dB, ataque de 5 ms y release de 80 ms. Desactiva el auto-level y compensa la latencia del limitador. El modo histórico `--mastering loudnorm` conserva la receta anterior; aunque solicita normalización lineal, FFmpeg puede pasar a dinámica si no hay margen de pico suficiente. La revisión debe medir también la ganancia master/mezcla y el offset final.

En la corrección musical de V4, la pista anterior ya era continua desde cero; se midieron cambios rápidos de ganancia en el sidechain y en el master. La nueva receta usa `--hold-ms 180 --max-reduction-db 4.5 --threshold-db -27 --ratio 1.8 --knee-db 10 --attack-ms 25 --release-ms 320 --mastering fixed-limiter`, conservando tempo, timbre, imagen y narración. Esto describe una modificación verificable de mezcla, no una escucha ni un diagnóstico perceptual.

La revisión focal posterior encontró otra caída alrededor de 21,38 s: un pico de voz activaba el limitador del bus y bajaba también el fondo. El modo `--mastering voice-only --mix-gain-db 2.05 --voice-peak-db -5.2` mueve ese control de picos **a la pista de voz antes de sumar la música**. Mantiene compensación de latencia, auto-level desactivado y la misma envolvente suave de sidechain. Después de la suma no hay limitador, compresor ni normalizador dinámico: solo una atenuación constante, si hace falta, para reservar margen de pico.

Ese modo conserva `voz_limitada_antes_suma.wav`, `voz_final.wav`, `musica_final.wav` y `suma_lineal_pre_ganancia_final.wav`. La prueba comprueba que los picos de voz no añadan modulación al stem musical y que el master sea la suma lineal de los stems. −14 LUFS es un objetivo orientativo; se admite −18 a −13 LUFS en el AAC y se exige pico menor a −2 dBTP, sin forzar volumen mediante dinámica conjunta. Registrar el nivel alcanzado. Los modos anteriores permanecen disponibles para reproducir su historial; no constituyen una aprobación de escucha.

Si el track no alcanza o la voz excede el video, termina antes de producir: no crea loops, saltos, cambios de velocidad ni truncamientos de narración. Las mediciones no reemplazan escuchar claridad, recuperación y posibles bombeos.

Pruebas específicas:

```powershell
python -m unittest discover -s tests -p test_music_track.py -v
```

Las recetas `componer.py`, `comparar.py`, `revisar.py` y `bigbeat.py` conservan las exploraciones anteriores. `analizar_referencia.py` sirve para medir un fragmento local completo sin convertirlo en un sample. Su existencia no modifica la fuente predeterminada seleccionada en el perfil.
