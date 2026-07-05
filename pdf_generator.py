import io
import os
import base64
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable

# ── Colores ───────────────────────────────────────────────────────────────────
DARK    = colors.HexColor('#1a1a1a')
GRAY    = colors.HexColor('#666666')
LGRAY   = colors.HexColor('#f4f4f4')
BORDER  = colors.HexColor('#cccccc')
ACCENT  = colors.HexColor('#2d6a2d')
WHITE   = colors.white

# ── Anchos de columna (total = 18 cm) ────────────────────────────────────────
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
        [[_p('REMISIÓN', size=9, bold=True, align=TA_CENTER, color=WHITE)],
         [_p(f'No. {remision["numero"]}', size=13, bold=True, align=TA_CENTER, color=WHITE)]],
        [4.5*cm],
        [('BACKGROUND', (0,0), (-1,-1), ACCENT),
         ('ROWBACKGROUNDS', (0,0), (-1,-1), [ACCENT, ACCENT])],
    )

    header = _tbl(
        [[logo, Paragraph(empresa_txt, _s(8.5)), remision_box]],
        [3.5*cm, 10*cm, 4.5*cm],
        [('BOX',      (0,0), (-1,-1), 1, BORDER),
         ('LINEBEFORE',(1,0),(1,0),   0.5, BORDER),
         ('LINEBEFORE',(2,0),(2,0),   0.5, BORDER),
         ('BACKGROUND',(0,0),(1,0),   LGRAY),
         ('ALIGN',    (0,0),(0,0),    'CENTER'),
         ('LEFTPADDING',(1,0),(1,0),  10)],
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
    hdr_style = _s(8, bold=True, align=TA_CENTER, color=WHITE)
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
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [WHITE, LGRAY]),
        ('ALIGN',         (0,1), (0,-1),  'CENTER'),
        ('ALIGN',         (2,1), (2,-1),  'CENTER'),
        ('ALIGN',         (3,0), (4,-1),  'RIGHT'),
    ]))
    elements.append(items_t)
    elements.append(Spacer(1, 0.3*cm))

    # ── OBSERVACIONES + TOTALES ───────────────────────────────────────────────
    obs_t = _tbl(
        [[lbl('PUNTO DE ENTREGA')],
         [_p(punto['nombre'], size=9, bold=True)]],
        [10*cm],
        [('BOX', (0,0), (-1,-1), 1, BORDER),
         ('BACKGROUND', (0,0), (-1,0), LGRAY)],
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
        ('VALIGN',         (0,0), (-1,-1), 'BOTTOM'),
        ('LINEBELOW',      (1,0), (1,0),   0.75, line),
        ('LINEBELOW',      (3,0), (3,0),   0.75, line),
        ('TOPPADDING',     (0,0), (-1,-1), 14),
        ('BOTTOMPADDING',  (0,0), (-1,-1), 2),
    ]))
    elements.append(sig)

    doc.build(elements)
    buffer.seek(0)
    return buffer
