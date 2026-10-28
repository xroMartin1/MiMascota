"""Verify UX pages and native encrypted session support in the Android artifact."""
import io
import sys
import tarfile
import zipfile

with zipfile.ZipFile(sys.argv[1]) as apk:
    with tarfile.open(fileobj=io.BytesIO(apk.read('assets/private.tar'))) as private:
        names=private.getnames()
        for module in ('screens/ux','services/session_storage'):
            assert any(name.endswith(module+ext) for name in names for ext in ('.py','.pyc')),module
        ux=private.extractfile(next(n for n in names if n.endswith('screens/ux.kv'))).read().decode()
        assert 'UxNotice' in ux and 'UxComposer' in ux and 'UxQr' in ux
        assert "icon: 'pencil-outline'" in ux
        features=private.extractfile(next(n for n in names if n.endswith('screens/features.kv'))).read().decode()
        loading=features[features.index('<NetworkWait'):]
        assert 'MDSpinner:' in loading and 'Conectando' not in loading
    dex=b''.join(apk.read(n) for n in apk.namelist() if n.endswith('.dex'))
    assert b'Lorg/mimascota/SessionVault;' in dex
    assert b'AndroidKeyStore' in dex and b'AES/GCM/NoPadding' in dex
print('PASS: new UX pages, inline reply, enlarged QR, pencil, spinner-only wait and native encrypted session vault in APK.')
