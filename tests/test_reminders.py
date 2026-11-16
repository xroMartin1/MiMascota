import unittest
from unittest.mock import Mock
from copy import deepcopy
from services.reminders import ReminderClient, plan_payload
from services.store import normalize, empty_data

class ReminderTests(unittest.TestCase):
    def test_legacy_data_starts_without_cloud_consent(self):
        data=normalize(empty_data())
        self.assertFalse(data['reminder_settings']['enabled'])
        self.assertEqual(data['reminder_revision'],0)

    def test_plan_excludes_health_and_contact_and_detects_completion(self):
        data=normalize(empty_data())
        data['routines']=[dict(id='id',title='secret medicine',detail='private dose',pet='private pet',
                              due_at='2026-10-08 10:00',done=False,repeat='No')]
        before=plan_payload(data)
        self.assertNotIn('private',str(before))
        self.assertNotIn('secret',str(before))
        data['routines'][0]['done']=True
        self.assertNotEqual(before,plan_payload(data))
        data['routines'].clear()
        self.assertEqual(plan_payload(data)['routines'],[])

    def test_invalid_zone_not_saved_for_enabled_plan(self):
        data=empty_data();data['reminder_settings']={'enabled':True,'timezone':'No/SuchZone'}
        with self.assertRaises(ValueError):normalize(data)

    def test_explicit_replacement_fetches_revision_but_auto_does_not(self):
        cloud,mobile,bridge=Mock(),Mock(),Mock()
        cloud.user={'id':'owner'}; mobile.configured=True
        mobile.native.return_value=(bridge,'activity');bridge.deviceId.return_value='device'
        payload={'enabled':False,'timezone':'UTC','routines':[]}
        cloud.request.side_effect=[{'revision':9},{'revision':10}]
        ReminderClient(cloud,mobile).publish(payload,1,replace=True)
        self.assertEqual(cloud.request.call_args.args[2]['revision'],9)
        cloud.request.reset_mock();cloud.request.side_effect=[{'revision':11}]
        ReminderClient(cloud,mobile).publish(payload,10)
        self.assertEqual(cloud.request.call_count,1)
        self.assertEqual(cloud.request.call_args.args[2]['revision'],10)
