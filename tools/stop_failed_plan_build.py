"""Stop only the failed toolchain using this task's dedicated storage directory."""
import os
from pathlib import Path
import signal
import sys
root=Path('/home/marco/MiMascotaBrand').resolve()
assert str(root)=='/home/marco/MiMascotaBrand'
matches=[]
for proc in Path('/proc').iterdir():
    if not proc.name.isdecimal():
        continue
    try:
        args=(proc/'cmdline').read_bytes().decode().replace('\0',' ')
        if ('-m pythonforandroid.toolchain create ' in args and
            '--storage-dir='+str(root / '.buildozer/android/platform/build-arm64-v8a') in args):
            matches.append(int(proc.name))
    except (OSError,UnicodeError):
        continue
for pid in matches:
    os.kill(pid,signal.SIGTERM)
print('Stopped failed task toolchain processes:',len(matches))
