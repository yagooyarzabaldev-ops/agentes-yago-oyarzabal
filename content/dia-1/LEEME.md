# Día 1 — V4 para revisar

La V4 responde al pedido de más cambios de plano y escenas donde se vea a la IA funcionando. Tiene 20 planos: aproximadamente 28 segundos de pantallas de la demo y 10 segundos de cámara. Conserva cuatro intervenciones de la voz original de Yago, con dos planos medios y primeros planos en el desafío y el cierre.

## Entrega

- [Video completo — 38 segundos](../../entregas/dia-1-v4/Dia_1_Ventas_v4.mp4), 1080×1920, 30 fps, H.264/AAC.
- [Avance — 13,5 segundos](../../entregas/dia-1-v4/Avance_v4_13s.mp4).
- [Portada](../../entregas/dia-1-v4/portada.jpg).
- [Copy de publicación](v4/copy-publicacion.md).
- [Subtítulos de las intervenciones habladas](../../entregas/dia-1-v4/Dia_1_Ventas_v4.srt).
- [Plantilla para el CTA](../../entregas/dia-1-v4/RULETA-plantilla-ventas.zip).
- [Visor autónomo de la ejecución](../../entregas/dia-1-v4/replay-demo.html): abrir en un navegador para avanzar por los planos y consultar el registro.
- [Verificación del video](../../entregas/dia-1-v4/verificacion.json), [verificación de estados del replay](../../entregas/dia-1-v4/replay-verificacion.json) y [hoja de contactos](../../entregas/dia-1-v4/contacto.jpg).

## Escenas y procedencia

El cliente aparece en una conversación; el agente consulta el catálogo y responde. Luego se ve la agenda, la solicitud de reserva rechazada y corregida, la reserva guardada, el alta de Alex en el CRM y la derivación pendiente de una persona. El cambio de pantallas sigue las acciones verificadas de la ejecución.

Las interfaces son un replay visual construido a partir del registro real de V2 con datos ficticios locales. No son una captura en vivo de WhatsApp, Google Calendar ni un CRM externo. Las escenas están rotuladas y no se enviaron mensajes a terceros. La [traza pública](../../entregas/dia-1-v4/prueba-agente.json) permite cotejar los resultados mostrados.

La cara y la voz provienen de `content/material/VID_20261114_165058226.mp4`, conservado intacto. La música y los efectos son originales y se ajustaron a los nuevos tiempos. El [documento de dirección](v4/direccion.md), el [visor fuente](v4/demo.html) y sus [datos](v4/datos.js) están en esta carpeta. Los medios y scripts reproducibles están en `runtime/jobs/46199eb8fb89/edicion-v4/`.

## Estado

La verificación técnica del video pasó y se revisaron los fotogramas de cámara y de las escenas principales. La verificación del replay comprobó que la reserva fallida no actualiza la agenda y que el estado final coincide con el registro original. La revisión creativa y la escucha por parte del usuario quedan pendientes.

**V4 es la candidata actual. V1 fue rechazada y V2/V3 se conservan como referencias anteriores. Ninguna versión fue publicada.** El trabajo `46199eb8fb89` mantiene el historial de revisiones; la aprobación histórica del guion V1 no se transfiere a este montaje. Los brutos, renders y trazas de runtime están excluidos de Git.
