from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from services.health_report import create_health_report
root=Path('previews/plan');root.mkdir(parents=True,exist_ok=True)
data={'pets':[dict(id='demo',name='Luna',kind='Perro',breed='Mestiza',age='3 años',weight='12')],
      'events':[dict(pet='demo',title='Control anual',date='2026-10-10 10:30',kind='Control',detail='Peso registrado: 12 kg. Información de ejemplo para revisar el formato.'),dict(pet='demo',title='Vacunación',date='2026-09-15 11:00',kind='Vacuna',detail='Registro de ejemplo. Confirmar fechas y antecedentes con el veterinario.')],
      'routines':[dict(pet='demo',title='Paseo de la tarde',kind='Cuidado',time='18:00',detail='Paseo de 30 minutos.',done=False)]}
path=create_health_report(data,'demo',root/'resumen-luna-ejemplo.pdf')
import fitz
document=fitz.open(path)
document[0].get_pixmap(matrix=fitz.Matrix(1.3,1.3)).save(str(root/'resumen-luna-ejemplo.png'))
print('PASS: example PDF rendered for review.')
