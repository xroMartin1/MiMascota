"""Create an isolated Android source snapshot, excluding accounts and build caches."""
from pathlib import Path
import zipfile
import re
import sys

version = sys.argv[1] if len(sys.argv) > 1 else '0.1.8'
if not re.fullmatch(r'\d+\.\d+\.\d+', version):
    raise ValueError('Invalid Android version')

root = Path(__file__).resolve().parents[1]
excluded = {'.git', '.venv', 'venv', '.kivy', '.buildozer', 'bin', 'apk', 'previews',
            'tests', 'tools', 'data', '__pycache__', 'supabase', '.codex', '.agents'}
suffixes = {'.py', '.kv', '.png', '.jpg', '.jpeg', '.json', '.ttf', '.java', '.xml'}
filename = sys.argv[2] if len(sys.argv) > 2 else 'qr-contact-source.zip'
if Path(filename).name != filename or not filename.endswith('.zip'):
    raise ValueError('Invalid snapshot filename')
target = root / 'apk' / filename
with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in root.rglob('*'):
        rel = path.relative_to(root)
        if not path.is_file() or any(part in excluded for part in rel.parts):
            continue
        if path.name == 'google-services.json' or path.name.startswith(('exp_', 'test_render', 'proper_screen', 'real_screen', 'shot')):
            continue
        if path.suffix not in suffixes and path.name not in {'buildozer.spec', 'requirements.txt'}:
            continue
        if path.name == 'buildozer.spec':
            source = re.sub(r'^version\s*=.*$', 'version = ' + version, path.read_text(encoding='utf-8'), count=1, flags=re.MULTILINE)
            assert 'version = ' + version in source
            archive.writestr(str(rel).replace('\\', '/'), source)
        else:
            archive.write(path, str(rel).replace('\\', '/'))
print('Isolated snapshot:', target.name)
