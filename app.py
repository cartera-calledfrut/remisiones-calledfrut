import os
import json
import base64
from datetime import date
from flask import Flask, render_template, request, send_file, jsonify, redirect, url_for, flash
from supabase import create_client
from config import PRODUCTOS
from pdf_generator import generar_pdf, generar_pdf_proforma

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'remisiones-secret-2024')

_sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])


# ── DB helpers ────────────────────────────────────────────────────────────────

def db_empresas():
    return _sb.table('empresas').select('*').order('id').execute().data

def db_clientes():
    return _sb.table('clientes').select('*').eq('activo', True).order('nombre').execute().data

def db_puntos(cliente_id):
    return _sb.table('puntos_entrega').select('*').eq('cliente_id', cliente_id).order('nombre').execute().data

def db_one(table, id_):
    rows = _sb.table(table).select('*').eq('id', id_).execute().data
    return rows[0] if rows else None


# ── Redirects (mantiene URLs anteriores funcionando) ──────────────────────────

@app.route('/')
def root():
    return redirect(url_for('remisiones_hub'))

@app.route('/historial')
def historial_redirect():
    return redirect(url_for('remisiones_historial'))


# ── Remisiones ────────────────────────────────────────────────────────────────

@app.route('/remisiones')
def remisiones_hub():
    try:
        ultima = _sb.table('remisiones').select('numero').order('id', desc=True).limit(1).execute().data
        ultima_remision = ultima[0]['numero'] if ultima else None
    except Exception:
        ultima_remision = None
    return render_template('remisiones_hub.html', ultima_remision=ultima_remision)


@app.route('/remisiones/nueva')
def remisiones_nueva():
    try:
        empresas = db_empresas()
        clientes = db_clientes()
    except Exception as e:
        return f'Error cargando datos: {e}', 500
    return render_template('index.html', empresas=empresas, clientes=clientes,
                           productos=PRODUCTOS, hoy=date.today().isoformat())


@app.route('/api/puntos')
def api_puntos():
    cid = request.args.get('cliente_id')
    if not cid:
        return jsonify([])
    try:
        return jsonify(db_puntos(int(cid)))
    except Exception:
        return jsonify([])


@app.route('/generar', methods=['POST'])
def generar():
    empresa_id = request.form.get('empresa_id', '').strip()
    cliente_id = request.form.get('cliente_id', '').strip()
    punto_id   = request.form.get('punto_id', '').strip()
    fecha      = request.form.get('fecha', date.today().isoformat())

    try:
        empresa = db_one('empresas', int(empresa_id))
        cliente = db_one('clientes', int(cliente_id))
        punto   = db_one('puntos_entrega', int(punto_id))
    except Exception as e:
        return f'Error cargando datos: {e}', 400

    if not empresa or not cliente or not punto:
        return 'Selecciona empresa, cliente y punto de entrega', 400

    observaciones = request.form.get('observaciones', '').strip()

    items = []
    for prod in PRODUCTOS:
        raw = request.form.get(f'qty_{prod["codigo"]}', '0').strip()
        try:
            qty = float(raw)
        except ValueError:
            qty = 0.0
        if qty > 0:
            items.append({'codigo': prod['codigo'], 'descripcion': prod['descripcion'], 'cantidad': qty})

    if not items:
        return 'Ingresa al menos una cantidad mayor a 0', 400

    try:
        row = _sb.table('remisiones').insert({
            'empresa_id':        empresa['id'],
            'cliente_nombre':    cliente['nombre'],
            'cliente_nit':       cliente['nit'],
            'cliente_telefono':  cliente.get('telefono', ''),
            'cliente_direccion': cliente.get('direccion', ''),
            'cliente_ciudad':    cliente.get('ciudad', ''),
            'punto_nombre':      punto['nombre'],
            'punto_ciudad':      punto['ciudad'],
            'fecha':             fecha,
            'items':             items,
        }).execute().data[0]
    except Exception as e:
        return f'Error Supabase: {e}', 500

    numero = str(row['id']).zfill(4)
    _sb.table('remisiones').update({'numero': numero}).eq('id', row['id']).execute()

    try:
        pdf = generar_pdf({'numero': numero, 'fecha': fecha,
                           'empresa': empresa, 'cliente': cliente,
                           'punto': punto, 'items': items,
                           'observaciones': observaciones})
    except Exception as e:
        return f'Error PDF: {e}', 500

    return send_file(pdf, as_attachment=True,
                     download_name=f'remision_{numero}.pdf',
                     mimetype='application/pdf')


@app.route('/remisiones/historial')
def remisiones_historial():
    try:
        rows     = _sb.table('remisiones').select('*').order('id', desc=True).execute().data
        empresas = {e['id']: e['nombre'] for e in db_empresas()}
    except Exception as e:
        return f'Error: {e}', 500
    return render_template('historial.html', remisiones=rows, empresas=empresas)


@app.route('/remision/<int:rid>/pdf')
def descargar_pdf(rid):
    r = db_one('remisiones', rid)
    if not r:
        return 'No encontrada', 404
    empresa = db_one('empresas', r['empresa_id']) if r.get('empresa_id') else {}
    try:
        pdf = generar_pdf({
            'numero':  r['numero'],
            'fecha':   r['fecha'],
            'empresa': empresa or {},
            'cliente': {'nombre': r['cliente_nombre'], 'nit': r['cliente_nit'],
                        'telefono': r['cliente_telefono'], 'direccion': r['cliente_direccion'],
                        'ciudad': r['cliente_ciudad']},
            'punto':   {'nombre': r['punto_nombre'], 'ciudad': r['punto_ciudad']},
            'items':   r['items'],
        })
    except Exception as e:
        return f'Error PDF: {e}', 500
    return send_file(pdf, as_attachment=True,
                     download_name=f'remision_{r["numero"]}.pdf',
                     mimetype='application/pdf')


# ── Proformas ─────────────────────────────────────────────────────────────────

@app.route('/proformas')
def proformas_hub():
    try:
        ultima = _sb.table('proformas').select('numero').order('id', desc=True).limit(1).execute().data
        ultima_proforma = ultima[0]['numero'] if ultima else None
    except Exception:
        ultima_proforma = None
    return render_template('proformas_hub.html', ultima_proforma=ultima_proforma)


@app.route('/proformas/nueva')
def proformas_nueva():
    try:
        empresas = db_empresas()
    except Exception as e:
        return f'Error cargando datos: {e}', 500
    return render_template('proforma_form.html', empresas=empresas, hoy=date.today().isoformat())


@app.route('/proformas/generar', methods=['POST'])
def proformas_generar():
    empresa_id = request.form.get('empresa_id', '').strip()
    fecha      = request.form.get('fecha', date.today().isoformat())
    items_json = request.form.get('items_json', '[]')

    try:
        empresa = db_one('empresas', int(empresa_id))
    except Exception as e:
        return f'Error cargando empresa: {e}', 400

    if not empresa:
        return 'Selecciona una empresa', 400

    try:
        items = json.loads(items_json)
    except Exception:
        return 'Error en los ítems: JSON inválido', 400

    if not items:
        return 'Agrega al menos un ítem', 400

    def fv(name, default=''):
        return request.form.get(name, default).strip()

    try:
        flete     = float(request.form.get('flete',     0) or 0)
        seguro    = float(request.form.get('seguro',    0) or 0)
        descuento = float(request.form.get('descuento', 0) or 0)
        anticipo  = int(request.form.get('anticipo_pct', 0) or 0)
    except ValueError:
        flete = seguro = descuento = 0
        anticipo = 0

    try:
        row = _sb.table('proformas').insert({
            'empresa_id':          empresa['id'],
            'comprador_nombre':    fv('comprador_nombre'),
            'comprador_tax_id':    fv('comprador_tax_id'),
            'comprador_direccion': fv('comprador_direccion'),
            'comprador_ciudad':    fv('comprador_ciudad'),
            'comprador_pais':      fv('comprador_pais'),
            'comprador_contacto':  fv('comprador_contacto'),
            'fecha':               fecha,
            'fecha_validez':       fv('fecha_validez') or None,
            'referencia':          fv('referencia'),
            'incoterm':            fv('incoterm', 'FOB'),
            'puerto_origen':       fv('puerto_origen'),
            'puerto_destino':      fv('puerto_destino'),
            'pais_origen':         fv('pais_origen', 'Colombia'),
            'pais_destino':        fv('pais_destino'),
            'moneda':              fv('moneda', 'USD'),
            'plazo_entrega':       fv('plazo_entrega'),
            'forma_pago':          fv('forma_pago'),
            'anticipo_pct':        anticipo,
            'banco_nombre':        fv('banco_nombre'),
            'banco_swift':         fv('banco_swift'),
            'banco_cuenta':        fv('banco_cuenta'),
            'banco_beneficiario':  fv('banco_beneficiario'),
            'items':               items,
            'flete':               flete,
            'seguro':              seguro,
            'descuento':           descuento,
            'observaciones':       fv('observaciones'),
        }).execute().data[0]
    except Exception as e:
        return f'Error Supabase: {e}', 500

    numero   = 'PF-' + str(row['id']).zfill(4)
    subtotal = sum(float(i.get('cantidad', 0)) * float(i.get('precio_unitario', 0)) for i in items)
    total    = subtotal + flete + seguro - descuento

    _sb.table('proformas').update({'numero': numero}).eq('id', row['id']).execute()

    try:
        pdf = generar_pdf_proforma({
            'numero':        numero,
            'fecha':         fecha,
            'fecha_validez': fv('fecha_validez'),
            'referencia':    fv('referencia'),
            'empresa':       empresa,
            'comprador': {
                'nombre':    fv('comprador_nombre'),
                'tax_id':    fv('comprador_tax_id'),
                'direccion': fv('comprador_direccion'),
                'ciudad':    fv('comprador_ciudad'),
                'pais':      fv('comprador_pais'),
                'contacto':  fv('comprador_contacto'),
            },
            'incoterm':      fv('incoterm', 'FOB'),
            'puerto_origen': fv('puerto_origen'),
            'puerto_destino':fv('puerto_destino'),
            'pais_origen':   fv('pais_origen', 'Colombia'),
            'pais_destino':  fv('pais_destino'),
            'moneda':        fv('moneda', 'USD'),
            'plazo_entrega': fv('plazo_entrega'),
            'items':         items,
            'subtotal':      subtotal,
            'flete':         flete,
            'seguro':        seguro,
            'descuento':     descuento,
            'total':         total,
            'forma_pago':    fv('forma_pago'),
            'anticipo_pct':  anticipo,
            'banco': {
                'nombre':       fv('banco_nombre'),
                'swift':        fv('banco_swift'),
                'cuenta':       fv('banco_cuenta'),
                'beneficiario': fv('banco_beneficiario'),
            },
            'observaciones': fv('observaciones'),
        })
    except Exception as e:
        return f'Error PDF: {e}', 500

    return send_file(pdf, as_attachment=True,
                     download_name=f'proforma_{numero}.pdf',
                     mimetype='application/pdf')


@app.route('/proformas/historial')
def proformas_historial():
    try:
        rows     = _sb.table('proformas').select('*').order('id', desc=True).execute().data
        empresas = {e['id']: e['nombre'] for e in db_empresas()}
    except Exception as e:
        return f'Error: {e}', 500
    return render_template('proformas_historial.html', proformas=rows, empresas=empresas)


@app.route('/proforma/<int:pid>/pdf')
def descargar_pdf_proforma(pid):
    p = db_one('proformas', pid)
    if not p:
        return 'No encontrada', 404
    empresa  = db_one('empresas', p['empresa_id']) if p.get('empresa_id') else {}
    items    = p['items']
    subtotal = sum(float(i.get('cantidad', 0)) * float(i.get('precio_unitario', 0)) for i in items)
    total    = subtotal + float(p.get('flete', 0)) + float(p.get('seguro', 0)) - float(p.get('descuento', 0))

    try:
        pdf = generar_pdf_proforma({
            'numero':        p['numero'],
            'fecha':         p['fecha'],
            'fecha_validez': p.get('fecha_validez', ''),
            'referencia':    p.get('referencia', ''),
            'empresa':       empresa or {},
            'comprador': {
                'nombre':    p.get('comprador_nombre', ''),
                'tax_id':    p.get('comprador_tax_id', ''),
                'direccion': p.get('comprador_direccion', ''),
                'ciudad':    p.get('comprador_ciudad', ''),
                'pais':      p.get('comprador_pais', ''),
                'contacto':  p.get('comprador_contacto', ''),
            },
            'incoterm':      p.get('incoterm', ''),
            'puerto_origen': p.get('puerto_origen', ''),
            'puerto_destino':p.get('puerto_destino', ''),
            'pais_origen':   p.get('pais_origen', 'Colombia'),
            'pais_destino':  p.get('pais_destino', ''),
            'moneda':        p.get('moneda', 'USD'),
            'plazo_entrega': p.get('plazo_entrega', ''),
            'items':         items,
            'subtotal':      subtotal,
            'flete':         float(p.get('flete', 0)),
            'seguro':        float(p.get('seguro', 0)),
            'descuento':     float(p.get('descuento', 0)),
            'total':         total,
            'forma_pago':    p.get('forma_pago', ''),
            'anticipo_pct':  p.get('anticipo_pct', 0),
            'banco': {
                'nombre':       p.get('banco_nombre', ''),
                'swift':        p.get('banco_swift', ''),
                'cuenta':       p.get('banco_cuenta', ''),
                'beneficiario': p.get('banco_beneficiario', ''),
            },
            'observaciones': p.get('observaciones', ''),
        })
    except Exception as e:
        return f'Error PDF: {e}', 500

    return send_file(pdf, as_attachment=True,
                     download_name=f'proforma_{p["numero"]}.pdf',
                     mimetype='application/pdf')


# ── Clientes ──────────────────────────────────────────────────────────────────

@app.route('/clientes')
def clientes_lista():
    try:
        clientes = _sb.table('clientes').select('*').order('nombre').execute().data
    except Exception as e:
        return f'Error: {e}', 500
    return render_template('clientes_lista.html', clientes=clientes)


@app.route('/clientes/nuevo', methods=['GET', 'POST'])
def cliente_nuevo():
    if request.method == 'POST':
        try:
            _sb.table('clientes').insert({
                'nombre':    request.form.get('nombre', '').strip().upper(),
                'nit':       request.form.get('nit', '').strip(),
                'telefono':  request.form.get('telefono', '').strip(),
                'direccion': request.form.get('direccion', '').strip(),
                'ciudad':    request.form.get('ciudad', '').strip(),
            }).execute()
            flash('Cliente creado correctamente.', 'success')
            return redirect(url_for('clientes_lista'))
        except Exception as e:
            flash(f'Error: {e}', 'danger')
    return render_template('cliente_form.html', cliente=None)


@app.route('/clientes/<int:cid>', methods=['GET', 'POST'])
def cliente_detalle(cid):
    try:
        cliente = db_one('clientes', cid)
        puntos  = db_puntos(cid)
    except Exception as e:
        return f'Error: {e}', 500

    if not cliente:
        return 'Cliente no encontrado', 404

    if request.method == 'POST':
        action = request.form.get('action')
        try:
            if action == 'update_cliente':
                _sb.table('clientes').update({
                    'nombre':    request.form.get('nombre', '').strip().upper(),
                    'nit':       request.form.get('nit', '').strip(),
                    'telefono':  request.form.get('telefono', '').strip(),
                    'direccion': request.form.get('direccion', '').strip(),
                    'ciudad':    request.form.get('ciudad', '').strip(),
                }).eq('id', cid).execute()
                flash('Cliente actualizado.', 'success')

            elif action == 'add_punto':
                _sb.table('puntos_entrega').insert({
                    'cliente_id': cid,
                    'nombre':     request.form.get('punto_nombre', '').strip().upper(),
                    'ciudad':     request.form.get('punto_ciudad', '').strip(),
                }).execute()
                flash('Punto de entrega agregado.', 'success')

            elif action == 'delete_punto':
                pid = int(request.form.get('punto_id'))
                _sb.table('puntos_entrega').delete().eq('id', pid).execute()
                flash('Punto eliminado.', 'success')

        except Exception as e:
            flash(f'Error: {e}', 'danger')

        return redirect(url_for('cliente_detalle', cid=cid))

    return render_template('cliente_detalle.html', cliente=cliente, puntos=puntos)


# ── Configuración de empresas ─────────────────────────────────────────────────

@app.route('/configuracion')
def configuracion():
    try:
        empresas = db_empresas()
    except Exception as e:
        return f'Error: {e}', 500
    return render_template('configuracion.html', empresas=empresas)


@app.route('/configuracion/nueva', methods=['GET', 'POST'])
def empresa_nueva():
    if request.method == 'POST':
        logo_b64 = ''
        if 'logo' in request.files and request.files['logo'].filename:
            logo_b64 = base64.b64encode(request.files['logo'].read()).decode('utf-8')
        try:
            _sb.table('empresas').insert({
                'nombre':      request.form.get('nombre', '').strip(),
                'nit':         request.form.get('nit', '').strip(),
                'telefono':    request.form.get('telefono', '').strip(),
                'email':       request.form.get('email', '').strip(),
                'direccion':   request.form.get('direccion', '').strip(),
                'ciudad':      request.form.get('ciudad', '').strip(),
                'logo_base64': logo_b64,
            }).execute()
            flash('Empresa creada correctamente.', 'success')
            return redirect(url_for('configuracion'))
        except Exception as e:
            flash(f'Error: {e}', 'danger')
    return render_template('empresa_form.html', empresa=None)


@app.route('/configuracion/<int:eid>', methods=['GET', 'POST'])
def empresa_editar(eid):
    empresa = db_one('empresas', eid)
    if not empresa:
        return 'No encontrada', 404

    if request.method == 'POST':
        logo_b64 = empresa.get('logo_base64', '')
        if 'logo' in request.files and request.files['logo'].filename:
            logo_b64 = base64.b64encode(request.files['logo'].read()).decode('utf-8')
        try:
            _sb.table('empresas').update({
                'nombre':      request.form.get('nombre', '').strip(),
                'nit':         request.form.get('nit', '').strip(),
                'telefono':    request.form.get('telefono', '').strip(),
                'email':       request.form.get('email', '').strip(),
                'direccion':   request.form.get('direccion', '').strip(),
                'ciudad':      request.form.get('ciudad', '').strip(),
                'logo_base64': logo_b64,
            }).eq('id', eid).execute()
            flash('Empresa actualizada.', 'success')
            return redirect(url_for('configuracion'))
        except Exception as e:
            flash(f'Error: {e}', 'danger')

    return render_template('empresa_form.html', empresa=empresa)


if __name__ == '__main__':
    app.run(debug=True)
