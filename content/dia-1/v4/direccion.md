# Día 1 / V4 — La demo toma la pantalla

El usuario valoró la mejora de V3, pero pidió más cambios de plano y escenas donde se vea a la IA funcionar. Esta versión cambia el montaje: 20 planos, aproximadamente 28 segundos de pantallas de la demo y 10 segundos de cámara, dentro de una pieza de 38 segundos.

## Secuencia

1. Yago abre el desafío; corte a la conversación con el pedido de USD 20 por un plan de USD 200.
2. Plano medio con su voz: «Nada de magia».
3. Vista de la llamada al catálogo, detalle de precios y regreso a la respuesta del agente en la conversación.
4. Solicitud de demo, pregunta de Yago sobre los límites y agenda con el turno ocupado y las alternativas libres.
5. El cliente confirma nombre y horario. La ejecución muestra la solicitud rechazada, la consulta posterior y la reserva que aparece en la agenda.
6. Cambio al CRM: aparece el lead Alex. Regreso al chat con el pedido de una garantía imposible.
7. Yago dice que se deriva a una persona; se abre la bandeja de revisión humana y el registro de acciones.
8. Primer plano con el CTA y cierre con la plantilla del agente.

Los planos de cámara combinan primer plano y plano medio con más entorno visible. La voz es la grabación original, sincronizada con sus tomas. La música y los efectos se rehicieron para los nuevos cortes.

## Qué muestran las pantallas

`demo.html` es un visor local interactivo del registro real de decisiones y herramientas de V2. Reproduce el catálogo consultado, las respuestas, la reserva, el lead y la derivación que figuran en la traza. `datos.js` contiene el registro público y la línea de tiempo. El visor permite avanzar por planos y abrir el registro completo.

Las pantallas están compuestas para esta edición a partir de esa ejecución. **No son una captura en directo de WhatsApp, Google Calendar ni un CRM externo.** La etiqueta «Replay de prueba real · datos ficticios» acompaña las escenas de la demo. No se ejecutaron nuevas llamadas al modelo para V4 ni se enviaron mensajes a terceros.

La reserva fallida no modifica la agenda. El registro de reserva aparece después de la acción exitosa; luego aparecen el lead y la derivación. Se comprobó la navegación del visor, la progresión de estados y que su contenido no se recorte.

## Producción y revisión

Fuentes, clips, audio y script de composición: `runtime/jobs/46199eb8fb89/edicion-v4/`. `prepare.py` arma los nuevos tiempos desde la grabación original; el renderizador de motion graphics genera las pantallas desde `demo.html`; `finish.py` monta y normaliza el video.

V4 se registra como nueva candidata a revisión. V3 permanece como referencia anterior. Ninguna versión fue publicada; la aprobación histórica del guion V1 no se transfiere a este montaje.
