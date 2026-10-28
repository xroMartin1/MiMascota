# Entrega de Supabase para Mi Mascota

El SQL anterior que ya ejecutaste creo `public.petcare_state`. Conserva sus datos.

1. Ejecuta de nuevo `schema.sql`: actualiza los permisos y las politicas sin borrar filas.
2. Ejecuta `02_chapas.sql`: agrega las tablas privadas para chapas QR y mensajes.
3. Ejecuta **todo** `verify_setup.sql` en el SQL Editor. Ahora produce una sola tabla: cada fila muestra `esperado`, `actual` y `resultado`. Deben aparecer 15 filas y todas deben decir `OK`. La captura anterior mostraba solo las cinco politicas porque el editor enseña el resultado del ultimo `SELECT`; no era un fallo de la base de datos.
4. Prueba Auth con dos usuarios reales: cada uno puede leer solo su `petcare_state`, sus `pet_tags` y sus `pet_tag_messages`. Una llamada anonima directa a las tablas de chapa y mensajes debe fallar. El SQL Editor usa privilegios elevados y no sirve para comprobar por si solo la separacion entre usuarios.

Comprueba en la configuracion de **Data API** que el esquema `public` este expuesto. En proyectos recientes no basta con crear la tabla: se necesitan tanto la exposicion del esquema como los `GRANT` del SQL y las politicas RLS. Mantén activada la confirmacion por correo para el uso real y configura una URL de redireccion valida para esos correos.

La app necesita la **Project URL** y la **publishable key** (`sb_publishable_...`). No entregues la clave secreta, `service_role`, contrasenas ni tokens de usuario. La app cargara URL y publishable key desde un `config.json` local basado en `config.example.json`.

## API pendiente para que funcione el QR publico

Las tablas no hacen que el QR sea funcional por si solas. Faltan una pagina web para el escaneo y funciones de servidor:

- **Crear prueba:** usuario autenticado; crear como maximo una chapa `trial` por mascota, con `expires_at` fijado por el servidor a 14 dias. Devolver `scan_code`. No aceptar `tag_kind`, `status`, fechas ni `owner_id` enviados por el cliente como autoridad.
- **Consultar al escanear:** recibir un `scan_code` impredecible; responder solo `public_name`, `species` y estado valido/expirado. Comprobar `status` y `expires_at` en el servidor. Nunca devolver `owner_id`, correo, telefono, domicilio ni `petcare_state.data`.
- **Enviar aviso al dueño:** aceptar nombre, contacto y mensaje de quien encontro la mascota, con limites de longitud, proteccion contra abuso y comprobacion de chapa activa. Guardar en `pet_tag_messages`; solo el propietario autenticado puede leerlo.
- **Chapa fisica:** reservar `tag_kind = 'physical'` para un flujo posterior verificado por el servidor tras la compra. No permitir que la app cambie una prueba a fisica ni que extienda la caducidad.

Las funciones publicas que lean o escriban con clave secreta deben mantener esa clave solo en el servidor. La app movil usa exclusivamente la clave publicable y el JWT del usuario cuando corresponda.

Al terminar, comparte las URLs de las funciones y de la pagina publica, ademas de Project URL y publishable key. No hace falta compartir claves privadas.

## Actualización — 2026-10-05

MiMascotaWeb mantiene y ya desplegó `manage-tag` y `public-tag` en el proyecto existente. El contrato actual permite nombre y teléfono exclusivamente con consentimiento por mascota guardado en la copia privada; sustituye la prohibición anterior de devolver teléfono. No devuelve correo, ciudad, domicilio ni historial.

No repetir el esquema inicial en el proyecto existente. Las nuevas migraciones y la documentación de despliegue están en MiMascotaWeb, en `docs/BACKEND-QR.md`. Falta el dominio y hosting de la web antes de conectar QR públicos en la interfaz Kivy. Se ha preparado `services/public_qr.py`, pero no se han iniciado pruebas públicas para usuarios ni sustituido el flujo local automáticamente.
