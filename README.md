# Mi Mascota

   **Mi Mascota** es una aplicación móvil y de escritorio desarrollada con **Python, Kivy y KivyMD**, diseñada para facilitar el seguimiento integral, la gestión médica y la rutina diaria de tus mascotas.

---

## Problema que resuelve

Cuidar de una o varias mascotas implica coordinar múltiples tareas: horarios de alimentación, paseos, desparasitación, administración de medicamentos, vacunación y consultas veterinarias. Al confiar en la memoria o en notas dispersas, es habitual:
- Olvidar dosis o momentos exactos de administración de medicamentos.
- Perder el seguimiento de las fechas de vacunación o desparasitación.
- Carecer de un registro médico centralizado con antecedentes de alergias, diagnósticos, síntomas y controles de peso.

**Mi Mascota** resuelve estos problemas ofreciendo un centro de control unificado e intuitivo donde puedes gestionar los perfiles de tus mascotas, programar sus cuidados recurrentes, recibir alertas y mantener un registro de salud detallado.

---

## Usuario Objetivo

- **Dueños de mascotas** (perros, gatos, etc.) que buscan una herramienta visual y organizada para asegurar el bienestar de sus animales.
- **Familias y cuidadores (Pet Sitters)** que comparten la responsabilidad de atender la rutina de una o múltiples mascotas.
- **Hogares de tránsito y rescatistas** que manejan fichas de salud e historiales médicos para varios animales de forma temporal.

---

## Características Principales

- **Gestión de Mascotas**: Creación, edición y eliminación de perfiles (nombre, especie, raza, peso, chip).
- **Rutinas y Tareas Recurrentes**: Programación de paseos, comidas, medicamentos, citas y vacunas con repetición (diaria, semanal, etc.).
- **Recordatorios Locales**: Alertas dentro de la app con avisos visuales según fecha y hora.
- **Historial Médico y de Salud**: Registro organizado por evento (vacunas, alergias, enfermedades, síntomas y controles veterinarios).
- **Almacenamiento Local de Datos**: Guardado atómico con respaldos automáticos `.bak` para evitar pérdida de información.
- **Chapa QR de Prueba**: Código escaneable por mascota, sin cuenta y sin datos privados.
- **Soporte Multiplataforma**: Funciona en PC (Windows) y está preparada para Android.

## Chapa digital QR

La chapa de **prueba local** ya funciona sin registro: crea una mascota, toca «Abrir mi chapa QR» y escanéala con otra cámara. El PNG contiene solo nombre, especie e identificador de prueba. Se guarda un período de 14 días por mascota y volver a abrir la pantalla no lo reinicia. La app oculta el QR cuando termina el período.

Esta prueba **no es una ficha pública ni un sistema de rescate**: una foto del QR seguirá siendo legible después del plazo y no permite contactar a la familia. Para la versión pública se necesita una URL por chapa, una página web de emergencia y caducidad comprobada en Supabase, nunca dentro del QR. Esa página debe mostrar solo los datos que el dueño elija y permitir enviar un mensaje sin publicar su correo ni teléfono. La compra y el envío de la placa física aún no están implementados.

La ilustración de Inicio se carga desde `assets/Placa_Icon.png`; las vistas de la placa física usan `assets/PlacaReal_Front.png` y `assets/PlacaReal_Back.png`. `assets/placa_preview.png` queda como alternativa cuando faltan las dos vistas. El QR de esos mockups es solo ilustrativo. Las decisiones visuales están en [DISENO_Y_QR.md](DISENO_Y_QR.md).

La ilustración de Rutina se carga desde `assets/MascotsBanner.png` y mantiene el texto como elemento editable de Kivy. Si falta el archivo, se usa la ilustración vectorial integrada.

---

## Instrucciones para Ejecutar

### Requisitos previos

- **Python 3.11** o **3.12** instalado.
- **Git** (opcional, para clonar el repositorio).

---

### Paso a paso desde consola (`python main.py`)

1. **Clonar el repositorio** (o descargar el código fuente):
   ```bash
   git clone https://github.com/xroMartin1/MiMascota.git
   cd MiMascota
   ```

2. **Crear y activar un entorno virtual** (recomendado):
   - **En Windows (PowerShell / CMD):**
     ```powershell
     python -m venv .venv
     .venv\Scripts\activate
     ```
   - **En Linux / macOS:**
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Ejecutar la aplicación**:
   ```bash
   python main.py
   ```

---

### Opción alternativa en Windows (`Iniciar MiMascota.bat`)

En Windows puedes hacer **doble clic** en `Iniciar MiMascota.bat`. Este script verifica el entorno de Python, crea automáticamente el entorno virtual local si no existe, instala las dependencias necesarias y ejecuta la app sin configuraciones adicionales.

---

## Pruebas Unitarias (Tests)

Para ejecutar las pruebas del sistema de persistencia y validación local:

```bash
python -m unittest discover -s tests -v
```

---

## Estructura del Proyecto

```text
MiMascota/
├── assets/                 # Recursos gráficos / iconos de la aplicación
├── screens/                # Vistas y componentes de la interfaz (Home, Formularios, Widgets)
│   ├── home.py
│   ├── features.py
│   └── widgets.py
├── services/               # Lógica de negocio, persistencia local y conectores
│   ├── store.py
│   └── cloud.py
├── tests/                  # Pruebas unitarias automatizadas
│   └── test_core.py
├── tools/                  # Scripts auxiliares de desarrollo y verificación de UI
├── supabase/               # Esquemas SQL preliminares para backend
├── main.py                 # Punto de entrada de la aplicación
├── requirements.txt        # Dependencias del proyecto (Kivy, KivyMD, etc.)
├── Iniciar MiMascota.bat   # Lanzador automático para Windows
└── README.md               # Documentación del proyecto
```

---

## Próximos Pasos (Roadmap)

- **Integración de Backend Completo**: Completar el flujo público de la chapa y la mensajería con Supabase; el registro y la copia privada ya tienen una base funcional cuando se configura el proyecto.
- **QR público con Supabase**: Publicar una ficha de emergencia, comprobar la caducidad en el servidor y recibir avisos de personas que encuentren a la mascota sin revelar los datos privados del dueño.
- **Notificaciones Push en Segundo Plano**: Integración con Firebase Cloud Messaging (FCM) para avisos en móviles sin requerir que la app esté abierta.
- **Publicación de APK Android**: Compilación oficial vía Buildozer / Docker para distribución en Android.
