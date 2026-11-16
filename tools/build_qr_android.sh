#!/usr/bin/env bash
set -euo pipefail
task_root=/home/marco/MiMascotaQrContact
test "$task_root" != /home/marco/MiMascota
test ! -e "$task_root"
mkdir "$task_root"
cp -a --reflink=auto /home/marco/MiMascota/.buildozer "$task_root/.buildozer"
cd "$task_root"
unzip -q '/mnt/c/Users/marco/OneDrive/Desktop/MiMascota/apk/qr-contact-source.zip'
source /home/marco/buildozer-venv/bin/activate
buildozer android debug > '/home/marco/MiMascotaQrContact/build.log' 2>&1
cp '/home/marco/MiMascotaQrContact/bin/mimascota-0.1.8-arm64-v8a-debug.apk' '/mnt/c/Users/marco/OneDrive/Desktop/MiMascota/apk/mimascota-0.1.8-qr-protegido.apk'
printf '%s\n' 'PASS: isolated Android 0.1.8 build complete.'
