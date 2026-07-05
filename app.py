import os
from datetime import date
from flask import Flask, render_template, request, send_file, jsonify
from supabase import create_client
from config import CLIENTES, PRODUCTOS
from pdf_generator import generar_pdf

app = Flask(__name__)

_sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])


def _cliente(cid):
    return next((c for c in CLIENTES if c['id'] == cid), None)

def _punto(cliente, nombre):
    return next((p for p in cliente['puntos'] if p['nombre'] == nombre), None)


@app.route('/')
def index():
    return render_template('index.html',
                           clientes=CLIENTES,
                           productos=PRODUCTOS,
                           hoy=date.today().isoformat())


@app.route('/api/puntos')
def api_puntos():
    cid = request.args.get('cliente_id')
    cliente = _cliente(cid)
    if not cliente:
        return jsonify([])
    return jsonify(cliente['puntos'])


@app.route('/generar', methods=['POST'])
def generar():
    cid   = request.form.get('cliente_id', '').strip()
    pnomb = request.form.get('punto', '').strip()
    fecha = request.form.get('fecha', date.today().isoformat())

    cliente = _cliente(cid)
    if not cliente:
        return 'Cliente no encontrado', 400

    punto = _punto(cliente, pnomb)
    if not punto:
        return 'Punto de entrega no encontrado', 400

    items = []
    for prod in PRODUCTOS:
        raw = request.form.get(f'qty_{prod["codigo"]}', '0').strip()
        try:
            qty = float(raw)
        except ValueError:
            qty = 0.0
        if qty > 0:
            items.append({
                'codigo':      prod['codigo'],
                'descripcion': prod['descripcion'],
                'cantidad':    qty,
            })

    if not items:
        return 'Ingresa al menos una cantidad mayor a 0', 400

    try:
        result = _sb.table('remisiones').insert({
            'cliente_nombre':    cliente['nombre'],
            'cliente_nit':       cliente['nit'],
            'cliente_telefono':  cliente.get('telefono', ''),
            'cliente_direccion': cliente.get('direccion', ''),
            'cliente_ciudad':    cliente.get('ciudad', ''),
            'punto_nombre':      punto['nombre'],
            'punto_ciudad':      punto['ciudad'],
            'fecha':             fecha,
            'items':             items,
        }).execute()
        row = result.data[0]
    except Exception as e:
        return f'Error Supabase: {e}', 500

    numero = str(row['id']).zfill(4)
    _sb.table('remisiones').update({'numero': numero}).eq('id', row['id']).execute()

    try:
        pdf = generar_pdf({
            'numero': numero,
            'fecha':  fecha,
            'cliente': {
                'nombre':    cliente['nombre'],
                'nit':       cliente['nit'],
                'telefono':  cliente.get('telefono', ''),
                'direccion': cliente.get('direccion', ''),
                'ciudad':    cliente.get('ciudad', ''),
            },
            'punto': punto,
            'items': items,
        })
    except Exception as e:
        return f'Error PDF: {e}', 500

    return send_file(pdf, as_attachment=True,
                     download_name=f'remision_{numero}.pdf',
                     mimetype='application/pdf')


@app.route('/historial')
def historial():
    try:
        rows = _sb.table('remisiones').select('*').order('id', desc=True).execute().data
    except Exception as e:
        return f'Error historial Supabase: {e}', 500
    try:
        return render_template('historial.html', remisiones=rows)
    except Exception as e:
        return f'Error historial template: {e} — datos: {rows}', 500


@app.route('/remision/<int:rid>/pdf')
def descargar_pdf(rid):
    data = _sb.table('remisiones').select('*').eq('id', rid).execute().data
    if not data:
        return 'No encontrada', 404
    r = data[0]
    pdf = generar_pdf({
        'numero': r['numero'],
        'fecha':  r['fecha'],
        'cliente': {
            'nombre':    r['cliente_nombre'],
            'nit':       r['cliente_nit'],
            'telefono':  r['cliente_telefono'],
            'direccion': r['cliente_direccion'],
            'ciudad':    r['cliente_ciudad'],
        },
        'punto': {'nombre': r['punto_nombre'], 'ciudad': r['punto_ciudad']},
        'items': r['items'],
    })
    return send_file(pdf, as_attachment=True,
                     download_name=f'remision_{r["numero"]}.pdf',
                     mimetype='application/pdf')


if __name__ == '__main__':
    app.run(debug=True)
