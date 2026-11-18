"""Android boundaries without a device: Parcelable extras and private provider paths."""
import importlib.util
from configparser import ConfigParser
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import xml.etree.ElementTree as ET

from services.health_report import share_health_report


class AndroidSharingTests(unittest.TestCase):
    def test_pdf_and_statistics_send_parcelable_stream_with_read_grant(self):
        # JNI overload resolution needs an exact Parcelable type, not a raw Uri.
        for mime, title in [('application/pdf', 'Resumen de salud'),
                            ('application/json', 'Estadísticas de uso')]:
            with self.subTest(mime=mime):
                raw_uri, parcelable = object(), object()
                activity, intent = Mock(), Mock()
                activity.getPackageName.return_value = 'org.mimascota.mimascota'
                def put_extra(key, value):
                    if value is not parcelable:
                        raise TypeError('Invalid Uri instance for selected putExtra overload')
                intent.putExtra.side_effect = put_extra
                intent_class = Mock(return_value=intent)
                labels = {title: object(), 'Compartir archivo': object()}
                chooser = object()
                def create_chooser(send, label):
                    if label is not labels['Compartir archivo']:
                        raise TypeError('No matching createChooser CharSequence overload')
                    return chooser
                intent_class.createChooser.side_effect = create_chooser
                provider, clip = Mock(), Mock()
                provider.getUriForFile.return_value = raw_uri
                classes = {'org.kivy.android.PythonActivity': SimpleNamespace(mActivity=activity),
                           'java.io.File': Mock(), 'androidx.core.content.FileProvider': provider,
                           'android.content.Intent': intent_class, 'android.content.ClipData': clip,
                           'java.lang.String': lambda value: SimpleNamespace(value=value)}
                def cast(name, value):
                    if name == 'android.os.Parcelable':
                        self.assertIs(value, raw_uri)
                        return parcelable
                    self.assertEqual(name, 'java.lang.CharSequence')
                    return labels[value.value]
                jnius = SimpleNamespace(autoclass=classes.__getitem__, cast=cast)
                with patch('kivy.utils.platform', 'android'), patch.dict('sys.modules', jnius=jnius):
                    share_health_report(Path('private-cache/report'), mime=mime, title=title)
                intent.setAction.assert_called_once_with('android.intent.action.SEND')
                intent.setType.assert_called_once_with(mime)
                intent.putExtra.assert_called_once_with('android.intent.extra.STREAM', parcelable)
                clip.newRawUri.assert_called_once_with(labels[title], raw_uri)
                intent_class.createChooser.assert_called_once_with(intent, labels['Compartir archivo'])
                intent.setClipData.assert_called_once_with(clip.newRawUri.return_value)
                intent.addFlags.assert_called_once_with(1)
                activity.startActivity.assert_called_once_with(chooser)
                provider.getUriForFile.assert_called_once_with(
                    activity, 'org.mimascota.mimascota.files', classes['java.io.File'].return_value)

    def test_share_diagnostic_does_not_expose_exception_paths_or_content(self):
        error = RuntimeError('PRIVATE /cache/pet-name.pdf content://private/token')
        jnius = SimpleNamespace(autoclass=Mock(side_effect=error), cast=Mock())
        with patch('kivy.utils.platform', 'android'), patch.dict('sys.modules', jnius=jnius):
            with self.assertRaisesRegex(RuntimeError, '^share-init-RuntimeError$') as caught:
                share_health_report('PRIVATE path')
        self.assertEqual(caught.exception.code, 'share-init-RuntimeError')
        self.assertIs(caught.exception.__cause__, error)

    def test_desktop_still_opens_local_file(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / 'resumen.pdf'
            path.write_bytes(b'%PDF-')
            with patch('kivy.utils.platform', 'win'), patch('webbrowser.open') as opened:
                share_health_report(path)
            opened.assert_called_once_with(path.resolve().as_uri())

    def test_build_hook_registers_private_provider_for_both_export_folders(self):
        root = Path(__file__).resolve().parents[1]
        config = ConfigParser(interpolation=None)
        config.read(root / 'buildozer.spec', encoding='utf-8')
        spec = importlib.util.spec_from_file_location('sharing_build_hook', root / config['app']['p4a.hook'])
        hook = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(hook)
        with TemporaryDirectory() as folder:
            dist = Path(folder)
            manifest = dist / 'src/main/AndroidManifest.xml'
            manifest.parent.mkdir(parents=True)
            manifest.write_text('<manifest package="org.mimascota.mimascota"><application /></manifest>')
            (dist / 'build.gradle').write_text('android { defaultConfig { } }')
            hook.before_apk_assemble(SimpleNamespace(_dist=SimpleNamespace(dist_dir=folder),
                                      ctx=SimpleNamespace(archs=[SimpleNamespace(arch='arm64-v8a')])))
            android = '{http://schemas.android.com/apk/res/android}'
            provider = next(p for p in ET.parse(manifest).findall('./application/provider')
                            if p.get(android + 'name') == 'androidx.core.content.FileProvider')
            self.assertEqual(provider.get(android + 'authorities'), 'org.mimascota.mimascota.files')
            package = config['app']['package.domain'] + '.' + config['app']['package.name']
            self.assertEqual(provider.get(android + 'authorities'), package + '.files')
            self.assertEqual(provider.get(android + 'exported'), 'false')
            self.assertEqual(provider.get(android + 'grantUriPermissions'), 'true')
            metadata = provider.find('meta-data')
            self.assertEqual(metadata.get(android + 'name'), 'android.support.FILE_PROVIDER_PATHS')
            self.assertEqual(metadata.get(android + 'resource'), '@xml/report_paths')
            resources = dict(entry.strip().rsplit(':', 1)[::-1]
                             for entry in config['app']['android.add_resources'].split(','))
            paths = ET.parse(root / resources['xml'] / 'report_paths.xml').getroot()
            self.assertEqual([(p.tag, p.get('path')) for p in paths],
                             [('cache-path', 'health-reports/'), ('cache-path', 'usage-exports/')])
            self.assertEqual(manifest.read_bytes(), (dist / 'AndroidManifest.xml').read_bytes())
