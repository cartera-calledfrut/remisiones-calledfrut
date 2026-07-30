import io
import os
import base64
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable

# ── Colores (escala de grises) ────────────────────────────────────────────────
DARK    = colors.HexColor('#1a1a1a')
GRAY    = colors.HexColor('#555555')
LGRAY   = colors.HexColor('#f0f0f0')
BORDER  = colors.HexColor('#aaaaaa')
ACCENT  = colors.HexColor('#333333')
WHITE   = colors.white

# ── Anchos de columna — remisiones (total = 18 cm) ───────────────────────────
COL_CLIENT = [2.2*cm, 5.3*cm, 2.2*cm, 8.3*cm]
COL_ITEMS  = [1.2*cm, 11.3*cm, 2.0*cm, 1.75*cm, 1.75*cm]
COL_BOT    = [10*cm, 8*cm]
COL_TOT    = [5.5*cm, 2.5*cm]


def _s(size=8.5, bold=False, align=TA_LEFT, color=DARK):
    return ParagraphStyle('x', fontSize=size, leading=size * 1.4,
                          fontName='Helvetica-Bold' if bold else 'Helvetica',
                          alignment=align, textColor=color)

def _p(text, **kw):
    return Paragraph(str(text) if text else '', _s(**kw))

def _tbl(data, cols, cmds):
    t = Table(data, colWidths=cols)
    t.setStyle(TableStyle([
        ('VALIGN',       (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING',   (0,0), (-1,-1), 5),
        ('BOTTOMPADDING',(0,0), (-1,-1), 5),
        ('LEFTPADDING',  (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ] + cmds))
    return t


def _logo_image(empresa):
    b64 = empresa.get('logo_base64', '')
    if b64:
        try:
            data = base64.b64decode(b64)
            return Image(io.BytesIO(data), width=3.2*cm, height=2.6*cm, kind='proportional')
        except Exception:
            pass
    local = os.path.join(os.path.dirname(__file__), 'static', 'logo.png')
    if os.path.exists(local):
        return Image(local, width=3.2*cm, height=2.6*cm, kind='proportional')
    return _p('')


# ── PDF Remisión ──────────────────────────────────────────────────────────────

def generar_pdf(remision):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=1.5*cm,  bottomMargin=1.5*cm,
                            title=f'Remision {remision["numero"]}')

    empresa = remision.get('empresa', {})
    cliente = remision['cliente']
    punto   = remision['punto']
    items   = remision['items']
    elements = []

    # ── ENCABEZADO ────────────────────────────────────────────────────────────
    logo = _logo_image(empresa)

    empresa_txt = (
        f'<b>{empresa.get("nombre","")}</b><br/>'
        f'NIT {empresa.get("nit","")}<br/>'
        f'{empresa.get("direccion","")}<br/>'
        f'Tel: {empresa.get("telefono","")}<br/>'
        f'{empresa.get("ciudad","")}<br/>'
        f'{empresa.get("email","")}'
    )

    remision_box = _tbl(
        [[_p('REMISIÓN', size=8, bold=True, align=TA_CENTER, color=WHITE)],
         [_p(f'No. {remision["numero"]}', size=11, bold=True, align=TA_CENTER, color=WHITE)]],
        [4.3*cm],
        [('BACKGROUND',    (0,0), (-1,-1), ACCENT),
         ('TOPPADDING',    (0,0), (-1,-1), 8),
         ('BOTTOMPADDING', (0,0), (-1,-1), 8)],
    )

    header = _tbl(
        [[logo, Paragraph(empresa_txt, _s(8.5)), remision_box]],
        [3.5*cm, 10.2*cm, 4.3*cm],
        [('BOX',           (0,0), (-1,-1), 1,   BORDER),
         ('LINEBEFORE',    (1,0), (1,0),   0.5, BORDER),
         ('LINEBEFORE',    (2,0), (2,0),   0.5, BORDER),
         ('BACKGROUND',    (0,0), (1,0),   LGRAY),
         ('ALIGN',         (0,0), (0,0),   'CENTER'),
         ('LEFTPADDING',   (1,0), (1,0),   10),
         ('LEFTPADDING',   (2,0), (2,0),   0),
         ('RIGHTPADDING',  (2,0), (2,0),   0),
         ('TOPPADDING',    (2,0), (2,0),   0),
         ('BOTTOMPADDING', (2,0), (2,0),   0)],
    )
    elements.append(header)
    elements.append(Spacer(1, 0.3*cm))

    # ── DATOS DEL CLIENTE ─────────────────────────────────────────────────────
    def lbl(txt): return _p(txt, bold=True, size=7.5, color=GRAY)
    def val(txt): return _p(txt, size=8.5)

    client_rows = [
        [lbl('SEÑORES'),   val(cliente.get('nombre','')),
         lbl('FECHA'),     val(remision['fecha'])],
        [lbl('NIT'),       val(cliente.get('nit','')),
         lbl('TELÉFONO'),  val(cliente.get('telefono',''))],
        [lbl('DIRECCIÓN'), val(cliente.get('direccion','')),
         lbl('CIUDAD'),    val(punto['ciudad'])],
    ]
    client_t = _tbl(client_rows, COL_CLIENT, [
        ('BOX',       (0,0), (-1,-1), 1,    BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.25, BORDER),
        ('BACKGROUND',(0,0), (0,-1),  LGRAY),
        ('BACKGROUND',(2,0), (2,-1),  LGRAY),
    ])
    elements.append(client_t)
    elements.append(Spacer(1, 0.3*cm))

    # ── TABLA DE ÍTEMS ────────────────────────────────────────────────────────
    def hdr(t, align=TA_CENTER): return Paragraph(t, _s(8, bold=True, align=align, color=WHITE))

    rows = [[
        hdr('Ítem'),
        hdr('Descripción', TA_LEFT),
        hdr('Cantidad'),
        hdr('Vr. Bruto', TA_RIGHT),
        hdr('Vr. Unit.', TA_RIGHT),
    ]]

    for i, item in enumerate(items, 1):
        rows.append([
            _p(str(i),                           align=TA_CENTER, size=8.5),
            _p(item['descripcion'],               size=8.5),
            _p(f'{float(item["cantidad"]):.2f}',  align=TA_CENTER, size=8.5),
            _p('0.00',                            align=TA_RIGHT, size=8.5),
            _p('0.00',                            align=TA_RIGHT, size=8.5),
        ])

    empty = max(0, 7 - len(items))
    for _ in range(empty):
        rows.append([_p(''), _p(''), _p(''), _p(''), _p('')])

    row_h = [0.7*cm] + [0.65*cm] * (len(rows) - 1)
    items_t = Table(rows, colWidths=COL_ITEMS, rowHeights=row_h)
    items_t.setStyle(TableStyle([
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING',    (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING',   (0,0), (-1,-1), 6),
        ('RIGHTPADDING',  (0,0), (-1,-1), 6),
        ('BOX',           (0,0), (-1,-1), 1,    BORDER),
        ('INNERGRID',     (0,0), (-1,-1), 0.25, BORDER),
        ('BACKGROUND',    (0,0), (-1,0),  ACCENT),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [WHITE, colors.HexColor('#f8f8f8')]),
        ('ALIGN',         (0,1), (0,-1),  'CENTER'),
        ('ALIGN',         (2,1), (2,-1),  'CENTER'),
        ('ALIGN',         (3,0), (4,-1),  'RIGHT'),
    ]))
    elements.append(items_t)
    elements.append(Spacer(1, 0.3*cm))

    # ── PUNTO DE ENTREGA + OBSERVACIONES + TOTALES ───────────────────────────
    obs_rows = [
        [lbl('PUNTO DE ENTREGA')],
        [_p(punto['nombre'], size=9, bold=True)],
    ]
    observaciones = remision.get('observaciones', '').strip()
    if observaciones:
        obs_rows.append([lbl('OBSERVACIONES')])
        obs_rows.append([_p(observaciones, size=8.5)])

    obs_t = _tbl(
        obs_rows,
        [10*cm],
        [('BOX', (0,0), (-1,-1), 1, BORDER),
         ('BACKGROUND', (0,0), (-1,0), LGRAY),
         ('BACKGROUND', (0,2), (-1,2), LGRAY)],
    )
    tot_t = _tbl(
        [[_p('Total Bruto',   bold=True, size=8.5), _p('0.00', align=TA_RIGHT, size=8.5)],
         [_p('Total a Pagar', bold=True, size=8.5), _p('0.00', align=TA_RIGHT, size=8.5)]],
        COL_TOT,
        [('BOX',       (0,0), (-1,-1), 1,    BORDER),
         ('INNERGRID', (0,0), (-1,-1), 0.25, BORDER),
         ('ALIGN',     (1,0), (1,-1),  'RIGHT'),
         ('BACKGROUND',(0,1), (0,1),   LGRAY)],
    )
    bottom = Table([[obs_t, tot_t]], colWidths=COL_BOT)
    bottom.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),
                                ('RIGHTPADDING',(0,0),(0,-1),8)]))
    elements.append(bottom)
    elements.append(Spacer(1, 2*cm))

    # ── FIRMAS ────────────────────────────────────────────────────────────────
    line = colors.HexColor('#aaaaaa')
    sig = Table(
        [[_p('Entregado por:', size=8, color=GRAY), _p(''),
          _p('Recibido por:',  size=8, color=GRAY), _p('')]],
        colWidths=[2.5*cm, 6.5*cm, 2.5*cm, 6.5*cm],
    )
    sig.setStyle(TableStyle([
        ('VALIGN',        (0,0), (-1,-1), 'BOTTOM'),
        ('LINEBELOW',     (1,0), (1,0),   0.75, line),
        ('LINEBELOW',     (3,0), (3,0),   0.75, line),
        ('TOPPADDING',    (0,0), (-1,-1), 14),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    elements.append(sig)

    doc.build(elements)
    buffer.seek(0)
    return buffer


# ── PDF Proforma de exportación ───────────────────────────────────────────────

def generar_pdf_proforma(proforma):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=1.5*cm,  bottomMargin=1.5*cm,
                            title=f'Proforma {proforma["numero"]}')

    empresa   = proforma.get('empresa', {})
    comprador = proforma.get('comprador', {})
    items     = proforma.get('items', [])
    moneda    = proforma.get('moneda', 'USD')
    subtotal  = float(proforma.get('subtotal', 0))
    flete     = float(proforma.get('flete', 0))
    seguro    = float(proforma.get('seguro', 0))
    descuento = float(proforma.get('descuento', 0))
    total     = float(proforma.get('total', 0))
    banco     = proforma.get('banco', {})
    elements  = []

    def lbl(txt):   return _p(txt, bold=True, size=7.5, color=GRAY)
    def val(txt):   return _p(str(txt) if txt else '', size=8.5)
    def val_b(txt): return _p(str(txt) if txt else '', size=8.5, bold=True)
    def fmt(n):     return f'{float(n):,.2f}'
    def hdr_p(txt, align=TA_CENTER):
        return Paragraph(str(txt), _s(8, bold=True, align=align, color=WHITE))

    # ── ENCABEZADO ────────────────────────────────────────────────────────────
    logo = _logo_image(empresa)

    empresa_txt = (
        f'<b>{empresa.get("nombre","")}</b><br/>'
        f'NIT {empresa.get("nit","")}<br/>'
        f'{empresa.get("direccion","")}<br/>'
        f'Tel: {empresa.get("telefono","")}<br/>'
        f'{empresa.get("ciudad","")}<br/>'
        f'{empresa.get("email","")}'
    )

    title_box = _tbl(
        [[_p('PROFORMA INVOICE', size=9, bold=True, align=TA_CENTER, color=WHITE)],
         [_p(f'No. {proforma["numero"]}', size=11, bold=True, align=TA_CENTER, color=WHITE)]],
        [4.8*cm],
        [('BACKGROUND',    (0,0), (-1,-1), ACCENT),
         ('TOPPADDING',    (0,0), (-1,-1), 8),
         ('BOTTOMPADDING', (0,0), (-1,-1), 8)],
    )

    header = _tbl(
        [[logo, Paragraph(empresa_txt, _s(8.5)), title_box]],
        [3.5*cm, 9.7*cm, 4.8*cm],
        [('BOX',           (0,0), (-1,-1), 1,   BORDER),
         ('LINEBEFORE',    (1,0), (1,0),   0.5, BORDER),
         ('LINEBEFORE',    (2,0), (2,0),   0.5, BORDER),
         ('BACKGROUND',    (0,0), (1,0),   LGRAY),
         ('ALIGN',         (0,0), (0,0),   'CENTER'),
         ('LEFTPADDING',   (1,0), (1,0),   10),
         ('LEFTPADDING',   (2,0), (2,0),   0),
         ('RIGHTPADDING',  (2,0), (2,0),   0),
         ('TOPPADDING',    (2,0), (2,0),   0),
         ('BOTTOMPADDING', (2,0), (2,0),   0)],
    )
    elements.append(header)
    elements.append(Spacer(1, 0.3*cm))

    # ── FECHA / VALIDEZ / REFERENCIA ──────────────────────────────────────────
    fecha_t = _tbl(
        [[lbl('FECHA / DATE'),         val(proforma.get('fecha', '')),
          lbl('VÁLIDA HASTA / VALID UNTIL'), val(proforma.get('fecha_validez', '')),
          lbl('REFERENCIA / REF.'),    val(proforma.get('referencia', ''))]],
        [3.0*cm, 3.0*cm, 4.2*cm, 3.5*cm, 2.5*cm, 1.8*cm],
        [('BOX',       (0,0), (-1,-1), 1,    BORDER),
         ('INNERGRID', (0,0), (-1,-1), 0.25, BORDER),
         ('BACKGROUND',(0,0), (0,0),   LGRAY),
         ('BACKGROUND',(2,0), (2,0),   LGRAY),
         ('BACKGROUND',(4,0), (4,0),   LGRAY)],
    )
    elements.append(fecha_t)
    elements.append(Spacer(1, 0.3*cm))

    # ── EXPORTADOR | COMPRADOR ────────────────────────────────────────────────
    def party_block(titulo, filas):
        header_row = [_p(titulo, size=8, bold=True, align=TA_CENTER, color=WHITE)]
        rows = [header_row] + filas
        t = Table([[r] for r in rows], colWidths=[8.7*cm])
        t.setStyle(TableStyle([
            ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING',    (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING',   (0,0), (-1,-1), 6),
            ('RIGHTPADDING',  (0,0), (-1,-1), 6),
            ('BOX',           (0,0), (-1,-1), 1,    BORDER),
            ('INNERGRID',     (0,0), (-1,-1), 0.25, BORDER),
            ('BACKGROUND',    (0,0), (-1,0),  ACCENT),
        ]))
        return t

    exp_filas = [
        lbl('Razón social'), val_b(empresa.get('nombre', '')),
        lbl('NIT'),          val(empresa.get('nit', '')),
        lbl('Dirección'),    val(empresa.get('direccion', '')),
        lbl('Ciudad / País'),val(empresa.get('ciudad', '')),
        lbl('Tel / Email'),  val(f'{empresa.get("telefono","")}  {empresa.get("email","")}'),
    ]
    cmp_filas = [
        lbl('Razón social'),      val_b(comprador.get('nombre', '')),
        lbl('Tax ID / NIT'),      val(comprador.get('tax_id', '')),
        lbl('Dirección'),         val(comprador.get('direccion', '')),
        lbl('Ciudad / País'),     val(f'{comprador.get("ciudad","")}  {comprador.get("pais","")}'),
        lbl('Contacto / Email'),  val(comprador.get('contacto', '')),
    ]

    exp_t = party_block('EXPORTADOR / EXPORTER', exp_filas)
    cmp_t = party_block('COMPRADOR / BUYER',     cmp_filas)

    parties = Table([[exp_t, cmp_t]], colWidths=[9.0*cm, 9.0*cm])
    parties.setStyle(TableStyle([
        ('VALIGN',       (0,0), (-1,-1), 'TOP'),
        ('RIGHTPADDING', (0,0), (0,-1),  6),
        ('LEFTPADDING',  (1,0), (1,-1),  0),
    ]))
    elements.append(parties)
    elements.append(Spacer(1, 0.3*cm))

    # ── CONDICIONES DE ENVÍO ──────────────────────────────────────────────────
    ship_t = _tbl(
        [[lbl('INCOTERM'),
          val_b(proforma.get('incoterm', '')),
          lbl('EMBARQUE / ORIGIN'),
          val(f'{proforma.get("puerto_origen","")} ({proforma.get("pais_origen","")})'),
          lbl('DESTINO / DESTINATION'),
          val(f'{proforma.get("puerto_destino","")} ({proforma.get("pais_destino","")})')],
         [lbl('MONEDA / CURRENCY'),
          val_b(moneda),
          lbl('PLAZO / DELIVERY TIME'),
          val(proforma.get('plazo_entrega', '')),
          lbl(''),
          val('')]],
        [2.0*cm, 1.5*cm, 3.5*cm, 4.5*cm, 3.5*cm, 3.0*cm],
        [('BOX',       (0,0), (-1,-1), 1,    BORDER),
         ('INNERGRID', (0,0), (-1,-1), 0.25, BORDER),
         ('BACKGROUND',(0,0), (0,-1),  LGRAY),
         ('BACKGROUND',(2,0), (2,-1),  LGRAY),
         ('BACKGROUND',(4,0), (4,-1),  LGRAY)],
    )
    elements.append(ship_t)
    elements.append(Spacer(1, 0.3*cm))

    # ── TABLA DE ÍTEMS ────────────────────────────────────────────────────────
    COL_PF_ITEMS = [0.8*cm, 6.4*cm, 2.0*cm, 1.5*cm, 1.3*cm, 2.5*cm, 3.5*cm]

    pf_rows = [[
        hdr_p('#'),
        hdr_p('Descripción / Description', TA_LEFT),
        hdr_p('HS Code'),
        hdr_p('Qty'),
        hdr_p('Unit'),
        hdr_p('Unit Price', TA_RIGHT),
        hdr_p('Total', TA_RIGHT),
    ]]

    for i, item in enumerate(items, 1):
        qty   = float(item.get('cantidad', 0))
        price = float(item.get('precio_unitario', 0))
        subtot_item = qty * price
        pf_rows.append([
            _p(str(i),                    align=TA_CENTER, size=8),
            _p(item.get('descripcion',''),               size=8.5),
            _p(item.get('hs_code',''),    align=TA_CENTER, size=8),
            _p(f'{qty:g}',                align=TA_CENTER, size=8),
            _p(item.get('unidad','KG'),   align=TA_CENTER, size=8),
            _p(fmt(price),                align=TA_RIGHT,  size=8),
            _p(fmt(subtot_item),          align=TA_RIGHT,  size=8),
        ])

    empty = max(0, 5 - len(items))
    for _ in range(empty):
        pf_rows.append([_p('')]*7)

    row_h_pf = [0.65*cm] + [0.6*cm] * (len(pf_rows) - 1)
    items_t = Table(pf_rows, colWidths=COL_PF_ITEMS, rowHeights=row_h_pf)
    items_t.setStyle(TableStyle([
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING',    (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING',   (0,0), (-1,-1), 5),
        ('RIGHTPADDING',  (0,0), (-1,-1), 5),
        ('BOX',           (0,0), (-1,-1), 1,    BORDER),
        ('INNERGRID',     (0,0), (-1,-1), 0.25, BORDER),
        ('BACKGROUND',    (0,0), (-1,0),  ACCENT),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [WHITE, colors.HexColor('#f8f8f8')]),
        ('ALIGN',         (3,1), (6,-1),  'RIGHT'),
        ('ALIGN',         (0,1), (0,-1),  'CENTER'),
        ('ALIGN',         (2,1), (4,-1),  'CENTER'),
    ]))
    elements.append(items_t)
    elements.append(Spacer(1, 0.3*cm))

    # ── PAGO + TOTALES ────────────────────────────────────────────────────────
    anticipo_pct = int(proforma.get('anticipo_pct', 0))
    saldo_pct    = 100 - anticipo_pct

    pago_filas = [
        [_p('CONDICIONES DE PAGO', size=8, bold=True, align=TA_CENTER, color=WHITE)],
        [lbl('Forma de pago')],
        [val(proforma.get('forma_pago', ''))],
        [lbl(f'Anticipo: {anticipo_pct}%   |   Saldo: {saldo_pct}%')],
        [lbl('Banco')],
        [val(banco.get('nombre', ''))],
        [lbl('SWIFT / BIC')],
        [val(banco.get('swift', ''))],
        [lbl('Cuenta / Account')],
        [val(banco.get('cuenta', ''))],
        [lbl('Beneficiario / Beneficiary')],
        [val(banco.get('beneficiario', ''))],
    ]
    pago_t = Table([[r] for r in pago_filas], colWidths=[9.3*cm])
    pago_t.setStyle(TableStyle([
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING',    (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING',   (0,0), (-1,-1), 6),
        ('RIGHTPADDING',  (0,0), (-1,-1), 6),
        ('BOX',           (0,0), (-1,-1), 1,    BORDER),
        ('INNERGRID',     (0,0), (-1,-1), 0.25, BORDER),
        ('BACKGROUND',    (0,0), (-1,0),  ACCENT),
    ]))

    tot_rows = [
        [lbl('Subtotal'),                 _p(f'{moneda} {fmt(subtotal)}', align=TA_RIGHT, size=8.5)],
        [lbl('Flete / Freight'),          _p(f'{moneda} {fmt(flete)}',    align=TA_RIGHT, size=8.5)],
        [lbl('Seguro / Insurance'),       _p(f'{moneda} {fmt(seguro)}',   align=TA_RIGHT, size=8.5)],
        [lbl('Descuento / Discount (−)'), _p(f'{moneda} {fmt(descuento)}',align=TA_RIGHT, size=8.5)],
        [_p('TOTAL', bold=True, size=9),  _p(f'{moneda} {fmt(total)}',   align=TA_RIGHT, size=9, bold=True)],
    ]
    tot_t = _tbl(tot_rows, [4.5*cm, 4.2*cm], [
        ('BOX',       (0,0), (-1,-1), 1,    BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.25, BORDER),
        ('ALIGN',     (1,0), (1,-1),  'RIGHT'),
        ('BACKGROUND',(0,4), (-1,4),  LGRAY),
        ('LINEABOVE', (0,4), (-1,4),  1,    ACCENT),
    ])

    bottom = Table([[pago_t, tot_t]], colWidths=[9.5*cm, 8.5*cm])
    bottom.setStyle(TableStyle([
        ('VALIGN',       (0,0), (-1,-1), 'TOP'),
        ('RIGHTPADDING', (0,0), (0,-1),  6),
        ('LEFTPADDING',  (1,0), (1,-1),  0),
    ]))
    elements.append(bottom)

    # ── OBSERVACIONES ─────────────────────────────────────────────────────────
    obs = proforma.get('observaciones', '').strip()
    if obs:
        elements.append(Spacer(1, 0.3*cm))
        obs_t = _tbl(
            [[lbl('OBSERVACIONES / NOTES')],
             [_p(obs, size=8.5)]],
            [18*cm],
            [('BOX',        (0,0), (-1,-1), 1,    BORDER),
             ('INNERGRID',  (0,0), (-1,-1), 0.25, BORDER),
             ('BACKGROUND', (0,0), (-1,0),  LGRAY)],
        )
        elements.append(obs_t)

    elements.append(Spacer(1, 1.5*cm))

    # ── FIRMA ─────────────────────────────────────────────────────────────────
    line_color = colors.HexColor('#aaaaaa')
    sig = Table(
        [[_p('Elaborado por / Prepared by:', size=8, color=GRAY), _p(''),
          _p('Autorizado por / Authorized by:', size=8, color=GRAY), _p('')]],
        colWidths=[3.5*cm, 5.5*cm, 3.5*cm, 5.5*cm],
    )
    sig.setStyle(TableStyle([
        ('VALIGN',        (0,0), (-1,-1), 'BOTTOM'),
        ('LINEBELOW',     (1,0), (1,0),   0.75, line_color),
        ('LINEBELOW',     (3,0), (3,0),   0.75, line_color),
        ('TOPPADDING',    (0,0), (-1,-1), 14),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    elements.append(sig)

    doc.build(elements)
    buffer.seek(0)
    return buffer
