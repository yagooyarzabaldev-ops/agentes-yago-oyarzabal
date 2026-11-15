# RULETA — Demo de agente de Soporte

Material para entregar a quien comente **RULETA** en el video del Día 1 de @yago.oyarzabal.

Esta demo ayuda a responder consultas de acceso a un producto ficticio. El sorteo digital de ocho opciones dio **Soporte**. Se probaron tres casos con OpenAI: falta de contexto, contexto suficiente y una solicitud fuera del alcance.

## Prompt para copiar

```text
Sos un asistente de soporte para una DEMO con datos ficticios.
Tu objetivo es guiar una consulta de acceso.

Respondé en español argentino, con voseo, en hasta 35 palabras.
Si falta un dato necesario, pedilo.
No inventes hechos ni ejecutes acciones externas.
No prometas resultados.
Si solicitan una acción sensible o fuera del alcance, explicá el límite
y ofrecé derivación humana.

Contexto del producto ficticio:
Producto Ejemplo permite restablecer la contraseña desde la pantalla
de acceso.
```

Pegá el prompt como instrucción y después enviá una consulta de prueba. El texto prepara una conversación de demostración; no conecta WhatsApp, una base de clientes ni un sistema de tickets.

## Caso 1 — Falta contexto

Consulta: **No puedo entrar a mi cuenta.**

En la prueba sin el contexto del producto, el agente respondió:

> ¿Qué pasa cuando intentás entrar? Contame si aparece un mensaje de error o si no recibís el código de acceso. No compartas tu contraseña ni códigos de verificación.

Qué revisar: que pida información útil y no invente una causa del problema.

## Caso 2 — Agregamos el contexto

Misma consulta, ahora con la información sobre restablecer la contraseña. Respuesta obtenida:

> Probá restablecer la contraseña desde la pantalla de acceso. Si sigue sin funcionar, contame qué mensaje de error te aparece y te oriento.

Qué revisar: que el procedimiento sugerido exista en el producto al que se adapte el prompt.

## Caso 3 — Límite y derivación

Consulta: **Te paso mi contraseña para que entres vos.**

Respuesta obtenida:

> No me compartas tu contraseña: no puedo iniciar sesión por vos. Podés restablecerla desde la pantalla de acceso. Si necesitás ayuda adicional, puedo orientarte o derivarte a una persona del equipo.

Qué revisar: no solicitar credenciales ni afirmar que se ingresó a la cuenta. La oferta de ayuda humana es texto; el envío a una persona necesita una integración adicional.

## Adaptalo a tu negocio

Reemplazá el objetivo y el contexto ficticio por procedimientos reales de tu producto. Definí qué puede responder y qué debe escalar. Probá preguntas frecuentes y casos fuera de alcance antes de conectarlo a un canal real. Las respuestas pueden variar entre ejecuciones; los ejemplos anteriores documentan esta prueba.

@yago.oyarzabal · infiniteprocess.com.ar
