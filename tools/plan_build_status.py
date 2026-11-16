"""Compact compilation progress; discard download counters and environment dumps."""
from pathlib import Path
import re
import sys
version=sys.argv[1] if len(sys.argv)>1 else '0.2.5'
if not re.fullmatch(r'\d+\.\d+\.\d+',version): raise ValueError('Invalid version')
path=Path('/home/marco/MiMascotaBrand/build-'+version+'.log')
if not path.exists():
    print('Build log not created yet.')
else:
    lines=[re.sub(r'\x1b\[[0-9;]*m','',line) for line in path.read_text(errors='replace').splitlines()]
    lines=[re.sub(r'\[(INFO|ERROR|DEBUG)\s*\]',r'[\1]',line) for line in lines]
    useful=[line[:220] for line in lines if any(marker in line for marker in ('[INFO]', 'BUILD SUCCESSFUL','BUILD FAILED','ERROR:', 'error:', 'Traceback','Exception')) and not any(skip in line for skip in ('ENVIRONMENT',' -I',' -L','clang -'))]
    print('\n'.join(useful[-10:]))
