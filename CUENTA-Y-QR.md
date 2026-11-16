# Cuenta y contacto de Mi Mascota

Actualización beta 0.2.0: consultar [APP-UX.md](APP-UX.md). Cuenta, Avisos y Chapa son páginas; los respaldos quedan en ajustes. Android conserva la sesión cifrada con Keystore, sin contraseña ni tokens en las copias JSON. La prueba nueva se limita a una chapa para una mascota durante 14 días por cuenta; borrar mascotas no permite repetirla. Las secciones siguientes documentan también entregas anteriores.

1. Inicia sesión y abre **Mi cuenta → Editar perfil**. Guarda un nombre, teléfono con código de país (ej. `+56 9 1234 5678`) y, opcionalmente, comuna/ciudad.
2. Si registraste mascotas como invitado, usa **Mis datos → Traer mascotas del invitado**. La importación es explícita y conserva el original del invitado.
3. Abre **Configurar contacto de una mascota** o **Chapa → Editar contacto**. Autoriza incluir contacto únicamente si quieres mostrar nombre y teléfono al escanear esa mascota.
4. En la versión de desarrollo y con cuenta, abre **Chapa → Crear QR** y confirma el inicio de los 14 días. El invitado conserva la prueba local de texto. Ver el flujo web detallado más abajo.
5. Usa **Mi cuenta → Mis datos → Guardar mis datos** para respaldar mascotas, cuidados y la configuración de cada chapa. El perfil de contacto se guarda directamente en los metadatos privados de la cuenta de Supabase Auth y se recupera al iniciar sesión. No se usa como autorización ni modifica las políticas RLS.

El registro pide nombre, correo y contraseña dos veces. Cada contraseña tiene un botón para mostrarla/ocultarla. Desde Seguridad se puede cambiar la contraseña verificando primero la actual. Las contraseñas y los tokens no se escriben en archivos locales.

## Alcance del QR actual

Es una **prueba local de texto**, no una ficha web pública. No incluye correo de acceso, ciudad, dirección, microchip ni historial médico. Sin autorización explícita no incluye teléfono. El contacto es una copia por mascota: editar el perfil de la cuenta no cambia chapas existentes.

La app oculta el QR después del plazo local de 14 días. Una fotografía o un PNG ya compartido sigue siendo legible; cambiar el contacto o retirar la autorización solo afecta a las nuevas imágenes generadas. Las copias locales, exportaciones y copias privadas de nube pueden contener el contacto autorizado.

El siguiente desarrollo es publicar una ficha web con token único, contacto y caducidad comprobada por Supabase. Permitirá actualizar/revocar la ficha manteniendo el mismo QR. No se implementan todavía compra de placas, recuperación de contraseña ni borrado remoto de cuenta desde esta pantalla.

## Integración web preparada — 2026-10-05

MiMascotaWeb mantiene las nuevas funciones `manage-tag` y `public-tag`, y la migración del backend. La lectura utiliza la copia privada guardada en `petcare_state`, incluido `qr_contact.share_phone` como booleano estricto, y verifica cada consulta contra el reloj del servidor. Se permite el contacto autorizado por mascota; no se publica el perfil general de Auth.

`services/public_qr.py` prepara el cliente autenticado y la generación de una imagen que contiene únicamente una URL estable. Exige un dominio HTTPS y no acepta fechas, propietario ni tipo de chapa enviados por la app. La primera emisión pública inicia catorce días nuevos desde el servidor; emitir de nuevo no los renueva. Eliminar y restaurar el mismo identificador tampoco reinicia esa prueba.

La interfaz de la app conserva por ahora el QR local. Desde el 2026-10-06 existe un despliegue público estable en https://mi-mascota-web.vercel.app, con el backend configurado; el dominio propio no es necesario para las pruebas. Antes de activar el flujo público, guardar explícitamente la copia en la nube, explicar el comienzo de la nueva prueba y conectar los controles de emisión y revocación. Retirar consentimiento en la nube afecta a posteriores consultas del mismo QR; una edición exclusivamente local aún no modifica el backend.

## Chapa web desde Kivy — 2026-10-06

La versión de desarrollo conecta ya la pantalla de chapa al backend publicado. Inicia sesión, importa los datos del invitado si corresponde y elige una mascota. **Chapa** consulta su registro sin iniciar una prueba. Si todavía no existe, **Crear QR** pide confirmación: guarda la copia privada completa y luego solicita la emisión autenticada. Nombre y especie son públicos; el teléfono solo se publica con autorización de esa mascota. La primera emisión inicia 14 días nuevos en el servidor, independientes de la prueba local.

**Más opciones → Actualizar ficha** conserva token y fechas. Una copia privada guardada en nube actualiza el contacto de todas las chapas activas de la cuenta, no únicamente la mascota abierta. **Más opciones → Desactivar chapa** requiere confirmación, no guarda otros cambios locales y desactiva definitivamente esa prueba. Los QR contienen solo la URL. El invitado conserva la prueba local de texto y un acceso al inicio de sesión. Un PNG público guardado se elimina al comprobar estado vencido o revocado; fotografías externas siguen abriendo la misma URL, cuyo servidor ya no muestra los datos.

La URL se configura con `MIMASCOTA_SITE_URL` en config.json o variable de entorno; por defecto usa https://mi-mascota-web.vercel.app. Cambiar la URL base afecta a nuevas imágenes: mantener la dirección anterior operativa para códigos ya compartidos. Las claves y sesiones no se añaden al QR.

Se preparó `.venv` con Python 3.12 y las dependencias existentes. Ejecutar `.venv\Scripts\python.exe main.py`. No se ha generado ni publicado un APK nuevo. La integración está en este checkout local; el remoto de la app sigue siendo el repositorio existente de `xroMartin1`, distinto del repositorio web privado del propietario. No se subieron sus cambios previos pendientes.

Pruebas: 30 unitarias, `tools/check_public_qr_ui.py` con event loop real y nube simulada, y regresiones `check_ui.py`/`check_account_ui.py`. Capturas en `previews/public-qr`. Ninguna cuenta ni mascota real fue alterada. Falta emitir con una sesión real y escanear desde otro teléfono; no enviar contraseñas ni tokens al chat.

## Verificación

`python -m unittest discover -s tests -v` comprueba validación, aislamiento, persistencia, consentimiento del QR y solicitudes Auth con respuestas simuladas.

`python tools/check_ui.py` verifica los flujos existentes y el renderizado. `python tools/check_account_ui.py` comprueba confirmación de contraseña, botones de visibilidad, contacto y pantalla de cuenta; requiere `MIMASCOTA_PREVIEW_DIR` con una carpeta de salida. No modifica cuentas reales.

## Simplificación y Android — 2026-10-06

La chapa muestra Ver ficha, Editar contacto y Más opciones. La cuenta agrupa Edición de perfil, Mis datos y Seguridad. Las rutas PNG y los nombres de proveedores se quitaron del flujo. El registro conserva una pantalla de confirmación para continuar sin repetir credenciales. Ver ANDROID-SERVICIOS.md para Google, Firebase, configuración del compañero y validaciones pendientes. No hay APK nuevo ni servicios móviles activados.
