# -*- coding: utf-8 -*-
"""Modelo semántico (TMDL) del Tablero Elecciones AR: tablas, relaciones y medidas DAX."""
import textwrap, uuid

NS = uuid.UUID('6f1c0a52-7b1e-4c55-9d3a-2b8f1f0a9c11')   # mismo espacio de nombres que common.py de Macro


def tag(nombre):
    """lineageTag estable: el mismo nombre da siempre el mismo identificador."""
    return str(uuid.uuid5(NS, 'elecciones:' + nombre))


SHEET_ID = '1gD1noYKGiWRA_XywAkbpqzelKTGvAwEzuoikLlu1KE8'

# ------------------------------------------------------------------------------------------------
# Tablas que vienen de la planilla: (nombre, [(columna, tipo_tmdl, tipo_m, formato, extra)])
# ------------------------------------------------------------------------------------------------
T, I, D, F, B = 'string', 'int64', 'dateTime', 'double', 'boolean'
M_TIPO = {T: 'type text', I: 'Int64.Type', D: 'type date', F: 'type number', B: 'type logical'}

TABLAS = {
    'elecciones': [
        ('id_eleccion', T), ('anio', I), ('fecha', D), ('tipo', T), ('instancia', T), ('cargo', T), ('categoria', T),
        ('es_intermedia', B), ('etiqueta', T, {'sort': 'orden'}), ('etiqueta_corta', T, {'sort': 'orden'}), ('orden', I),
        ('anterior', T), ('provincias', I), ('electores', F), ('votantes', F), ('positivos', F), ('participacion', F),
        ('ganador', T), ('ganador_espacio', T), ('ganador_pct', F), ('segundo', T), ('segundo_espacio', T),
        ('segundo_pct', F), ('margen_pp', F), ('prov_ganadas', I), ('sin_clasificar_pct', F), ('recuento', T),
        ('fuente', T), ('nota', T)],
    'provincias': [
        ('id_prov', T), ('provincia', T, {'sort': 'orden', 'cat': 'StateOrProvince'}), ('nombre_corto', T, {'sort': 'orden'}),
        ('provincia_mapa', T, {'sort': 'orden'}), ('region', T), ('orden', I), ('electores_ultimo', F), ('peso_padron', F),
        ('svg_path', T, {'hidden': True}), ('label_x', F, {'hidden': True}), ('label_y', F, {'hidden': True})],
    'espacios': [
        ('id_espacio', T), ('espacio', T, {'sort': 'orden'}), ('espacio_corto', T, {'sort': 'orden'}), ('color', T),
        ('orden', I), ('descripcion', T), ('tono1', T), ('tono2', T), ('tono3', T), ('tono4', T), ('tono5', T)],
    'resultados': [
        ('id_eleccion', T), ('id_prov', T), ('opcion', T), ('id_espacio', T), ('votos', F), ('pct', F), ('posicion', I), ('listas', T)],
    'prov_eleccion': [
        ('id_eleccion', T), ('id_prov', T), ('electores', F), ('votantes', F), ('positivos', F), ('blancos_nulos', F),
        ('blancos_nulos_pct', F), ('participacion', F), ('ganador', T), ('ganador_espacio', T), ('ganador_pct', F),
        ('ganador_votos', F), ('segundo', T), ('segundo_espacio', T), ('segundo_pct', F), ('margen_pp', F), ('nep', F),
        ('peso_padron', F), ('ganador_espacio_anterior', T), ('cambio_ganador', T)],
    'nacional': [
        ('id_eleccion', T), ('nivel', T), ('opcion', T), ('id_espacio', T), ('votos', F), ('pct', F), ('posicion', I),
        ('pct_anterior', F), ('var_pp', F)],
    'kpis': [
        ('clave', T), ('id_eleccion', T), ('etiqueta', T), ('ganador', T), ('ganador_pct', F), ('margen_pp', F),
        ('participacion', F), ('prov_ganadas', I)],
    'resumen': [('tema', T), ('texto', T)],
    'control': [('id_eleccion', T), ('control', T), ('oficial_pct', F), ('tablero_pct', F), ('diferencia_pp', F), ('estado', T)],
    'info': [('ultima_actualizacion', T), ('cobertura', T), ('fuentes', T), ('mapa', T), ('errores', T)],
    # --- Gobernadores ---
    'gob_elecciones': [
        ('id_gob', T), ('anio', I), ('id_prov', T), ('gobernador', T), ('id_espacio', T), ('mandato', T), ('hasta', I),
        ('vuelta_final', T), ('hubo_balotaje', B), ('lista_ganadora', T), ('ganador_pct', F), ('segundo', T),
        ('segundo_espacio', T), ('segundo_pct', F), ('margen_pp', F), ('participacion', F), ('electores', F), ('cambio', T),
        ('reelecto', B), ('gobernador_anterior', T), ('espacio_anterior', T), ('nota', T), ('fuente', T),
        ('foto_url', T, {'cat': 'ImageUrl'}), ('etiqueta', T), ('iniciales', T)],
    'gob_resultados': [
        ('id_gob', T), ('anio', I), ('id_prov', T), ('vuelta', T), ('vuelta_txt', T), ('etiqueta', T), ('lista', T),
        ('candidato', T), ('id_espacio', T), ('votos', F), ('pct', F), ('posicion', I), ('fuente', T)],
    'gob_mapa': [
        ('anio_corte', I), ('id_prov', T), ('id_gob', T), ('gobernador', T), ('id_espacio', T), ('electo_en', I),
        ('mandato', T), ('etiqueta_anio', T), ('iniciales', T), ('foto_url', T, {'cat': 'ImageUrl'})],
    # --- Congreso ---
    'camara_anio': [('id_camara_anio', T), ('camara', T), ('anio', I), ('etiqueta', T, {'sort': 'orden'}), ('orden', I),
                    ('tiene_composicion', B)],
    'bancas': [
        ('camara', T), ('id_eleccion', T), ('anio', I), ('id_prov', T), ('opcion', T), ('id_espacio', T), ('votos', F),
        ('pct', F), ('posicion', I), ('bancas', I), ('id_camara_anio', T), ('vigente', B)],
    'composicion': [('camara', T), ('anio', I), ('id_espacio', T), ('bancas', I), ('total_bancas', I), ('pct', F),
                    ('mayoria', I), ('id_camara_anio', T)],
    'hemiciclo': [('camara', T), ('asiento', I), ('x', I), ('y', I), ('r', I)],
    # --- Presidentes ---
    'presidentes': [
        ('orden', I), ('anio', I), ('id_eleccion', T), ('presidente', T), ('formula', T), ('id_espacio', T),
        ('pct', F), ('instancia', T), ('desde', D), ('hasta', D), ('mandato', T, {'sort': 'orden'}), ('nota', T),
        ('foto_url', T, {'cat': 'ImageUrl'}), ('iniciales', T)],
}
CON_ID_PROV = {'provincias', 'resultados', 'prov_eleccion', 'gob_elecciones', 'gob_resultados', 'gob_mapa', 'bancas'}

RELACIONES = [
    ('resultados', 'id_eleccion', 'elecciones', 'id_eleccion'),
    ('resultados', 'id_prov', 'provincias', 'id_prov'),
    ('resultados', 'id_espacio', 'espacios', 'id_espacio'),
    ('prov_eleccion', 'id_eleccion', 'elecciones', 'id_eleccion'),
    ('prov_eleccion', 'id_prov', 'provincias', 'id_prov'),
    ('nacional', 'id_eleccion', 'elecciones', 'id_eleccion'),
    ('nacional', 'id_espacio', 'espacios', 'id_espacio'),
    ('gob_elecciones', 'id_prov', 'provincias', 'id_prov'),
    ('gob_elecciones', 'id_espacio', 'espacios', 'id_espacio'),
    ('gob_resultados', 'id_gob', 'gob_elecciones', 'id_gob'),     # sin relación directa a provincias/espacios: evita caminos ambiguos
    ('gob_mapa', 'id_prov', 'provincias', 'id_prov'),
    ('gob_mapa', 'id_espacio', 'espacios', 'id_espacio'),
    ('bancas', 'id_prov', 'provincias', 'id_prov'),
    ('bancas', 'id_espacio', 'espacios', 'id_espacio'),
    ('bancas', 'id_camara_anio', 'camara_anio', 'id_camara_anio'),
    ('composicion', 'id_espacio', 'espacios', 'id_espacio'),
    ('composicion', 'id_camara_anio', 'camara_anio', 'id_camara_anio'),
    ('presidentes', 'id_espacio', 'espacios', 'id_espacio'),
]


def tabla_tmdl(nombre, cols):
    out = ['table %s' % nombre, '\tlineageTag: %s' % tag('tabla:' + nombre), '']
    for c in cols:
        col, tipo = c[0], c[1]
        ex = c[2] if len(c) > 2 else {}
        out.append('\tcolumn %s' % col)
        out.append('\t\tdataType: %s' % tipo)
        if ex.get('hidden'):
            out.append('\t\tisHidden')
        if tipo == F:
            out.append('\t\tformatString: #,0.00')
        elif tipo == I:
            out.append('\t\tformatString: 0')
        elif tipo == D:
            out.append('\t\tformatString: dd/mm/yyyy')
        out.append('\t\tlineageTag: %s' % tag('col:%s.%s' % (nombre, col)))
        if ex.get('cat'):
            out.append('\t\tdataCategory: %s' % ex['cat'])
        out.append('\t\tsummarizeBy: none')
        out.append('\t\tsourceColumn: %s' % col)
        if ex.get('sort'):
            out.append('\t\tsortByColumn: %s' % ex['sort'])
        out.append('')
        if tipo == D:
            out += ['\t\tannotation UnderlyingDateTimeDataType = Date', '']
    nombres = ', '.join('"%s"' % c[0] for c in cols)
    tipos = ', '.join('{"%s", %s}' % (c[0], M_TIPO[c[1]]) for c in cols if c[0] != 'id_prov')
    m = ['let',
         '    Libro = Excel.Workbook(Web.Contents(UrlPlanilla), true, true),',
         '    Hoja = Libro{[Item="%s",Kind="Sheet"]}[Data],' % nombre,
         '    Columnas = Table.SelectColumns(Hoja, {%s}, MissingField.UseNull),' % nombres,
         '    SinBlancos = Table.ReplaceValue(Columnas, "", null, Replacer.ReplaceValue, {%s}),' % nombres,
         '    Vacios = Table.SelectRows(SinBlancos, each Record.Field(_, "%s") <> null),' % cols[0][0]]
    if nombre in CON_ID_PROV:
        m.append('    Codigo = Table.TransformColumns(Vacios, {{"id_prov", each if _ = null then null else Text.PadStart(Text.From(_), 2, "0"), type text}}),')
        prev = 'Codigo'
    else:
        prev = 'Vacios'
    m += ['    Tipos = Table.TransformColumnTypes(%s, {%s}, "en-US")' % (prev, tipos), 'in', '    Tipos']
    out.append('\tpartition %s = m' % nombre)
    out.append('\t\tmode: import')
    out.append('\t\tsource =')
    out += ['\t\t\t\t' + l for l in m]
    out += ['', '\tannotation PBI_ResultType = Table', '']
    return '\n'.join(out)


# ------------------------------------------------------------------------------------------------
# Medidas DAX: (nombre, expresión, formato, carpeta, extra)
# ------------------------------------------------------------------------------------------------
PCT = '0.0%;-0.0%;0.0%'
PP = '0.0 "pp";-0.0 "pp";0.0 "pp"'
N0 = '#,0'
GRIS_VACIO = '"#E4E2EE"'

MEDIDAS = []


def med(nombre, expr, fmt=None, carpeta=None, **ex):
    MEDIDAS.append(dict(name=nombre, expr=textwrap.dedent(expr).strip('\n'), fmt=fmt, folder=carpeta, **ex))


# --- Elección elegida ---
med('Orden elección', 'MAX ( elecciones[orden] )', '0', 'Base', hidden=True)
med('Id elección', '''
    VAR o = [Orden elección]
    RETURN CALCULATE ( MAX ( elecciones[id_eleccion] ), REMOVEFILTERS ( elecciones ), elecciones[orden] = o )''', None, 'Base')
med('Etiqueta elección', '''
    VAR e = [Id elección]
    RETURN CALCULATE ( MAX ( elecciones[etiqueta] ), REMOVEFILTERS ( elecciones ), elecciones[id_eleccion] = e )''', None, 'Base')
med('Hay provincia', 'HASONEVALUE ( provincias[id_prov] )', None, 'Base', hidden=True)
med('Ámbito', 'IF ( [Hay provincia], SELECTEDVALUE ( provincias[provincia] ), "Total del país" )', None, 'Base')
med('Etiqueta ámbito', '[Ámbito] & " · " & [Etiqueta elección]', None, 'Etiquetas')

# --- Votos y porcentajes ---
med('Votos', 'SUM ( resultados[votos] )', N0, 'Votos')
med('Votos positivos', '''
    CALCULATE (
        SUM ( resultados[votos] ),
        REMOVEFILTERS ( espacios ),
        REMOVEFILTERS ( resultados[opcion] ),
        REMOVEFILTERS ( resultados[id_espacio] ),
        REMOVEFILTERS ( resultados[posicion] )
    )''', N0, 'Votos')
med('% votos', 'DIVIDE ( [Votos], [Votos positivos] )', PCT, 'Votos')
med('% votos (top 8)', '''
    VAR r = RANKX ( ALLSELECTED ( resultados[opcion] ), [% votos],, DESC, Dense )
    RETURN IF ( r <= 8, [% votos] )''', PCT, 'Votos')
med('% votos (top 6)', '''
    VAR r = RANKX ( ALLSELECTED ( resultados[opcion] ), [% votos],, DESC, Dense )
    RETURN IF ( r <= 6, [% votos] )''', PCT, 'Votos')
med('Color opción', '''
    VAR e = CALCULATE ( MAX ( resultados[id_espacio] ) )
    RETURN COALESCE ( LOOKUPVALUE ( espacios[color], espacios[id_espacio], e ), "#A9ABBF" )''', None, 'Colores')
med('Color espacio', 'COALESCE ( SELECTEDVALUE ( espacios[color] ), "#A9ABBF" )', None, 'Colores')
med('% espacio (nacional)', 'DIVIDE ( CALCULATE ( SUM ( nacional[pct] ), nacional[nivel] = "espacio" ), 100 )', PCT, 'Votos')
med('Var. espacio vs anterior (pp)', 'CALCULATE ( SUM ( nacional[var_pp] ), nacional[nivel] = "espacio" )', PP, 'Votos')

# --- Participación ---
med('Electores', 'SUM ( prov_eleccion[electores] )', N0, 'Participación')
med('Votantes', 'SUM ( prov_eleccion[votantes] )', N0, 'Participación')
med('Participación', '''
    VAR completas = COUNTROWS ( FILTER ( prov_eleccion, NOT ISBLANK ( prov_eleccion[participacion] ) ) )
    VAR filas = COUNTROWS ( prov_eleccion )
    RETURN
        IF (
            filas > 0 && completas = filas,
            DIVIDE ( SUM ( prov_eleccion[votantes] ), SUM ( prov_eleccion[electores] ) )
        )''', PCT, 'Participación')
med('Blancos y nulos (%)', 'DIVIDE ( SUM ( prov_eleccion[blancos_nulos] ), [Votantes] )', PCT, 'Participación')
for e_, nombre_ in (('Presidente 1ra vuelta', 'Participación presidencial (1ra vuelta)'),
                    ('Diputados (intermedia)', 'Participación intermedias')):
    med(nombre_, 'CALCULATE ( [Participación], elecciones[categoria] = "%s" )' % e_, PCT, 'Participación')
med('Etiqueta participación', '"Participación · " & [Etiqueta ámbito]', None, 'Etiquetas')

# --- Ganador (provincia elegida o país) ---
def por_ambito(col_prov, col_pais):
    return ('VAR e = [Id elección]\nRETURN IF ( [Hay provincia], SELECTEDVALUE ( prov_eleccion[%s] ), '
            'CALCULATE ( SELECTEDVALUE ( elecciones[%s] ), REMOVEFILTERS ( elecciones ), elecciones[id_eleccion] = e ) )' % (col_prov, col_pais))

med('Ganador', por_ambito('ganador', 'ganador'), None, 'Ganador')
med('Ganador espacio (id)', por_ambito('ganador_espacio', 'ganador_espacio'), None, 'Ganador', hidden=True)
med('Ganador espacio', 'LOOKUPVALUE ( espacios[espacio_corto], espacios[id_espacio], [Ganador espacio (id)] )', None, 'Ganador')
med('% ganador (pp)', por_ambito('ganador_pct', 'ganador_pct'), '0.0', 'Ganador', hidden=True)
med('% ganador', 'DIVIDE ( [% ganador (pp)], 100 )', PCT, 'Ganador')
med('Segundo', por_ambito('segundo', 'segundo'), None, 'Ganador')
med('% segundo (pp)', por_ambito('segundo_pct', 'segundo_pct'), '0.0', 'Ganador', hidden=True)
med('% segundo', 'DIVIDE ( [% segundo (pp)], 100 )', PCT, 'Ganador')
med('Margen (pp)', por_ambito('margen_pp', 'margen_pp'), PP, 'Ganador')
med('Ganador y porcentaje', '[Ganador] & " · " & FORMAT ( [% ganador], "0.0%" )', None, 'Ganador')
med('Color ganador', 'COALESCE ( LOOKUPVALUE ( espacios[color], espacios[id_espacio], [Ganador espacio (id)] ), %s )' % GRIS_VACIO, None, 'Colores')
med('Distritos ganados', '''
    VAR e = [Id elección]
    VAR n = CALCULATE ( SELECTEDVALUE ( elecciones[prov_ganadas] ), REMOVEFILTERS ( elecciones ), elecciones[id_eleccion] = e )
    RETURN IF ( NOT ISBLANK ( n ), n & " de 24" )''', None, 'Ganador')
med('Cambio de ganador', 'SELECTEDVALUE ( prov_eleccion[cambio_ganador] )', None, 'Ganador')
med('Partidos efectivos (NEP)', 'AVERAGE ( prov_eleccion[nep] )', '0.0', 'Ganador')
med('Cambios de ganador', 'COUNTROWS ( FILTER ( prov_eleccion, prov_eleccion[cambio_ganador] = "Cambia" ) )', '0', 'Ganador')
med('Elecciones ganadas por el peronismo', 'COUNTROWS ( FILTER ( prov_eleccion, prov_eleccion[ganador_espacio] = "PJ" ) )', '0', 'Ganador')
med('Ganador espacio (celda)', 'LOOKUPVALUE ( espacios[espacio_corto], espacios[id_espacio], SELECTEDVALUE ( prov_eleccion[ganador_espacio] ) )', None, 'Ganador')
med('Color ganador (celda)', 'COALESCE ( LOOKUPVALUE ( espacios[color], espacios[id_espacio], SELECTEDVALUE ( prov_eleccion[ganador_espacio] ) ), "#FFFFFF" )', None, 'Colores')

# --- Mapas por intensidad (5 tonos) ---
med('Color intensidad del espacio', '''
    VAR p = [% votos]
    VAR t =
        SWITCH (
            TRUE (),
            ISBLANK ( p ), BLANK (),
            p < 0.10, SELECTEDVALUE ( espacios[tono1] ),
            p < 0.20, SELECTEDVALUE ( espacios[tono2] ),
            p < 0.30, SELECTEDVALUE ( espacios[tono3] ),
            p < 0.40, SELECTEDVALUE ( espacios[tono4] ),
            SELECTEDVALUE ( espacios[tono5] )
        )
    RETURN COALESCE ( t, "#F4F3FA" )''', None, 'Colores')
med('Color participación', '''
    VAR p = DIVIDE ( MAX ( prov_eleccion[participacion] ), 100 )
    RETURN
        SWITCH (
            TRUE (),
            ISBLANK ( p ), "#E4E2EE",
            p < 0.65, "#ECEAFA",
            p < 0.70, "#C5BFF0",
            p < 0.75, "#9488DD",
            p < 0.80, "#5F55BE",
            "#2F2C7A"
        )''', None, 'Colores')
med('Espacio elegido', 'COALESCE ( SELECTEDVALUE ( espacios[espacio] ), "Elegí un espacio" )', None, 'Etiquetas')
med('Etiqueta intensidad', '"Votos de " & [Espacio elegido] & " por provincia · " & [Etiqueta elección]', None, 'Etiquetas')

# --- Series históricas por espacio (para gráficos de evolución) ---
ESPACIOS_SERIE = [('PJ', 'Peronismo'), ('PF', 'Terceras vías'), ('UCR', 'UCR y aliados'), ('PRO', 'PRO-JxC'),
                  ('LLA', 'LLA'), ('CD', 'Centroderecha'), ('CI', 'Centroizquierda'), ('IZQ', 'Izquierda'),
                  ('PROV', 'Provinciales')]
for cod, nom in ESPACIOS_SERIE:   # país, o la provincia elegida (segmentador o clic en el mapa)
    med('%% %s' % nom, 'IF ( [Hay provincia], CALCULATE ( [%% votos], espacios[id_espacio] = "%s" ), '
        'DIVIDE ( CALCULATE ( SUM ( nacional[pct] ), nacional[nivel] = "espacio", nacional[id_espacio] = "%s" ), 100 ) )' % (cod, cod),
        PCT, 'Series por espacio')

# --- KPIs de la portada (hoja kpis) ---
def kpi(campo, clave):
    return 'LOOKUPVALUE ( kpis[%s], kpis[clave], "%s" )' % (campo, clave)

med('KPI balotaje ganador', kpi('ganador', 'ult_presidencial'), None, 'KPIs')
med('KPI balotaje %', 'DIVIDE ( %s, 100 )' % kpi('ganador_pct', 'ult_presidencial'), PCT, 'KPIs')
med('KPI balotaje margen', kpi('margen_pp', 'ult_presidencial'), PP, 'KPIs')
med('KPI balotaje título', '"Ganador · " & %s' % kpi('etiqueta', 'ult_presidencial'), None, 'KPIs')
med('KPI intermedia ganador', kpi('ganador', 'ult_intermedia'), None, 'KPIs')
med('KPI intermedia %', 'DIVIDE ( %s, 100 )' % kpi('ganador_pct', 'ult_intermedia'), PCT, 'KPIs')
med('KPI intermedia título', '"Más votado · " & %s' % kpi('etiqueta', 'ult_intermedia'), None, 'KPIs')
med('KPI intermedia distritos', kpi('prov_ganadas', 'ult_intermedia') + ' & " de 24"', None, 'KPIs')
med('KPI intermedia participación', 'DIVIDE ( %s, 100 )' % kpi('participacion', 'ult_intermedia'), PCT, 'KPIs')
med('KPI intermedia part. título', '"Participación · " & %s' % kpi('etiqueta', 'ult_intermedia'), None, 'KPIs')
med('Id última intermedia', kpi('id_eleccion', 'ult_intermedia'), None, 'KPIs', hidden=True)
med('Id último balotaje', kpi('id_eleccion', 'ult_presidencial'), None, 'KPIs', hidden=True)
med('% espacio última intermedia', '''
    VAR e = [Id última intermedia]
    RETURN CALCULATE ( [% espacio (nacional)], REMOVEFILTERS ( elecciones ), elecciones[id_eleccion] = e )''', PCT, 'KPIs')
med('Ganador última intermedia (provincia)', '''
    VAR e = [Id última intermedia]
    RETURN CALCULATE ( SELECTEDVALUE ( prov_eleccion[ganador] ), REMOVEFILTERS ( elecciones ), prov_eleccion[id_eleccion] = e )''', None, 'KPIs')
med('% ganador última intermedia (provincia)', '''
    VAR e = [Id última intermedia]
    RETURN DIVIDE ( CALCULATE ( SELECTEDVALUE ( prov_eleccion[ganador_pct] ), REMOVEFILTERS ( elecciones ), prov_eleccion[id_eleccion] = e ), 100 )''', PCT, 'KPIs')
med('Margen última intermedia (provincia)', '''
    VAR e = [Id última intermedia]
    RETURN CALCULATE ( SELECTEDVALUE ( prov_eleccion[margen_pp] ), REMOVEFILTERS ( elecciones ), prov_eleccion[id_eleccion] = e )''', PP, 'KPIs')
med('Espacio ganador última intermedia (provincia)', '''
    VAR e = [Id última intermedia]
    VAR g = CALCULATE ( SELECTEDVALUE ( prov_eleccion[ganador_espacio] ), REMOVEFILTERS ( elecciones ), prov_eleccion[id_eleccion] = e )
    RETURN LOOKUPVALUE ( espacios[espacio_corto], espacios[id_espacio], g )''', None, 'KPIs')
med('Lectura resumen', 'CONCATENATEX ( resumen, resumen[tema] & ": " & resumen[texto], UNICHAR ( 10 ) & UNICHAR ( 10 ) )', None, 'Textos')
med('Actualizado', '"Actualizado: " & MAX ( info[ultima_actualizacion] )', None, 'Textos')
med('Nota de la elección', '''
    VAR e = [Id elección]
    VAR n = CALCULATE ( MAX ( elecciones[nota] ), REMOVEFILTERS ( elecciones ), elecciones[id_eleccion] = e )
    VAR f = CALCULATE ( MAX ( elecciones[fuente] ), REMOVEFILTERS ( elecciones ), elecciones[id_eleccion] = e )
    VAR r = CALCULATE ( MAX ( elecciones[recuento] ), REMOVEFILTERS ( elecciones ), elecciones[id_eleccion] = e )
    RETURN "Fuente: " & f & " · escrutinio " & LOWER ( r ) & IF ( n <> "", ". " & n, "." )''', None, 'Textos')
med('Lectura de la elección', '''
    VAR g = [Ganador]
    VAR s = [Segundo]
    VAR pg = [% ganador]
    VAR m = [Margen (pp)]
    VAR pa = [Participación]
    RETURN
        IF (
            NOT ISBLANK ( g ),
            [Ámbito] & ": ganó " & g & " con " & FORMAT ( pg, "0.0%" ) & ", "
                & FORMAT ( m, "0.0" ) & " puntos sobre " & s
                & IF ( NOT ISBLANK ( pa ), ". Votó el " & FORMAT ( pa, "0.0%" ) & " del padrón.", "." )
        )''', None, 'Textos')
med('Tooltip título', '[Ámbito] & " · " & [Etiqueta elección] & UNICHAR ( 10 ) & "Ganó " & [Ganador] & " (" & FORMAT ( [% ganador], "0.0%" ) & ") · margen " & FORMAT ( [Margen (pp)], "0.0" ) & " pp"', None, 'Textos')

# --- Mapa SVG (respaldo que se ve siempre; colorea la última intermedia o la elección elegida) ---
med('SVG mapa ganadores', '''
    VAR e = [Id elección]
    VAR provs =
        ADDCOLUMNS (
            ALL ( provincias ),
            "@color",
                VAR p = provincias[id_prov]
                VAR g = CALCULATE ( MAX ( prov_eleccion[ganador_espacio] ), REMOVEFILTERS ( provincias ), REMOVEFILTERS ( elecciones ), prov_eleccion[id_prov] = p, prov_eleccion[id_eleccion] = e )
                RETURN COALESCE ( LOOKUPVALUE ( espacios[color], espacios[id_espacio], g ), "#E4E2EE" )
        )
    VAR ganadores =
        FILTER (
            ALL ( espacios ),
            VAR c = espacios[id_espacio]
            RETURN CALCULATE ( COUNTROWS ( prov_eleccion ), REMOVEFILTERS ( provincias ), REMOVEFILTERS ( elecciones ), prov_eleccion[id_eleccion] = e, prov_eleccion[ganador_espacio] = c ) > 0
        )
    VAR caminos = CONCATENATEX ( provs, "<path d='" & provincias[svg_path] & "' fill='" & [@color] & "' stroke='white' stroke-width='0.7'/>", "" )
    VAR leyenda =
        CONCATENATEX (
            ganadores,
            VAR y = 430 + 17 * ( RANKX ( ganadores, espacios[orden],, ASC ) - 1 )
            RETURN "<rect x='232' y='" & y & "' width='11' height='11' rx='2' fill='" & espacios[color] & "'/><text x='248' y='" & y + 9 & "' font-family='Arial' font-size='10' fill='#1B1F3B'>" & espacios[espacio_corto] & "</text>",
            "",
            espacios[orden], ASC
        )
    VAR svg = "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 360 750'>" & caminos
        & "<text x='338' y='392' font-family='Arial' font-size='9' text-anchor='middle' fill='#6B6F8A'>CABA</text>"
        & leyenda & "</svg>"
    RETURN "data:image/svg+xml;utf8," & SUBSTITUTE ( svg, "#", "%23" )''', None, 'Mapa', data_category='ImageUrl')
med('SVG mapa última intermedia', '''
    VAR e = [Id última intermedia]
    RETURN CALCULATE ( [SVG mapa ganadores], REMOVEFILTERS ( elecciones ), elecciones[id_eleccion] = e )''', None, 'Mapa', data_category='ImageUrl')


# Provincia, gobernadores, Congreso y presidentes
import elecciones_medidas_nuevas  # noqa: E402
elecciones_medidas_nuevas.registrar(med, PCT, PP, GRIS_VACIO)

def medida_tmdl(m):
    lines = [l.rstrip() for l in m['expr'].split('\n') if l.strip()]
    q = "'" + m['name'].replace("'", "''") + "'"
    out = []
    if len(lines) == 1:
        out.append('\tmeasure %s = %s' % (q, lines[0].strip()))
    else:
        body = textwrap.dedent('\n'.join(lines)).split('\n')
        out.append('\tmeasure %s =' % q)
        out += ['\t\t\t' + l.replace('\t', '    ') for l in body]
    if m.get('hidden'):
        out.append('\t\tisHidden')
    if m.get('fmt'):
        out.append('\t\tformatString: ' + m['fmt'])
    if m.get('folder'):
        out.append('\t\tdisplayFolder: ' + m['folder'])
    out.append('\t\tlineageTag: ' + tag('medida:' + m['name']))
    if m.get('data_category'):
        out.append('\t\tdataCategory: ' + m['data_category'])
    return '\n'.join(out) + '\n'


def medidas_tmdl():
    nombres = [m['name'] for m in MEDIDAS]
    assert len(nombres) == len(set(nombres)), 'medida duplicada'
    out = ['table Medidas', '\tlineageTag: %s' % tag('tabla:Medidas'), '']
    for m in MEDIDAS:
        out.append(medida_tmdl(m))
    out += ['\tcolumn Value', '\t\tdataType: string', '\t\tisHidden', '\t\tlineageTag: %s' % tag('col:Medidas.Value'),
            '\t\tsummarizeBy: none', '\t\tisNameInferred', '\t\tsourceColumn: [Value]', '',
            '\t\tannotation SummarizationSetBy = Automatic', '',
            '\tpartition Medidas = calculated', '\t\tmode: import', '\t\tsource = { "" }', '',
            '\tannotation PBI_Id = %s' % tag('pbiid:Medidas').replace('-', ''), '']
    return '\n'.join(out)


def modelo_tmdl():
    orden = ['UrlPlanilla'] + list(TABLAS)
    out = ['model Model', '\tculture: es-AR', '\tdefaultPowerBIDataSourceVersion: powerBI_V3', '\tdiscourageImplicitMeasures',
           '\tsourceQueryCulture: es-AR', '\tdataAccessOptions', '\t\tlegacyRedirects', '\t\treturnErrorValuesAsNull', '',
           'annotation __PBI_TimeIntelligenceEnabled = 0', '',
           'annotation PBI_QueryOrder = [%s]' % ','.join('"%s"' % n for n in orden), '',
           'annotation PBI_ProTooling = ["DevMode"]', '',
           'ref table Medidas']
    out += ['ref table %s' % n for n in TABLAS]
    return '\n'.join(out) + '\n'


def expresiones_tmdl():
    return ('expression UrlPlanilla = "https://docs.google.com/spreadsheets/d/%s/export?format=xlsx" '
            'meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]\n'
            '\tlineageTag: %s\n\n\tannotation PBI_ResultType = Text\n' % (SHEET_ID, tag('expr:UrlPlanilla')))


def relaciones_tmdl():
    out = []
    for f_t, f_c, t_t, t_c in RELACIONES:
        out += ['relationship %s' % tag('rel:%s.%s-%s.%s' % (f_t, f_c, t_t, t_c)),
                '\tfromColumn: %s.%s' % (f_t, f_c), '\ttoColumn: %s.%s' % (t_t, t_c), '']
    return '\n'.join(out)
