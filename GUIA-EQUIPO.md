# Mi Mascota · Guía rápida del equipo

Documento de apoyo para entender el proyecto y preparar la presentación. Estado revisado: 28 de octubre de 2026. Describe lo implementado y distingue lo pendiente.

## 1. ¿Qué problema resuelve?

Mi Mascota reúne los perfiles, cuidados e historial de salud de las mascotas. Su función principal es la chapa QR: quien encuentra una mascota puede abrir su ficha web y contactar a su familia mediante las opciones autorizadas por el dueño.

Se puede comenzar sin registro. Los datos se guardan en el dispositivo; la cuenta permite usar servicios de nube.

## 2. Tecnologías y para qué sirven

| Tecnología | Uso |
| --- | --- |
| Python | Lógica, validación y conexión entre módulos. |
| Kivy y KivyMD | Interfaz de escritorio y Android. |
| Archivos `.kv` | Distribución y apariencia de los componentes. |
| JSON | Persistencia local de mascotas, cuidados e historial. |
| Supabase | Autenticación, respaldos y servicios de QR/contacto. |
| Firebase Cloud Messaging | Notificaciones push enviadas desde el backend. |
| Java + Pyjnius | Integraciones nativas de Android. |
| Buildozer + python-for-android | Empaquetado del proyecto como APK desde Linux/WSL. |

La web del QR es un proyecto separado, desarrollado con Next.js y alojado en Vercel.

## 3. Organización del código

Las rutas siguientes son relativas a la raíz del repositorio:

| Archivo o carpeta | Responsabilidad |
| --- | --- |
| `main.py` y `main.kv` | Arranque, tema y ciclo de vida de la app. |
| `screens/home.py` | Controlador principal y navegación. |
| `screens/*.kv` | Diseño visual de las pantallas y componentes. |
| `screens/features.py` | Formularios y acciones de mascotas, cuidados y cuenta. |
| `services/store.py` | Validación, lectura y guardado del JSON. |
| `services/cloud.py` | Autenticación y peticiones a Supabase. |
| `services/google_auth.py` | Inicio con Google y recuperación mediante navegador. |
| `screens/sync.py` y `services/backup_sync.py` | Sincronización automática y conflictos. |
| `screens/reminders.py` y `services/reminders.py` | Calendario de avisos remotos. |
| `services/public_qr.py` y `services/qr_inbox.py` | Chapa pública y contacto protegido. |
| `android/` | Integraciones nativas y configuración Android. |
| `supabase/` | SQL y funciones del backend. |
| `tests/` | Pruebas automatizadas. |
| `assets/` | Imágenes, fuentes e identidad visual. |
| `buildozer.spec` | Versión, dependencias y configuración del APK. |

No toda la lógica está en `main.py`: ese archivo inicia la aplicación y delega en otros módulos.

## 4. Recorrido de un dato

**Crear cuidado → validar formulario → guardar con `LocalStore.save()` → actualizar interfaz → intentar sincronizar si hay cuenta.**

El guardado escribe primero un archivo temporal, conserva un respaldo `.bak` y reemplaza el original. En Android el JSON está en el almacenamiento privado de la app; los datos del invitado y de las cuentas se separan. Sin conexión se conserva el trabajo local y la sincronización reintenta después. Los cambios incompatibles entre dispositivos requieren revisión.

Las contraseñas no se guardan en el JSON de mascotas. Supabase gestiona la autenticación y la sesión persistente utiliza almacenamiento protegido.

## 5. Avisos: qué existe y qué falta

- **Aviso dentro de la app:** `check_reminders()` en `screens/features.py` revisa cuidados vencidos cada 30 segundos y muestra un diálogo. No es una notificación del sistema con la app cerrada.
- **Push:** el servidor procesa el calendario y Firebase entrega el aviso al teléfono. Requiere configuración, permisos, conexión y cuenta.
- **Notificación local programada:** pendiente. Propuesta: recordar un paseo o cuidado sin cuenta ni internet, guardando sus datos en JSON y programándolo mediante Android. El JSON conserva la fecha; no ejecuta la notificación por sí mismo.
- **Configuración remota implementada:** Inicio muestra un consejo leído desde `app_public_config` de Supabase, sin cuenta. `services/remote_config.py` valida el texto y guarda una copia en `remote-config.json`. La interfaz indica «Actualizado en línea», «Último consejo guardado» o «Consejo disponible sin conexión». No utiliza Firebase Remote Config. Ver `CONFIGURACION-REMOTA.md`.

La notificación local programada sigue pendiente; no presentarla como terminada. Al añadirla habrá que evitar duplicados con los push. La configuración remota del consejo ya está implementada.

## 6. Ejecución y compilación

En Windows, ejecutar `Iniciar MiMascota.bat`. Para la nube se necesita `config.json` configurado; no compartir secretos ni credenciales de servidor.

Si el entorno de compilación ya está preparado en Ubuntu/WSL y el repositorio está en `~/MiMascota`:

```bash
cd ~/MiMascota
git pull
source ~/buildozer-venv/bin/activate
buildozer -v android debug
```

Revisar o guardar cambios locales antes del pull. No hay que clonar de nuevo. El APK se genera en `bin/`; la primera compilación tarda más por las descargas y compilación de dependencias.

## 7. Respuestas para la defensa

- **¿Por qué JSON?** Permite persistencia sencilla en el dispositivo y uso sin conexión.
- **¿Por qué también una base de datos?** Para datos compartidos, cuentas y respaldo entre dispositivos.
- **¿Qué es persistencia?** Que los datos se conservan después de cerrar y abrir la aplicación.
- **¿Qué diferencia hay entre local y push?** El aviso local lo programa el teléfono; el push llega desde un servidor.
- **¿Qué hace `.kv`?** Describe la interfaz y la separa de parte de la lógica Python.
- **¿Qué pasa si se niega el permiso de notificaciones?** La app sigue funcionando, pero Android no muestra sus avisos del sistema.
- **¿Qué pasa al desinstalar?** Se pueden perder los datos locales; cerrar la app no equivale a desinstalarla.
- **¿El QR muestra todos los datos?** No. La ficha pública expone únicamente los campos autorizados; el historial privado no se publica.

## 8. Preparación de la demo

Crear una mascota y un cuidado, reiniciar para demostrar persistencia, probar el uso sin internet y mostrar el QR público con otra cámara. Comprobar antes las cuentas, permisos y avisos que realmente se expondrán.

Para mostrar configuración remota, abrir Inicio con internet y esperar «Actualizado en línea»; reiniciar sin internet muestra el último consejo guardado. La rúbrica también pide una modificación en vivo. Cada integrante debe saber ubicar el login, el guardado JSON, el disparador del aviso y el origen de un valor remoto. Practiquen cambiar un texto y explicar qué sucede cuando falla la conexión.
