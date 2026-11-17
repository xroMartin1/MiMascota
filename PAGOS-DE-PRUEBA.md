# Premium con Webpay Plus de prueba

Precio: **$3.990 CLP por un mes calendario por mascota**. La renovación es manual; no se guarda tarjeta ni se solicitan cobros futuros. Mantiene la ficha pública con el mismo QR. No incluye fabricación o envío de chapa física. Solo ambiente de integración Transbank, sin dinero real.

## Probar desde la aplicación

1. Iniciar sesión, guardar la mascota en la cuenta y activar su chapa digital de prueba. El servidor exige que la mascota y su chapa pertenezcan a esa cuenta.
2. Entrar en **Cuenta → Ver Premium** o **Chapa → Ver Premium** y elegir la mascota.
3. Pulsar **Pagar con Webpay** o **Renovar Premium**. Confirmar el aviso de sandbox y usar únicamente las tarjetas de integración publicadas por Transbank. No se necesita una cuenta de comprador de Mercado Pago.
4. Completar el formulario alojado por Webpay. La app no recibe números de tarjeta ni claves bancarias.
5. Regresar y pulsar **Actualizar estado**. Abrir el navegador o llegar al retorno no activa Premium; solo una aprobación confirmada en servidor concede el periodo.
6. Una renovación aprobada conserva el tiempo vigente y agrega un mes. Un rechazo, anulación o vencimiento no elimina un periodo ya pagado. Un resultado incierto se comprueba antes de volver a intentar pagar.

## Código y configuración

- App: `services/subscription.py` consume `webpay-payments` con sesión autenticada. `screens/billing.py` muestra vigencia, referencia y estados. La URL debe coincidir con `MIMASCOTA_SITE_URL`, ruta `/pago/webpay` y capability `UUID.HMAC`.
- Repo MiMascotaWeb, rama `feature/webpay-sandbox`: `supabase/09_webpay.sql`, funciones `webpay-payments` y `webpay-checkout`, rutas `/pago/webpay` y `/pago/webpay/retorno`, y `WEBPAY-SANDBOX.md`.
- Servidor Supabase: `WEBPAY_SITE_URL`, `WEBPAY_COMMERCE_CODE`, `WEBPAY_API_KEY` de integración y `WEBPAY_CHECKOUT_SECRET`. Next.js usa el mismo `WEBPAY_CHECKOUT_SECRET`, exclusivamente servidor. Ninguno se añade al APK, a `NEXT_PUBLIC_*` ni al repositorio.
- Las funciones fijan propietario, precio, moneda y ambiente. La confirmación valida la respuesta del proveedor: orden, sesión, importe, estado y código de respuesta. La base bloquea por mascota, reserva un pago abierto y aplica una transacción una sola vez.
- Dos órdenes aprobadas distintas acumulan dos meses; dos consultas del mismo pago no. La integración conserva las tablas, periodos y API anterior de Mercado Pago para compatibilidad con APK anteriores mientras esté configurada su credencial. Esa API aún admite creación; el cliente nuevo ya no la usa. No cancela compromisos antiguos automáticamente. Revisar las obligaciones existentes antes de retirar esa credencial o deshabilitar el servicio anterior.

El SQL y las funciones deben configurarse y desplegarse en el proyecto correcto antes de distribuir la nueva app. Los pasos exactos, fuentes oficiales y pruebas están en `WEBPAY-SANDBOX.md` del repo web. No ejecutar migraciones en un proyecto Supabase ajeno.

## Medición y límites

El KPI de pagos se calcula desde órdenes únicas del servidor, con estados pendientes separados. No contar cada refresco de pantalla como otra conversión. `supabase/export_webpay_snapshot.sql` del repo web genera un objeto mínimo para `tools/report_measurement.py --payments`, sin propietario, mascota, token ni datos de tarjeta. Es estado al exportar, no un historial reconstruido de un corte pasado. No son ventas reales.

Las pruebas automatizadas usan proveedor simulado, escenarios UI y SQL local. Falta ejecutar aprobación, rechazo, anulación y timeout del sandbox con cuenta y teléfono reales, además de probar el retorno HTTPS desplegado.

No hay conciliación programada: callback y comprobación en app consultan el proveedor. Si se pierde la respuesta inicial antes de guardar el token, la orden permanece `creating` y requiere revisión administrativa; no se repite un cobro a ciegas. PGlite verifica SQL en un fixture mínimo y ejecución secuencial, no prueba el esquema remoto completo o contención real entre conexiones.

Antes de ventas reales se necesitan firma de distribución, términos del proveedor, revisión de seguridad, operación de conciliación y reembolsos y pruebas end-to-end. Esta entrega mantiene sandbox de forma explícita.
