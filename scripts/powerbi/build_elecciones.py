# -*- coding: utf-8 -*-
"""Genera el proyecto Power BI (PBIP) del Tablero Elecciones AR desde cero.

Mismas convenciones que los tableros Macro y Energía (tema azul-violeta TemaArgentina, banda superior,
navegador de páginas, tarjetas y gráficos con el mismo estilo; formato PBIR + TMDL).

Uso:  python scripts/powerbi/build_elecciones.py [carpeta_salida]
      (por defecto: ./out/Tablero Elecciones Argentina). Después se abre el .pbip en Power BI Desktop.
"""
import json, os, shutil, sys, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import elecciones_modelo as mdl  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.getcwd(), 'out', 'Tablero Elecciones Argentina')
NOMBRE = 'Tablero Elecciones AR'
REP = NOMBRE + '.Report'
MOD = NOMBRE + '.SemanticModel'
PAGES = os.path.join(OUT, REP, 'definition', 'pages')
# Fijado a un commit: el mapa no depende de main ni de que exista la rama (el archivo no cambia).
URL_MAPA = ('https://raw.githubusercontent.com/camilofiocca/tableros-ar/'
            '57ffa60d5570d5fd331581972481f727e112f239/data/elecciones/mapa/provincias_ar.topojson')
BASE_THEME = os.path.join(AQUI, 'recursos', 'CY24SU10.json')

SCH = 'https://developer.microsoft.com/json-schemas/fabric/'
SCHEMA_VC = SCH + 'item/report/definition/visualContainer/2.7.0/schema.json'
SCHEMA_PAGE = SCH + 'item/report/definition/page/2.1.0/schema.json'
SCHEMA_REPORT = SCH + 'item/report/definition/report/3.2.0/schema.json'

# ----------------------------------------------------------------------------------------------- paleta
NAVY, INDIGO, VIOLETA, LINEA, CAPTION = '#242C4F', '#4643A8', '#9B6BEA', '#7C5CE6', '#5F52C9'
CELESTE, SOL, ARANDANO, VERDE, ROJO = '#2A9FD6', '#E0A100', '#C2185B', '#2E7D33', '#C62828'
INK, INK2, BORDE, SOMBRA, GRILLA = '#1B1F3B', '#6B6F8A', '#DEDBF0', '#BDB7E0', '#EAE8F5'
FILA_ALT, PAGINA, LAVANDA = '#F6F5FC', '#F4F3FA', '#A99BEA'
COLOR_ESP = {'Peronismo': '#2A9FD6', 'Terceras vías': '#00897B', 'UCR y aliados': '#C62828', 'PRO-JxC': '#E0A100',
             'LLA': '#4643A8', 'Centroderecha': '#EF6C00', 'Centroizquierda': '#2E7D33', 'Izquierda': '#C2185B',
             'Provinciales': '#8D6E63'}


# ----------------------------------------------------------------------------------------------- utilidades
def wjson(p, d):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    s = json.dumps(d, ensure_ascii=False, indent=2)
    with open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(s.replace('\n', '\r\n'))


def wtext(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(s.replace('\r\n', '\n').replace('\n', '\r\n'))


def L(v): return {'expr': {'Literal': {'Value': v}}}
def S(t): return L("'" + t.replace("'", "''") + "'")
def C(h): return {'solid': {'color': S(h)}}
def M(m, e='Medidas'): return {'Measure': {'Expression': {'SourceRef': {'Entity': e}}, 'Property': m}}
def COL(e, p): return {'Column': {'Expression': {'SourceRef': {'Entity': e}}, 'Property': p}}
def CM(m): return {'solid': {'color': {'expr': M(m)}}}


def proj_m(m, display=None, e='Medidas'):
    p = {'field': M(m, e), 'queryRef': '%s.%s' % (e, m), 'nativeQueryRef': m}
    if display: p['displayName'] = display
    return p


def proj_c(e, prop, display=None, active=False):
    p = {'field': COL(e, prop), 'queryRef': '%s.%s' % (e, prop), 'nativeQueryRef': prop}
    if display: p['displayName'] = display
    if active: p['active'] = True
    return p


WILD = {'data': [{'dataViewWildcard': {'matchingOption': 1}}]}


def filtro_in(entidad, prop, valores, alias='f'):
    return {'Version': 2, 'From': [{'Name': alias, 'Entity': entidad, 'Type': 0}],
            'Where': [{'Condition': {'In': {'Expressions': [{'Column': {'Expression': {'SourceRef': {'Source': alias}}, 'Property': prop}}],
                                            'Values': [[{'Literal': {'Value': "'" + v.replace("'", "''") + "'"}}] for v in valores]}}}]}


def filtro_cfg(nombre, entidad, prop, valores):
    return {'name': nombre, 'field': COL(entidad, prop), 'type': 'Categorical', 'filter': filtro_in(entidad, prop, valores),
            'howCreated': 'User'}


def contenedor(titulo=None, titulo_medida=None, borde=True, fondo='#FFFFFF', sombra=True, header=False,
               pad=(6, 6, 10, 10), titulo_color=NAVY, titulo_size=11, alineacion='left'):
    t = {'show': L('true' if (titulo or titulo_medida) else 'false'), 'fontFamily': S('Arial'),
         'fontSize': L('%dD' % titulo_size), 'fontColor': C(titulo_color), 'bold': L('true'), 'alignment': S(alineacion)}
    if titulo: t['text'] = S(titulo)
    if titulo_medida: t['text'] = {'expr': M(titulo_medida)}
    o = {'title': [{'properties': t}],
         'background': [{'properties': {'show': L('true' if fondo else 'false'), 'color': C(fondo or '#FFFFFF'), 'transparency': L('0D')}}],
         'border': [{'properties': {'show': L('true' if borde else 'false'), 'color': C(BORDE), 'radius': L('10D')}}],
         'dropShadow': [{'properties': {'show': L('true' if sombra else 'false'), 'color': C(SOMBRA), 'position': S('Outer'),
                                        'preset': S('BottomRight'), 'transparency': L('78D')}}],
         'padding': [{'properties': {'top': L('%dD' % pad[0]), 'bottom': L('%dD' % pad[1]), 'left': L('%dD' % pad[2]), 'right': L('%dD' % pad[3])}}]}
    if not header:
        o['visualHeader'] = [{'properties': {'show': L('false')}}]
    return o


def visual(name, pos, vtype, query=None, objects=None, vco=None, extra=None, filtros=None):
    x, y, w, h, z = pos
    v = {'visualType': vtype}
    if query is not None: v['query'] = query
    if objects is not None: v['objects'] = objects
    v['visualContainerObjects'] = vco if vco is not None else contenedor()
    v['drillFilterOtherVisuals'] = True
    if extra: v.update(extra)
    d = {'$schema': SCHEMA_VC, 'name': name,
         'position': {'x': x, 'y': y, 'z': z, 'height': h, 'width': w, 'tabOrder': z // 100}, 'visual': v}
    if filtros:
        d['filterConfig'] = {'filters': filtros}
    return d


def tarjeta(name, pos, medida, etiqueta, titulo=None, titulo_medida=None, size=20, color=NAVY):
    objects = {'labels': [{'properties': {'fontSize': L('%dD' % size), 'color': C(color), 'labelDisplayUnits': L('1D'),
                                          'fontFamily': S('Arial'), 'bold': L('true')}}],
               'categoryLabels': [{'properties': {'show': L('true'), 'fontSize': L('9D'), 'fontFamily': S('Arial'), 'color': C(INK2)}}],
               'wordWrap': [{'properties': {'show': L('true')}}]}
    q = {'queryState': {'Values': {'projections': [proj_m(medida, etiqueta)]}}}
    return visual(name, pos, 'card', q, objects,
                  contenedor(titulo=titulo, titulo_medida=titulo_medida, titulo_color=CAPTION, titulo_size=9, alineacion='center'))


def tarjeta_texto(name, pos, medida, titulo=None, size=10, bold=False, color=INK, fondo='#FFFFFF', borde=True):
    objects = {'labels': [{'properties': {'fontSize': L('%dD' % size), 'color': C(color), 'labelDisplayUnits': L('1D'),
                                          'fontFamily': S('Arial'), 'bold': L('true' if bold else 'false')}}],
               'categoryLabels': [{'properties': {'show': L('false'), 'fontSize': L('9D'), 'fontFamily': S('Arial'), 'color': C(INK2)}}],
               'wordWrap': [{'properties': {'show': L('true')}}]}
    q = {'queryState': {'Values': {'projections': [proj_m(medida)]}}}
    return visual(name, pos, 'card', q, objects, contenedor(titulo=titulo, fondo=fondo, borde=borde, sombra=borde))


def imagen(name, pos, medida, titulo=None):
    objects = {'image': [{'properties': {'sourceType': S('imageData'), 'sourceField': {'expr': M(medida)},
                                         'transparency': L('0D'), 'effects': L('false')}}],
               'imageScaling': [{'properties': {'imageScalingType': S('Fit')}}]}
    return visual(name, pos, 'image', None, objects, contenedor(titulo=titulo))


def texto(name, pos, parrafos, fondo='#FFFFFF', borde=True):
    ps = []
    for runs in parrafos:
        trs = []
        for t, size, bold, color in runs:
            st = {'fontFamily': 'Arial', 'fontSize': '%spt' % size, 'color': color}
            if bold: st['fontWeight'] = 'bold'
            trs.append({'value': t, 'textStyle': st})
        ps.append({'textRuns': trs})
    return visual(name, pos, 'textbox', None, {'general': [{'properties': {'paragraphs': ps}}]},
                  contenedor(borde=borde, sombra=borde, fondo=fondo))


def _ejes(columnas=False, mostrar_valor=True):
    cat = {'showAxisTitle': L('false'), 'fontFamily': S('Arial'), 'fontSize': L('9D'), 'labelColor': C(INK2), 'gridlineShow': L('false')}
    if columnas: cat['innerPadding'] = L('18D')
    val = {'show': L('true' if mostrar_valor else 'false'), 'showAxisTitle': L('false'), 'fontFamily': S('Arial'), 'fontSize': L('9D'),
           'labelColor': C(INK2), 'gridlineShow': L('true'), 'gridlineColor': C(GRILLA), 'gridlineStyle': S('solid'), 'gridlineThickness': L('1D')}
    return [{'properties': cat}], [{'properties': val}]


def grafico(name, pos, tipo, eje, series, titulo, leyenda=None, filtros=None, marcadores=False):
    """tipo: lineChart | clusteredColumnChart. eje: (tabla, columna). series: [(medida, nombre, color)]."""
    cat, val = _ejes(tipo != 'lineChart')
    if leyenda is None: leyenda = len(series) > 1
    objects = {'legend': [{'properties': {'show': L('true' if leyenda else 'false'), 'position': S('Top'), 'showTitle': L('false'),
                                          'fontFamily': S('Arial'), 'fontSize': L('9D'), 'labelColor': C(INK)}}],
               'categoryAxis': cat, 'valueAxis': val,
               'dataPoint': [{'properties': {'fill': C(c)}, 'selector': {'metadata': 'Medidas.' + m}} for m, n, c in series]}
    if tipo == 'lineChart':
        objects['lineStyles'] = [{'properties': {'strokeWidth': L('2D'), 'showMarker': L('true' if marcadores else 'false')}}]
    q = {'queryState': {'Category': {'projections': [proj_c(eje[0], eje[1], active=True)]},
                        'Y': {'projections': [proj_m(m, n) for m, n, c in series]}}}
    return visual(name, pos, tipo, q, objects, contenedor(titulo=titulo, header=True), filtros=filtros)


def barras(name, pos, cat, medida, color_medida, titulo, nombre_valor=None, orden_medida=True, filtros=None, titulo_medida=None):
    """Barras horizontales con el color de cada barra tomado de una medida (color del espacio)."""
    c_ax, v_ax = _ejes(False, mostrar_valor=False)
    objects = {'categoryAxis': c_ax, 'valueAxis': v_ax,
               'legend': [{'properties': {'show': L('false')}}],
               'dataPoint': [{'properties': {'fill': CM(color_medida)}, 'selector': WILD}],
               'labels': [{'properties': {'show': L('true'), 'fontFamily': S('Arial'), 'fontSize': L('9D'), 'color': C(INK),
                                          'labelDisplayUnits': L('1D'), 'labelPrecision': L('1L')}}]}
    q = {'queryState': {'Category': {'projections': [proj_c(cat[0], cat[1], active=True)]},
                        'Y': {'projections': [proj_m(medida, nombre_valor)]}}}
    if orden_medida:
        q['sortDefinition'] = {'sort': [{'field': M(medida), 'direction': 'Descending'}], 'isDefaultSort': True}
    return visual(name, pos, 'clusteredBarChart', q, objects, contenedor(titulo=titulo, titulo_medida=titulo_medida, header=True), filtros=filtros)


def tabla(name, pos, columnas, titulo, anchos=None, orden=None, titulo_medida=None):
    """columnas: [('M'|'C', tabla, campo, nombre)]."""
    projs = [proj_m(c, n, t) if k == 'M' else proj_c(t, c, n) for k, t, c, n in columnas]
    q = {'queryState': {'Values': {'projections': projs}}}
    if orden:
        k, t, c, d = orden
        q['sortDefinition'] = {'sort': [{'field': (M(c, t) if k == 'M' else COL(t, c)), 'direction': d}], 'isDefaultSort': True}
    objects = {'values': [{'properties': {'wordWrap': L('true'), 'fontSize': L('9D'), 'fontFamily': S('Arial'),
                                          'fontColorPrimary': C(INK), 'fontColorSecondary': C(INK),
                                          'backColorPrimary': C('#FFFFFF'), 'backColorSecondary': C(FILA_ALT)}}],
               'columnHeaders': [{'properties': {'wordWrap': L('true'), 'fontSize': L('9D'), 'bold': L('true'), 'fontFamily': S('Arial'),
                                                 'fontColor': C('#FFFFFF'), 'backColor': C(NAVY), 'alignment': S('Left')}}],
               'grid': [{'properties': {'rowPadding': L('4D'), 'gridHorizontal': L('true'), 'gridHorizontalColor': C(GRILLA),
                                        'gridVertical': L('false'), 'outlineColor': C(GRILLA)}}],
               'total': [{'properties': {'totals': L('false')}}]}
    if anchos:
        objects['columnWidth'] = [{'properties': {'value': L('%dD' % w)}, 'selector': {'metadata': '%s.%s' % (t, c)}}
                                  for (k, t, c, n), w in zip(columnas, anchos)]
    return visual(name, pos, 'tableEx', q, objects, contenedor(titulo=titulo, titulo_medida=titulo_medida, header=True))


def matriz(name, pos, filas, columnas, valor, color_fondo, titulo):
    q = {'queryState': {'Rows': {'projections': [proj_c(filas[0], filas[1], active=True)]},
                        'Columns': {'projections': [proj_c(columnas[0], columnas[1], active=True)]},
                        'Values': {'projections': [proj_m(valor, ' ')]}}}
    objects = {'values': [{'properties': {'fontSize': L('8D'), 'fontFamily': S('Arial'), 'fontColorPrimary': C('#FFFFFF'),
                                          'fontColorSecondary': C('#FFFFFF'), 'wordWrap': L('false'),
                                          'bandedRowHeaders': L('false')}},
                          {'properties': {'backColor': CM(color_fondo)}, 'selector': {'data': [{'dataViewWildcard': {'matchingOption': 1}}], 'metadata': 'Medidas.' + valor}}],
               'columnHeaders': [{'properties': {'fontSize': L('8D'), 'bold': L('true'), 'fontFamily': S('Arial'),
                                                 'fontColor': C('#FFFFFF'), 'backColor': C(NAVY), 'alignment': S('Center'), 'wordWrap': L('true')}}],
               'rowHeaders': [{'properties': {'fontSize': L('9D'), 'fontFamily': S('Arial'), 'fontColor': C(INK), 'backColor': C('#FFFFFF')}}],
               'grid': [{'properties': {'rowPadding': L('2D'), 'gridHorizontal': L('true'), 'gridHorizontalColor': C('#FFFFFF'),
                                        'gridHorizontalWeight': L('2D'), 'gridVertical': L('true'), 'gridVerticalColor': C('#FFFFFF'),
                                        'gridVerticalWeight': L('2D')}}],
               'subTotals': [{'properties': {'rowSubtotals': L('false'), 'columnSubtotals': L('false')}}]}
    return visual(name, pos, 'pivotTable', q, objects, contenedor(titulo=titulo, header=True))


def mapa_formas(name, pos, color_medida, titulo, tooltips, tooltip_pagina=None, titulo_medida=None):
    """Mapa de formas de provincias (TopoJSON por URL), coloreado por una medida que devuelve el color."""
    q = {'queryState': {'Category': {'projections': [proj_c('provincias', 'provincia_mapa', 'Provincia', active=True)]},
                        'Tooltips': {'projections': [proj_m(m, n) for m, n in tooltips]}}}
    objects = {'shape': [{'properties': {'datasourceType': S('url'), 'mapUrl': S(URL_MAPA), 'projectionEnum': S('mercator')}}],
               'dataPoint': [{'properties': {'fill': CM(color_medida)}, 'selector': WILD}],
               'defaultColors': [{'properties': {'defaultShow': L('true'), 'defaultColor': C('#E4E2EE'),
                                                 'borderColor': C('#FFFFFF'), 'borderThickness': L('1D')}}],
               'zoom': [{'properties': {'autoZoom': L('true'), 'manualZoom': L('true'), 'selectionZoom': L('false')}}],
               'legend': [{'properties': {'show': L('false')}}]}
    vco = contenedor(titulo=titulo, titulo_medida=titulo_medida, header=True)
    if tooltip_pagina:
        vco['visualTooltip'] = [{'properties': {'show': L('true'), 'type': S('Canvas'), 'section': S(tooltip_pagina)}}]
    return visual(name, pos, 'shapeMap', q, objects, vco)


def segmentador(name, pos, entidad, prop, titulo, defecto, multiple=False, modo='Dropdown', orden_desc=True):
    objects = {'data': [{'properties': {'mode': S(modo)}}],
               'selection': [{'properties': {'singleSelect': L('false' if multiple else 'true'),
                                             'strictSingleSelect': L('false' if multiple else 'true')}}],
               'header': [{'properties': {'show': L('false')}}],
               'items': [{'properties': {'fontFamily': S('Arial'), 'fontColor': C(INK), 'textSize': L('10D'), 'background': C('#FFFFFF')}}],
               'general': [{'properties': {'filter': {'filter': filtro_in(entidad, prop, defecto)}}}]}
    q = {'queryState': {'Values': {'projections': [proj_c(entidad, prop, active=True)]}}}
    if orden_desc:
        q['sortDefinition'] = {'sort': [{'field': COL(entidad, prop), 'direction': 'Descending'}], 'isDefaultSort': True}
    return visual(name, pos, 'slicer', q, objects, contenedor(titulo=titulo, titulo_color=CAPTION, titulo_size=9, pad=(4, 4, 8, 8)))


# ----------------------------------------------------------------------------------------------- páginas
PAGINAS = [('resumen', 'Resumen'), ('mapa', 'Mapa'), ('fuerza', 'Por espacio'), ('presidenciales', 'Presidenciales'),
           ('intermedias', 'Intermedias'), ('evolucion', 'Evolución'), ('participacion', 'Participación'), ('datos', 'Datos')]
ORDEN = [p for p, _ in PAGINAS] + ['tt_provincia']


def pagina(name, display, filtros=None, interacciones=None, tooltip=False):
    d = {'$schema': SCHEMA_PAGE, 'name': name, 'displayName': display, 'displayOption': 'FitToPage', 'height': 720, 'width': 1280,
         'objects': {'background': [{'properties': {'color': C(PAGINA), 'transparency': L('0D')}}]}}
    if tooltip:
        d.update({'displayOption': 'ActualSize', 'height': 240, 'width': 320, 'type': 'Tooltip', 'visibility': 'HiddenInViewMode',
                  'pageBinding': {'name': 'tt_' + name, 'type': 'Tooltip'}})
        d['objects']['background'][0]['properties']['color'] = C('#FFFFFF')
    if filtros:
        d['filterConfig'] = {'filters': filtros}
    if interacciones:
        d['visualInteractions'] = [{'source': i[0], 'target': i[1], 'type': i[2] if len(i) > 2 else 'NoFilter'} for i in interacciones]
    wjson(os.path.join(PAGES, name, 'page.json'), d)


def put(page, v):
    wjson(os.path.join(PAGES, page, 'visuals', v['name'], 'visual.json'), v)


def encabezado(p, titulo, sub):
    put(p, texto(p + '_banda', (0, 0, 1280, 58, 100), [[(titulo, 15, True, '#FFFFFF')], [(sub, 9, False, '#C9C5EE')]], fondo=NAVY, borde=False))
    put(p, texto(p + '_linea', (0, 58, 1280, 3, 110), [[(' ', 1, False, LINEA)]], fondo=LINEA, borde=False))
    v = tarjeta_texto(p + '_upd', (1040, 15, 224, 30, 120), 'Actualizado', size=9, color='#FFFFFF', fondo=INDIGO, borde=False)
    v['visual']['visualContainerObjects']['border'] = [{'properties': {'show': L('false'), 'radius': L('14D')}}]
    put(p, v)
    nav = {'fill': [{'properties': {'show': L('true'), 'fillColor': C('#FFFFFF'), 'transparency': L('0D')}, 'selector': {'id': 'default'}},
                    {'properties': {'fillColor': C(INDIGO)}, 'selector': {'id': 'selected'}},
                    {'properties': {'fillColor': C('#E4E0FA')}, 'selector': {'id': 'hover'}}],
           'text': [{'properties': {'fontFamily': S('Arial'), 'fontSize': L('10D'), 'fontColor': C(INK), 'bold': L('false')}, 'selector': {'id': 'default'}},
                    {'properties': {'fontColor': C('#FFFFFF'), 'bold': L('true')}, 'selector': {'id': 'selected'}}],
           'outline': [{'properties': {'show': L('true'), 'lineColor': C(BORDE), 'weight': L('1D')}, 'selector': {'id': 'default'}}],
           'shape': [{'properties': {'tileShape': S('rectangleRounded'), 'rectangleRoundedCurve': L('8L')}}],
           'pages': [{'properties': {'showHiddenPages': L('false'), 'showTooltipPages': L('false')}}],
           'layout': [{'properties': {'cellPadding': L('6L')}}]}
    put(p, visual(p + '_nav', (16, 68, 1248, 32, 130), 'pageNavigator', None, nav,
                  contenedor(borde=False, sombra=False, fondo=None, pad=(0, 0, 0, 0))))


def tarjetas(p, y, defs, x0=16, ancho=1248, h=80, z0=500):
    n = len(defs); gap = 8
    w = (ancho - gap * (n - 1)) / n
    for i, d in enumerate(defs):
        medida, etiqueta, kw = d[0], d[1], (d[2] if len(d) > 2 else {})
        put(p, tarjeta('%s_k%d' % (p, i), (round(x0 + i * (w + gap), 1), y, round(w, 1), h, z0 + 10 * i), medida, etiqueta, **kw))


TT = [('Ganador', 'Ganador'), ('% ganador', '% ganador'), ('Segundo', 'Segundo'), ('Margen (pp)', 'Margen'), ('Participación', 'Participación')]
SERIES_HIST = [('% Peronismo', 'Peronismo', COLOR_ESP['Peronismo']), ('% UCR y aliados', 'UCR y aliados', COLOR_ESP['UCR y aliados']),
               ('% PRO-JxC', 'PRO-JxC', COLOR_ESP['PRO-JxC']), ('% LLA', 'LLA', COLOR_ESP['LLA']),
               ('% Terceras vías', 'Terceras vías', COLOR_ESP['Terceras vías']), ('% Centroizquierda', 'Centroizquierda', COLOR_ESP['Centroizquierda']),
               ('% Centroderecha', 'Centroderecha', COLOR_ESP['Centroderecha']), ('% Izquierda', 'Izquierda', COLOR_ESP['Izquierda'])]


def construir_reporte():
    # ---------------------------------------------------------------- Resumen
    P = 'resumen'
    pagina(P, 'Resumen')
    encabezado(P, 'Elecciones en Argentina, 1983-2025', 'Presidenciales y legislativas nacionales por provincia · DINE, CNE y Atlas Electoral de Andy Tow')
    tarjetas(P, 110, [('KPI balotaje ganador', 'Ganador del balotaje', {'titulo_medida': 'KPI balotaje título', 'size': 16}),
                      ('KPI balotaje %', 'Votos positivos', {'titulo': 'Porcentaje en el balotaje'}),
                      ('KPI intermedia ganador', 'Espacio más votado', {'titulo_medida': 'KPI intermedia título', 'size': 16}),
                      ('KPI intermedia %', 'Votos para diputados', {'titulo': 'Porcentaje nacional (diputados)'}),
                      ('KPI intermedia participación', 'Del padrón', {'titulo_medida': 'KPI intermedia part. título'})])
    put(P, imagen('res_mapa', (16, 200, 262, 507, 600), 'SVG mapa última intermedia', 'Ganador por provincia, última intermedia'))
    put(P, grafico('res_evol', (288, 200, 600, 300, 700), 'lineChart', ('elecciones', 'anio'), SERIES_HIST[:6],
                   'Intermedias 1985-2025: votos para diputados por espacio (% nacional)',
                   filtros=[filtro_cfg('f_res_evol', 'elecciones', 'categoria', ['Diputados (intermedia)'])], marcadores=True))
    put(P, barras('res_barras', (288, 510, 600, 197, 800), ('espacios', 'espacio_corto'), '% espacio última intermedia', 'Color espacio',
                  'Última intermedia: votos por espacio (% nacional)', '% nacional'))
    put(P, tarjeta_texto('res_lectura', (898, 200, 366, 300, 900), 'Lectura resumen', titulo='Lectura automática', size=10))
    put(P, tabla('res_tabla', (898, 510, 366, 197, 1000),
                 [('C', 'provincias', 'provincia', 'Provincia'), ('M', 'Medidas', 'Espacio ganador última intermedia (provincia)', 'Ganó'),
                  ('M', 'Medidas', '% ganador última intermedia (provincia)', '%'), ('M', 'Medidas', 'Margen última intermedia (provincia)', 'Margen')],
                 'Última intermedia por provincia', anchos=[130, 95, 55, 60], orden=('C', 'provincias', 'provincia', 'Ascending')))

    # ---------------------------------------------------------------- Mapa
    P = 'mapa'
    pagina(P, 'Mapa', interacciones=[('map_mapa', 'map_barras', 'DataFilter')])
    encabezado(P, 'Mapa electoral interactivo', 'Elegí una elección y hacé clic en una provincia: toda la página pasa a mostrar esa provincia')
    put(P, segmentador('map_eleccion', (16, 110, 360, 58, 300), 'elecciones', 'etiqueta', 'Elección', ['2025 · Diputados (intermedia)']))
    put(P, tarjeta_texto('map_nota', (386, 110, 878, 58, 310), 'Nota de la elección', size=9, color=INK2))
    put(P, mapa_formas('map_mapa', (16, 176, 520, 531, 400), 'Color ganador', None, TT, 'tt_provincia', titulo_medida='Etiqueta elección'))
    tarjetas(P, 176, [('Ganador', 'Ganador', {'titulo_medida': 'Ámbito', 'size': 14}), ('% ganador', 'Votos positivos', {'titulo': 'Porcentaje del ganador'}),
                      ('Margen (pp)', 'Sobre el segundo', {'titulo': 'Margen'}), ('Participación', 'Del padrón', {'titulo': 'Participación'})],
             x0=546, ancho=718)
    put(P, tarjeta_texto('map_lectura', (546, 264, 718, 52, 600), 'Lectura de la elección', size=10))
    put(P, barras('map_barras', (546, 324, 350, 383, 700), ('espacios', 'espacio_corto'), '% votos', 'Color espacio',
                  None, '% votos', titulo_medida='Etiqueta ámbito'))
    put(P, tabla('map_tabla', (906, 324, 358, 383, 800),
                 [('C', 'provincias', 'provincia', 'Provincia'), ('M', 'Medidas', 'Ganador espacio', 'Ganó'),
                  ('M', 'Medidas', '% ganador', '%'), ('M', 'Medidas', 'Margen (pp)', 'Margen'), ('M', 'Medidas', 'Participación', 'Partic.')],
                 'Todas las provincias', anchos=[110, 80, 50, 55, 55], orden=('C', 'provincias', 'provincia', 'Ascending')))

    # ---------------------------------------------------------------- Por espacio (intensidad)
    P = 'fuerza'
    pagina(P, 'Por espacio')
    encabezado(P, 'Dónde es fuerte cada espacio', 'Porcentaje de votos de un espacio en cada provincia · elegí la elección y el espacio')
    put(P, segmentador('fue_eleccion', (16, 110, 360, 58, 300), 'elecciones', 'etiqueta', 'Elección', ['2025 · Diputados (intermedia)']))
    put(P, segmentador('fue_espacio', (386, 110, 300, 58, 310), 'espacios', 'espacio_corto', 'Espacio', ['LLA'], orden_desc=False))
    put(P, tarjeta_texto('fue_nota', (696, 110, 568, 58, 320), 'Etiqueta intensidad', size=10, bold=True, color=NAVY))
    put(P, mapa_formas('fue_mapa', (16, 176, 520, 531, 400), 'Color intensidad del espacio', 'Más oscuro = más votos (escalones de 10 puntos)',
                       [('% votos', '% del espacio'), ('Votos', 'Votos')]))
    put(P, barras('fue_barras', (546, 176, 718, 531, 500), ('provincias', 'provincia'), '% votos', 'Color espacio',
                  'Votos del espacio por provincia (%)', '% votos'))

    # ---------------------------------------------------------------- Presidenciales
    P = 'presidenciales'
    pagina(P, 'Presidenciales', filtros=[filtro_cfg('f_pres', 'elecciones', 'cargo', ['Presidente'])],
           interacciones=[('pre_eleccion', 'pre_hist'), ('pre_mapa', 'pre_hist'), ('pre_mapa', 'pre_barras', 'DataFilter')])
    encabezado(P, 'Elecciones presidenciales', 'Primera vuelta 1983-2023, balotajes 2015 y 2023 y PASO 2011-2023 · hacé clic en el mapa para ver una provincia')
    put(P, segmentador('pre_eleccion', (16, 110, 360, 58, 300), 'elecciones', 'etiqueta', 'Elección', ['2023 · Presidente balotaje']))
    put(P, tarjeta_texto('pre_nota', (386, 110, 878, 58, 310), 'Nota de la elección', size=9, color=INK2))
    tarjetas(P, 176, [('Ganador', 'Fórmula ganadora', {'titulo_medida': 'Ámbito', 'size': 13}), ('% ganador', 'Votos positivos', {'titulo': 'Porcentaje del ganador'}),
                      ('Segundo', 'Segunda fórmula', {'titulo': 'Segundo', 'size': 13}), ('Margen (pp)', 'Diferencia', {'titulo': 'Margen'}),
                      ('Distritos ganados', 'Distritos', {'titulo': 'Distritos ganados por el ganador'})])
    put(P, barras('pre_barras', (16, 264, 420, 443, 600), ('resultados', 'opcion'), '% votos (top 8)', 'Color opción',
                  None, '% votos', titulo_medida='Etiqueta ámbito'))
    put(P, mapa_formas('pre_mapa', (446, 264, 330, 443, 700), 'Color ganador', 'Ganador por provincia', TT, 'tt_provincia'))
    put(P, tabla('pre_tabla', (786, 264, 478, 215, 800),
                 [('C', 'provincias', 'provincia', 'Provincia'), ('M', 'Medidas', 'Ganador', 'Ganó'), ('M', 'Medidas', '% ganador', '%'),
                  ('M', 'Medidas', 'Segundo', 'Segundo'), ('M', 'Medidas', '% segundo', '%'), ('M', 'Medidas', 'Margen (pp)', 'Margen')],
                 'Resultado por provincia', anchos=[105, 115, 45, 110, 45, 50], orden=('C', 'provincias', 'provincia', 'Ascending')))
    put(P, grafico('pre_hist', (786, 489, 478, 218, 900), 'lineChart', ('elecciones', 'anio'),
                   [s for s in SERIES_HIST if s[1] != 'Izquierda'],
                   'Primera vuelta 1983-2023: % nacional por espacio',
                   filtros=[filtro_cfg('f_pre_hist', 'elecciones', 'categoria', ['Presidente 1ra vuelta'])], marcadores=True))

    # ---------------------------------------------------------------- Intermedias
    P = 'intermedias'
    pagina(P, 'Intermedias', filtros=[filtro_cfg('f_dip', 'elecciones', 'cargo', ['Diputados nacionales'])],
           interacciones=[('int_eleccion', 'int_hist'), ('int_mapa', 'int_hist'), ('int_mapa', 'int_barras', 'DataFilter')])
    encabezado(P, 'Elecciones intermedias y diputados nacionales', 'Legislativas 1985-2025 (y diputados de años presidenciales) · cada provincia elige su lista')
    put(P, segmentador('int_eleccion', (16, 110, 360, 58, 300), 'elecciones', 'etiqueta', 'Elección', ['2025 · Diputados (intermedia)']))
    put(P, tarjeta_texto('int_nota', (386, 110, 878, 58, 310), 'Nota de la elección', size=9, color=INK2))
    tarjetas(P, 176, [('Ganador', 'Espacio (país) o lista (provincia)', {'titulo_medida': 'Ámbito', 'size': 13}),
                      ('% ganador', 'Votos positivos', {'titulo': 'Porcentaje del más votado'}),
                      ('Segundo', 'Segundo', {'titulo': 'Segundo', 'size': 13}),
                      ('Distritos ganados', 'Distritos', {'titulo': 'Distritos ganados por el más votado'}),
                      ('Participación', 'Del padrón', {'titulo': 'Participación'})])
    put(P, barras('int_barras', (16, 264, 400, 443, 600), ('espacios', 'espacio_corto'), '% votos', 'Color espacio',
                  None, '% votos', titulo_medida='Etiqueta ámbito'))
    put(P, mapa_formas('int_mapa', (426, 264, 330, 443, 700), 'Color ganador', 'Espacio de la lista ganadora', TT, 'tt_provincia'))
    put(P, tabla('int_tabla', (766, 264, 498, 215, 800),
                 [('C', 'provincias', 'provincia', 'Provincia'), ('M', 'Medidas', 'Ganador', 'Lista ganadora'), ('M', 'Medidas', 'Ganador espacio', 'Espacio'),
                  ('M', 'Medidas', '% ganador', '%'), ('M', 'Medidas', 'Margen (pp)', 'Margen'), ('M', 'Medidas', 'Cambio de ganador', 'Vs. anterior')],
                 'Resultado por provincia', anchos=[100, 140, 75, 45, 50, 60], orden=('C', 'provincias', 'provincia', 'Ascending')))
    put(P, grafico('int_hist', (766, 489, 498, 218, 900), 'lineChart', ('elecciones', 'anio'), SERIES_HIST[:7],
                   'Intermedias 1985-2025: % nacional por espacio',
                   filtros=[filtro_cfg('f_int_hist', 'elecciones', 'categoria', ['Diputados (intermedia)'])], marcadores=True))

    # ---------------------------------------------------------------- Evolución
    P = 'evolucion'
    pagina(P, 'Evolución')
    encabezado(P, 'Quién ganó cada provincia, elección por elección', 'Color = espacio de la fórmula o lista más votada · elegí qué tipo de elecciones comparar')
    put(P, segmentador('evo_categoria', (16, 110, 600, 58, 300), 'elecciones', 'categoria', 'Tipo de elección',
                       ['Presidente 1ra vuelta', 'Diputados (intermedia)'], multiple=True, modo='Dropdown', orden_desc=False))
    put(P, matriz('evo_matriz', (16, 176, 960, 531, 400), ('provincias', 'nombre_corto'), ('elecciones', 'etiqueta_corta'),
                  'Ganador espacio (celda)', 'Color ganador (celda)', 'Espacio ganador por provincia y elección'))
    put(P, tabla('evo_cambios', (986, 110, 278, 330, 500),
                 [('C', 'provincias', 'nombre_corto', 'Provincia'), ('M', 'Medidas', 'Cambios de ganador', 'Cambios'),
                  ('M', 'Medidas', 'Elecciones ganadas por el peronismo', 'Ganó el PJ')],
                 'Cambios de espacio ganador', anchos=[120, 60, 70], orden=('M', 'Medidas', 'Cambios de ganador', 'Descending')))
    leyenda = [[('Cómo leerlo', 11, True, NAVY)],
               [('Cada celda es una provincia en una elección; el color es el espacio que ganó. "Cambios" cuenta las veces que '
                 'el ganador fue de un espacio distinto al de la elección anterior del mismo tipo.', 9, False, INK)]]
    for nom, col in COLOR_ESP.items():
        leyenda.append([('■ ', 11, True, col), (nom, 9, False, INK)])
    put(P, texto('evo_leyenda', (986, 450, 278, 257, 600), leyenda))

    # ---------------------------------------------------------------- Participación
    P = 'participacion'
    pagina(P, 'Participación', interacciones=[('par_eleccion', 'par_hist'), ('par_eleccion', 'par_blancos'),
                                              ('par_mapa', 'par_hist'), ('par_mapa', 'par_blancos')])
    encabezado(P, 'Participación electoral', 'Votantes sobre electores habilitados (sin residentes en el exterior) · votos en blanco y nulos')
    put(P, grafico('par_hist', (16, 110, 620, 290, 300), 'lineChart', ('elecciones', 'anio'),
                   [('Participación presidencial (1ra vuelta)', 'Presidenciales (1ra vuelta)', INDIGO),
                    ('Participación intermedias', 'Intermedias', CELESTE)],
                   'Participación 1983-2025 (% del padrón)', marcadores=True))
    put(P, grafico('par_blancos', (16, 410, 620, 297, 400), 'clusteredColumnChart', ('elecciones', 'etiqueta_corta'),
                   [('Blancos y nulos (%)', 'Blancos y nulos', LAVANDA)], 'Votos en blanco y nulos (% de los votantes)', leyenda=False,
                   filtros=[filtro_cfg('f_par_bl', 'elecciones', 'categoria', ['Presidente 1ra vuelta', 'Diputados (intermedia)'])]))
    put(P, segmentador('par_eleccion', (646, 110, 380, 58, 500), 'elecciones', 'etiqueta', 'Elección', ['2025 · Diputados (intermedia)']))
    put(P, tarjeta('par_k0', (1036, 110, 228, 58, 510), 'Participación', 'Total del país o provincia', titulo='Participación', size=16))
    put(P, mapa_formas('par_mapa', (646, 176, 300, 531, 600), 'Color participación', 'Más oscuro = más participación',
                       [('Participación', 'Participación'), ('Blancos y nulos (%)', 'Blancos y nulos')]))
    put(P, tabla('par_tabla', (956, 176, 308, 531, 700),
                 [('C', 'provincias', 'provincia', 'Provincia'), ('M', 'Medidas', 'Participación', 'Participación'),
                  ('M', 'Medidas', 'Blancos y nulos (%)', 'Blancos y nulos')],
                 'Por provincia', anchos=[130, 80, 80], orden=('M', 'Medidas', 'Participación', 'Descending')))

    # ---------------------------------------------------------------- Datos
    P = 'datos'
    pagina(P, 'Datos')
    encabezado(P, 'Datos, fuentes y método', 'De dónde salen los números, cómo se agrupan los partidos y cómo se actualiza el tablero')
    T_ = lambda t, s=9, b=False, c=INK: (t, s, b, c)
    put(P, texto('dat_fuentes', (16, 110, 620, 597, 300), [
        [T_('Fuentes', 12, True, NAVY)],
        [T_('• Presidenciales 1983-2019 (primera vuelta) y balotaje 2015: ', 9, True), T_('escrutinio definitivo del Atlas Electoral de Andy Tow, vía el repositorio PolAr (Tucumán 2015: DINE).')],
        [T_('• Presidenciales 2023: ', 9, True), T_('escrutinio definitivo de la Cámara Nacional Electoral por provincia.')],
        [T_('• Diputados 2011-2025 y PASO 2011-2023: ', 9, True), T_('escrutinio provisorio de la Dirección Nacional Electoral (DINE). Los totales quedan 1 a 4% debajo del definitivo.')],
        [T_('• Diputados 1983-2009: ', 9, True), T_('base de Ernesto Calvo (1983-1999) y PolAr/Andy Tow (2003-2009), compiladas por departamento en el repositorio 257arg. No hay datos de las legislativas de 2001.')],
        [T_('Espacios políticos', 12, True, NAVY)],
        [T_('Cada lista o fórmula se asigna a uno de diez espacios comparables en el tiempo (tabla de la derecha) con las reglas de data/elecciones/reglas_espacios.csv. '
            'En diputados, "ganador" es la lista más votada de cada provincia; a nivel país se suman las listas de cada espacio.')],
        [T_('Qué mirar con cuidado', 12, True, NAVY)],
        [T_('• 1983 y 1989 fueron por colegio electoral: se muestran los votos populares. • En 1989 y 1995 algunas listas provinciales aliadas no se atribuyen al ganador (ver controles). '
            '• 1997-1999 vienen de una base sin corregir, con códigos de lista. • 2003: un 20% de los votos de diputados son listas provinciales sin espacio asignado.')],
        [T_('Cómo se actualiza', 12, True, NAVY)],
        [T_('GitHub Actions corre el notebook "Tablero Elecciones AR - ETL v1" los lunes (o a mano: Actions → Actualizar tableros → elecciones) y escribe la planilla '
            '"Elecciones AR - Datos limpios"; Power BI web la vuelve a leer en su actualización programada. Cuando haya una elección nueva, se suma a la base con '
            'scripts/etl/elecciones_base.py.')],
    ]))
    put(P, tabla('dat_control', (646, 110, 618, 300, 400),
                 [('C', 'control', 'id_eleccion', 'Elección'), ('C', 'control', 'control', 'Control'), ('C', 'control', 'oficial_pct', 'Oficial %'),
                  ('C', 'control', 'tablero_pct', 'Tablero %'), ('C', 'control', 'diferencia_pp', 'Dif. pp'), ('C', 'control', 'estado', 'Estado')],
                 'Controles contra los resultados oficiales', anchos=[95, 190, 65, 65, 55, 110]))
    put(P, tabla('dat_espacios', (646, 420, 618, 287, 500),
                 [('C', 'espacios', 'espacio', 'Espacio'), ('C', 'espacios', 'descripcion', 'Qué incluye')],
                 'Los diez espacios políticos', anchos=[150, 430], orden=('C', 'espacios', 'espacio', 'Ascending')))

    # ---------------------------------------------------------------- Tooltip del mapa
    P = 'tt_provincia'
    pagina(P, 'Tooltip provincia', tooltip=True)
    v = tarjeta_texto('tt_titulo', (0, 0, 320, 58, 100), 'Tooltip título', size=9, bold=True, color=NAVY, borde=False)
    v['visual']['visualContainerObjects'] = contenedor(borde=False, sombra=False, pad=(4, 2, 8, 8))
    put(P, v)
    v = barras('tt_barras', (0, 58, 320, 182, 200), ('resultados', 'opcion'), '% votos (top 6)', 'Color opción', None, '% votos')
    v['visual']['visualContainerObjects'] = contenedor(borde=False, sombra=False, pad=(2, 4, 6, 8))
    put(P, v)

    wjson(os.path.join(PAGES, 'pages.json'), {'$schema': SCH + 'item/report/definition/pagesMetadata/1.0.0/schema.json',
                                               'pageOrder': ORDEN, 'activePageName': 'resumen'})


# ----------------------------------------------------------------------------------------------- archivos del proyecto
def construir():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    logico = lambda n: str(uuid.uuid5(mdl.NS, 'elecciones:logical:' + n))
    wjson(os.path.join(OUT, NOMBRE + '.pbip'), {'$schema': SCH + 'pbip/pbipProperties/1.0.0/schema.json', 'version': '1.0',
                                                 'artifacts': [{'report': {'path': REP}}], 'settings': {'enableAutoRecovery': True}})
    wtext(os.path.join(OUT, '.gitignore'), '**/.pbi/localSettings.json\n**/.pbi/cache.abf\n')
    # ---- informe
    wjson(os.path.join(OUT, REP, '.platform'), {'$schema': SCH + 'gitIntegration/platformProperties/2.0.0/schema.json',
                                               'metadata': {'type': 'Report', 'displayName': NOMBRE},
                                               'config': {'version': '2.0', 'logicalId': logico('report')}})
    wjson(os.path.join(OUT, REP, 'definition.pbir'), {'$schema': SCH + 'item/report/definitionProperties/2.0.0/schema.json', 'version': '4.0',
                                                     'datasetReference': {'byPath': {'path': '../' + MOD}}})
    wjson(os.path.join(OUT, REP, 'definition', 'version.json'), {'$schema': SCH + 'item/report/definition/versionMetadata/1.0.0/schema.json',
                                                                 'version': '2.0.0'})
    ver = {'visual': '2.7.0', 'report': '3.2.0', 'page': '2.1.0'}
    wjson(os.path.join(OUT, REP, 'definition', 'report.json'), {
        '$schema': SCHEMA_REPORT,
        'themeCollection': {'baseTheme': {'name': 'CY24SU10', 'reportVersionAtImport': ver, 'type': 'SharedResources'},
                            'customTheme': {'name': 'TemaArgentina.json', 'reportVersionAtImport': ver, 'type': 'RegisteredResources'}},
        'objects': {'outspacePane': [{'properties': {'expanded': L('false')}}]},
        'resourcePackages': [{'name': 'SharedResources', 'type': 'SharedResources',
                              'items': [{'name': 'CY24SU10', 'path': 'BaseThemes/CY24SU10.json', 'type': 'BaseTheme'}]},
                             {'name': 'RegisteredResources', 'type': 'RegisteredResources',
                              'items': [{'name': 'TemaArgentina.json', 'path': 'TemaArgentina.json', 'type': 'CustomTheme'}]}],
        'settings': {'useStylableVisualContainerHeader': True, 'exportDataMode': 'AllowSummarized', 'defaultDrillFilterOtherVisuals': True,
                     'allowChangeFilterTypes': True, 'useEnhancedTooltips': True, 'useDefaultAggregateDisplayName': True}})
    dir_base = os.path.join(OUT, REP, 'StaticResources', 'SharedResources', 'BaseThemes')
    os.makedirs(dir_base, exist_ok=True)
    shutil.copy(BASE_THEME, os.path.join(dir_base, 'CY24SU10.json'))
    tema = {'name': 'TemaArgentina', 'dataColors': [INDIGO, CELESTE, VERDE, VIOLETA, SOL, ARANDANO, LAVANDA, '#6B6F8A', NAVY, '#EF6C00'],
            'foreground': INK, 'foregroundNeutralSecondary': INK2, 'background': '#FFFFFF', 'backgroundLight': PAGINA,
            'tableAccent': NAVY, 'good': VERDE, 'neutral': '#E7BA61', 'bad': ROJO, 'maximum': '#2F2C7A', 'center': '#9488DD', 'minimum': '#ECEAFA',
            'textClasses': {'callout': {'fontFace': 'Arial', 'fontSize': 22, 'color': NAVY}, 'title': {'fontFace': 'Arial', 'fontSize': 11, 'color': NAVY},
                            'header': {'fontFace': 'Arial', 'fontSize': 12, 'color': NAVY}, 'label': {'fontFace': 'Arial', 'fontSize': 9, 'color': '#3C4060'},
                            'largeTitle': {'fontFace': 'Arial', 'fontSize': 18, 'color': NAVY}, 'smallLabel': {'fontFace': 'Arial', 'fontSize': 8, 'color': INK2}},
            'visualStyles': {'page': {'*': {'background': [{'color': {'solid': {'color': PAGINA}}, 'transparency': 0}]}},
                             '*': {'*': {'title': [{'fontFamily': 'Arial'}], 'tooltip': [{'fontFamily': 'Arial'}]}}}}
    wjson(os.path.join(OUT, REP, 'StaticResources', 'RegisteredResources', 'TemaArgentina.json'), tema)
    construir_reporte()
    # ---- modelo semántico
    wjson(os.path.join(OUT, MOD, '.platform'), {'$schema': SCH + 'gitIntegration/platformProperties/2.0.0/schema.json',
                                               'metadata': {'type': 'SemanticModel', 'displayName': NOMBRE},
                                               'config': {'version': '2.0', 'logicalId': logico('model')}})
    wjson(os.path.join(OUT, MOD, 'definition.pbism'), {'$schema': SCH + 'item/semanticModel/definitionProperties/1.0.0/schema.json',
                                                      'version': '4.2', 'settings': {}})
    DEF = os.path.join(OUT, MOD, 'definition')
    wtext(os.path.join(DEF, 'database.tmdl'), 'database\n\tcompatibilityLevel: 1567\n\n')
    wtext(os.path.join(DEF, 'model.tmdl'), mdl.modelo_tmdl())
    wtext(os.path.join(DEF, 'expressions.tmdl'), mdl.expresiones_tmdl())
    wtext(os.path.join(DEF, 'relationships.tmdl'), mdl.relaciones_tmdl())
    for nombre, cols in mdl.TABLAS.items():
        wtext(os.path.join(DEF, 'tables', nombre + '.tmdl'), mdl.tabla_tmdl(nombre, cols))
    wtext(os.path.join(DEF, 'tables', 'Medidas.tmdl'), mdl.medidas_tmdl())
    print('Proyecto generado en', OUT, '·', len(mdl.MEDIDAS), 'medidas')


if __name__ == '__main__':
    construir()
