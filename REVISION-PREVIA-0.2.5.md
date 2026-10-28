# Revisión previa de beta 0.2.5

## Resultado

APK: `apk/mimascota-0.2.5-cuidados-compartidos.apk` (40.281.133 bytes).
SHA-256: `ec1ad031b3c62be9b182f7b5e6480ff9276038d055ee6eb1e1838401be6a2c2a`.
La firma V2 coincide con la beta anterior. Instalar encima, sin desinstalar.
Snapshot reproducible: `apk/plan-0.2.5-source.zip`.

## Correcciones

- Ventanas con encabezados adaptables; nombres largos dentro del contenido.
- Borrador de respuesta conservado al actualizar o volver a Avisos; enviar lo limpia.
- Actualizar mensajes disponible dentro de Opciones.
- Validación de invitación en el formulario; límite de tres personas explicado antes de intentar una cuarta.
- Recuperación de la copia si la mascota vinculada a la prueba no está en este teléfono.
- PDF: fallos de selector recuperables; cambiar cuenta durante la generación cancela la apertura y elimina el archivo temporal.
- Servidor: eliminar una mascota de la copia sincronizada termina exclusivamente sus invitaciones y accesos. Restaurarla no recupera el permiso; otras mascotas conservan el suyo. Aceptar invita requiere que la mascota siga guardada.

## Comprobaciones

- 76 pruebas unitarias de datos, sincronización, sesiones, QR, invitaciones, recordatorios y PDF.
- Pantallas a 320/390 px; encabezados, menú de cuenta, tres familiares, conversación, QR y PDF con fallos simulados.
- SQL en cuentas ficticias y ROLLBACK: vigencia/renovación, mismo QR, idempotencia, prueba única, revocación, invitaciones vencidas/canceladas/usadas, alcance de una mascota y RLS. Guardar desde el rol authenticated también ejecuta correctamente la limpieza de accesos.
- Web: 26 casos seleccionados de descarga, navegación, accesibilidad, FAQ y 3D en escritorio/móvil. La medición de fotogramas se ajustó al desfase entre el ticker GSAP y el muestreador rAF; continuidad repetida tres veces en cada tamaño.
- APK final inspeccionada: código actualizado, encabezado adaptable, PDF/ReportLab/FileProvider, bóveda de sesión y configuración cliente sin secretos ni datos personales. Firma verificada.

## Requiere el teléfono

Todavía no se ha probado esta APK en un Android real. Verificar actualización con sesión existente, teclado y botón Atrás, PDF con selector nativo, envío/lectura con dos cuentas y acceso retirado. Las pruebas de escritorio no confirman esos comportamientos nativos.

La suscripción sigue sin cobros: faltan proveedor, precio y conexión de pagos. Compartir es consulta durante la beta. La fabricación requiere una muestra grabada. La descarga pública continúa en la versión previamente aprobada hasta probar esta beta.
