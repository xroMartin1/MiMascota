# Mi Mascota

   **Mi Mascota** es una aplicación móvil y de escritorio desarrollada con **Python, Kivy y KivyMD**, diseñada para facilitar el seguimiento integral, la gestión médica y la rutina diaria de tus mascotas.

---

## Problema que resuelve

Cuidar de una o varias mascotas implica coordinar múltiples tareas: horarios de alimentación, paseos, desparasitación, administración de medicamentos, vacunación y consultas veterinarias. Al confiar en la memoria o en notas dispersas, es habitual:
- Olvidar dosis o momentos exactos de administración de medicamentos.
- Perder el seguimiento de las fechas de vacunación o desparasitación.
- Carecer de un registro médico centralizado con antecedentes de alergias, diagnósticos, síntomas y controles de peso.

** Mi mascota** resuelve estos problemas ofreciendo un centro de control unificado e intuitivo donde puedes gestionar los perfiles de tus mascotas, programar sus cuidados recurrentes, recibir alertas y mantener un registro de salud detallado.

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
- **Soporte Multiplataforma**: Funciona en PC (Windows) y está preparada para Android.

## Chapa Digital QR (Identificación Inteligente)

Mi Mascota incluirá un sistema de identificación digital mediante códigos QR diseñado para la seguridad de tu mascota:

- **Funcionamiento**: Cada usuario registrado podrá asociar una chapa física a su perfil de mascota. Al escanear el código QR impreso en el collar, cualquier persona que encuentre a la mascota podrá ver una página web pública de emergencia con los datos médicos relevantes y los métodos de contacto del dueño, **sin necesidad de instalar la aplicación**.
- **Privacidad y Control**: El dueño decidirá desde la app qué datos de contacto (teléfono, comuna/ciudad, notas de alergias o medicamentos críticos) serán visibles en la pantalla de emergencia al escanear el código.
- **Modelo de Adquisición**: Las chapas físicas se podrán adquirir directamente a través de la plataforma, viniendo el código QR ya preconfigurado y vinculado automáticamente a la cuenta del usuario.

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
├── Iniciar PetCare.bat     # Lanzador automático para Windows
└── README.md               # Documentación del proyecto
```

---

## Próximos Pasos (Roadmap)

- **Integración de Backend Completo**: Implementación de base de datos en la nube (Supabase / PostgreSQL) y autenticación de usuarios (Inicio de sesión / Registro).
- **Sistema de Chapa Digital QR**: Desarrollo de la generación automática de códigos QR en Python, diseño de la página web pública de emergencia para escaneo móvil y habilitación del flujo de vinculación con perfiles de mascotas.
- **Notificaciones Push en Segundo Plano**: Integración con Firebase Cloud Messaging (FCM) para avisos en móviles sin requerir que la app esté abierta.
- **Publicación de APK Android**: Compilación oficial vía Buildozer / Docker para distribución en Android.
