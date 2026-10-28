"""Comprueba módulos, layouts y configuración pública sin extraer datos del APK."""
import io
import json
from pathlib import Path
import sys
import tarfile
import zipfile

apk = Path(sys.argv[1])
with zipfile.ZipFile(apk) as archive:
    assert all(name.startswith('lib/arm64-v8a/') for name in archive.namelist() if name.startswith('lib/') and name.endswith('.so'))
    with tarfile.open(fileobj=io.BytesIO(archive.read('assets/private.tar'))) as private:
        names = private.getnames()
        for module in ('main', 'services/cloud', 'services/profile', 'services/public_qr',
                       'services/google_auth', 'services/mobile', 'screens/public_tag'):
            assert any(name.endswith(module + ext) for name in names for ext in ('.py', '.pyc')), module
        for layout in ('main.kv', 'screens/home.kv', 'screens/features.kv', 'screens/widgets.kv'):
            assert any(name.endswith(layout) for name in names), layout
        config_path = next(name for name in names if name.endswith('/config.json') or name == 'config.json')
        config = json.load(private.extractfile(config_path))
        assert config['SUPABASE_PUBLISHABLE_KEY'].startswith('sb_publishable_')
        assert config['SUPABASE_URL'].startswith('https://')
        assert set(config) <= {'SUPABASE_URL', 'SUPABASE_PUBLISHABLE_KEY', 'MIMASCOTA_SITE_URL',
                               'GOOGLE_SIGN_IN_ENABLED', 'FIREBASE_ENABLED', 'FIREBASE_ANDROID'}
        assert 'sb_secret_' not in json.dumps(config)
        for name in names:
            base = Path(name).name
            assert not base.startswith(('exp_', 'test_render', 'proper_screen', 'real_screen', 'shot0001')), name
            assert not '/data/' in name and not '/tests/' in name
    dex = b''.join(archive.read(name) for name in archive.namelist() if name.endswith('.dex'))
    assert b'Lorg/mimascota/FirebaseBridge;' in dex
    assert b'Lorg/mimascota/CareMessagingService;' in dex
print('PASS: app modules, KV layouts, public client config, Firebase classes and no user data/diagnostic images.')
