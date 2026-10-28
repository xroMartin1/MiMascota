# Cuenta, Google y recuperación

La app conserva el acceso cifrado (Android Keystore en el teléfono y DPAPI en Windows). Un fallo de internet o un error temporal al renovar el acceso no debe cerrar la sesión. Si el servidor confirma que la sesión fue revocada o caducó, será necesario iniciar sesión de nuevo. Desinstalar la app elimina su acceso local.

## Activar Google (una vez)

1. Abre [Google Auth Platform](https://console.cloud.google.com/auth/overview) en el proyecto de Google que usarás para la app. Completa **Branding** con nombre de la aplicación, correo de soporte y contacto del desarrollador. Para personas ajenas a tu organización, selecciona audiencia externa.
2. Durante las pruebas, añade los correos de quienes probarán la app en **Audience → Test users**.
3. En **Clients → Create client**, selecciona **Web application / Aplicación web**. Este cliente es para Supabase aunque Mi Mascota se instale en Android.
4. En **Authorized redirect URIs**, añade exactamente:

   ```text
   https://thkzrjwalcxfiucqppfv.supabase.co/auth/v1/callback
   ```

5. Crea el cliente. En [Supabase → Authentication → Sign In / Providers](https://supabase.com/dashboard/project/thkzrjwalcxfiucqppfv/auth/providers), abre Google, activa el proveedor y guarda el **Client ID** y el **Client Secret**. No marques opciones para omitir verificaciones de seguridad.
6. En [Authentication → URL Configuration](https://supabase.com/dashboard/project/thkzrjwalcxfiucqppfv/auth/url-configuration), revisa **Site URL**: debe apuntar a `https://mi-mascota-web.vercel.app`, no a `localhost:3000`. Añade esta entrada a **Redirect URLs**:

   ```text
   mimascota://auth/callback**
   ```

   El sufijo permite los parámetros del retorno (estado y código). Es el retorno al teléfono; no reemplaza el callback HTTPS que se configura en Google. Conserva cualquier otra dirección que ya necesite la web.
7. Abre o vuelve a Mi Mascota con conexión a internet. El botón **Continuar con Google** aparece al detectar que el proveedor está activo. No hay que compilar de nuevo por activar el proveedor.

**El secreto OAuth se guarda solo en Supabase.** No lo añadas a `config.json`, al APK ni a GitHub. El inicio con Google y los enlaces de recuperación implementados aquí regresan a la app Android. Windows conserva la sesión de correo/contraseña; no registra el protocolo del navegador automáticamente.

Documentación: [Google en Supabase](https://supabase.com/docs/guides/auth/social-login/auth-google), [direcciones de retorno](https://supabase.com/docs/guides/auth/redirect-urls).

## Recuperar contraseña

En **Cuenta → Iniciar sesión → Olvidé mi contraseña**, escribe tu correo. Abre el enlace en el mismo teléfono desde el que lo solicitaste. Mi Mascota te permitirá escribir y repetir la nueva contraseña. El enlace usa PKCE: el verificador queda cifrado en el teléfono, nunca en la URL.

Es necesario permitir el retorno móvil del paso 6. Los mensajes de correo deben conservar `{{ .ConfirmationURL }}` en la plantilla de recuperación de Supabase. No sustituirlo por una dirección fija. Por privacidad, el aviso no revela si un correo tiene cuenta.

## Guardado automático

Con cuenta, la app consulta la copia al entrar y guarda cambios en segundo plano después de editar. Reintenta al volver a la app y periódicamente mientras está abierta. Sin internet, conserva los cambios locales. Sin cuenta, guarda solo en el teléfono.

La cuenta muestra un estado sencillo, sin un botón de guardado habitual. Las opciones de exportación y recuperación están en **Ajustes de cuenta → Datos y respaldos**. Cambios independientes de dos dispositivos pueden combinarse; cambios incompatibles sobre el mismo dato detienen la combinación y conservan las copias. Antes de recuperar una copia se crea un respaldo local.

El guardado de datos no vuelve a publicar automáticamente una ficha QR: los datos de contacto públicos requieren la acción explícita de actualizar la ficha. Los avisos automáticos siguen requiriendo consentimiento y permisos del teléfono.

## Prueba en teléfono

Instala el APK actualizado sobre la versión anterior sin desinstalarla. Inicia sesión, añade una mascota o cuidado y espera que Cuenta muestre **Todo guardado en tu cuenta**. Cierra y vuelve a abrir; comprueba que sigues en la misma cuenta. Repite sin internet: los datos locales deben seguir disponibles. Al recuperar conexión, espera el guardado automático.

Para Google y recuperación se debe completar la configuración anterior y probar el retorno con un correo real. Las pruebas automatizadas usan cuentas y respuestas sintéticas; no envían correos ni notificaciones reales.
