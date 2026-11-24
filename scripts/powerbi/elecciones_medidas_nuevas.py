# -*- coding: utf-8 -*-
"""Medidas DAX de las páginas Provincia, Gobernadores, Congreso y Presidentes (se registran en elecciones_modelo)."""


def registrar(med, PCT, PP, GRIS_VACIO):

    def avatar(tabla):
        """Foto (si la planilla tiene foto_url) o un círculo con las iniciales en el color del espacio."""
        return """
        VAR f = SELECTEDVALUE ( %(t)s[foto_url] )
        VAR ini = SELECTEDVALUE ( %(t)s[iniciales] )
        VAR c = COALESCE ( LOOKUPVALUE ( espacios[color], espacios[id_espacio], SELECTEDVALUE ( %(t)s[id_espacio] ) ), "#A9ABBF" )
        VAR svg = "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 60 60'><circle cx='30' cy='30' r='29' fill='" & c
            & "'/><text x='30' y='" & IF ( LEN ( ini ) > 2, 36, 37 ) & "' font-family='Arial' font-size='" & IF ( LEN ( ini ) > 2, 17, 21 )
            & "' font-weight='bold' fill='white' text-anchor='middle'>" & ini & "</text></svg>"
        RETURN
            IF ( NOT ISBLANK ( f ) && f <> "", f,
                IF ( NOT ISBLANK ( ini ) && ini <> "", "data:image/svg+xml;utf8," & SUBSTITUTE ( svg, "#", "%%23" ) ) )""" % {'t': tabla}

    # ------------------------------------------------------------------ Provincia
    med('Provincia elegida', 'IF ( [Hay provincia], SELECTEDVALUE ( provincias[provincia] ), "Total del país" )', None, 'Provincia')
    med('Título provincia', '''
        IF ( [Hay provincia],
            SELECTEDVALUE ( provincias[provincia] ) & " · quién gobierna, cómo vota y cuántas bancas tiene",
            "Total del país · elegí una provincia en el segmentador o hacé clic en el mapa" )''', None, 'Provincia')
    med('Año último gobernador', 'CALCULATE ( MAX ( gob_mapa[anio_corte] ), REMOVEFILTERS ( gob_mapa ) )', '0', 'Gobernadores', hidden=True)
    med('Gobernador actual', '''
        VAR a = [Año último gobernador]
        RETURN IF ( [Hay provincia],
            CALCULATE ( SELECTEDVALUE ( gob_mapa[gobernador] ), REMOVEFILTERS ( gob_mapa[anio_corte] ), gob_mapa[anio_corte] = a ),
            "Elegí una provincia" )''', None, 'Provincia')
    med('Espacio gobernador actual (id)', '''
        VAR a = [Año último gobernador]
        RETURN CALCULATE ( SELECTEDVALUE ( gob_mapa[id_espacio] ), REMOVEFILTERS ( gob_mapa[anio_corte] ), gob_mapa[anio_corte] = a )''',
        None, 'Provincia', hidden=True)
    med('Gobernador actual: espacio y mandato', '''
        VAR a = [Año último gobernador]
        VAR m = CALCULATE ( SELECTEDVALUE ( gob_mapa[mandato] ), REMOVEFILTERS ( gob_mapa[anio_corte] ), gob_mapa[anio_corte] = a )
        VAR e = LOOKUPVALUE ( espacios[espacio_corto], espacios[id_espacio], [Espacio gobernador actual (id)] )
        RETURN IF ( [Hay provincia], COALESCE ( e, "Sin espacio" ) & IF ( m <> "", " · " & m ), "—" )''', None, 'Provincia')
    med('Color gobernador actual',
        'COALESCE ( LOOKUPVALUE ( espacios[color], espacios[id_espacio], [Espacio gobernador actual (id)] ), %s )' % GRIS_VACIO,
        None, 'Colores')
    med('Balotaje 2023 en el ámbito', '''
        VAR e = [Id último balotaje]
        VAR g = CALCULATE ( SELECTEDVALUE ( prov_eleccion[ganador] ), REMOVEFILTERS ( elecciones ), prov_eleccion[id_eleccion] = e )
        VAR p = CALCULATE ( SELECTEDVALUE ( prov_eleccion[ganador_pct] ), REMOVEFILTERS ( elecciones ), prov_eleccion[id_eleccion] = e )
        RETURN IF ( [Hay provincia], g & " · " & FORMAT ( p / 100, "0.0%" ),
            [KPI balotaje ganador] & " · " & FORMAT ( [KPI balotaje %], "0.0%" ) )''', None, 'Provincia')
    med('Última intermedia en el ámbito', '''
        IF ( [Hay provincia],
            [Ganador última intermedia (provincia)] & " · " & FORMAT ( [% ganador última intermedia (provincia)], "0.0%" ),
            [KPI intermedia ganador] & " · " & FORMAT ( [KPI intermedia %], "0.0%" ) )''', None, 'Provincia')
    med('Diputados que elige',
        'CALCULATE ( SUM ( bancas[bancas] ), bancas[camara] = "Diputados", bancas[vigente] = TRUE () )', '0', 'Congreso')

    def bancas_hoy(camara):
        return """
        VAR t =
            FILTER (
                ADDCOLUMNS ( ALL ( espacios ),
                    "@b", CALCULATE ( SUM ( bancas[bancas] ), bancas[camara] = "%s", bancas[vigente] = TRUE () ) ),
                [@b] > 0 )
        RETURN CONCATENATEX ( t, espacios[espacio_corto] & " " & [@b], " · ", [@b], DESC )""" % camara

    med('Diputados hoy (por espacio)', bancas_hoy('Diputados'), None, 'Congreso')
    med('Senadores hoy (por espacio)', bancas_hoy('Senado'), None, 'Congreso')
    med('Título hist diputados', '"Diputados 1983-2025: % por espacio · " & [Provincia elegida]', None, 'Etiquetas')
    med('Título participación hist', '"Participación 1983-2025 (% del padrón) · " & [Provincia elegida]', None, 'Etiquetas')
    med('Título blancos hist', '"Votos en blanco y nulos (% de los votantes) · " & [Provincia elegida]', None, 'Etiquetas')
    med('Título hist intermedias', '"Intermedias 1985-2025: % por espacio · " & [Provincia elegida]', None, 'Etiquetas')
    med('Título hist presidencial', '"Presidente, primera vuelta 1983-2023: % por espacio · " & [Provincia elegida]', None, 'Etiquetas')

    # ------------------------------------------------------------------ Gobernadores
    med('Año gobernadores', 'MAX ( gob_mapa[anio_corte] )', '0', 'Gobernadores', hidden=True)
    med('Gobernador', 'SELECTEDVALUE ( gob_mapa[gobernador] )', None, 'Gobernadores')
    med('Espacio del gobernador',
        'LOOKUPVALUE ( espacios[espacio_corto], espacios[id_espacio], SELECTEDVALUE ( gob_mapa[id_espacio] ) )', None, 'Gobernadores')
    med('Mandato del gobernador', 'SELECTEDVALUE ( gob_mapa[mandato] )', None, 'Gobernadores')
    med('Color gobernador',
        'COALESCE ( LOOKUPVALUE ( espacios[color], espacios[id_espacio], SELECTEDVALUE ( gob_mapa[id_espacio] ) ), %s )' % GRIS_VACIO,
        None, 'Colores')
    med('Provincias gobernadas', '''
        VAR n = CALCULATE ( COUNTROWS ( gob_mapa ), NOT ISBLANK ( gob_mapa[id_espacio] ) )
        RETURN IF ( n > 0, n )''', '0', 'Gobernadores')
    for cod, nom in [('PJ', 'Peronismo'), ('UCR', 'UCR y aliados'), ('PRO', 'PRO-JxC'), ('PROV', 'Provinciales'),
                     ('PF', 'Terceras vías'), ('CI', 'Centroizquierda')]:
        med('Gobernaciones %s' % nom, 'CALCULATE ( COUNTROWS ( gob_mapa ), espacios[id_espacio] = "%s" ) + 0' % cod, '0', 'Gobernadores')
    med('Título mapa gobernadores', '"Quién gobernaba cada provincia a fines de " & [Año gobernadores]', None, 'Gobernadores')
    med('Título historia gobernadores', '"Elecciones a gobernador 1983-2025 · " & [Provincia elegida]', None, 'Gobernadores')
    med('Lectura gobernadores', '''
        VAR a = [Año gobernadores]
        VAR t = ADDCOLUMNS ( FILTER ( ALL ( espacios ), [Provincias gobernadas] > 0 ), "@n", [Provincias gobernadas] )
        RETURN
            IF ( [Hay provincia],
                [Provincia elegida] & " a fines de " & a & ": " & [Gobernador]
                    & IF ( NOT ISBLANK ( [Espacio del gobernador] ), " (" & [Espacio del gobernador] & ", " & [Mandato del gobernador] & ")" ) & ".",
                "A fines de " & a & ": " & CONCATENATEX ( t, espacios[espacio_corto] & " " & [@n], " · ", [@n], DESC )
                    & " provincias. Los frentes de Cambiemos/JxC cuentan como PRO-JxC aunque el gobernador sea radical." )''',
        None, 'Gobernadores')
    med('Avatar gobernador (mapa)', avatar('gob_mapa'), None, 'Gobernadores', data_category='ImageUrl')
    med('Avatar gobernador', avatar('gob_elecciones'), None, 'Gobernadores', data_category='ImageUrl')
    med('% gobernador electo', 'DIVIDE ( SUM ( gob_elecciones[ganador_pct] ), 100 )', PCT, 'Gobernadores')
    med('Margen gobernador (pp)', 'SUM ( gob_elecciones[margen_pp] )', PP, 'Gobernadores')
    med('Segundo gobernador', 'SELECTEDVALUE ( gob_elecciones[segundo] )', None, 'Gobernadores')
    med('Año última gobernación', 'MAX ( gob_elecciones[anio] )', '0', 'Gobernadores',
        hidden=True)
    med('Vuelta última gobernación', '''
        VAR a = [Año última gobernación]
        RETURN CALCULATE ( MAX ( gob_elecciones[vuelta_final] ), gob_elecciones[anio] = a )''',
        None, 'Gobernadores', hidden=True)
    med('% última elección a gobernador', '''
        VAR a = [Año última gobernación]
        VAR v = [Vuelta última gobernación]
        VAR p = CALCULATE ( SUM ( gob_resultados[pct] ), gob_elecciones[anio] = a, gob_resultados[vuelta] = v )
        RETURN IF ( [Hay provincia], DIVIDE ( p, 100 ) )''', PCT, 'Gobernadores')
    med('% última gobernación (top 6)', '''
        VAR x = [% última elección a gobernador]
        VAR r = RANKX ( ALLSELECTED ( gob_resultados[etiqueta] ), [% última elección a gobernador],, DESC, Dense )
        RETURN IF ( NOT ISBLANK ( x ) && r <= 6, x )''', PCT, 'Gobernadores')
    med('Color lista gobernador', '''
        VAR a = [Año última gobernación]
        VAR e = CALCULATE ( MAX ( gob_resultados[id_espacio] ), gob_elecciones[anio] = a )
        RETURN COALESCE ( LOOKUPVALUE ( espacios[color], espacios[id_espacio], e ), "#A9ABBF" )''', None, 'Colores')
    med('Título última gobernación', '''
        VAR a = [Año última gobernación]
        RETURN IF ( [Hay provincia],
            "Última elección a gobernador · " & [Provincia elegida] & " " & a & IF ( [Vuelta última gobernación] = "BAL", " (balotaje)" ),
            "Última elección a gobernador · elegí una provincia" )''', None, 'Gobernadores')

    # ------------------------------------------------------------------ Congreso
    med('Bancas en juego', 'SUM ( bancas[bancas] )', '0', 'Congreso')
    med('Bancas ganadas', '''
        VAR b = SUM ( bancas[bancas] )
        RETURN IF ( b > 0, b )''', '0', 'Congreso')
    med('% votos lista (con banca)', 'IF ( [Bancas ganadas] > 0, DIVIDE ( SUM ( bancas[pct] ), 100 ) )', PCT, 'Congreso')
    med('Bancas vigentes', '''
        VAR b = SUM ( composicion[bancas] )
        RETURN IF ( b > 0, b )''', '0', 'Congreso')
    for cod, nom in [('PJ', 'Peronismo'), ('UCR', 'UCR y aliados'), ('PRO', 'PRO-JxC'), ('LLA', 'LLA'), ('PF', 'Terceras vías'),
                     ('PROV', 'Provinciales')]:
        med('Bancas %s' % nom, 'CALCULATE ( SUM ( composicion[bancas] ), espacios[id_espacio] = "%s" )' % cod, '0', 'Congreso')
    med('Etiqueta cámara', 'SELECTEDVALUE ( camara_anio[etiqueta], "Elegí cámara y año" )', None, 'Congreso')
    med('Título composición', '"Cómo queda la cámara después de la elección · " & [Etiqueta cámara]', None, 'Congreso')
    med('Título bancas ganadas', '"Bancas ganadas · " & [Etiqueta cámara] & " · " & [Provincia elegida]', None, 'Congreso')
    med('Título historia cámara',
        '"Bancas por espacio en " & SELECTEDVALUE ( camara_anio[camara], "la cámara" ) & ", elección por elección"', None, 'Congreso')
    med('Color bancas provincia', '''
        VAR t =
            TOPN ( 1,
                ADDCOLUMNS ( VALUES ( bancas[id_espacio] ),
                    "@b", CALCULATE ( SUM ( bancas[bancas] ) ), "@v", CALCULATE ( SUM ( bancas[votos] ) ) ),
                [@b], DESC, [@v], DESC )
        VAR e = MAXX ( FILTER ( t, [@b] > 0 ), bancas[id_espacio] )
        RETURN COALESCE ( LOOKUPVALUE ( espacios[color], espacios[id_espacio], e ), %s )''' % GRIS_VACIO, None, 'Colores')
    med('Reparto de bancas', '''
        VAR t = FILTER ( ADDCOLUMNS ( VALUES ( bancas[opcion] ), "@b", CALCULATE ( SUM ( bancas[bancas] ) ) ), [@b] > 0 )
        RETURN CONCATENATEX ( t, bancas[opcion] & ": " & [@b], " · ", [@b], DESC )''', None, 'Congreso')
    med('Lectura congreso', '''
        VAR jue = [Bancas en juego]
        VAR rep =
            CONCATENATEX ( FILTER ( ADDCOLUMNS ( ALL ( espacios ), "@b", [Bancas ganadas] ), [@b] > 0 ),
                espacios[espacio_corto] & " " & [@b], ", ", [@b], DESC )
        VAR comp = ADDCOLUMNS ( FILTER ( ALL ( espacios ), [Bancas vigentes] > 0 ), "@c", [Bancas vigentes] )
        VAR primero = TOPN ( 1, comp, [@c], DESC )
        VAR n1 = MAXX ( primero, [@c] )
        VAR may = CALCULATE ( MAX ( composicion[mayoria] ), REMOVEFILTERS ( espacios ) )
        VAR tc = CALCULATE ( MAX ( composicion[total_bancas] ), REMOVEFILTERS ( espacios ) )
        RETURN
            [Provincia elegida] & " · " & [Etiqueta cámara] & ": se repartieron " & jue & " bancas (" & rep & ")."
            & IF ( COUNTROWS ( comp ) > 0,
                " En la cámara, la primera minoría es " & MAXX ( primero, espacios[espacio_corto] ) & " con " & n1 & " de " & tc
                    & IF ( n1 >= may, ": tiene quórum propio (" & may & ").", "; nadie llega al quórum propio (" & may & ")." ),
                " Para este año no se puede reconstruir la composición completa." )''', None, 'Congreso')
    med('SVG hemiciclo', """
        VAR cam = SELECTEDVALUE ( camara_anio[camara] )
        VAR comp =
            ADDCOLUMNS (
                FILTER ( ALL ( espacios ), [Bancas vigentes] > 0 ),
                "@n", [Bancas vigentes],
                "@o", SWITCH ( espacios[id_espacio], "IZQ", 1, "CI", 2, "PJ", 3, "PF", 4, "PROV", 5, "OTR", 6, "UCR", 7, "PRO", 8, "CD", 9, "LLA", 10, 11 )
            )
        VAR acum = ADDCOLUMNS ( comp, "@hasta", VAR o = [@o] RETURN SUMX ( FILTER ( comp, [@o] <= o ), [@n] ) )
        VAR total = SUMX ( comp, [@n] )
        VAR may = CALCULATE ( MAX ( composicion[mayoria] ), REMOVEFILTERS ( espacios ) )
        VAR asientos = FILTER ( ALL ( hemiciclo ), hemiciclo[camara] = cam )
        VAR lleno = COUNTROWS ( asientos )
        VAR puntos =
            CONCATENATEX (
                asientos,
                VAR k = hemiciclo[asiento]
                VAR omin = MINX ( FILTER ( acum, [@hasta] >= k ), [@o] )
                VAR c = COALESCE ( MAXX ( FILTER ( acum, [@o] = omin ), espacios[color] ), "#E4E2EE" )
                RETURN "<circle cx='" & hemiciclo[x] & "' cy='" & hemiciclo[y] & "' r='" & hemiciclo[r] & "' fill='" & c & "'/>",
                "", hemiciclo[asiento], ASC )
        VAR leyenda =
            CONCATENATEX (
                acum,
                VAR i = RANKX ( acum, [@o],, ASC ) - 1
                VAR lx = 14 + MOD ( i, 5 ) * 118
                VAR ly = 356 + INT ( i / 5 ) * 22
                RETURN "<rect x='" & lx & "' y='" & ly - 10 & "' width='12' height='12' rx='2' fill='" & espacios[color] & "'/><text x='" & lx + 17
                    & "' y='" & ly & "' font-family='Arial' font-size='12' fill='#1B1F3B'>" & espacios[espacio_corto] & " " & [@n] & "</text>",
                "", [@o], ASC )
        VAR centro =
            "<text x='300' y='262' font-family='Arial' font-size='36' font-weight='bold' fill='#242C4F' text-anchor='middle'>" & total & "</text>"
            & "<text x='300' y='284' font-family='Arial' font-size='12' fill='#6B6F8A' text-anchor='middle'>"
            & IF ( total < lleno, "bancas con datos (de " & lleno & ")", "bancas" ) & "</text>"
            & "<text x='300' y='302' font-family='Arial' font-size='12' fill='#6B6F8A' text-anchor='middle'>quórum propio: " & may & "</text>"
        VAR vacio =
            "<text x='300' y='200' font-family='Arial' font-size='15' fill='#6B6F8A' text-anchor='middle'>"
            & "Para este año no se puede reconstruir la composición</text>"
        VAR svg = "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 600 400'>" & IF ( total > 0, puntos & centro & leyenda, vacio ) & "</svg>"
        RETURN "data:image/svg+xml;utf8," & SUBSTITUTE ( svg, "#", "%23" )""", None, 'Congreso', data_category='ImageUrl')

    # ------------------------------------------------------------------ Presidentes
    med('Avatar presidente', avatar('presidentes'), None, 'Presidentes', data_category='ImageUrl')
    med('% presidente', 'DIVIDE ( SUM ( presidentes[pct] ), 100 )', PCT, 'Presidentes')
    med('Años de gobierno',
        'SUMX ( presidentes, DATEDIFF ( presidentes[desde], COALESCE ( presidentes[hasta], TODAY () ), DAY ) ) / 365.25',
        '0.0', 'Presidentes')
    med('SVG presidentes', """
        VAR filas =
            ADDCOLUMNS ( ALL ( presidentes ),
                "@col", COALESCE ( LOOKUPVALUE ( espacios[color], espacios[id_espacio], presidentes[id_espacio] ), "#A9ABBF" ),
                "@esp", COALESCE ( LOOKUPVALUE ( espacios[espacio_corto], espacios[id_espacio], presidentes[id_espacio] ), "Otros" ) )
        VAR tarjetas =
            CONCATENATEX (
                filas,
                VAR i = presidentes[orden] - 1
                VAR gx = MOD ( i, 5 ) * 248
                VAR gy = INT ( i / 5 ) * 150
                VAR nom = presidentes[presidente]
                VAR k = SEARCH ( " ", nom, 1, 0 )
                VAR l1 = IF ( k > 0, LEFT ( nom, k - 1 ), nom )
                VAR l2 = IF ( k > 0, MID ( nom, k + 1, 60 ) )
                VAR ini = presidentes[iniciales]
                RETURN
                    "<g transform='translate(" & gx & "," & gy & ")'>"
                    & "<rect x='3' y='3' width='240' height='142' rx='10' fill='white' stroke='#DEDBF0'/>"
                    & "<rect x='3' y='3' width='240' height='6' rx='3' fill='" & [@col] & "'/>"
                    & "<circle cx='42' cy='58' r='30' fill='" & [@col] & "'/>"
                    & "<text x='42' y='" & IF ( LEN ( ini ) > 2, 64, 66 ) & "' font-family='Arial' font-size='" & IF ( LEN ( ini ) > 2, 18, 22 )
                    & "' font-weight='bold' fill='white' text-anchor='middle'>" & ini & "</text>"
                    & "<text x='82' y='46' font-family='Arial' font-size='14' font-weight='bold' fill='#1B1F3B'>" & l1 & "</text>"
                    & "<text x='82' y='64' font-family='Arial' font-size='" & IF ( LEN ( l2 ) > 16, 11, 14 )
                    & "' font-weight='bold' fill='#1B1F3B'>" & l2 & "</text>"
                    & "<text x='82' y='82' font-family='Arial' font-size='11' fill='#6B6F8A'>" & presidentes[mandato] & "</text>"
                    & "<text x='14' y='112' font-family='Arial' font-size='12' font-weight='bold' fill='" & [@col] & "'>" & [@esp] & "</text>"
                    & "<text x='14' y='131' font-family='Arial' font-size='11' fill='#1B1F3B'>" & FORMAT ( presidentes[pct] / 100, "0.0%" )
                    & " · " & LOWER ( presidentes[instancia] ) & " " & presidentes[anio] & "</text></g>",
                "", presidentes[orden], ASC )
        VAR svg = "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1244 300'>" & tarjetas & "</svg>"
        RETURN "data:image/svg+xml;utf8," & SUBSTITUTE ( SUBSTITUTE ( svg, "%", "%25" ), "#", "%23" )""", None, 'Presidentes', data_category='ImageUrl')
