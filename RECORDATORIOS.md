# Recordatorios automáticos · APK 0.1.7

## Activación y prueba en el teléfono

1. Instala `apk/mimascota-0.1.7-recordatorios.apk` sobre la versión anterior, sin desinstalar.
2. Inicia sesión, activa los avisos en **Mi cuenta → Notificaciones y privacidad** y acepta el permiso de Android.
3. Abre **Mi cuenta → Recordatorios automáticos**, selecciona **Sí**, confirma tu zona (por ejemplo, `America/Santiago`) y pulsa **Publicar calendario**. Espera la confirmación.
4. En **Rutina**, crea un cuidado para dentro de 3 minutos, con repetición **No**. Puedes introducir la fecha y hora en el formato mostrado. Espera **Avisos sincronizados** antes de minimizar.
5. Minimiza o bloquea la pantalla, manteniendo internet. El procesador revisa el calendario cada minuto: no es una alarma de precisión y Android/Firebase pueden retrasar la entrega.
6. Repite con otro cuidado y complétalo o elimínalo antes de su hora. Espera la sincronización: ese aviso pendiente debe cancelarse. Si ya estaba enviándose, puede llegar.

El calendario de avisos es único por cuenta. Publicarlo explícitamente reemplaza el calendario anterior con los cuidados de ese teléfono. Después, las modificaciones se sincronizan automáticamente con control de revisiones mientras haya sesión, permisos e internet. Si otro dispositivo actualizó la versión, se conserva el cambio local y se muestra pendiente; revisa los cuidados y publica explícitamente el calendario que quieras conservar. La copia completa de mascotas e historial sigue teniendo su flujo propio de guardado/restauración.

## Uso sin conexión y repetición

Los invitados siguen guardando localmente. Los avisos con la app minimizada requieren cuenta y calendario publicado. Si no hay internet, la edición, eliminación o finalización queda local y pendiente: el calendario anterior del servidor podría seguir avisando hasta que se confirme el cambio. La app reintenta mientras está abierta y al regresar; cerrar la sesión retira ese teléfono en línea y desactiva su recepción local.

Todos los cuidados del calendario usan la zona confirmada en la activación, incluso los existentes. Los avisos diarios y semanales mantienen su hora local mediante las zonas IANA. Ante una hora repetida o inexistente al cambiar el horario de verano, se aplica la resolución de PostgreSQL; conviene evitar programar en esa franja. La app incluye `tzdata` para calcular pendientes y completar recurrencias en la misma zona, aunque el teléfono esté en otra.

Cada fecha recurrente se avisa aunque el usuario no haya marcado la anterior como completada; la app conserva el cuidado pendiente hasta que lo complete. No se envían ráfagas de ocurrencias antiguas: el servidor admite un retraso máximo de 15 minutos y salta las anteriores. No se trata de un sistema clínico ni de una confirmación de administración de medicamentos.

## Implementación

- `services/reminders.py`: envía solo IDs, fechas, repetición y estado; no transmite nombres, contactos, medicamentos o dosis al calendario.
- `screens/reminders.py`: activación, cola local, sincronización serial, reintentos y conflictos entre teléfonos.
- `supabase/04_recordatorios.sql`: plan privado, calendario, entregas y funciones internas; RLS y acceso exclusivo del backend.
- `push-device`: verifica al usuario en Supabase Auth. El propietario se obtiene de la sesión, nunca del cuerpo del cliente. Activar un plan exige un teléfono propio registrado recientemente.
- `reminder-worker`: clave aleatoria de 256 bits generada y guardada en Vault; el servidor valida la clave en DB antes de obtener credenciales Firebase. No existe en el APK ni se imprime.
- `05_activar_recordatorios.sql`: Cron cada minuto con pg_net, sin credenciales en el comando del cron. Si no hay nada que procesar, no invoca la función Edge.
- Avisos genéricos con `event_id`, data-only, sin información médica en pantalla bloqueada. Android respeta el permiso, la elección local y recuerda los últimos 500 IDs para suprimir duplicados.
- Cola con bloqueo `SKIP LOCKED`, unicidad por cuidado/fecha/teléfono, revalidación inmediatamente antes de enviar, cancelación y caducidad. Hasta 3 intentos ante rechazo transitorio conocido; una respuesta de red ambigua se marca `uncertain` para evitar reenviarla ciegamente. Firebase aceptado (`sent`) no significa recibido.
- Tokens vencen tras 30 días sin registro. Con sesión y avisos activos, la app detecta un token renovado mientras está abierta y vuelve a publicar. No hay un servicio Python permanente en segundo plano.
- No se puede garantizar cancelar un envío que ya pasó la última validación; completar sin internet tampoco cancela una entrega remota inmediatamente. No se ofrece entrega exactamente una vez.

## Verificación

48 pruebas Python, 10 Deno y comprobación real de UI Kivy: guardado local, privacidad del payload, versiones, autenticación, cancelación, reintentos y fallos ambiguos. `verify_recordatorios.sql` prueba la cola dentro de una transacción que revierte todos los fixtures, sin HTTP ni Firebase. Verifica también el cambio de horario de Santiago. No requiere leer valores de secretos.

Se comprobaron los permisos RLS y los endpoints desplegados: un usuario no puede leer la cola, publicar directamente por RPC ni ejecutar el procesador; solicitudes sin autorización se rechazan. La revisión automática rechazó una prueba con fixtures persistentes y una llamada al procesador sobre la base real. No se ejecutó esa prueba ni se enviaron avisos reales desde las herramientas; la recepción completa debe comprobarse con los pasos anteriores en el teléfono.

El asesor de seguridad no detectó problemas nuevos en esta estructura. Mantiene un aviso anterior de Supabase Auth sobre [protección contra contraseñas filtradas](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection), que no se modificó en esta tarea.

