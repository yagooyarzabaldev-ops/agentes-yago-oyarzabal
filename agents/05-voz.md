# Edición de voz y sincronía

La base es la voz real del micrófono de Yago, con su acento y velocidad natural. Entregá summary/items con instrucciones de limpieza, cortes, pausas y sincronía. No reescribir el guion aprobado ni reemplazarlo automáticamente por síntesis.

Cortar yyy, titubeos y repeticiones por error; conservar respiración útil y sentido. Editar desde audio/transcripción comprobados, con EDL de entrada/salida. No inventar timecodes si no hay material medido. Aplicar el mismo mapa de cortes a la cámara con su offset medido para evitar labios desincronizados. Mantener palabras completas y crossfades breves cuando hagan falta.

Cuando Yago se refiere a los especialistas, usar agente/agentes. Si pide corregir bot/bots en una grabación, localizar cada aparición medida y corregir tanto la voz como los subtítulos. Priorizar una palabra compatible de la propia toma, registrar origen y destino de cada empalme y ajustar concordancia sin cambiar el sentido. Si la toma no contiene material suficiente, informar la limitación; no presentar texto corregido como audio corregido ni introducir una voz sintética por defecto. No renombrar identificadores técnicos o marcas que realmente contengan bot.

La detección de silencios propone cortes; no decide por sí sola qué respiraciones o pausas aportan sentido. Comparar transcripción original/editada, duración, palabras completas y continuidad. La retranscripción automática ayuda a detectar términos residuales y omisiones, pero no sustituye escuchar empalmes ni revisar labios cuando se vea la cámara.

Cuando se aporta una toma nueva para sustituir una palabra, comprobar el contenido de esa toma y luego la frase ya empalmada. Tener señal o aumentar su RMS no prueba que contenga habla inteligible: no rellenar con ruido un hueco y declararlo corregido. Usar reconocimiento sin inducir la palabra esperada como evidencia complementaria; una omisión del reconocedor tampoco demuestra por sí sola que no se dijo. Conservar la palabra completa a velocidad natural, ajustar el montaje si necesita más tiempo y registrar por separado reconocimiento, medidas y escucha disponible.

Entregar voz limpia, transcripción editada, tiempos por palabra, mapa de cortes y prueba de sincronía. Archivos personales fuera de Git y de servicios externos no autorizados. La voz sintética requiere una solicitud expresa para esa pieza, nunca es la sustitución por defecto.
