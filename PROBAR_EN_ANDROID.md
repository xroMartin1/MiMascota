# Probar PetCare en un teléfono Android

El proyecto ya tiene `buildozer.spec`. El APK **todavía no está compilado**: este equipo Windows no tiene WSL instalado. Para crear el APK usa estos pasos. El empaquetado conserva Kivy y KivyMD.

## 1. Preparar WSL en Windows

Abre PowerShell **como administrador**:

```powershell
wsl --list --online
wsl --install -d Ubuntu-24.04
```

Si `Ubuntu-24.04` no aparece en la lista, instala la versión Ubuntu disponible. Reinicia Windows si se te pide, abre Ubuntu y crea tu usuario de Linux. Comprueba que usa WSL 2 con `wsl --list --verbose`. [Microsoft explica la instalación de WSL](https://learn.microsoft.com/es-es/windows/wsl/install).

## 2. Preparar Buildozer dentro de Ubuntu 24.04

Estos comandos van en la consola de **Ubuntu**, no en PowerShell:

```bash
sudo apt update
sudo apt install -y git zip unzip rsync openjdk-17-jdk python3-pip python3-virtualenv autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo6 cmake libffi-dev libssl-dev automake autopoint gettext
virtualenv ~/buildozer-venv
source ~/buildozer-venv/bin/activate
pip install buildozer setuptools cython==0.29.34
```

La [guía de Buildozer](https://buildozer.readthedocs.io/en/latest/installation/) recomienda compilar en el sistema de archivos de WSL, no bajo `/mnt/c`.

## 3. Copiar el código y crear el APK

Todavía en Ubuntu:

```bash
mkdir -p ~/PetCareApp
rsync -a --exclude='venv/' --exclude='.venv/' --exclude='data/' --exclude='previews/' --exclude='.kivy/' --exclude='.buildozer/' --exclude='bin/' --exclude='__pycache__/' /mnt/c/Users/marco/OneDrive/Desktop/PetCareApp/ ~/PetCareApp/
cd ~/PetCareApp
source ~/buildozer-venv/bin/activate
buildozer -v android debug
```

La primera compilación descarga Android SDK/NDK y puede tardar bastante. Acepta las licencias si te las pide. Si termina bien, el APK estará en `~/PetCareApp/bin/`. La [guía oficial de Kivy](https://kivy.org/doc/stable/guide/packaging-android.html) describe este flujo con Buildozer.

Para dejar el APK accesible desde Windows:

```bash
mkdir -p /mnt/c/Users/marco/OneDrive/Desktop/PetCareApp/apk
cp bin/*.apk /mnt/c/Users/marco/OneDrive/Desktop/PetCareApp/apk/
```

## 4. Instalarlo en el teléfono

Conecta el teléfono por USB y copia el `.apk` de la carpeta `apk` a Descargas. Ábrelo desde el gestor de archivos del teléfono y autoriza la instalación desde esa app si Android lo solicita. Para usar ADB también puedes activar la depuración USB y comprobar el dispositivo con `adb devices`; [Android documenta ese proceso](https://developer.android.com/studio/run/device).

La app abrirá en modo invitado. Prueba a registrar una mascota, agregar un cuidado, cerrar y volver a abrir: los datos deben seguir allí. En Android se guardan en la carpeta privada de la app; son independientes de `data/petcare.json` de Windows. Si desinstalas el APK, esos datos pueden perderse: exporta una copia o usa una cuenta con respaldo antes de hacerlo.

La nube requiere configurar Supabase según [CONFIGURACION.md](CONFIGURACION.md). El archivo `config.json`, si existe al copiar el proyecto, se incluye en el APK; coloca sólo la **clave publicable**, nunca secretos. Las notificaciones push de Firebase y el QR público aún no funcionan en el teléfono.

Si tu teléfono es iPhone, esta ruta no genera una app iOS. Para iOS se necesita macOS y el flujo `kivy-ios`/Xcode; [Buildozer describe los requisitos](https://buildozer.readthedocs.io/en/latest/installation/#targeting-ios).
