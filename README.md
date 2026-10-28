# Mi Mascota

Mi Mascota es una aplicación desarrollada con Python, Kivy y KivyMD para organizar mascotas, cuidados e historial de salud. Ayuda a recordar tareas y ofrece una chapa QR: al escanear una ficha pública activa, quien encuentra una mascota puede contactar a su familia mediante las opciones autorizadas por el propietario.

Puede usarse sin cuenta para guardar información en el dispositivo. La cuenta habilita funciones en la nube. La venta y el envío de chapas físicas todavía no están implementados.

## Requisitos

- Windows 10/11 con Python 3.11 o 3.12 y Git. Internet es necesario para instalar dependencias y utilizar servicios remotos.
- Para Android: teléfono arm64-v8a con Android 7 o superior. Para compilar, Linux o WSL 2 con Ubuntu, Java y Buildozer; ver [PROBAR_EN_ANDROID.md](PROBAR_EN_ANDROID.md).
- Para probar la nube se usa el proyecto de Supabase configurado para la evaluación. El ejemplo contiene solo configuración publicable del cliente; no debe incluir contraseñas, claves de servidor ni archivos de cuenta de servicio.

## Instalación y ejecución en Windows

1. Instala Python 3.12 o 3.11, incluyendo el lanzador `py`, y Git.
2. En PowerShell:

   ```powershell
   git clone https://github.com/xroMartin1/MiMascota.git
   cd MiMascota
   Copy-Item config.example.json config.json
   ```

3. Abre `Iniciar MiMascota.bat`. La primera vez crea un entorno propio e instala los paquetes; puede tardar varios minutos. Las siguientes veces reutiliza el entorno.

Alternativamente, ejecuta manualmente:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Si utilizas Python 3.11, sustituye `-3.12` por `-3.11`. Para ejecutar solo el modo invitado, la app también abre sin `config.json`, pero autenticación, QR público y configuración remota necesitan una configuración válida y conexión.

Si se usa otro proyecto de Supabase, reemplaza URL y clave publicable en `config.json` y prepara el backend con la documentación de `supabase/`. La conexión al proyecto de evaluación depende de que siga disponible y configurado; copiar el ejemplo no instala ni despliega un servidor nuevo.

## Demostración de los servicios

1. **Autenticación:** en Cuenta, crear una cuenta o iniciar sesión. La verificación de correo depende de la configuración de Supabase. El regreso automático desde Google está preparado para Android.
2. **JSON:** sin cuenta, registrar una mascota y un cuidado, cerrar y reabrir. Los registros se recuperan desde el dispositivo. En escritorio el archivo del invitado es `data/petcare.json`; Android usa el almacenamiento privado de la app.
3. **Notificaciones:** con la app abierta, un cuidado vencido dispara un diálogo local; el sistema revisa cada 30 segundos. En Android también existen push opcionales mediante Firebase y el servidor, sujetos a cuenta, permisos, configuración y conexión. El diálogo local no es una notificación de Android programada para cuando la app está cerrada.
4. **Configuración remota:** en Inicio, esperar el consejo con «Actualizado en línea». Llega desde Supabase sin iniciar sesión y se guarda en JSON. Sin conexión se muestra el último valor guardado o un valor predeterminado. Consulta [CONFIGURACION-REMOTA.md](CONFIGURACION-REMOTA.md).

Para la demo QR público, iniciar sesión, crear una mascota y activar su chapa desde la app. La ficha web permite el contacto según las opciones elegidas; el historial médico no es público. La vista de prueba local no sustituye la ficha pública.

## Estructura y servicios

| Ruta | Función |
| --- | --- |
| `main.py`, `main.kv` | Arranque y ciclo de vida. |
| `screens/home.py`, `screens/*.kv` | Navegación, estructura visual y componentes. |
| `screens/features.py` | Formularios, cuidados y comprobación del aviso local. |
| `services/store.py` | Validación, lectura y guardado JSON con copia `.bak`. |
| `services/cloud.py`, `services/google_auth.py` | Registro, login, sesión y Google mediante Supabase Auth. |
| `screens/sync.py`, `services/backup_sync.py` | Copias y resolución de cambios de cuenta. |
| `screens/remote_config.py`, `services/remote_config.py` | Consejo remoto, actualización de UI y caché local. |
| `screens/reminders.py`, `services/reminders.py`, `services/push.py` | Calendario remoto y registro de notificaciones push. |
| `services/public_qr.py`, `services/qr_inbox.py`, `screens/qr_inbox.py` | Chapa pública y mensajes protegidos. |
| `android/` | Integraciones nativas Android. |
| `supabase/` | SQL, funciones y documentación del backend. |
| `assets/`, `tests/`, `tools/` | Recursos, pruebas y herramientas de desarrollo. |
| `buildozer.spec`, `requirements.txt` | Configuración Android y dependencias. |

## Pruebas y compilación

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Las pruebas de interfaz Kivy incluyen `tools/check_ui.py` y `tools/check_remote_config_ui.py`; esta última necesita acceso al proyecto configurado. El APK de prueba también está disponible en [la web de Mi Mascota](https://mi-mascota-web.vercel.app). Para compilar uno nuevo sigue [PROBAR_EN_ANDROID.md](PROBAR_EN_ANDROID.md). Es una compilación de prueba, no una publicación en una tienda.

## Dificultades y soluciones

- **Pantalla blanca al migrar a KV:** se revisó el orden de carga y la adición de contenido en `main.py` y `screens/home.py`; se verificó con la interfaz real de Kivy.
- **Persistencia y pérdida de sesión:** se separaron los datos locales de las cuentas, se añadieron escrituras temporales y respaldo, y se protege la sesión con almacenamiento específico del sistema. Los fallos temporales de red no deberían borrar la sesión.
- **Avisos en segundo plano:** los temporizadores de Kivy no garantizan ejecución con la app cerrada; se integraron Firebase y el backend para push. El aviso local dentro de la app tiene un alcance distinto.
- **Configuración remota sin internet:** el consejo se consulta en segundo plano, se valida y conserva una copia local; si nunca se obtuvo usa un valor predeterminado.
- **QR y privacidad:** la ficha pública se separó de los registros privados y el propietario elige las opciones de contacto. La disponibilidad y caducidad de la ficha pública dependen del servidor.

La guía de defensa del equipo está en [GUIA-EQUIPO.md](GUIA-EQUIPO.md), y la declaración de herramientas en [USO_IA.md](USO_IA.md).
