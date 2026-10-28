# Beta 0.2.5: producto y cuidados compartidos

## Disponible para probar

- Cuenta con nombre primero, correo secundario y lápiz; datos y copias en Ajustes.
- Campana abre Avisos directamente; conversación con respuesta en la misma pantalla y contexto de quien encontró a la mascota.
- QR grande, días restantes en prueba y estado de acceso pagado compatible con el servidor.
- Cuenta → Cuidados compartidos: propietario elige mascota y autoriza compartir sus rutinas e historial. Código de 48 horas y un solo uso; máximo tres personas por mascota. Crear otro código cancela el anterior. Acceso de consulta, revocable por dueño; familiar puede dejar de seguir.
- Salud → PDF: resumen privado de la mascota seleccionada. Se genera sin conexión y se comparte con el selector nativo de Android, previa confirmación. No incluye correo, teléfono, microchip, QR ni sesiones. El archivo temporal queda en la caché privada; FileProvider solo da acceso de lectura al PDF elegido.

Las funciones de compartir y PDF se prueban sin cobros durante esta beta. No son todavía una suscripción comercial ni permiten completar cuidados desde otra cuenta. No se modificó el sistema de recordatorios de la otra conversación.

## Continuidad de la chapa

El servidor dispone de `apply_tag_paid_period`: solo un servicio de confianza podrá activarlo al verificar un pago real. Conserva el token existente, el propietario, mascota, privacidad y fecha de la prueba original. Eventos repetidos son idempotentes; un evento reutilizado con otra fecha o propietario se rechaza. Al vencer el periodo, la ficha deja de mostrar datos; renovar extiende el periodo sobre la misma chapa. Una chapa desactivada manualmente no se reactiva por pagar.

No hay botón que conceda acceso pagado desde el cliente. Falta elegir proveedor, precio, condiciones, política de cancelación/reembolso, validar los avisos del proveedor y conectar el cobro. Mercado Pago es una posibilidad, no una integración activada. Comparar comisión total, impuestos, plazo de abono y pagos recurrentes cuando estén definidos país y modalidad.

La URL que se grabe debe conservarse y redirigir si cambia el dominio. No grabar lotes definitivos hasta fijar la URL y probar una muestra real.

## Prueba

1. Instalar la beta sobre la anterior, sin desinstalar, manteniendo paquete y firma.
2. Cuenta → Cuidados compartidos → mascota → Invitar. En otra cuenta, usar Tengo una invitación.
3. Consultar rutinas e historial. Retirar acceso desde la cuenta propietaria y comprobar que deja de abrir.
4. Salud → PDF. Verificar nombre, registros y compartir el archivo desde Android.
5. El cobro no se puede probar todavía. Renovación/vencimiento se verificaron con cuentas ficticias y transacciones revertidas en el servidor.

La APK pública anterior no se sustituye hasta probar esta beta en un teléfono.

## Revisión previa 0.2.5

- Títulos de ventanas se ajustan a varias líneas en pantallas pequeñas; nombres largos van dentro del contenido desplazable.
- Actualizar mensajes desde Opciones conserva el borrador; enviarlo lo limpia.
- Código inválido se explica dentro del formulario. Los nombres largos se ajustan al límite del servidor.
- Con tres personas no se ofrece otra invitación; se explica cómo liberar un acceso.
- Eliminar una mascota en la copia de cuenta termina sus invitaciones y accesos. Restaurarla no recupera ese consentimiento; las otras mascotas conservan sus permisos. Sin conexión, este cambio se aplica cuando se sincroniza la eliminación.
- Si falta en el teléfono la mascota que usó la prueba, se ofrece revisar y restaurar la copia de cuenta.
- Cambiar de cuenta mientras se prepara un PDF cancela su apertura y elimina ese archivo temporal. Un fallo del selector de Android muestra un mensaje recuperable.
- Verificados con datos ficticios: 76 pruebas unitarias, pantallas a 320/390 px y casos del servidor en transacciones revertidas. El selector nativo, teclado y actualización sobre la app instalada requieren la prueba en Android.

La compilación usa una receta local de ReportLab 4.4.10 desde su paquete oficial de PyPI. Se instala la implementación Python, sin los aceleradores opcionales ni la receta antigua que descargaba fuentes de Mercurial. Pillow se compila con la receta Android existente; charset-normalizer llega con requests.
