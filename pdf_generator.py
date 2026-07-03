from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
import io
import os

_BASE = os.path.dirname(__file__)
_LOGO = os.path.join(_BASE, 'static', 'logo.png')

# 18 cm usable width (A4 - 1.5cm margins each side)
COL_HEADER  = [3.5*cm, 10.0*cm, 4.5*cm]
COL_CLIENT  = [2.0*cm, 4.5*cm, 2.3*cm, 3.5*cm, 2.7*cm, 3.0*cm]
COL_ITEMS   = [1.5*cm, 7.0*cm, 2.5*cm, 2.0*cm, 2.5*cm, 2.5*cm]
COL_BOTTOM  = [9.5*cm, 5.5*cm, 3.0*cm]

BORDER   = ('BOX',       (0,0), (-1,-1), 0.75, colors.black)
GRID     = ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black)
VMID     = ('VALIGN',    (0,0), (-1,-1), 'MIDDLE')
PAD4     = [('TOPPADDING',(0,0),(-1,-1),4), ('BOTTOMPADDING',(0,0),(-1,-1),4),
            ('LEFTPADDING',(0,0),(-1,-1),4), ('RIGHTPADDING',(0,0),(-1,-1),4)]

def _s(size=8, bold=False, align=TA_LEFT):
    return ParagraphStyle(
        'x', fontSize=size, leading=size*1.35,
        fontName='Helvetica-Bold' if bold else 'Helvetica',
        alignment=align,
    )

def _p(text, size=8, bold=False, align=TA_LEFT):
    return Paragraph(str(text), _s(size, bold, align))

def _table(data, cols, style_cmds):
    t = Table(data, colWidths=cols)
    t.setStyle(TableStyle([VMID] + PAD4 + style_cmds))
    return t


def generar_pdf(remision):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=1.5*cm, rightMargin=1.5*cm,
        topMargin=1.5*cm,  bottomMargin=1.5*cm,
        title=f'Remision {remision["numero"]}',
    )

    elements = []
    cl = remision['cliente']
    pt = remision['punto']

    # ── HEADER ──────────────────────────────────────────────────────────────
    logo = (Image(_LOGO, width=3.0*cm, height=2.5*cm)
            if os.path.exists(_LOGO) else _p(''))

    empresa = (
        '<b>Sierra Viva SAS</b><br/>'
        'NIT 901.321.715-3<br/>'
        'Cra 27 20 Sur 101<br/>'
        'Tel: (3194839769)<br/>'
        'Medellín - Colombia<br/>'
        'cartera@calledfrut.co'
    )

    remision_box = _table(
        [[_p('Remisión', size=10, bold=True, align=TA_CENTER)],
         [_p(f'No. {remision["numero"]}', size=11, bold=True, align=TA_CENTER)]],
        [4.5*cm],
        [BORDER, ('ALIGN',(0,0),(-1,-1),'CENTER')],
    )

    header = _table(
        [[logo, Paragraph(empresa, _s(8)), remision_box]],
        COL_HEADER,
        [BORDER,
         ('LINEAFTER', (0,0), (0,0), 0.75, colors.black),
         ('LINEAFTER', (1,0), (1,0), 0.75, colors.black),
         ('ALIGN',  (0,0), (0,0), 'CENTER'),
         ('LEFTPADDING', (1,0), (1,0), 8)],
    )
    elements.append(header)

    # ── CLIENT INFO ──────────────────────────────────────────────────────────
    client_data = [
        [_p('Señores', bold=True), _p(cl['nombre']), '', '',
         _p('Fecha Elaboración', bold=True), _p(remision['fecha'])],
        [_p('NIT', bold=True), _p(cl['nit']),
         _p('Teléfono', bold=True), _p(cl.get('telefono', '')), '', ''],
        [_p('Dirección', bold=True), _p(cl.get('direccion', '')),
         _p('Ciudad', bold=True), _p(pt['ciudad']), '', ''],
    ]
    client_t = _table(client_data, COL_CLIENT, [
        BORDER, GRID,
        ('SPAN', (1,0), (3,0)),
        ('SPAN', (4,1), (5,1)),
        ('SPAN', (4,2), (5,2)),
    ])
    elements.append(client_t)

    # ── ITEMS TABLE ──────────────────────────────────────────────────────────
    def _hdr(txt, align=TA_LEFT):
        return _p(txt, bold=True, align=align)

    items_rows = [[
        _hdr('Ítem',         TA_CENTER),
        _hdr('Descripción'),
        _hdr('Producto',     TA_CENTER),
        _hdr('Cantidad',     TA_CENTER),
        _hdr('Vr. Bruto',   TA_RIGHT),
        _hdr('Vr. Unitario',TA_RIGHT),
    ]]

    for i, item in enumerate(remision['items'], 1):
        items_rows.append([
            _p(str(i),                       align=TA_CENTER),
            _p(item['descripcion']),
            _p(item['codigo'],               align=TA_CENTER),
            _p(f'{float(item["cantidad"]):.2f}', align=TA_CENTER),
            _p('0.00',                       align=TA_RIGHT),
            _p('0.00',                       align=TA_RIGHT),
        ])

    empty_needed = max(0, 8 - len(remision['items']))
    for _ in range(empty_needed):
        items_rows.append(['', '', '', '', '', ''])

    row_h = [0.65*cm] * len(items_rows)
    items_t = Table(items_rows, colWidths=COL_ITEMS, rowHeights=row_h)
    items_t.setStyle(TableStyle([
        VMID, BORDER, GRID,
        *PAD4,
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('ALIGN',  (0,1), (0,-1), 'CENTER'),
        ('ALIGN',  (2,1), (2,-1), 'CENTER'),
        ('ALIGN',  (3,1), (3,-1), 'CENTER'),
        ('ALIGN',  (4,0), (5,-1), 'RIGHT'),
    ]))
    elements.append(items_t)

    # ── OBSERVACIONES + TOTALES ──────────────────────────────────────────────
    obs_t = _table(
        [[_p('Observaciones:', bold=True)],
         [_p(pt['nombre'])]],
        [9.5*cm],
        [BORDER],
    )
    totales_t = _table(
        [[_p('Total Bruto',   bold=True), _p('0.00', align=TA_RIGHT)],
         [_p('Total a Pagar', bold=True), _p('0.00', align=TA_RIGHT)]],
        [5.5*cm, 3.0*cm],
        [BORDER, GRID, ('ALIGN',(1,0),(1,-1),'RIGHT')],
    )
    bottom = Table([[obs_t, totales_t]], colWidths=[9.5*cm, 8.5*cm])
    bottom.setStyle(TableStyle([VMID, ('ALIGN',(0,0),(-1,-1),'LEFT')]))
    elements.append(bottom)

    elements.append(Spacer(1, 1.8*cm))

    # ── SIGNATURES ───────────────────────────────────────────────────────────
    sig_t = Table(
        [[_p('Entregado\npor:'), _p('_' * 48), _p(''), _p('Recibido\npor:'), _p('_' * 48)]],
        colWidths=[2.0*cm, 6.0*cm, 0.5*cm, 2.0*cm, 7.5*cm],
    )
    sig_t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'BOTTOM')]))
    elements.append(sig_t)

    doc.build(elements)
    buffer.seek(0)
    return buffer
