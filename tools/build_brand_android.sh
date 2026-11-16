#!/usr/bin/env bash
set -euo pipefail
task_root=/home/marco/MiMascotaBrand
test "$(realpath "$task_root")" = /home/marco/MiMascotaBrand
cd "$task_root"
unzip -qo '/mnt/c/Users/marco/OneDrive/Desktop/MiMascota/apk/brand-0.2.3-source.zip'
grep -q '^version = 0.2.3$' buildozer.spec
test -f assets/brand/icono-app.png
test -f assets/brand/arranque.png
source /home/marco/buildozer-venv/bin/activate
printf '%s\n' 'Building Android 0.2.3 with final brand assets.'
buildozer android debug > "$task_root/build-0.2.3.log" 2>&1
cp "$task_root/bin/mimascota-0.2.3-arm64-v8a-debug.apk" '/mnt/c/Users/marco/OneDrive/Desktop/MiMascota/apk/mimascota-0.2.3-logo.apk'
printf '%s\n' 'PASS: Android 0.2.3 brand build complete.'
