"""Genera recursos Android desde configuración pública de Firebase; no admite claves de servidor."""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

PACKAGE = 'org.mimascota.mimascota'


def parse_config(data):
    if data.get('type') == 'service_account' or 'private_key' in data:
        raise ValueError('Este archivo es una credencial de servidor. No se puede incluir en la app.')
    project = data['project_info']
    matches = [c for c in data['client'] if c['client_info']['android_client_info']['package_name'] == PACKAGE]
    if len(matches) != 1:
        raise ValueError('Registra el paquete ' + PACKAGE + ' en Firebase.')
    client = matches[0]
    result = dict(app_id=client['client_info']['mobilesdk_app_id'], api_key=client['api_key'][0]['current_key'],
                  project_id=project['project_id'], sender_id=project['project_number'])
    if not all(isinstance(value, str) and value.strip() for value in result.values()):
        raise ValueError('Configuración pública incompleta.')
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('file', type=Path, help='google-services.json del cliente Android')
    args = parser.parse_args()
    config = parse_config(json.loads(args.file.read_text(encoding='utf-8')))
    root = Path(__file__).resolve().parents[1]
    resources = ET.Element('resources')
    for key, source in {'google_app_id': 'app_id', 'google_api_key': 'api_key',
                        'project_id': 'project_id', 'gcm_defaultSenderId': 'sender_id'}.items():
        ET.SubElement(resources, 'string', {'name': key, 'translatable': 'false'}).text = config[source]
    output = root / 'android/res/values/google-services.xml'
    ET.ElementTree(resources).write(output, encoding='utf-8', xml_declaration=True)
    path = root / 'config.json'
    app = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    app.update(FIREBASE_ANDROID=config, FIREBASE_ENABLED=True)
    path.write_text(json.dumps(app, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Configuración Android guardada localmente. No se activó analítica ni notificaciones del usuario.')


if __name__ == '__main__':
    main()
