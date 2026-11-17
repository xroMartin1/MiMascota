import unittest
from pathlib import Path
from PIL import Image
from services.pet_profiles import BREEDS, age_text, pet_details, portrait_path


class PetProfilesTests(unittest.TestCase):
    def test_ages_keep_units_and_old_text(self):
        for value, expected in [('3', '3 años'), ('1', '1 año'), ('1,5', '1,5 años'),
                                ('6 meses', '6 meses'), ('3 años', '3 años'), ('Sin registrar', '')]:
            self.assertEqual(age_text(value), expected)

    def test_details_show_useful_fields_without_species_or_separators(self):
        self.assertEqual(pet_details(dict(kind='Perro', breed='Labrador', age='3', weight='4.5')),
                         'Labrador\n3 años\n4.5 kg')
        self.assertEqual(pet_details(dict(breed='Sin registrar', age='', weight='—')), 'Completa su perfil')
        self.assertEqual(pet_details(dict(kind='Conejo', age='6 meses')), 'Conejo\n6 meses')
        self.assertEqual(pet_details(dict(kind='Perro', breed='Perro', age='3')), '3 años')

    def test_each_catalog_breed_has_its_own_small_offline_asset(self):
        paths = []
        for kind, breeds in BREEDS.items():
            for breed in breeds:
                path = Path(portrait_path(kind, breed))
                self.assertTrue(path.is_file())
                self.assertLess(path.stat().st_size, 128000)
                paths.append(path)
        self.assertEqual(len(paths), len(set(paths)))
        self.assertEqual(Path(portrait_path('Gato', 'siames')).name, 'siames.png')
        self.assertEqual(Path(portrait_path('Perro', 'Una raza anterior')).name, 'perro.png')
        self.assertEqual(portrait_path('Conejo'), '')

    def test_portraits_are_small_transparent_cutouts(self):
        folder = Path(portrait_path('Perro')).parent
        portraits = list(folder.glob('*.png'))
        self.assertEqual(len(portraits), 12)
        self.assertLess(sum(path.stat().st_size for path in portraits), 1200000)
        for path in portraits:
            with self.subTest(path=path.name), Image.open(path) as portrait:
                self.assertEqual(portrait.size, (256, 256))
                self.assertEqual(portrait.mode, 'RGBA')
                alpha = portrait.getchannel('A')
                self.assertEqual(alpha.getextrema()[0], 0)
                self.assertGreaterEqual(alpha.getextrema()[1], 250)
                self.assertGreater(alpha.histogram()[0], 256*256*.2)
