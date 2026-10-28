# Avisos privados del QR

La implementación del servidor y web está documentada en `../MiMascotaWeb/docs/CONTACTO-PROTEGIDO.md`. Se agrega una bandeja de mensajes desde la campana de Inicio, conservando el acceso a los recordatorios de cuidados. El otro chat se ocupa del calendario de cuidados; esta integración no modifica su planificación.

Los mensajes se guardan en el servidor durante 30 días y no se incluyen en `petcare.json`. Borrar una notificación no borra ni marca el aviso como leído. La app verifica la cuenta al consultar, responder, archivar o bloquear. Los textos se muestran literalmente, sin markup. Al cambiar o cerrar la cuenta se limpia la bandeja visible y el borrador en memoria.

En las opciones de la chapa, «Privacidad del contacto» permite contacto protegido, teléfono autorizado con confirmación adicional, o desactivar el contacto. Cambiarlo no renueva los 14 días. El modo protegido no publica el teléfono. La familia puede responder en la conversación; el visitante debe conservar su enlace privado y volver a consultarlo.

Firebase solo anuncia «Tienes un nuevo aviso». Se usa el permiso existente de notificaciones, con canal e identificador separados de los cuidados. La campana consulta los avisos cuando hay sesión; no depende de que se vea o conserve el push. Android puede impedir o retrasar el push según permisos y batería.

Pruebas: `tests/test_qr_inbox.py`, `tools/check_qr_inbox_ui.py`. Para compilar sin afectar al otro chat: `tools/build_qr_snapshot.py` crea una copia sin cuentas ni datos personales y `tools/build_qr_android.sh` usa una carpeta independiente en WSL. La APK 0.1.8 incorpora la bandeja; requiere prueba física de envío, lectura y respuesta.

Corrección 0.1.9: la campana de 0.1.8 quedaba en (0,0) porque su contenedor FloatLayout no posicionaba el botón. Se añade `pos_hint` para ubicarlo dentro de la cabecera. La prueba verifica que botón y contenedor coinciden y el verificador APK comprueba la regla KV empaquetada. Usar `mimascota-0.1.9-campana-qr.apk` como actualización para continuar la prueba. No desinstalar ni borrar datos.
