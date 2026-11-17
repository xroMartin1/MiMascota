"""Informes MJV sin servicios de pago: JSON, CSV y HTML imprimible."""
import argparse
import csv
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.measurement import Measurement, stamp, valid_event


def _identity(row):
    if 'participant' in row and not re.fullmatch(r'[a-f0-9]{32}', str(row['participant'])):
        raise ValueError('Código de participante inválido')
    if 'cohort' in row and row['cohort'] not in ('evaluation', 'team'):
        raise ValueError('Grupo de evaluación inválido')


def read_dataset(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if data.get('version') != 1 or not re.fullmatch(r'[a-f0-9]{32}', str(data.get('dataset_id'))):
        raise ValueError('Exportación de medición no reconocida')
    stamp(data['exported_at'])
    stamp(data['coverage_start'])
    for key in ('events', 'segments', 'completions', 'participants'):
        if not isinstance(data.get(key), list):
            raise ValueError('Exportación incompleta')
        for row in data[key]:
            _identity(row)
            if key == 'segments':
                if row['repeat'] not in ('No', 'Diaria', 'Semanal') or not isinstance(row['zone'], str):
                    raise ValueError('Programación inválida')
                stamp(row['start'])
                if row.get('end'):
                    stamp(row['end'])
            else:
                stamp(row['at'])
            if key in ('segments', 'completions'):
                if not re.fullmatch(r'[a-f0-9]{64}', str(row['task'])):
                    raise ValueError('Referencia local inválida')
                if row.get('due'):
                    stamp(row['due'])
            if key == 'events' and not valid_event(row['name'], row['params']):
                raise ValueError('Evento fuera del diccionario permitido')
            if key == 'participants' and (type(row.get('new')) is not bool or not row.get('participant') or not row.get('cohort')):
                raise ValueError('Ficha de participante inválida')
            if key == 'completions' and type(row.get('undo')) is not bool:
                raise ValueError('Resultado de cuidado inválido')
    return data


def payment_summary(path, start, end, selection_path, cohort):
    if selection_path is None:
        raise ValueError('Selecciona las órdenes observadas de la cohorte antes de calcular pagos')
    selection = json.loads(Path(selection_path).read_text(encoding='utf-8'))
    selected = selection.get('order_ids')
    if (selection.get('cohort') != cohort or not isinstance(selected, list)
            or any(not isinstance(i, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', i) for i in selected)):
        raise ValueError('Selección de órdenes o cohorte inválida')
    selected = set(selected)
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if data.get('test_mode') is not True or not isinstance(data.get('orders'), list):
        raise ValueError('Se requiere la exportación de órdenes sandbox del servidor')
    exported = stamp(data['exported_at'])
    states = dict.fromkeys(('active', 'rejected', 'cancelled', 'expired', 'pending', 'creating'), 0)
    unique = {}
    found = set()
    for row in data['orders']:
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', str(row.get('order_id'))) or row.get('state') not in states:
            raise ValueError('Orden de pago inválida')
        if row['order_id'] not in selected:
            continue
        found.add(row['order_id'])
        if start <= stamp(row['created_at']) < end:
            if row['order_id'] in unique and unique[row['order_id']]['state'] != row['state']:
                raise ValueError('Exportación contiene estados contradictorios de una orden')
            unique[row['order_id']] = row
    if found != selected:
        raise ValueError('La selección incluye órdenes ausentes de la exportación del servidor')
    for row in unique.values():
        states[row['state']] += 1
    terminal = sum(states[k] for k in ('active', 'rejected', 'cancelled', 'expired'))
    return dict(states, approved=states['active'], terminal=terminal,
                rate=states['active'] / terminal if terminal else None,
                exported_at=exported.isoformat(), source='server_export', test_mode=True, cohort=cohort)


def build_report(paths, start, end, cohort='evaluation', payments=None, payment_orders=None):
    start, end = stamp(start), stamp(end)
    if start >= end or cohort not in ('evaluation', 'team'):
        raise ValueError('Periodo o grupo inválido')
    latest = {}
    for path in paths:
        data = read_dataset(path)
        previous = latest.get(data['dataset_id'])
        if previous is None or stamp(data['exported_at']) > stamp(previous['exported_at']):
            latest[data['dataset_id']] = data
    if not latest:
        raise ValueError('Incluye al menos una exportación consentida')
    combined = {k: [] for k in ('events', 'segments', 'completions', 'participants')}
    coverage = []
    for data in latest.values():
        # No inventar actividad posterior a la extracción del dispositivo.
        cutoff = min(end, stamp(data['exported_at']))
        coverage.append({'dataset_id': data['dataset_id'], 'start': data['coverage_start'],
                         'end': cutoff.isoformat()})
        for key in combined:
            for original in data[key]:
                row = dict(original)
                if key == 'segments':
                    row['end'] = min(stamp(row['end']), cutoff).isoformat() if row.get('end') else cutoff.isoformat()
                elif stamp(row['at']) > cutoff:
                    continue
                combined[key].append(row)
    for key in ('events', 'completions', 'participants'):
        combined[key].sort(key=lambda r: stamp(r['at']))
    first_enrollment = {}
    for row in combined['participants']:
        key = (row['participant'], row['cohort'])
        first_enrollment.setdefault(key, row)
    combined['participants'] = list(first_enrollment.values())
    combined['coverage_start'] = min(stamp(d['coverage_start']) for d in latest.values()).isoformat()
    measurement = Measurement(Path('unused-readonly-report'))
    measurement.ledger = combined  # enabled=False: summary no escribe ni llama al SDK.
    result = measurement.summary(start, end, cohort=cohort)
    result['coverage_end'] = max(stamp(row['end']) for row in coverage).isoformat()
    result.update(datasets=len(latest), coverage=coverage,
                  generated_at=datetime.now(timezone.utc).isoformat(),
                  events=[r for r in combined['events'] if r.get('cohort') == cohort and start <= stamp(r['at']) < end],
                  payments=payment_summary(payments, start, end, payment_orders, cohort) if payments else None)
    return result


def write_report(report, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    public = {k: v for k, v in report.items() if k != 'events'}
    (output / 'summary.json').write_text(json.dumps(public, ensure_ascii=False, indent=2), encoding='utf-8')
    with (output / 'events.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(('at', 'event', 'participant', 'cohort', 'operation', 'result', 'screen', 'active_seconds', 'idle_seconds'))
        for row in report['events']:
            params = row['params']
            writer.writerow((row['at'], row['name'], row.get('participant', ''), row.get('cohort', ''),
                             *(params.get(key, '') for key in ('operation', 'result', 'screen', 'active_seconds', 'idle_seconds'))))
    charts = []
    def chart(title, numerator, denominator, description):
        percent = None if not denominator else numerator / denominator * 100
        value = 'Sin datos' if percent is None else f'{percent:.1f} %'
        bar = '' if percent is None else f'<progress max="100" value="{percent:.4f}" aria-label="{escape(title)}">{value}</progress>'
        charts.append(f'<article><h2>{escape(title)}</h2><strong>{value}</strong>{bar}<p>{numerator} / {denominator}</p><p>{escape(description)}</p></article>')
    activation, care = report['activation'], report['care']
    chart('Activación', activation['activated'], activation['eligible'], 'Participantes nuevos que guardaron su primera mascota.')
    chart('Cumplimiento de cuidados', care['completed'], care['eligible'],
          f'Ocurrencias previstas en el periodo observado. {care["late"]} completadas tarde; {care["unscheduled_completed"]} sin fecha, excluidas del porcentaje.')
    for operation, label in (('pet', 'Mascotas'), ('care', 'Cuidados'), ('health', 'Salud'), ('account', 'Cuenta')):
        values = report['saves'][operation]
        chart('Guardado: ' + label, values['success'], values['success'] + values['failed'],
              f'{values["validation"]} errores de validación; {values["abandoned"]} abandonos. No incluidos en el denominador de operaciones finalizadas.')
    payment = report['payments']
    if payment:
        chart('Pagos de prueba', payment['approved'], payment['terminal'],
              f'{payment["pending"] + payment["creating"]} pendientes. Órdenes seleccionadas explícitamente de esta cohorte e iniciadas en el periodo; estado observado al exportar: {payment["exported_at"]}. No son ventas reales.')
    else:
        charts.append('<article><h2>Pagos de prueba</h2><strong>Sin datos</strong><p>Falta una exportación de órdenes del servidor.</p></article>')
    period = escape(report['start'] + ' — ' + report['end'])
    cohort = 'Participantes' if report['cohort'] == 'evaluation' else 'Pruebas del equipo'
    coverage_rows = ''.join(f'<tr><td>{i}</td><td>{escape(row["start"])}</td><td>{escape(row["end"])}</td></tr>'
                            for i, row in enumerate(report['coverage'], 1))
    html = f'''<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mi Mascota — evaluación MJV</title><style>
body{{font:16px system-ui;color:#133d48;background:#fff;margin:40px auto;padding:0 24px;max-width:1080px;line-height:1.55}}h1{{font-size:32px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:20px}}article{{background:#f3f8f8;border:1px solid #cadcdd;border-radius:18px;padding:22px}}h2{{font-size:19px}}strong{{display:block;font-size:30px}}progress{{width:100%;accent-color:#167b87;height:24px}}table{{border-collapse:collapse;width:100%;font-size:13px}}td,th{{padding:8px;border-bottom:1px solid #cadcdd;text-align:left}}@media print{{body{{margin:0}}article{{break-inside:avoid}}}}
</style><h1>Mi Mascota: Medir, Jugar y Validar</h1><p>{cohort}. Periodo UTC: {period}</p>
<p>{report['datasets']} conjuntos observados; muestra de activación: {activation['eligible']} participantes nuevos. Sin datos no equivale a 0 %.</p>
<main class="grid">{''.join(charts)}</main><h2>Uso observado</h2><p>{report['interactions']} interacciones; {report['active_seconds']:.1f} segundos activos y {report['idle_seconds']:.1f} segundos de inactividad en primer plano. Umbral de inactividad: 30 segundos. Más tiempo no implica mejor experiencia.</p>
<h2>Cobertura por conjunto</h2><table><thead><tr><th>Conjunto</th><th>Desde</th><th>Hasta</th></tr></thead><tbody>{coverage_rows}</tbody></table>
<h2>Interpretación y mejoras</h2><p>Contrasta cada resultado con la meta declarada antes de medir y con las observaciones de la prueba. Documenta obstáculos, mejora propuesta, impacto, esfuerzo y resultado de una segunda prueba. Este informe no inventa conclusiones ni demuestra impacto causal.</p>
<p>Los porcentajes corresponden a uso consentido y a la cobertura disponible, sin extrapolar a todas las personas. No mezclar pruebas técnicas con participantes. Los datos locales se retienen 30 días; custodia y elimina por separado las exportaciones compartidas.</p></html>'''
    (output / 'report.html').write_text(html, encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('exports', type=Path, nargs='+')
    parser.add_argument('--start', required=True, help='Fecha ISO con zona horaria, inclusiva')
    parser.add_argument('--end', required=True, help='Fecha ISO con zona horaria, exclusiva')
    parser.add_argument('--cohort', choices=('evaluation', 'team'), default='evaluation')
    parser.add_argument('--payments', type=Path, help='Exportación mínima sandbox del servidor')
    parser.add_argument('--payment-orders', type=Path, help='Selección de referencias de orden observadas, con cohort y order_ids')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        report = build_report(args.exports, args.start, args.end, args.cohort, args.payments, args.payment_orders)
        write_report(report, args.output)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        parser.exit(1, 'No se pudo generar el informe: revisa las exportaciones y el periodo con zona horaria.\n')
    print('Informe generado: summary.json, events.csv y report.html. Datos consentidos; no son resultados de toda la población.')


if __name__ == '__main__':
    main()
