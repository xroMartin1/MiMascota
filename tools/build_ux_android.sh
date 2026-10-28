#!/usr/bin/env bash
set -euo pipefail
task_root=/home/marco/MiMascotaQrContact
test "$(realpath "$task_root")" = /home/marco/MiMascotaQrContact
test -f "$task_root/buildozer.spec"
cd "$task_root"
unzip -qo '/mnt/c/Users/marco/OneDrive/Desktop/MiMascota/apk/qr-contact-source.zip'
grep -q '^version = 0.2.0$' buildozer.spec
source /home/marco/buildozer-venv/bin/activate
buildozer android debug > "$task_root/build-0.2.0.log" 2>&1
cp "$task_root/bin/mimascota-0.2.0-arm64-v8a-debug.apk" '/mnt/c/Users/marco/OneDrive/Desktop/MiMascota/apk/mimascota-0.2.0-ux.apk'
printf '%s\n' 'PASS: Android 0.2.0 UX and encrypted session build complete.'
