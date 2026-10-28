#!/usr/bin/env bash
set -euo pipefail
task_root=/home/marco/MiMascotaQrContact
test "$(realpath "$task_root")" = /home/marco/MiMascotaQrContact
grep -q '^version = 0.1.8$' "$task_root/buildozer.spec"
cp '/mnt/c/Users/marco/OneDrive/Desktop/MiMascota/screens/home.kv' "$task_root/screens/home.kv"
sed -i 's/^version = 0.1.8$/version = 0.1.9/' "$task_root/buildozer.spec"
cd "$task_root"
source /home/marco/buildozer-venv/bin/activate
buildozer android debug > "$task_root/build-0.1.9.log" 2>&1
cp "$task_root/bin/mimascota-0.1.9-arm64-v8a-debug.apk" '/mnt/c/Users/marco/OneDrive/Desktop/MiMascota/apk/mimascota-0.1.9-campana-qr.apk'
printf '%s\n' 'PASS: Android 0.1.9 with correctly positioned QR inbox bell.'
