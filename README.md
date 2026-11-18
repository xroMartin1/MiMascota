# Mi Mascota

Mi Mascota es una aplicación desarrollada con Python, Kivy y KivyMD para organizar mascotas, cuidados e historial de salud. Ayuda a recordar tareas y ofrece una chapa QR: al escanear una ficha pública activa, quien encuentra una mascota puede contactar a su familia mediante las opciones autorizadas por el propietario.

Puede usarse sin cuenta para guardar información en el dispositivo. La cuenta habilita funciones en la nube. La versión actual es **0.2.17**, disponible como APK de prueba desde [la web de Mi Mascota](https://mi-mascota-web.vercel.app). Los pagos utilizan Transbank en modo de integración; no hay cobros reales ni un flujo de envío de chapas físicas.

## Qué incluye

- Perfiles con selección de raza, retratos asociados, edad y peso; agenda de cuidados e historial de salud privado.
- Chapa QR pública con contacto protegido y mensajes. Cada cuenta dispone de una prueba de 14 días para una mascota; borrar su perfil no reinicia la prueba.
- Premium con renovación mensual manual, confirmación del pago, distintivo de cuenta y acceso a cuidados compartidos y resumen PDF. La app explica cuándo falta crear la chapa y protege la eliminación de una mascota con Premium activo.
- Notificaciones push opcionales en Android y controles en **Cuenta → Notificaciones**. No se necesita escribir un número de teléfono para activar estos avisos.
- Estadísticas opcionales con Firebase Analytics y un registro JSON local exportable. El sitio web tiene un dashboard privado mediante código del equipo, con tres KPIs y sus metas, usuarios, sesiones, tiempos, pantallas y eventos.
- Interfaz con fondo blanco, retratos por raza y animaciones breves. El indicador de navegación se desplaza entre pestañas y se respeta la preferencia de movimiento reducido.

## Requisitos

- Windows 10/11 con Python 3.11 o 3.12 y Git. Internet es necesario para instalar dependencias y utilizar servicios remotos.
- Para Android: teléfono arm64-v8a con Android 7 o superior. Para compilar, Linux o WSL 2 con Ubuntu, Java y Buildozer; ver [PROBAR_EN_ANDROID.md](PROBAR_EN_ANDROID.md).
- Para probar la nube se necesita la URL y la clave publicable del proyecto de Supabase de evaluación. El ejemplo contiene marcadores que deben completarse; nunca incluyas claves de servidor ni archivos de cuenta de servicio.

## Instalación y ejecución en Windows

1. Instala Python 3.12 o 3.11, incluyendo el lanzador `py`, y Git.
2. En PowerShell:

   ```powershell
   git clone https://github.com/xroMartin1/MiMascota.git
   cd MiMascota
   Copy-Item config.example.json config.json
   ```

3. Abre `config.json` y reemplaza los marcadores de Supabase con la URL y la clave publicable proporcionadas por el equipo. Para Firebase en Android, sigue [ANDROID-SERVICIOS.md](ANDROID-SERVICIOS.md).
4. Abre `Iniciar MiMascota.bat`. La primera vez crea un entorno propio e instala los paquetes; puede tardar varios minutos. Las siguientes veces reutiliza el entorno.

Alternativamente, ejecuta manualmente:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Si utilizas Python 3.11, sustituye `-3.12` por `-3.11`. Para ejecutar solo el modo invitado, la app también abre sin `config.json`, pero autenticación, QR público y configuración remota necesitan una configuración válida y conexión.

Si se usa otro proyecto de Supabase, reemplaza URL y clave publicable en `config.json` y prepara el backend con la documentación de `supabase/`. La conexión al proyecto de evaluación depende de que siga disponible y configurado; copiar el ejemplo no instala ni despliega un servidor nuevo ni proporciona las claves del equipo.

## Demostración de los servicios

1. **Autenticación:** en Cuenta, crear una cuenta o iniciar sesión. La verificación de correo depende de la configuración de Supabase. El regreso automático desde Google está preparado para Android.
2. **JSON:** sin cuenta, registrar una mascota y un cuidado, cerrar y reabrir. Los registros se recuperan desde el dispositivo. En escritorio el archivo del invitado es `data/petcare.json`; Android usa el almacenamiento privado de la app.
3. **Notificaciones:** con la app abierta, un cuidado vencido dispara un diálogo local; el sistema revisa cada 30 segundos. En Android también existen push opcionales mediante Firebase y el servidor, sujetos a cuenta, permisos, configuración y conexión. El diálogo local no es una notificación de Android programada para cuando la app está cerrada.
4. **Configuración remota:** en Inicio, consultar «Consejo de cuidado». Llega desde Supabase sin iniciar sesión y se guarda en JSON; no se muestra un estado técnico de actualización al usuario. Sin conexión se muestra el último valor guardado o un valor predeterminado. Consulta [CONFIGURACION-REMOTA.md](CONFIGURACION-REMOTA.md).

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
| `services/subscription.py`, `screens/billing.py` | Estado Premium, checkout Webpay y confirmación del periodo. |
| `services/measurement.py`, `screens/measurement.py` | Consentimiento, eventos permitidos y exportación JSON de estadísticas. |
| `services/health_report.py` | Generación PDF y menú de compartir PDF/JSON, con URI privada y permiso temporal en Android. |
| `android/` | Integraciones nativas Android. |
| `supabase/` | SQL, funciones y documentación del backend. |
| `assets/`, `tests/`, `tools/` | Recursos, pruebas y herramientas de desarrollo. |
| `buildozer.spec`, `requirements.txt` | Configuración Android y dependencias. |

## Pruebas y compilación

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Las pruebas de interfaz Kivy incluyen `tools/check_ui.py` y `tools/check_remote_config_ui.py`; esta última necesita acceso al proyecto configurado. El APK de prueba también está disponible en [la web de Mi Mascota](https://mi-mascota-web.vercel.app). Para compilar uno nuevo sigue [PROBAR_EN_ANDROID.md](PROBAR_EN_ANDROID.md). Es una compilación de prueba, no una publicación en una tienda.

En 0.2.17 se corrigieron los tipos Java usados para abrir el selector de compartir PDF y JSON. La comprobación local ejecutó **169 pruebas** y reprodujo las llamadas con Pyjnius y una API Java de prueba. Esto no reemplaza la comprobación en un teléfono: si falla, el diálogo muestra un código de soporte sin incluir rutas, nombres de archivos ni contenido privado.

## Dificultades y soluciones

- **Pantalla blanca al migrar a KV:** se revisó el orden de carga y la adición de contenido en `main.py` y `screens/home.py`; se verificó con la interfaz real de Kivy.
- **Persistencia y pérdida de sesión:** se separaron los datos locales de las cuentas, se añadieron escrituras temporales y respaldo, y se protege la sesión con almacenamiento específico del sistema. Los fallos temporales de red no deberían borrar la sesión.
- **Avisos en segundo plano:** los temporizadores de Kivy no garantizan ejecución con la app cerrada; se integraron Firebase y el backend para push. El aviso local dentro de la app tiene un alcance distinto.
- **Configuración remota sin internet:** el consejo se consulta en segundo plano, se valida y conserva una copia local; si nunca se obtuvo usa un valor predeterminado.
- **QR y privacidad:** la ficha pública se separó de los registros privados y el propietario elige las opciones de contacto. La disponibilidad y caducidad de la ficha pública dependen del servidor.

La guía de defensa del equipo está en [GUIA-EQUIPO.md](GUIA-EQUIPO.md), y la declaración de herramientas en [USO_IA.md](USO_IA.md).

## Suscripción de prueba

En **Cuenta → Ver Premium**, o desde **Chapa → Ver Premium**, está el checkout de prueba de **Webpay Plus**: $3.990 CLP por mes, con renovación manual y asociado a la chapa de la mascota elegida. Solo usar tarjetas de integración de Transbank; nunca tarjetas personales. La app consulta al servidor antes de confirmar el periodo. Preparación, código del backend y límites en [PAGOS-DE-PRUEBA.md](PAGOS-DE-PRUEBA.md).

La primera compra incluye la chapa física y las renovaciones mantienen el servicio. La confirmación muestra la mascota con una animación breve; el perfil conserva un distintivo mientras haya Premium vigente en la cuenta. El nombre de la placa de producto se dibuja con los datos de la mascota, sin generar una imagen por nombre. La entrega física no tiene un flujo logístico implementado en esta beta.

`services/subscription.py` realiza solicitudes autenticadas a `webpay-payments`; `screens/billing.py` muestra el estado y abre el checkout del sitio propio. No pide correo de comprador ni autoriza cobros automáticos. El backend y las rutas web se entregan en la rama correspondiente de MiMascotaWeb; requieren configurar y desplegar antes de usar este cliente.

## Medición y evaluación MJV

En **Cuenta → Privacidad y estadísticas**, también disponible para invitado, se puede elegir compartir estadísticas, confirmar la zona horaria, participar en una prueba de uso y exportar los datos mínimos. Es opcional: rechazarlo no deshabilita el cuidado local. Firebase Analytics recibe solo eventos y parámetros permitidos; el registro local permite calcular KPIs reproducibles sin BigQuery ni otro servicio de pago.

Protocolo, fórmulas, diccionario y comandos de informes: [MEDICION-MJV.md](MEDICION-MJV.md). Arquitectura, evidencia y límites para la defensa: [DOCUMENTATION.md](DOCUMENTATION.md). Los informes necesitan datos realmente recogidos; no se incluyen resultados inventados.

El JSON local conserva el detalle necesario para evaluar **Medir, Juzgar y Validar**. El dashboard consulta datos agregados de GA4 desde su servidor, sin pedir una sesión de Google a quien lo visita. Usuarios activos, cuidados marcados y porcentaje de guardados exitosos se comparan con metas del mismo periodo de siete días. Un resultado ausente queda pendiente; no se convierte en un éxito ni en cero. La configuración del panel se documenta en [MiMascotaWeb](https://github.com/Marcos0o0/MiMascotaWeb/blob/main/docs/DASHBOARD.md).

## Antes de publicar como producto

La app se entrega como **beta**, no como un producto con todos sus servicios de producción validados. Falta confirmar en Android físico la exportación PDF/JSON de 0.2.17, los permisos y la entrega de notificaciones en segundo plano. Las pruebas automatizadas y las capturas con datos de ejemplo no sustituyen esas comprobaciones.

Para aceptar pagos reales se necesita habilitar producción con Transbank y completar la gestión de entrega de la chapa física. Las metas MJV deben evaluarse con datos consentidos y participantes reales; las simulaciones no demuestran adopción ni impacto. Deben revisarse también firma y distribución del APK, copias de seguridad y funcionamiento de los servicios con la configuración final.
