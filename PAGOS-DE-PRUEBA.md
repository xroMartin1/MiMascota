# Suscripción de prueba · preparación de Mercado Pago

Estado: proveedor elegido por el equipo; todavía no hay cuenta/aplicación de prueba configurada. No hay un checkout operativo ni se ha realizado un pago. El APK no debe anunciar una suscripción pagada hasta recibir confirmación verificable del proveedor.

## Preparar la cuenta

1. Ingresar o crear la cuenta de vendedor en [Mercado Pago Developers](https://www.mercadopago.cl/developers/es/docs/subscriptions/overview).
2. Crear la aplicación Mi Mascota en Integraciones para el flujo de Suscripciones.
3. Seleccionar el entorno **Prueba** y consultar sus credenciales. No usar el entorno de producción para esta entrega.
4. Si el checkout requiere iniciar sesión como comprador, usar una cuenta de prueba del mismo país que el vendedor. Consultar el usuario, contraseña y código de verificación en el panel; nunca utilizar una tarjeta personal para la demo.
5. Cuando la aplicación esté preparada, guardar el Access Token de **prueba** como secreto del servidor en Supabase. No pegarlo en un chat, `config.json`, archivo de ejemplo, repositorio ni APK. El prefijo por sí solo no garantiza que sea de prueba: confirmar el entorno en el panel.

La integración requiere definir también el precio y qué incluye el plan. Aún no se acordaron esos datos; no se presupone un precio ni que la chapa física esté incluida.

## Flujo de implementación acordado

1. Desde Cuenta → Chapa y suscripción se muestra el precio y el entorno de prueba, y el usuario elige la mascota.
2. Una función autenticada de Supabase crea la suscripción mensual en Mercado Pago y conserva la relación entre cuenta, mascota y suscripción. El cliente no decide el importe ni el propietario.
3. La app abre el checkout HTTPS del proveedor. La app no recibe ni guarda datos de tarjeta.
4. El servidor recibe y valida la notificación del proveedor y vuelve a consultar el recurso de pago. Debe comprobar propietario, importe, moneda, estado efectivo y que sea una operación de prueba. Volver del checkout o autorizar pagos futuros no equivale a un cobro aprobado.
5. Solo un pago aprobado habilita el periodo correspondiente mediante la función existente `apply_tag_paid_period`. El identificador del evento debe impedir que un reintento otorgue dos periodos.
6. Al volver a la app se consulta el estado del servidor: pendiente, activo, rechazado, cancelado o vencido. Debe permitirse cancelar futuros cobros desde el flujo soportado por el proveedor.

## Base existente y límites

El proyecto web incluye periodos pagados y eventos idempotentes en `supabase/migrations/20261010235621_paid_tag_continuity_and_care_sharing.sql`. Esto es una base de backend, no una pasarela de pago completa. Hay que comprobar las funciones desplegadas antes de conectarla.

El inicio de una suscripción no debe publicar datos de contacto nuevos, reactivar una chapa desactivada por privacidad ni reiniciar la prueba gratuita. El QR debe conservarse al renovar. Los datos locales siguen disponibles al terminar el periodo.

## Pruebas que faltan para entregar el cobro

- Pago aprobado y rechazado en el entorno de prueba del proveedor.
- Doble clic en pagar y notificaciones repetidas sin doble activación.
- Regreso a la app antes de la confirmación: mostrar pendiente.
- Falsa notificación o cambio de importe/propietario: rechazar sin otorgar acceso.
- Cancelación y fin del periodo; renovación sin cambiar el QR.

Referencias oficiales consultadas: [Suscripciones](https://www.mercadopago.cl/developers/es/docs/subscriptions/overview), [entornos de la aplicación](https://www.mercadopago.cl/developers/es/docs/subscriptions/additional-content/your-integrations/application-details) y [cuentas de prueba](https://www.mercadopago.cl/developers/es/docs/your-integrations/test/accounts).
