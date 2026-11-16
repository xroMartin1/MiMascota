"""Verify the exact inbox layout/modules and Java QR handler shipped in the APK."""
import io
from pathlib import Path
import sys
import tarfile
import zipfile

with zipfile.ZipFile(sys.argv[1]) as archive:
    with tarfile.open(fileobj=io.BytesIO(archive.read('assets/private.tar'))) as private:
        names = private.getnames()
        for module in ('services/qr_inbox', 'screens/qr_inbox'):
            assert any(name.endswith(module + ext) for name in names for ext in ('.py', '.pyc')), module
        layout = next(name for name in names if name.endswith('screens/qr_inbox.kv'))
        content = private.extractfile(layout).read().decode()
        assert 'QrInboxLabel' in content and 'markup: False' in content
        home = next(name for name in names if name.endswith('screens/home.kv'))
        home_content = private.extractfile(home).read().decode()
        assert 'qr_unread_badge' in home_content
        assert "pos_hint: {'x': 0, 'y': 0}" in home_content
    dex = b''.join(archive.read(name) for name in archive.namelist() if name.endswith('.dex'))
    assert b'Lorg/mimascota/QrContactNotifications;' in dex
    assert b'qr_contact_messages' in dex
print('PASS: QR inbox modules, corrected plaintext bubbles, unread badge and native push channel included.')
