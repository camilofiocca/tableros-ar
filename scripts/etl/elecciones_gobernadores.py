# -*- coding: utf-8 -*-
"""Arma la base de GOBERNADORES y SENADORES del Tablero Elecciones AR (se corre a mano, una vez por elección).

Deja en data/elecciones/:
  base_gob_listas.csv   anio, id_prov, vuelta, opcion, partido, candidato, votos, pct_fuente, id_espacio_fijo, fuente
  base_gob_totales.csv  anio, id_prov, vuelta, electores, votantes, blancos, nulos, fuente
  base_sen_listas.csv   id_eleccion (AAAA-SEN), id_prov, fuerza, bloque_fuente, votos, fuente
  base_sen_totales.csv  id_eleccion, id_prov, electores, votantes, blancos, nulos, fuente

Fuentes:
  1. Gobernador 1983-2019 (y jefe de Gobierno porteño 1996-2019): escrutinio DEFINITIVO del Atlas Electoral
     de Andy Tow, en PolAr (PoliticaArgentina/data_warehouse, mismo commit fijado que las presidenciales).
  2. Elecciones de gobernador que PolAr no trae (1995 en Córdoba, Jujuy, La Pampa, La Rioja, Mendoza, Neuquén y
     Río Negro; Santiago del Estero 2021): compilación por departamento de azha2005/257arg.
  3. Gobernador 2013 (Corrientes), 2021 (Corrientes), 2023 y 2025: data/elecciones/manual/gobernadores_manual.csv,
     transcripto de informes de la DINE, escrutinios provinciales y medios (fuente fila por fila).
  4. Senadores nacionales 2003-2025 (tercios por provincia): 257arg (DINE / PolAr). No hay datos de 2001.

Uso:  python scripts/etl/elecciones_gobernadores.py [--cache /ruta/a/cache]
"""
import argparse, io, os, re, sys
import numpy as np
import pandas as pd
import requests

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from elecciones_base import (DATA, URL_POLAR, FUENTE_POLAR, FUENTE_257, SLUG_POLAR, FILAS_NO_LISTA,  # noqa: E402
                             bajar, cod_prov, master_257_completo, desde_master)

FUENTE_MANUAL = 'Carga manual verificada (ver columna fuente de gobernadores_manual.csv)'
ANIOS_GOB = list(range(1983, 2020))
SIN_LISTA = re.compile(r'^(votos? )?(nulos?|en blanco( y nulos)?|blancos?( y nulos)?|recurridos?|impugnados?|anulados?)$', re.I)
BLANCO = re.compile(r'blanco', re.I)


def partir_lista(txt):
    """'Schiaretti - Calvo (Hacemos Por Cordoba)' -> ('Hacemos Por Cordoba', 'Schiaretti - Calvo')."""
    txt = re.sub(r'\s+', ' ', str(txt).replace('.', ' ')).strip()
    m = re.match(r'^(.*?)\s*\((.+?)\)?\s*$', txt)
    if m and '(' in txt and re.search(r'\w\s*-\s*\w', m.group(1)) and not re.search(r'(frente|partido|alianza|lema)', m.group(1), re.I):
        return m.group(2).strip(), re.sub(r'\s*-\s*', ' - ', m.group(1).strip())
    if ' - ' in txt and not re.search(r'(frente|partido|alianza|union|movimiento|lema)', txt, re.I):
        return '', txt
    return txt, ''


def gobernadores_polar(cache=None):
    listas, totales = [], []
    # Índice de archivos de gobernador del commit fijado de PolAr (evita pedir cientos de URLs inexistentes).
    indice = open(os.path.join(DATA, 'manual', 'polar_gobernador_archivos.txt')).read().split()
    for arch in indice:
        mm = re.match(r'^([a-z]+)_gober_(gral|balota)(\d{4})\.csv$', arch)
        slug, tipo, a = mm.group(1), mm.group(2), int(mm.group(3))
        vuelta = '1V' if tipo == 'gral' else 'BAL'
        if a not in ANIOS_GOB:
            continue
        if True:
            if True:
                raw = bajar(URL_POLAR.format(archivo=arch), cache, 'polar_' + arch)
                d = pd.read_csv(io.BytesIO(raw))
                cp = cod_prov(slug)
                d['lista'] = d['lista'].astype(str).str.strip()
                esp = d['lista'].str.lower().map(FILAS_NO_LISTA)
                no_lista = d['lista'].str.match(SIN_LISTA)
                esp = esp.where(esp.notna() | ~no_lista, np.where(d['lista'].str.contains(BLANCO), 'blancos', 'nulos'))
                otros = no_lista & esp.isna()
                l = d[esp.isna() & ~otros & (d['votos'] > 0)]
                t = {'anio': a, 'id_prov': cp, 'vuelta': vuelta, 'electores': float(d['electores'].max()),
                     'blancos': float(d.loc[esp == 'blancos', 'votos'].sum()),
                     'nulos': float(d.loc[esp == 'nulos', 'votos'].sum()), 'fuente': FUENTE_POLAR}
                t['votantes'] = float(l['votos'].sum() + d.loc[otros, 'votos'].sum()) + t['blancos'] + t['nulos']
                totales.append(t)
                for _, r in l.iterrows():
                    partido, cand = partir_lista(r['lista'])
                    listas.append({'anio': a, 'id_prov': cp, 'vuelta': vuelta, 'opcion': r['lista'], 'partido': partido,
                                   'candidato': cand, 'votos': float(r['votos']), 'pct_fuente': None,
                                   'id_espacio_fijo': None, 'fuente': FUENTE_POLAR})
    return pd.DataFrame(listas), pd.DataFrame(totales)


def gobernadores_257(m, ya):
    """Elecciones de gobernador que están en 257arg y no en PolAr (anio, id_prov)."""
    g = m[m.cargo.isin(['gobernador', 'jefe_de_gobierno', 'jefe_de_gobierno_1v'])].copy()
    g['id_eleccion'] = g.anio.astype(str) + '-GOB'
    faltan = sorted({(a, p) for a, p in zip(g.anio, g.id_prov)} - ya)
    if not faltan:
        return pd.DataFrame(), pd.DataFrame()
    g = g[[(a, p) in set(faltan) for a, p in zip(g.anio, g.id_prov)]]
    listas, tot = desde_master(g, g.id_eleccion.unique())
    listas['anio'] = listas.id_eleccion.str[:4].astype(int)
    tot['anio'] = tot.id_eleccion.str[:4].astype(int)
    listas = listas.rename(columns={'fuerza': 'opcion'})
    listas['partido'] = listas.opcion
    listas['candidato'] = ''
    listas['vuelta'] = '1V'
    listas['pct_fuente'] = None
    listas['id_espacio_fijo'] = None
    tot['vuelta'] = '1V'
    cols_l = ['anio', 'id_prov', 'vuelta', 'opcion', 'partido', 'candidato', 'votos', 'pct_fuente', 'id_espacio_fijo', 'fuente']
    cols_t = ['anio', 'id_prov', 'vuelta', 'electores', 'votantes', 'blancos', 'nulos', 'fuente']
    return listas[cols_l], tot[cols_t]


def gobernadores_manual():
    d = pd.read_csv(os.path.join(DATA, 'manual', 'gobernadores_manual.csv'), dtype={'id_prov': str})
    d['id_prov'] = d.id_prov.str.zfill(2)
    return pd.DataFrame({'anio': d.anio, 'id_prov': d.id_prov, 'vuelta': d.vuelta, 'opcion': d.opcion,
                         'partido': d.opcion, 'candidato': d.candidato.fillna(''), 'votos': d.votos,
                         'pct_fuente': d.pct, 'id_espacio_fijo': d.id_espacio, 'fuente': d.fuente})


def senadores(m):
    s = m[(m.cargo == 'senadores') & (m.anio >= 2001)].copy()
    s['id_eleccion'] = s.anio.astype(str) + '-SEN'
    return desde_master(s, s.id_eleccion.unique())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache', default=None)
    a = ap.parse_args()
    gl, gt = gobernadores_polar(a.cache)
    m = master_257_completo(a.cache)
    man = gobernadores_manual()
    ya = {(r.anio, r.id_prov) for r in gt.itertuples()}
    dup = {(r.anio, r.id_prov) for r in man.itertuples()} & ya
    if dup:
        raise SystemExit('Elecciones cargadas a mano que ya vienen de PolAr: %s' % sorted(dup))
    # La carga manual (definitivos verificados) tiene prioridad sobre 257arg.
    l2, t2 = gobernadores_257(m, ya | {(r.anio, r.id_prov) for r in man.itertuples()})
    listas = pd.concat([gl, l2, man], ignore_index=True)
    totales = pd.concat([gt, t2], ignore_index=True)
    listas.to_csv(os.path.join(DATA, 'base_gob_listas.csv'), index=False)
    totales.to_csv(os.path.join(DATA, 'base_gob_totales.csv'), index=False)
    sl, st = senadores(m)
    sl.to_csv(os.path.join(DATA, 'base_sen_listas.csv'), index=False)
    st.to_csv(os.path.join(DATA, 'base_sen_totales.csv'), index=False)
    n = listas.groupby(['anio', 'id_prov', 'vuelta']).ngroups
    print('gobernador: %d elecciones (%d listas) · senadores: %d elecciones-provincia (%d listas)' % (
        n, len(listas), st.groupby(['id_eleccion', 'id_prov']).ngroups, len(sl)))


if __name__ == '__main__':
    main()
