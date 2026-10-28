# Notificaciones de prueba (APK 0.1.5)

El backend `push-device` está desplegado en el proyecto de Mi Mascota. Usa el secreto **FIREBASE_SERVICE_ACCOUNT_JSON**, guardado directamente en Supabase; nunca se incluye en el código, APK o config.json.

## Probar en teléfono

1. Instalar `apk/mimascota-0.1.5-push.apk` sobre la versión anterior.
2. Iniciar sesión y activar **Notificaciones y privacidad**; aceptar el permiso de Android.
3. Abrir **Mi cuenta → Probar notificaciones → Registrar este teléfono**.
4. Pulsar **Enviar notificación de prueba**. Revisar la barra de notificaciones. El aviso dice «Notificaciones listas».
5. Para comprobarlo en segundo plano, pulsar Enviar y salir a Inicio del teléfono mientras se procesa. No forzar la detención de la app. Se permite una prueba por minuto por cuenta.

El servidor confirma aceptación por FCM, no recepción. La entrega depende de conexión, servicios Google Play y restricciones del teléfono. Si Firebase rechaza el envío, revisar que el secreto pertenezca al mismo proyecto del google-services.json, la cuenta de servicio siga activa y Firebase Cloud Messaging API (HTTP v1) esté habilitada. No compartir credenciales ni tokens para diagnosticar.

## Funcionamiento y privacidad

- UUID aleatorio por instalación y token FCM en preferencias privadas Android. No se imprimen en logs ni se guardan en los JSON de mascotas.
- Registro autenticado; el dueño se obtiene consultando Supabase Auth, nunca del cuerpo de la petición. Requiere correo confirmado.
- Tablas `push_devices` y `push_test_limits` con RLS, permisos de cliente revocados y políticas de denegación explícitas. Solo el backend puede leer/escribir tokens.
- Cada registro se renueva al iniciar sesión o enviar una prueba. Los registros sin renovación durante 30 días no pueden enviar pruebas. No hay aún envío automático de rotaciones desde segundo plano.
- Desactivar avisos retira el registro del servidor. Cerrar sesión intenta retirarlo antes de revocar la sesión y apaga Firebase Messaging localmente. Sin conexión, la retirada remota puede fallar; la app lo avisa y el token local se elimina.
- El envío solo puede dirigirse al teléfono registrado de quien lo solicita. No acepta mensajes, dueño ni destinatarios arbitrarios. La cuota de una prueba por minuto se aplica de forma atómica en la base de datos.
- Mensajes data-only, con texto fijo sin nombres de personas/mascotas ni datos médicos. El receptor verifica consentimiento y permiso.
- `verify_jwt=false` en la puerta de Edge Functions permite claves de firma modernas; el código **verifica la sesión en Supabase Auth antes de cada operación**. No es un endpoint de envío anónimo.

## Validación y pendiente

Pruebas Python de permiso, vinculación y desvinculación; pruebas Deno de autenticación, propiedad, cuota y destino/mensaje fijo; comprobación remota de rechazo 401 sin sesión y controles SQL de acceso. La credencial real y la recepción deben verificarse desde una cuenta iniciada en el teléfono. No se ha enviado una prueba real desde el agente.

Esta entrega no programa vacunas ni citas. El siguiente paso es sincronizar recordatorios con fecha/zona horaria, ejecutar un programador del servidor y evitar envíos duplicados. No usar el endpoint de prueba como programador.

Fuentes: https://supabase.com/docs/guides/functions/auth y https://firebase.google.com/docs/cloud-messaging/send/v1-api

## Prueba con la app minimizada (0.1.6)

Mi cuenta → Probar notificaciones → Probar en 30 segundos. Espera el mensaje «Prueba aceptada» y entonces minimiza la app o bloquea la pantalla. Supabase responde con HTTP 202 y mantiene una tarea de fondo que espera 30 segundos antes de enviar a Firebase; la conexión del teléfono a esta petición ya terminó. Android debe tener permiso de notificaciones e internet. No fuerces la detención de la app desde Ajustes.

Se conserva el límite de una prueba por minuto y la verificación de la cuenta. Antes de enviar se comprueba de nuevo que el teléfono siga registrado con el mismo token. Retirarlo durante la espera cancela la prueba. No se aceptan destinatarios ni textos arbitrarios desde el cliente.

Esta espera corta usa EdgeRuntime.waitUntil y no es una cola persistente: un fallo del servidor o Firebase puede impedir la entrega. «Prueba aceptada» confirma la solicitud, no la recepción. Los recordatorios reales todavía necesitan un planificador persistente. Las versiones anteriores del APK también reciben esta espera del servidor, pero muestran el texto anterior.

## Recordatorios reales (0.1.7)
Los avisos de cuidados únicos, diarios y semanales ya pueden activarse en Mi cuenta → Recordatorios automáticos. Consulta RECORDATORIOS.md para publicar el calendario, confirmar la zona horaria y probarlo con la app minimizada.

