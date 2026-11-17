"""Opt-in evaluation ledger. Only fixed, aggregate fields leave this device."""
from datetime import datetime, timedelta, timezone
from functools import wraps
import hashlib
import hmac
import json
import math
import os
from pathlib import Path
from time import monotonic
import uuid
from zoneinfo import ZoneInfo

SCREENS = ('Inicio', 'Mascotas', 'Chapa', 'Rutina', 'Salud', 'Cuenta', 'Avisos', 'Premium')
OPERATIONS = ('pet', 'care', 'health', 'account')
RESULTS = ('success', 'validation', 'failed', 'abandoned')
EVENTS = {
    'screen_view': {'screen': SCREENS},
    'interaction': {'screen': SCREENS},
    'screen_time': {'screen': SCREENS, 'active_seconds': None, 'idle_seconds': None},
    'save_attempt': {'operation': OPERATIONS},
    'save_result': {'operation': OPERATIONS, 'result': RESULTS},
    'care_complete': {'result': ('completed', 'undo')},
    'payment_result': {'result': ('approved', 'rejected', 'cancelled', 'pending', 'expired', 'failed')},
    'usage_error': {'code': ('storage', 'network', 'validation', 'auth', 'payment')},
    'pet_saved': {},
}


def valid_event(name, params):
    if name not in EVENTS or not isinstance(params, dict) or set(params) != set(EVENTS[name]):
        return False
    return all((type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 2147483647)
               if choices is None else type(value) is str and value in choices
               for key, choices in EVENTS[name].items() for value in (params[key],))


def utcnow():
    return datetime.now(timezone.utc)


def stamp(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if value.tzinfo is None:
        raise ValueError('Evaluation periods require a timezone')
    return value.astimezone(timezone.utc)


def optional(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception:
            # Evaluation must never interrupt functional persistence or care.
            return False
    return wrapped


class Measurement:
    def __init__(self, path, sender=None):
        self.path, self.sender = Path(path), sender
        self.enabled = False
        self.ledger = {}
        self.current = None
        self.foreground = True
        self.tick = self.last_touch = monotonic()
        self.zone = datetime.now().astimezone().tzinfo

    @optional
    def configure(self, enabled, data=None):
        if not enabled:
            self.enabled = False
            self.ledger = {}
            self.current = None
            self.path.unlink(missing_ok=True)
            self.path.with_suffix('.tmp').unlink(missing_ok=True)
            return True
        if not self.enabled:
            self.ledger = (json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else
                           {'version': 1, 'salt': uuid.uuid4().hex, 'events': [], 'segments': [], 'completions': [],
                            'participants': [], 'coverage_start': utcnow().isoformat()})
            self.ledger.setdefault('dataset_id', uuid.uuid4().hex)
            self.enabled = True
            self.tick = self.last_touch = monotonic()
        self._persist()
        if data is not None:
            self.observe(data)
        return True

    def _persist(self):
        cutoff = utcnow() - timedelta(days=30)
        self.ledger['coverage_start'] = max(stamp(self.ledger['coverage_start']), cutoff).isoformat()
        for key in ('events', 'completions', 'participants'):
            self.ledger[key] = [r for r in self.ledger[key] if stamp(r['at']) >= cutoff]
        self.ledger['segments'] = [s for s in self.ledger['segments']
                                   if s['end'] is None or stamp(s['end']) >= cutoff]
        for segment in self.ledger['segments']:
            segment['start'] = max(stamp(segment['start']), cutoff).isoformat()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix('.tmp')
        with temp.open('w', encoding='utf-8') as stream:
            json.dump(self.ledger, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, self.path)

    def _ref(self, task_id):
        key = self._context().get('participant') or self.ledger['salt']
        return hmac.new(key.encode(), str(task_id).encode(), hashlib.sha256).hexdigest()

    def _due(self, value):
        value = datetime.fromisoformat(value)
        return value.replace(tzinfo=self.zone).isoformat() if value.tzinfo is None else value.isoformat()

    def _context(self):
        participant = self.ledger.get('participant')
        record = next((p for p in self.ledger['participants'] if p['participant'] == participant), None)
        return {'participant': participant, 'cohort': record['cohort']} if record else {}

    @optional
    def event(self, name, **params):
        if not self.enabled or not valid_event(name, params):
            return False
        row = {'at': utcnow().isoformat(), 'name': name, 'params': params}
        row.update(self._context())
        self.ledger['events'].append(row)
        self._persist()
        if self.sender:
            try:
                self.sender(name, params)
            except Exception:
                pass
        return True

    @optional
    def enroll(self, participant=None, cohort='evaluation', new_participant=True):
        if not self.enabled or cohort not in ('evaluation', 'team'):
            return False
        participant = participant or uuid.uuid4().hex
        if not isinstance(participant, str) or len(participant) != 32 or any(c not in '0123456789abcdef' for c in participant):
            return False
        existing = next((p for p in self.ledger['participants'] if p['participant'] == participant), None)
        if existing and (existing['cohort'] != cohort or existing['new'] != bool(new_participant)):
            return False
        self._flush()
        if not existing:
            self.ledger['participants'].append({'at': utcnow().isoformat(), 'participant': participant,
                                               'cohort': cohort, 'new': bool(new_participant)})
        if self.ledger.get('participant') != participant:
            self.ledger['participant'] = participant
            now = utcnow().isoformat()
            for old in list(self.ledger['segments']):
                if old['end'] is None:
                    old['end'] = now
        self._persist()
        return participant

    def _flush(self):
        now = monotonic()
        if self.enabled and self.foreground and self.current and now > self.tick:
            active = max(0, min(now, self.last_touch + 30) - self.tick)
            self.event('screen_time', screen=self.current, active_seconds=active,
                       idle_seconds=now - self.tick - active)
        self.tick = now

    @optional
    def screen(self, name):
        if not self.enabled or name not in SCREENS or self.current == name:
            return False
        self._flush()
        self.current = name
        self.last_touch = monotonic()
        return self.event('screen_view', screen=name)

    @optional
    def touch(self):
        if not self.enabled or not self.foreground:
            return False
        self._flush()
        self.last_touch = monotonic()
        if self.current:
            return self.event('interaction', screen=self.current)

    @optional
    def pause(self):
        self._flush()
        self.foreground = False

    @optional
    def resume(self):
        self.foreground = True
        self.tick = self.last_touch = monotonic()

    @optional
    def observe(self, data):
        if not self.enabled:
            return False
        settings = data.get('reminder_settings', {})
        zone = settings.get('timezone') if settings.get('enabled') else data.get('measurement_timezone')
        self.zone = ZoneInfo(zone) if zone else datetime.now().astimezone().tzinfo
        now = utcnow().isoformat()
        current = {s['task']: s for s in self.ledger['segments'] if s['end'] is None}
        seen = set()
        for task in data.get('routines', []):
            ref = self._ref(task['id'])
            seen.add(ref)
            due = self._due(task['due_at']) if task.get('due_at') else None
            repeat = task.get('repeat', 'No')
            old = current.get(ref)
            if old and (old['due'] == due and old['repeat'] == repeat):
                continue
            # A completion advances the functional cursor; keep its original recurrence interval.
            advanced = old and due and old['due'] and repeat == old['repeat'] and repeat != 'No' and any(
                c['task'] == ref and not c['undo'] and c['due'] == old.get('cursor', old['due'])
                for c in self.ledger['completions'])
            if advanced and stamp(due) > stamp(old['due']):
                old['cursor'] = due
                continue
            if old:
                old['end'] = now
                old['cancelled'] = True
            if not task.get('done'):
                self.ledger['segments'].append({'task': ref, 'due': due, 'repeat': repeat, 'start': now,
                                                'end': None, 'zone': str(self.zone), **self._context()})
        for ref, old in current.items():
            if ref not in seen:
                old['end'] = now
                old['cancelled'] = True
        self._persist()
        return True

    @optional
    def care_completed(self, task_id, due_at, undo=False):
        if not self.enabled:
            return False
        self.ledger['completions'].append({'at': utcnow().isoformat(), 'task': self._ref(task_id),
                                           'due': self._due(due_at) if due_at else None, 'undo': bool(undo), **self._context()})
        self._persist()
        return self.event('care_complete', result='undo' if undo else 'completed')

    @optional
    def export(self, path):
        if not self.enabled:
            return False
        target = Path(path)
        if target.resolve() == self.path.resolve():
            return False
        self._flush()
        self._persist()
        payload = {k: v for k, v in self.ledger.items() if k != 'salt'}
        payload['exported_at'] = utcnow().isoformat()
        temp = target.with_suffix(target.suffix + '.tmp')
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(temp, target)
        return target

    def summary(self, start, end, cohort=None):
        start, end = stamp(start), stamp(end)
        if end < start:
            raise ValueError('Evaluation period ends before it starts')
        if self.enabled:
            self._flush()
            self._persist()
        ledger = self.ledger
        if cohort is not None:
            if cohort not in ('team', 'evaluation'):
                raise ValueError('Unknown cohort')
            ledger = dict(ledger)
            for key in ('events', 'segments', 'completions', 'participants'):
                ledger[key] = [r for r in ledger.get(key, []) if r.get('cohort') == cohort]
        rows = [r for r in ledger.get('events', []) if start <= stamp(r['at']) < end]
        coverage_end = stamp(ledger['exported_at']) if ledger.get('exported_at') else utcnow()
        eligible = set()
        for segment in ledger.get('segments', []):
            if not segment['due']:
                continue
            lower = max(start, stamp(segment['start']))
            closed = (stamp(segment['end']) + timedelta(microseconds=int(segment.get('cancelled', False)))) if segment['end'] else end
            upper = min(end, coverage_end + timedelta(microseconds=1), closed)
            due = datetime.fromisoformat(segment['due'])
            if segment['repeat'] != 'No':
                try:
                    due = due.astimezone(ZoneInfo(segment['zone']))
                except (ValueError, KeyError):
                    pass
                step = timedelta(days=1 if segment['repeat'] == 'Diaria' else 7)
                due += step * max(0, (lower.astimezone(due.tzinfo).replace(tzinfo=None) - due.replace(tzinfo=None)) // step)
            else:
                step = None
            while stamp(due) < upper:
                if stamp(due) >= lower:
                    eligible.add((segment['task'], stamp(due).isoformat()))
                if step is None:
                    break
                due += step
        states = {}
        unscheduled = set()
        for row in ledger.get('completions', []):
            if stamp(row['at']) < end:
                key = (row['task'], stamp(row['due']).isoformat() if row['due'] else None)
                states[key] = row
        done = [states[k] for k in eligible if k in states and not states[k]['undo']]
        unscheduled = {k for k, r in states.items() if k[1] is None and not r['undo'] and stamp(r['at']) >= start}
        participants = {p['participant'] for p in ledger.get('participants', [])
                        if start <= stamp(p['at']) < end and p['new'] and p['cohort'] == 'evaluation'}
        activated = {r.get('participant') for r in rows if r['name'] == 'pet_saved'} & participants
        saves = {}
        for operation in OPERATIONS:
            results = [r['params']['result'] for r in rows if r['name'] == 'save_result' and r['params']['operation'] == operation]
            saves[operation] = {result: results.count(result) for result in RESULTS}
            finished = results.count('success') + results.count('failed')
            saves[operation].update(attempts=sum(r['name'] == 'save_attempt' and r['params']['operation'] == operation for r in rows),
                                    rate=results.count('success') / finished if finished else None)
        active_seconds = idle_seconds = 0
        for row in ledger.get('events', []):
            if row['name'] != 'screen_time':
                continue
            finish = stamp(row['at'])
            idle_start = finish - timedelta(seconds=row['params']['idle_seconds'])
            active_start = idle_start - timedelta(seconds=row['params']['active_seconds'])
            active_seconds += max(0, (min(end, idle_start) - max(start, active_start)).total_seconds())
            idle_seconds += max(0, (min(end, finish) - max(start, idle_start)).total_seconds())
        return {'start': start.isoformat(), 'end': end.isoformat(), 'cohort': cohort,
                'coverage_start': ledger.get('coverage_start'), 'coverage_end': coverage_end.isoformat(),
                'care': {'eligible': len(eligible), 'completed': len(done), 'late': sum(stamp(r['at']) > stamp(r['due']) for r in done),
                         'unscheduled_completed': len(unscheduled), 'rate': len(done) / len(eligible) if eligible else None},
                'activation': {'eligible': len(participants), 'activated': len(activated),
                               'rate': len(activated) / len(participants) if participants else None},
                'saves': saves, 'interactions': sum(r['name'] == 'interaction' for r in rows),
                'active_seconds': active_seconds, 'idle_seconds': idle_seconds}
