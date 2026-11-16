"""Inserta componentes nativos como hijos de application antes de Gradle."""
from copy import deepcopy
from pathlib import Path
import xml.etree.ElementTree as ET

ANDROID = 'http://schemas.android.com/apk/res/android'
ET.register_namespace('android', ANDROID)


def before_apk_assemble(toolchain):
    path = Path(toolchain._dist.dist_dir) / 'src/main/AndroidManifest.xml'
    tree = ET.parse(path)
    app = tree.getroot().find('application')
    if app is None:
        raise ValueError('El manifest no contiene application')
    fragment = Path(__file__).with_name('firebase-manifest.xml').read_text(encoding='utf-8')
    additions = ET.fromstring(f'<application xmlns:android="{ANDROID}">{fragment}</application>')
    name_attr = '{' + ANDROID + '}name'
    for addition in additions:
        for existing in list(app):
            if existing.tag == addition.tag and existing.get(name_attr) == addition.get(name_attr):
                app.remove(existing)
        app.append(deepcopy(addition))
    tree.write(path, encoding='utf-8', xml_declaration=True)
    tree.write(Path(toolchain._dist.dist_dir) / 'AndroidManifest.xml', encoding='utf-8', xml_declaration=True)
    # Las AAR pueden traer otras ABI; limita el paquete a las compiladas por p4a.
    architectures = [arch.arch for arch in toolchain.ctx.archs]
    if not architectures or any(abi not in ('arm64-v8a', 'armeabi-v7a', 'x86', 'x86_64') for abi in architectures):
        raise ValueError('Arquitecturas Android inválidas')
    gradle_path = Path(toolchain._dist.dist_dir) / 'build.gradle'
    gradle = gradle_path.read_text(encoding='utf-8')
    marker = 'defaultConfig {'
    if gradle.count(marker) != 1:
        raise ValueError('No se encontró la configuración Android de Gradle')
    filters = ', '.join(repr(abi) for abi in architectures)
    gradle = gradle.replace(marker, marker + '\n        ndk { abiFilters ' + filters + ' }', 1)
    gradle_path.write_text(gradle, encoding='utf-8')
