# Avisos QR · corrección 0.2.7

La prueba de 30 segundos registra el teléfono antes de enviarse. Anteriormente, activar el permiso por sí solo no garantizaba ese registro si el calendario de cuidados estaba desactivado o se restauraba una sesión. Se encontraron dos trabajos del QR fallidos con `no_devices` en el servidor.

La app ahora intenta registrar el teléfono desde su ciclo de reintento incluso sin calendario de cuidados. Respeta el permiso y la elección del usuario, reintenta errores de red y renueva una vez al día o al cambiar cuenta/token. No depende de ejecutar una prueba manual. El registro ocurre mientras la app está abierta o al volver a ella.

## Eventos

- Al abrir la ficha pública de una chapa vigente se guarda un aviso de escaneo, como máximo uno cada diez minutos por chapa. Una recarga, vista previa o apertura del propio dueño también puede contar como apertura: no demuestra que se haya encontrado la mascota ni identifica quién abrió el enlace.
- Al enviar un mensaje se mantiene el aviso de mensaje. Si ya fue leído o la conversación se cerró, el servidor puede omitirlo.
- Android muestra textos distintos para escaneo y mensaje, sin nombres, teléfonos o información médica en el push.
- El servidor intenta enviar inmediatamente los avisos nuevos; la cola existente revisa cada minuto los trabajos pendientes y reintenta fallos. Internet, permisos y restricciones del teléfono afectan la entrega; no se promete recepción inmediata.

## Prueba física pendiente

1. Instalar el APK 0.2.7 encima del anterior, sin desinstalar.
2. Iniciar sesión, activar los permisos de notificación y dejar la app abierta unos 30 segundos.
3. Minimizar; abrir una chapa **vigente** desde otro teléfono y esperar aproximadamente un minuto.
4. Enviar un mensaje desde la ficha; comprobar el push y después la campana.
5. Recargar la ficha dentro de diez minutos: no debe crear otro aviso de escaneo. Este límite no bloquea el aviso de mensaje.

Los avisos locales programados siguen fuera de este cambio. Una prueba automatizada no demuestra recepción en hardware real.
