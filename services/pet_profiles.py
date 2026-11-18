"""Presentation catalog; saved breed and age remain backwards-compatible strings."""
import re
import unicodedata
from pathlib import Path

BREEDS = {
    'Perro': ('Golden retriever', 'Labrador', 'Pastor alemán', 'Bulldog francés', 'Poodle', 'Chihuahua',
              'Beagle', 'Dachshund', 'Husky'),
    'Gato': ('Siamés', 'Persa', 'Maine coon', 'Británico de pelo corto', 'Bengalí', 'Ragdoll'),
}
PORTRAITS = {
    'perro': {'golden retriever': 'perro', 'labrador': 'labrador', 'pastor aleman': 'pastor-aleman',
              'bulldog frances': 'bulldog-frances', 'poodle': 'poodle', 'chihuahua': 'chihuahua',
              'beagle': 'beagle', 'dachshund': 'dachshund', 'husky': 'husky'},
    'gato': {'siames': 'siames', 'persa': 'persa', 'maine coon': 'maine-coon',
             'britanico de pelo corto': 'britanico', 'bengali': 'bengali', 'ragdoll': 'ragdoll'},
}


def normalized(value):
    return ''.join(c for c in unicodedata.normalize('NFD', value.strip().casefold()) if not unicodedata.combining(c))


def portrait_path(kind, breed=''):
    species = normalized(kind)
    if species not in PORTRAITS:
        return ''
    folder = Path(__file__).resolve().parents[1] / 'assets/avatars'
    name = PORTRAITS[species].get(normalized(breed), 'gato' if species == 'gato' else 'perro')
    portrait = folder / (name + '.png')
    if not portrait.is_file():
        portrait = folder / ('gato.png' if species == 'gato' else 'perro.png')
    return str(portrait)


def age_text(value):
    age = value.strip()
    if age in ('', 'Sin registrar', '—'):
        return ''
    if re.fullmatch(r'\d+(?:[.,]\d+)?', age):
        return age + (' año' if float(age.replace(',', '.')) == 1 else ' años')
    return age


def pet_details(pet):
    breed = pet.get('breed', '')
    kind = pet.get('kind', '')
    parts = [kind] if kind and normalized(kind) not in ('perro', 'gato') else []
    if breed and breed != 'Sin registrar' and normalized(breed) != normalized(kind):
        parts.append(breed)
    age = age_text(pet.get('age', ''))
    if age:
        parts.append(age)
    weight = pet.get('weight', '')
    if weight and weight != '—':
        parts.append(weight + ' kg')
    return '\n'.join(parts) or 'Completa su perfil'
