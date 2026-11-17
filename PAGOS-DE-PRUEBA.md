# Suscripción mensual de prueba

Precio: **$3.990 CLP por mascota al mes**. Mantiene vigente su ficha pública con el mismo QR; no incluye fabricación ni envío de una chapa física. Esta integración es para la demostración universitaria, con cuentas y tarjetas ficticias de Mercado Pago Chile.

## Probar desde la aplicación

1. Iniciar sesión en Mi Mascota, registrar la mascota y activar su chapa QR de prueba.
2. Entrar en **Cuenta → Ver Premium** o en **Chapa → Ver Premium**, elegir la mascota y pulsar **Elegir Premium**.
3. En **Pago de prueba → Correo del comprador de prueba**, ingresar el correo de la cuenta ficticia de comprador de Mercado Pago y pulsar **Continuar a Mercado Pago**. No crear otra cuenta en Mi Mascota para esto.
4. Completar el checkout del proveedor con su cuenta y tarjeta de prueba. Nunca usar una tarjeta personal para esta demo.
5. Volver a la app y pulsar **Actualizar estado**. Autorizar una suscripción no garantiza un cobro inmediato: mientras no exista un pago aprobado seguirá pendiente.
6. Revisar el periodo confirmado y, si se desea, **Cancelar renovación**. Se conserva el periodo que ya se había confirmado.

## Código y configuración

- App: `services/subscription.py` llama a la función autenticada; `screens/billing.py` muestra el estado y abre el checkout HTTPS. No almacena tarjetas ni el Access Token.
- Backend en el repositorio MiMascotaWeb: `supabase/functions/subscription-payments/index.ts`, `supabase/functions/_shared/billing.ts`, `supabase/08_suscripciones_prueba.sql` y `supabase/verify_billing.sql`.
- Secreto servidor: `MERCADOPAGO_ACCESS_TOKEN_TEST`, configurado exclusivamente en Supabase. `config.json` sigue llevando únicamente las claves públicas del cliente.
- El servidor fija propietario, precio, moneda y periodicidad. Comprueba vendedor de prueba, relación entre suscripción y pago, comprador, importe, estado aprobado y `live_mode = false` antes de conceder el periodo.
- La base impide dos suscripciones abiertas de la misma mascota y aplica cada identificador de pago una sola vez. Los roles públicos y usuarios no pueden otorgarse periodos desde la base de datos.
- La página `/pago/resultado` solo explica cómo volver a la app; no confirma pagos.

## Límites de esta entrega

La consulta se realiza al comprobar el pago o regresar a la pantalla abierta de suscripción. No hay webhook ni conciliación programada: las renovaciones no extienden la ficha hasta que el dueño consulte el estado. No usar para ventas reales sin completar ese mecanismo, reembolsos y pruebas de facturación.

Una creación con respuesta de red incierta queda bloqueada para evitar una segunda suscripción; requiere revisar el estado en el proveedor antes de desbloquearla. Una denegación explícita permite reintentar. Se limitan las nuevas solicitudes a cinco por hora y usuario.

Las pruebas automatizadas usan datos ficticios y transacciones SQL revertidas. La aprobación y el rechazo reales en el checkout de pruebas todavía deben validarse con el comprador del equipo.
