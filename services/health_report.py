"""Private, offline PDF for a single pet; no account metadata or QR tokens."""
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape


def create_health_report(data, pet_id, target):
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    pet = next((p for p in data['pets'] if p['id'] == pet_id), None)
    if pet is None:
        raise ValueError('Selecciona una mascota para preparar su resumen.')
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    ink, muted = colors.HexColor('#103D49'), colors.HexColor('#526A74')
    styles = {
        'title': ParagraphStyle('title', fontName='Helvetica-Bold', fontSize=24, leading=29, textColor=ink, spaceAfter=14),
        'section': ParagraphStyle('section', fontName='Helvetica-Bold', fontSize=14, leading=19, textColor=ink, spaceBefore=18, spaceAfter=8, keepWithNext=True),
        'body': ParagraphStyle('body', fontName='Helvetica', fontSize=11, leading=16, textColor=ink, spaceAfter=7, alignment=TA_LEFT, splitLongWords=True),
        'note': ParagraphStyle('note', fontName='Helvetica', fontSize=9, leading=13, textColor=muted, spaceAfter=8),
    }
    def para(text, style='body'):
        # No user markup, external image/link or embedded attachment in the document.
        return Paragraph(escape(str(text)).replace('\n', '<br/>'), styles[style])
    story = [para('Resumen de salud', 'title'), para(pet['name'], 'section')]
    story.append(para(' · '.join(label + ': ' + str(pet.get(k) or 'Sin registrar') for k, label in [('kind','Especie'),('breed','Raza'),('age','Edad'),('weight','Peso (kg)')])) )
    story.append(para('Preparado el ' + datetime.now().strftime('%d/%m/%Y · %H:%M'), 'note'))
    story.append(para('Información registrada por la familia. No sustituye la ficha clínica del veterinario.', 'note'))
    story.append(para('Historial', 'section'))
    events = sorted((e for e in data['events'] if e.get('pet') == pet_id), key=lambda e: e.get('date',''), reverse=True)
    if not events:
        story.append(para('Todavía no hay registros de salud.'))
    for entry in events:
        story.append(para(f"{entry.get('date','Sin fecha')} · {entry.get('kind','Registro')} · {entry['title']}"))
        if entry.get('detail'):
            story.append(para(entry['detail']))
        story.append(Spacer(1, 6))
    story.append(para('Cuidados y tratamientos pendientes', 'section'))
    tasks = [r for r in data['routines'] if r.get('pet') == pet_id and not r.get('done')]
    if not tasks:
        story.append(para('No hay cuidados pendientes registrados.'))
    for task in tasks:
        story.append(para(f"{task.get('due_at') or task.get('time') or 'Sin fecha'} · {task.get('kind','Cuidado')} · {task['title']}"))
        if task.get('detail'):
            story.append(para(task['detail']))
    def footer(canvas, document):
        canvas.setStrokeColor(colors.HexColor('#DCE5E7'))
        canvas.line(44, 38, A4[0]-44, 38)
        canvas.setFont('Helvetica', 9)
        canvas.setFillColor(muted)
        canvas.drawString(44, 24, 'Mi Mascota · Resumen privado')
        canvas.drawRightString(A4[0]-44, 24, str(document.page))
    document = SimpleDocTemplate(str(target), pagesize=A4, rightMargin=44, leftMargin=44, topMargin=42, bottomMargin=54,
                                 title='Resumen de salud', author='Mi Mascota')
    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return target


def share_health_report(path):
    from kivy.utils import platform
    if platform == 'android':
        from jnius import autoclass
        activity = autoclass('org.kivy.android.PythonActivity').mActivity
        file = autoclass('java.io.File')(str(path))
        provider = autoclass('androidx.core.content.FileProvider')
        uri = provider.getUriForFile(activity, activity.getPackageName()+'.files', file)
        intent = autoclass('android.content.Intent')()
        intent.setAction('android.intent.action.SEND')
        intent.setType('application/pdf')
        intent.putExtra('android.intent.extra.STREAM', uri)
        intent.setClipData(autoclass('android.content.ClipData').newRawUri('Resumen de salud', uri))
        intent.addFlags(1)  # Temporary read grant; no exported directory or storage permission.
        activity.startActivity(autoclass('android.content.Intent').createChooser(intent, 'Compartir resumen'))
    else:
        import webbrowser
        webbrowser.open(Path(path).resolve().as_uri())
