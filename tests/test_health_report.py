import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from services.health_report import create_health_report


class HealthReportTests(unittest.TestCase):
    def test_single_pet_private_pdf_with_long_history(self):
        from pypdf import PdfReader
        data = {'pets': [{'id':'one','name':'Luna','kind':'Perro','breed':'Mestiza','age':'3 años','weight':'12','chip':'PRIVATE','qr_contact':{'phone':'PRIVATE'}}],
                'events':[{'pet':'one','title':'Vacuna <b>sin markup</b>','kind':'Vacuna','date':'2026-10-10','detail':'Revisión y cuidado. '*30} for _ in range(24)]+[{'pet':'other','title':'SECRET'}],
                'routines':[{'pet':'one','title':'Paseo','kind':'Cuidado','time':'18:00','done':False},{'pet':'other','title':'SECRET'}],
                'user':{'email':'PRIVATE'},'qr_trials':{'one':{'code':'PRIVATE'}}}
        with TemporaryDirectory() as temp:
            report = create_health_report(data, 'one', Path(temp)/'resumen.pdf')
            reader = PdfReader(report)
            self.assertGreater(len(reader.pages),1)
            text = '\n'.join(p.extract_text() for p in reader.pages)
            self.assertIn('Luna',text)
            self.assertIn('Revisión',text)
            self.assertIn('<b>sin markup</b>',text)
            self.assertNotIn('PRIVATE',text)
            self.assertNotIn('SECRET',text)
            self.assertIn('Paseo',text)
            self.assertIn('Mi Mascota',text)

    def test_missing_pet_does_not_create_file(self):
        with TemporaryDirectory() as temp:
            target=Path(temp)/'missing.pdf'
            with self.assertRaises(ValueError):
                create_health_report({'pets':[]},'missing',target)
            self.assertFalse(target.exists())
