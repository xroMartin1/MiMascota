"""Three-way account backup merge. Concurrent edits never silently overwrite."""
from copy import deepcopy
import json
import os
from pathlib import Path
from services.store import normalize


class SyncConflict(ValueError):
    pass


def payload(data):
    clean = normalize(data)
    return {key: deepcopy(clean[key]) for key in ('version', 'pets', 'routines', 'events', 'qr_trials', 'reminder_settings')}


_MISSING = object()


def merge_value(base, local, remote):
    if local == remote:
        return local
    if local == base:
        return remote
    if remote == base:
        return local
    if all(isinstance(value, dict) for value in (base, local, remote)):
        result = {}
        for key in set(base) | set(local) | set(remote):
            merged = merge_value(base.get(key, _MISSING), local.get(key, _MISSING), remote.get(key, _MISSING))
            if merged is not _MISSING:
                result[key] = merged
        return result
    raise SyncConflict('Hay cambios distintos en el mismo registro. Tus datos siguen guardados en este teléfono.')


def merge(base, local, remote):
    result = {}
    for key in ('pets', 'routines', 'events'):
        maps = [{item['id']: item for item in value.get(key, [])} for value in (base, local, remote)]
        combined = merge_value(*maps)
        order = list(dict.fromkeys(list(maps[1]) + list(maps[2])))
        result[key] = [deepcopy(combined[item]) for item in order if item in combined]
    for key in ('qr_trials', 'reminder_settings'):
        result[key] = deepcopy(merge_value(base.get(key, {}), local.get(key, {}), remote.get(key, {})))
    # Do not retain orphaned care records if another device deleted the pet.
    pets = {pet['id'] for pet in result['pets']}
    if any(item.get('pet') and item['pet'] not in pets for key in ('routines', 'events') for item in result[key]):
        raise SyncConflict('Una mascota se eliminó en otro teléfono y tiene cuidados nuevos aquí. Revisa las dos copias.')
    result['version'] = 2
    return payload(result)


class SyncJournal:
    def __init__(self, data_file):
        self.path = Path(data_file).with_suffix('.sync.json')
        self.base = None
        if self.path.exists():
            saved = json.loads(self.path.read_text(encoding='utf-8'))
            self.base = payload(saved['base'])

    def accept(self, base):
        clean = payload(base)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix('.tmp')
        with temp.open('w', encoding='utf-8') as stream:
            json.dump({'base': clean}, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        temp.replace(self.path)
        self.base = clean


def synchronize(cloud, local, base):
    local = payload(local)
    row = cloud.download()
    remote = payload(row['data']) if row else payload({})
    revision = row['revision'] if row else 0
    if base is None:
        # An existing pre-sync copy provides no deletion history. Merge only safely.
        base = payload({})
        if local['reminder_settings'] == payload({})['reminder_settings']:
            local['reminder_settings'] = remote['reminder_settings']
        base['reminder_settings'] = remote['reminder_settings']
    merged = merge(base, local, remote)
    if merged != remote:
        result = cloud.upload(dict(merged, cloud_revision=revision))
        revision = result['revision']
    return merged, revision
