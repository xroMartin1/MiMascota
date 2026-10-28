"""Verify PDF, private sharing and Android file-provider packaging."""
import io
from pathlib import Path
import sys
import tarfile
import zipfile

with zipfile.ZipFile(sys.argv[1]) as apk:
    with tarfile.open(fileobj=io.BytesIO(apk.read('assets/private.tar'))) as bundle:
        names=bundle.getnames()
        for module in ('services/health_report','services/care_share','screens/ux'):
            assert any(n.endswith(module+ext) for n in names for ext in ('.py','.pyc')),module
        assert any('/reportlab/' in n or n.startswith('reportlab/') for n in names),'reportlab missing'
        layout=bundle.extractfile(next(n for n in names if n.endswith('screens/features.kv'))).read().decode()
        assert 'file-export-outline' in layout
        assert 'res/xml/report_paths.xml' in apk.namelist()
    dex=b''.join(apk.read(n) for n in apk.namelist() if n.endswith('.dex'))
    assert b'Landroidx/core/content/FileProvider;' in dex,'FileProvider missing'
print('PASS: PDF dependency, private share client, health export action and Android FileProvider packaged.')
