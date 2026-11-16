# Android: acceso y servicios opcionales

## Estado de esta entrega

La cuenta y la chapa tienen acciones agrupadas y textos orientados al usuario. El registro conserva una pantalla de confirmación: después de validar el correo, **Ya confirmé mi correo** inicia sesión con los datos mantenidos temporalmente en memoria. Cerrar la pantalla elimina esa copia; no se guarda la contraseña. La verificación sigue siendo obligatoria.

Google está implementado para Android mediante navegador del sistema, retorno a la app y canje PKCE. El SDK nativo de Firebase y su adaptador están preparados para avisos y estadísticas opcionales. Firebase está configurado localmente mediante google-services.json e incluido en el APK 0.1.3. Google Sign-In sigue desactivado; los avisos y estadísticas requieren elección del usuario. No se crearon proyectos externos ni se enviaron mensajes.

**Pendiente real:** configurar proyecto/proveedor, verificar retorno OAuth, permiso Android 13+, recepción en segundo plano y consentimiento. El APK 0.1.2 se compiló con Buildozer en WSL/Ubuntu; se comprobaron contenido y firma. Su ejecución en un teléfono todavía debe verificarse. Los tests Python no sustituyen esas pruebas nativas. Falta además conectar el registro de dispositivos por propietario y un emisor/programador autenticado en backend para que los recordatorios se envíen automáticamente. El token FCM se conserva solo en almacenamiento privado del dispositivo; todavía no se sube a la nube.

## Arquitectura

- Mantener Supabase Auth para identidad y propiedad existentes; añadir Google como proveedor. No mezclar Firebase Auth como una segunda identidad: el backend actual y sus RLS usan los UUID de estas cuentas.
- `services/google_auth.py`: verificador PKCE y estado aleatorio solo en memoria, vencimiento de cinco minutos, callback estricto y de un solo uso. No registra códigos ni tokens. Si Android cierra el proceso durante el acceso, hay que reiniciar el intento.
- `android/auth-intent.xml`: callback `mimascota://auth/callback`; actividad `singleTask` y `on_new_intent`. PKCE evita que otra app que intercepte el enlace pueda canjear el código. Antes de publicar, evaluar Android App Links verificados con el dominio definitivo.
- Firebase Messaging 25.1.3 y Analytics 23.2.0, fijados en buildozer.spec. API mínima Android 24 (Android 7.0), necesaria para Python 3.14; arquitectura ARM64. Configuración pública desde recursos XML; no se incluye una cuenta de servicio ni clave privada en el APK.
- Colección automática y publicidad apagadas por defecto. `Notificaciones y privacidad` aparece cuando Android tiene configuración válida. La elección de estadísticas es independiente del permiso de avisos. Solo se envían nombres fijos de pantallas; no se añaden nombres de mascotas, teléfonos, historial ni tokens a eventos.
- `CareMessagingService`: mensajes **data-only** con `kind=care`, consentimiento y permiso verificados, aviso genérico sin datos personales. No enviar payload `notification`: Firebase puede mostrarlo en segundo plano sin pasar por este manejador.

## Configuración que debe hacer el compañero

1. Reutilizar su proyecto Firebase/Google Cloud si pertenece a Mi Mascota. Registrar cliente Android **org.mimascota.mimascota**, compatible con package.domain/package.name actuales. Registrar huellas de certificados debug y release cuando se configure el acceso nativo de Google; no distribuir keystores privados.
2. Para el flujo Google de navegador actual, crear cliente OAuth de tipo **Web**, con branding Mi Mascota y solo scopes openid/email/profile. Configurar su callback autorizado: `https://thkzrjwalcxfiucqppfv.supabase.co/auth/v1/callback`.
3. Guardar Client ID y Client Secret en el proveedor Google del dashboard Supabase, **nunca en la app ni en el chat**. Añadir el retorno `mimascota://auth/callback**` a la lista de Redirect URLs, limitado a esta ruta (incluye su query de estado). Configurar Site URL con el sitio público. Probar usuarios permitidos mientras el consentimiento de Google esté en modo Testing.
4. Después de configurar y probar el proveedor, poner `GOOGLE_SIGN_IN_ENABLED: true` en config.json. El botón aparece en la cuenta del invitado en Android. Escritorio mantiene acceso por correo.
5. Descargar **google-services.json del cliente Android**, guardarlo localmente y ejecutar:

```powershell
.venv\Scripts\python.exe tools\configure_firebase.py google-services.json
```

El script comprueba el paquete, rechaza credenciales service_account y genera `android/res/values/google-services.xml` más configuración pública en config.json. Ambos quedan ignorados por Git. Activa la disponibilidad del SDK, **no** las preferencias de los usuarios. No hace falta añadir el plugin Gradle google-services porque se generan directamente sus recursos.

6. Compilar con Buildozer en Linux/WSL con SDK/NDK compatibles, revisar el manifest fusionado y firmar con los certificados previstos. Los archivos nativos se incluyen mediante add_src/add_resources; la configuración pública no sustituye una compilación real.
7. Prueba FCM: habilitar avisos en la app, aceptar permiso y usar un emisor de desarrollo autenticado con un mensaje data-only. No pegar tokens de dispositivo en el chat ni en logs públicos. La credencial de envío va en un servidor protegido.
8. Antes de activar avisos automáticos: implementar registro/revocación de dispositivos autenticados, cambio de cuenta, logout, rotación de token, cuotas y programación de recordatorios. No exponer un endpoint anónimo que pueda enviar notificaciones. Esta parte todavía no está implementada.

## Checklist

- [x] Pantalla principal de chapa con tres acciones y sin rutas técnicas.
- [x] Cuenta con perfil, datos y seguridad agrupados.
- [x] Confirmación de correo sin repetir credenciales en la misma sesión de registro.
- [x] Cliente Google PKCE, callback Android y configuración opcional.
- [x] Adaptador y clases Firebase, manifest, permiso y generación de recursos.
- [x] Pruebas de PKCE, callbacks, configuración pública y SDK opcional desactivado.
- [ ] Proveedor Google configurado y probado en teléfono.
- [x] APK nativo compilado; contenido, manifest y firma comprobados.
- [ ] Instalación y ejecución del APK verificadas en un teléfono.
- [ ] Backend de dispositivos y envío/programación de push.
- [ ] Pruebas de notificaciones en segundo plano, cambio de cuenta, logout y revocación.
- [ ] Firebase Analytics DebugView con consentimiento y sin información personal.

## Fuentes oficiales

- https://supabase.com/docs/guides/auth/social-login/auth-google
- https://supabase.com/docs/reference/javascript/auth-resend
- https://firebase.google.com/docs/cloud-messaging/android/get-started
- https://firebase.google.com/docs/projects/multiprojects
- https://firebase.google.com/support/release-notes/android
- https://raw.githubusercontent.com/kivy/buildozer/master/buildozer/default.spec

## Compilación 0.1.2

El fragmento `android/firebase-manifest.xml` se inserta mediante `android/build_hook.py` antes de Gradle. `android.extra_manifest_application_arguments` agrega atributos y no admite los elementos service/meta-data. La configuración también excluye las bibliotecas ARM32/x86 de Firebase y las capturas de diagnóstico. Las compilaciones sucesivas reutilizan las dependencias de API 24; no hace falta clonar ni limpiar el proyecto.

## Configuración Firebase 0.1.3
Se ejecutó tools/configure_firebase.py con el cliente Android del proyecto. Se verificaron configuración pública empaquetada, recursos Android, arquitectura ARM64 y firma. Instalar apk/mimascota-0.1.3-firebase.apk sobre la versión anterior; iniciar sesión y abrir Mi cuenta → Notificaciones y privacidad. Falta probar en teléfono la recepción de FCM y conectar el backend de dispositivos y envío programado. El archivo google-services.json, config.json y recursos generados permanecen ignorados por Git.

## Área segura Android 0.1.4
android/src/org/mimascota/SystemBars.java aplica systemBars y displayCutout a la vista nativa de contenido en Android 15+. El fondo blanco ocupa las franjas del sistema y la superficie SDL queda dentro de los límites, manteniendo las coordenadas de toque y protegiendo pantallas y diálogos. En Android anterior se conserva el layout fullscreen=0 sin duplicar márgenes. main.py configura la vista al iniciar y al reanudar. El IME conserva el dispatch para below_target. Se verificaron compilación Java, clase nativa empaquetada, integración del ciclo de vida, firma y pruebas UI en escritorio; falta verificar en dispositivo gestos/tres botones, teclado y retorno desde segundo plano. APK: apk/mimascota-0.1.4-barras.apk.

## Pruebas push 0.1.5
Registro autenticado de teléfonos, límite atómico de pruebas y envío FCM HTTP v1 desplegados. Ver PUSH.md para instalar el APK y probar. La credencial queda exclusivamente en el secreto FIREBASE_SERVICE_ACCOUNT_JSON. No se ha confirmado todavía la recepción en teléfono. La programación automática de cuidados sigue pendiente; no confundir el botón de prueba con recordatorios programados.

## Actualización 0.1.7
Calendario automático en Supabase activo cada minuto. Activación explícita, sincronización opcional con revisiones, cancelaciones, zona IANA y cola privada. La prueba en segundo plano de 0.1.6 se mantiene. Ver RECORDATORIOS.md. APK listo en apk/mimascota-0.1.7-recordatorios.apk.

