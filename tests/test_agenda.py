import unittest
from datetime import datetime
from services.agenda import agenda
from services.store import empty_data, complete_task


class AgendaTests(unittest.TestCase):
    def test_sections_and_progress_include_real_completions(self):
        data = empty_data()
        for i, due in enumerate(('2026-11-16 08:00','2026-11-16 18:00','2026-11-17 08:00','')):
            data['routines'].append(dict(id=str(i), due_at=due, done=False, pet='p', title='Paseo', detail='',
                                         kind='Cuidado', time=due, repeat='Diaria' if i == 0 else 'No'))
        now = datetime(2026,11,16,12)
        groups, completed, total = agenda(data, now)
        self.assertEqual([t['id'] for t in groups['Ahora']], ['0'])
        self.assertEqual(len(groups['Más tarde']), 2)
        self.assertEqual(len(groups['Sin fecha']), 1)
        self.assertEqual(total, 2)
        complete_task(data, data['routines'][0], now)
        groups, completed, total = agenda(data, now)
        self.assertEqual(len(completed), 1)
        self.assertEqual(total, 2)
        self.assertFalse(data['routines'][0]['done'])
        self.assertEqual(len(groups['Más tarde']), 3)

    def test_undated_overdue_and_reopen_do_not_invent_progress(self):
        data = empty_data();now = datetime(2026,11,16,12)
        task=dict(id='one',due_at='2026-11-16 08:00',done=False,pet='p',title='Comida',detail='',kind='Cuidado',time='',repeat='No')
        data['routines']=[task]
        complete_task(data,task,now)
        groups,completed,total=agenda(data,now)
        self.assertEqual((len(completed),total),(1,1))
        self.assertEqual(len(groups['Completados']),1)
        complete_task(data,task,now)
        groups,completed,total=agenda(data,now)
        self.assertEqual((len(completed),total),(0,1))
        task['due_at']='2026-11-15 08:00'
        self.assertEqual(agenda(data,now)[2],0)
        self.assertEqual(len(agenda(data,now)[0]['Ahora']),1)

    def test_deleting_care_keeps_the_saved_completion(self):
        data=empty_data();now=datetime(2026,11,16,12)
        task=dict(id='one',due_at='2026-11-16 08:00',done=False,pet='p',title='Comida',detail='',kind='Cuidado',time='',repeat='No')
        data['routines']=[task]
        complete_task(data,task,now)
        data['routines'].clear()
        self.assertEqual((len(agenda(data,now)[1]),agenda(data,now)[2]),(1,1))
