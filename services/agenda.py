"""Read-only presentation of care; completion remains owned by store.complete_task."""
from datetime import datetime
from services.store import DATE_FORMAT


def agenda(data, now):
    groups = {title: [] for title in ('Ahora', 'Más tarde', 'Sin fecha', 'Completados')}
    today_ids = set()
    for task in sorted(data['routines'], key=lambda t: t['due_at'] or '9999'):
        due = datetime.strptime(task['due_at'], DATE_FORMAT) if task['due_at'] else None
        if task['done']:
            groups['Completados'].append(task)
        else:
            groups['Sin fecha' if due is None else 'Ahora' if due <= now else 'Más tarde'].append(task)
            if due and due.date() == now.date():
                today_ids.add(task['id'])
    completed = {}
    for event in sorted(data['events'], key=lambda e: str(e.get('date', ''))):
        task_id = event.get('task_id')
        stamp = event.get('date', '')
        if (isinstance(task_id, str) and task_id and event.get('status') == 'Completado'
                and isinstance(stamp, str) and stamp[:10] == now.strftime('%Y-%m-%d')):
            completed[task_id] = event
    return groups, completed, len(today_ids | completed.keys())
