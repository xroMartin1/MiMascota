#!/usr/bin/env bash
set -euo pipefail
task_root=/home/marco/MiMascotaBrand
test "$(realpath "$task_root")" = /home/marco/MiMascotaBrand
test -f "$task_root/buildozer.spec"
cd "$task_root"
unzip -qo '/mnt/c/Users/marco/OneDrive/Desktop/MiMascota/apk/plan-0.2.5-source.zip'
grep -q '^version = 0.2.5$' buildozer.spec
source /home/marco/buildozer-venv/bin/activate
buildozer android debug > "$task_root/build-0.2.5.log" 2>&1
cp "$task_root/bin/mimascota-0.2.5-arm64-v8a-debug.apk" '/mnt/c/Users/marco/OneDrive/Desktop/MiMascota/apk/mimascota-0.2.5-cuidados-compartidos.apk'
printf '%s\n' 'PASS: Android 0.2.5 build complete.'
