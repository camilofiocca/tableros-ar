# -*- coding: utf-8 -*-
"""Arma la base del Tablero Elecciones AR (presidenciales y legislativas nacionales, 1983-2025).

Se corre a mano, una vez por elección nueva (los resultados históricos no cambian). Deja en
data/elecciones/ dos CSV que el notebook ETL lee en cada corrida:

  base_listas.csv   id_eleccion, id_prov, fuerza, bloque_fuente, votos, fuente
  base_totales.csv  id_eleccion, id_prov, electores, votantes, blancos, nulos, fuente

Fuentes (todas públicas; las de GitHub van fijadas a un commit para que el resultado sea reproducible):
  1. Presidenciales 1983-2019 (1ra vuelta) y balotaje 2015: escrutinio DEFINITIVO por provincia del
     Atlas Electoral de Andy Tow, en el repositorio PolAr (PoliticaArgentina/data_warehouse, CC BY 4.0).
  2. Presidenciales 2023 (1ra vuelta y balotaje): escrutinio definitivo por provincia (Cámara Nacional
     Electoral, transcripto de la tabla "Results by province" de Wikipedia) en data/elecciones/manual/.
  3. Diputados nacionales 1983-2025 y PASO presidenciales 2011-2023: escrutinio PROVISORIO de la
     Dirección Nacional Electoral (2011-2025), PolAr/Andy Tow (2003-2009) y base de Ernesto Calvo
     (1983-1999), compilados por departamento en azha2005/257arg (MASTER_resultados.xlsx, CC BY 4.0).

Uso:  python scripts/etl/elecciones_base.py [--cache /ruta/a/cache]
"""
import argparse, io, os, re, sys, unicodedata
import pandas as pd
import requests

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(AQUI, '..', '..'))
DATA = os.path.join(REPO, 'data', 'elecciones')

SHA_POLAR = '9304ac9b102b94ee140a2a5ad671f0cacd9cd114'
SHA_257 = '573038a4ab8a59b266c2de04d086e301c26467e7'
URL_POLAR = ('https://raw.githubusercontent.com/PoliticaArgentina/data_warehouse/%s/'
             'electorAr/data/escrutinios_definitivos/{archivo}' % SHA_POLAR)
URL_MASTER = 'https://raw.githubusercontent.com/azha2005/257arg/%s/resultados_xlsx/MASTER_resultados.xlsx' % SHA_257

FUENTE_POLAR = 'Atlas Electoral de Andy Tow vía PolAr (escrutinio definitivo)'
FUENTE_CNE = 'Cámara Nacional Electoral, escrutinio definitivo (tabla por provincia de Wikipedia)'
FUENTE_257 = {'dine': 'DINE, escrutinio provisorio (compilado en 257arg)',
              'polar': 'PolAr / Andy Tow, escrutinio provisorio por mesa (compilado en 257arg)',
              'calvo': 'Base de Ernesto Calvo (compilada en 257arg)'}

# ------------------------------------------------------------------------------------------------
# Provincias (código INDEC de 2 dígitos)
# ------------------------------------------------------------------------------------------------
PROVINCIAS = [
    ('02', 'Ciudad de Buenos Aires', 'CABA', 'Centro'), ('06', 'Buenos Aires', 'Buenos Aires', 'Centro'),
    ('10', 'Catamarca', 'Catamarca', 'NOA'), ('14', 'Córdoba', 'Córdoba', 'Centro'),
    ('18', 'Corrientes', 'Corrientes', 'NEA'), ('22', 'Chaco', 'Chaco', 'NEA'),
    ('26', 'Chubut', 'Chubut', 'Patagonia'), ('30', 'Entre Ríos', 'Entre Ríos', 'Centro'),
    ('34', 'Formosa', 'Formosa', 'NEA'), ('38', 'Jujuy', 'Jujuy', 'NOA'),
    ('42', 'La Pampa', 'La Pampa', 'Centro'), ('46', 'La Rioja', 'La Rioja', 'NOA'),
    ('50', 'Mendoza', 'Mendoza', 'Cuyo'), ('54', 'Misiones', 'Misiones', 'NEA'),
    ('58', 'Neuquén', 'Neuquén', 'Patagonia'), ('62', 'Río Negro', 'Río Negro', 'Patagonia'),
    ('66', 'Salta', 'Salta', 'NOA'), ('70', 'San Juan', 'San Juan', 'Cuyo'),
    ('74', 'San Luis', 'San Luis', 'Cuyo'), ('78', 'Santa Cruz', 'Santa Cruz', 'Patagonia'),
    ('82', 'Santa Fe', 'Santa Fe', 'Centro'), ('86', 'Santiago del Estero', 'Santiago del Estero', 'NOA'),
    ('90', 'Tucumán', 'Tucumán', 'NOA'), ('94', 'Tierra del Fuego', 'Tierra del Fuego', 'Patagonia'),
]


def norm(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


ALIAS = {}
for cod, nom, corto, reg in PROVINCIAS:
    ALIAS[norm(nom)] = cod
    ALIAS[norm(corto)] = cod
ALIAS.update({norm(k): v for k, v in {
    'Capital Federal': '02', 'Ciudad Autónoma de Buenos Aires': '02', 'Ciudad Autónoma Bs.As.': '02',
    'Buenos Aires City': '02', 'caba': '02', 'pba': '06', 'Tierra del Fuego AeIAS': '94',
    'Tierra Del Fuego, Antártida E Islas Del Atlántico Sur': '94', 'tdf': '94', 'erios': '30',
    'pampa': '42', 'rioja': '46', 'rnegro': '62', 'sanluis': '74', 'sjuan': '70', 'scruz': '78',
    'sfe': '82', 'santiago': '86', 'cordoba': '14', 'neuquen': '58', 'tucuman': '90',
}.items()})


def cod_prov(nombre):
    c = ALIAS.get(norm(nombre))
    if c is None:
        raise KeyError('Provincia sin código: %r' % nombre)
    return c


# ------------------------------------------------------------------------------------------------
# Catálogo de elecciones
# ------------------------------------------------------------------------------------------------
# (id, año, fecha, tipo, instancia, cargo)
ELECCIONES = []
for a, f in [(1983, '1983-10-30'), (1989, '1989-05-14'), (1995, '1995-05-14'), (1999, '1999-10-24'),
             (2003, '2003-04-27'), (2007, '2007-10-28'), (2011, '2011-10-23'), (2015, '2015-10-25'),
             (2019, '2019-10-27'), (2023, '2023-10-22')]:
    ELECCIONES.append(('%d-PRES-1V' % a, a, f, 'Presidencial', 'Primera vuelta', 'Presidente'))
for a, f in [(2015, '2015-11-22'), (2023, '2023-11-19')]:
    ELECCIONES.append(('%d-PRES-BAL' % a, a, f, 'Presidencial', 'Balotaje', 'Presidente'))
for a, f in [(2011, '2011-08-14'), (2015, '2015-08-09'), (2019, '2019-08-11'), (2023, '2023-08-13')]:
    ELECCIONES.append(('%d-PRES-PASO' % a, a, f, 'Presidencial', 'PASO', 'Presidente'))
for a, f in [(1983, '1983-10-30'), (1985, '1985-11-03'), (1987, '1987-09-06'), (1989, '1989-05-14'),
             (1991, '1991-09-08'), (1993, '1993-10-03'), (1995, '1995-05-14'), (1997, '1997-10-26'),
             (1999, '1999-10-24'), (2003, '2003-04-27'), (2005, '2005-10-23'), (2007, '2007-10-28'),
             (2009, '2009-06-28'), (2011, '2011-10-23'), (2013, '2013-10-27'), (2015, '2015-10-25'),
             (2017, '2017-10-22'), (2019, '2019-10-27'), (2021, '2021-11-14'), (2023, '2023-10-22'),
             (2025, '2025-10-26')]:
    tipo = 'Presidencial' if a in (1983, 1989, 1995, 1999, 2003, 2007, 2011, 2015, 2019, 2023) else 'Legislativa'
    ELECCIONES.append(('%d-DIP' % a, a, f, tipo, 'General', 'Diputados nacionales'))


# ------------------------------------------------------------------------------------------------
# Descargas (con caché local opcional)
# ------------------------------------------------------------------------------------------------
H = {'User-Agent': 'tableros-ar ETL (github.com/camilofiocca/tableros-ar)'}


def bajar(url, cache=None, nombre=None):
    if cache:
        p = os.path.join(cache, nombre or os.path.basename(url))
        if os.path.exists(p):
            return open(p, 'rb').read()
    for intento in range(4):
        r = requests.get(url, headers=H, timeout=(15, 300))
        if r.status_code == 429 or (r.ok and r.content[:15].lower().startswith(b'<html')):
            import time; time.sleep(20 * (intento + 1)); continue
        r.raise_for_status()
        if cache:
            os.makedirs(cache, exist_ok=True)
            open(os.path.join(cache, nombre or os.path.basename(url)), 'wb').write(r.content)
        return r.content
    raise RuntimeError('No se pudo bajar ' + url)


SLUG_POLAR = ['caba', 'pba', 'catamarca', 'cordoba', 'corrientes', 'chaco', 'chubut', 'erios', 'formosa',
              'jujuy', 'pampa', 'rioja', 'mendoza', 'misiones', 'neuquen', 'rnegro', 'salta', 'sjuan',
              'sanluis', 'scruz', 'sfe', 'santiago', 'tucuman', 'tdf']
FILAS_NO_LISTA = {'votos nulos': 'nulos', 'votos en blanco': 'blancos', 'votos blancos': 'blancos'}


def presidenciales_polar(cache=None):
    """1ra vuelta 1983-2019 y balotaje 2015, por provincia (definitivo)."""
    listas, totales = [], []
    for a in (1983, 1989, 1995, 1999, 2003, 2007, 2011, 2015, 2019):
        for tipo, sufijo in (('gral', '1V'), ('balota', 'BAL')):
            if tipo == 'balota' and a != 2015:
                continue
            ide = '%d-PRES-%s' % (a, sufijo)
            for slug in SLUG_POLAR:
                arch = '%s_presi_%s%d.csv' % (slug, tipo, a)
                try:
                    raw = bajar(URL_POLAR.format(archivo=arch), cache, 'polar_' + arch)
                except requests.HTTPError:
                    continue  # p. ej., Tierra del Fuego no votaba para presidente antes de 1991
                d = pd.read_csv(io.BytesIO(raw))
                cp = cod_prov(slug)
                d['lista'] = d['lista'].astype(str).str.replace('.', ' ', regex=False).str.replace(r'\s+', ' ', regex=True).str.strip()
                esp = d['lista'].str.lower().map(FILAS_NO_LISTA)
                t = {'id_eleccion': ide, 'id_prov': cp, 'electores': float(d['electores'].max()),
                     'blancos': float(d.loc[esp == 'blancos', 'votos'].sum()),
                     'nulos': float(d.loc[esp == 'nulos', 'votos'].sum()), 'fuente': FUENTE_POLAR}
                l = d[esp.isna() & (d['votos'] > 0)]
                t['votantes'] = float(l['votos'].sum()) + t['blancos'] + t['nulos']
                totales.append(t)
                for _, r in l.iterrows():
                    listas.append({'id_eleccion': ide, 'id_prov': cp, 'fuerza': r['lista'], 'bloque_fuente': None,
                                   'votos': float(r['votos']), 'fuente': FUENTE_POLAR})
    return pd.DataFrame(listas), pd.DataFrame(totales)


def presidenciales_2023(master_tot):
    """Definitivo 2023 por provincia (data/elecciones/manual/presidente_2023_cne.csv)."""
    m = pd.read_csv(os.path.join(DATA, 'manual', 'presidente_2023_cne.csv'), dtype={'id_prov': str})
    listas, totales = [], []
    for ide, g in m.groupby('id_eleccion'):
        for cp, h in g.groupby('id_prov'):
            cand = h[h['fuerza'] != '(Blancos y nulos)']
            bn = float(h.loc[h['fuerza'] == '(Blancos y nulos)', 'votos'].sum())
            # electores: el padrón no cambia entre provisorio y definitivo; se toma de la DINE
            el = master_tot.loc[(master_tot.id_eleccion == ide) & (master_tot.id_prov == cp), 'electores']
            totales.append({'id_eleccion': ide, 'id_prov': cp, 'electores': float(el.iloc[0]) if len(el) else None,
                            'votantes': float(cand['votos'].sum()) + bn, 'blancos': None, 'nulos': None,
                            'blancos_y_nulos': bn, 'fuente': FUENTE_CNE + '; electores: DINE'})
            for _, r in cand.iterrows():
                listas.append({'id_eleccion': ide, 'id_prov': cp, 'fuerza': r['fuerza'], 'bloque_fuente': None,
                               'votos': float(r['votos']), 'fuente': FUENTE_CNE})
    return pd.DataFrame(listas), pd.DataFrame(totales)


def master_257(cache=None):
    """Diputados 1983-2025 y PASO presidenciales 2011-2023 (por departamento -> provincia)."""
    p = os.path.join(cache, 'master_largo.csv.gz') if cache else None
    if p and os.path.exists(p):
        d = pd.read_csv(p, low_memory=False)
    else:
        raw = bajar(URL_MASTER, cache, 'MASTER_resultados.xlsx')
        d = pd.read_excel(io.BytesIO(raw), 'largo')
        if p:
            d.to_csv(p, index=False)
    d = d[(d.anio >= 1983) & (d.fuente_id == 'principal') &
          d.cargo.isin(['diputados', 'presidente_paso', 'presidente', 'presidente_balotaje'])].copy()
    d['id_eleccion'] = d.anio.astype(str) + d.cargo.map({'diputados': '-DIP', 'presidente_paso': '-PRES-PASO',
                                                         'presidente': '-PRES-1V', 'presidente_balotaje': '-PRES-BAL'})
    d['id_prov'] = d.provincia.map(cod_prov)
    d['familia'] = 'dine'
    d.loc[d.anio <= 1999, 'familia'] = 'calvo'
    d.loc[d.anio.between(2003, 2009), 'familia'] = 'polar'
    # La base de Calvo de 1997 rotula los votos positivos ('pos19') como si fueran un partido.
    es_pos = d.codigo_partido.fillna('').str.match(r'^pos\d*$')
    d.loc[es_pos & (d.tipo_fila == 'agrupacion'), 'tipo_fila'] = 'positivos'
    return d


def nombre_master(r):
    if isinstance(r.partido, str) and r.partido.strip():
        return re.sub(r'\s+', ' ', r.partido).strip()
    # Base de Calvo (1995-1999): solo trae códigos; en 1997 llevan el sufijo del distrito ('ali19', 'pj19').
    return 'cod:' + re.sub(r'\d+$', '', str(r.codigo_partido).strip())


def desde_master(d, ids):
    x = d[d.id_eleccion.isin(ids)]
    a = x[x.tipo_fila == 'agrupacion'].copy()
    a['fuerza'] = a.apply(nombre_master, axis=1)
    a['bloque_fuente'] = a.bloque.where(a.bloque.notna() & (a.bloque != 'Otros (sin agrupar)'))
    listas = (a.groupby(['id_eleccion', 'id_prov', 'fuerza', 'familia'], dropna=False)
              .agg(votos=('votos', 'sum'), bloque_fuente=('bloque_fuente', 'first')).reset_index())
    listas = listas[listas.votos > 0]
    listas['fuente'] = listas.familia.map(FUENTE_257)
    t = x[x.tipo_fila.isin(['electores', 'votantes', 'blancos', 'nulos', 'impugnados', 'recurridos',
                            'impugnados_recurridos'])]
    t = t.pivot_table(index=['id_eleccion', 'id_prov', 'familia'], columns='tipo_fila', values='votos', aggfunc='sum').reset_index()
    pos = a.groupby(['id_eleccion', 'id_prov']).votos.sum().rename('positivos').reset_index()
    t = t.merge(pos, on=['id_eleccion', 'id_prov'], how='left')
    for c in ('votantes', 'blancos', 'nulos', 'impugnados', 'recurridos', 'impugnados_recurridos', 'electores'):
        if c not in t:
            t[c] = float('nan')
    otros = t[['impugnados', 'recurridos', 'impugnados_recurridos']].fillna(0).sum(axis=1)
    calc = t.positivos + t.blancos.fillna(0) + t.nulos.fillna(0) + otros
    t['votantes'] = t.votantes.where(t.votantes.notna(), calc)
    t['fuente'] = t.familia.map(FUENTE_257)
    return listas.drop(columns='familia'), t[['id_eleccion', 'id_prov', 'electores', 'votantes', 'blancos', 'nulos', 'fuente']]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache', default=None)
    args = ap.parse_args()

    m = master_257(args.cache)
    ids_master = [e[0] for e in ELECCIONES if e[0].endswith('-DIP') or e[0].endswith('-PASO')]
    l_m, t_m = desde_master(m, ids_master)
    _, t_m23 = desde_master(m, ['2023-PRES-1V', '2023-PRES-BAL'])
    l_p, t_p = presidenciales_polar(args.cache)
    # Provincias que faltan en PolAr (balotaje 2015: Tucumán) -> escrutinio provisorio de la DINE
    ids_p = sorted(set(t_p.id_eleccion))
    l_mp, t_mp = desde_master(m, ids_p)
    tenidas = set(zip(t_p.id_eleccion, t_p.id_prov))
    falta = [k for k in zip(t_mp.id_eleccion, t_mp.id_prov) if k not in tenidas]
    if falta:
        print('Completado con la DINE:', falta)
        sel = lambda d: d[[k in falta for k in zip(d.id_eleccion, d.id_prov)]]
        l_p = pd.concat([l_p, sel(l_mp)], ignore_index=True)
        t_p = pd.concat([t_p, sel(t_mp)], ignore_index=True)
    l_23, t_23 = presidenciales_2023(t_m23)

    listas = pd.concat([l_p, l_23, l_m], ignore_index=True)
    totales = pd.concat([t_p, t_23, t_m], ignore_index=True)
    validos = set(e[0] for e in ELECCIONES)
    assert set(listas.id_eleccion) <= validos, set(listas.id_eleccion) - validos
    listas = listas.sort_values(['id_eleccion', 'id_prov', 'votos'], ascending=[True, True, False])
    totales = totales.sort_values(['id_eleccion', 'id_prov'])

    os.makedirs(DATA, exist_ok=True)
    listas.to_csv(os.path.join(DATA, 'base_listas.csv'), index=False, float_format='%.0f')
    totales.to_csv(os.path.join(DATA, 'base_totales.csv'), index=False, float_format='%.0f')
    pd.DataFrame(ELECCIONES, columns=['id_eleccion', 'anio', 'fecha', 'tipo', 'instancia', 'cargo']).to_csv(
        os.path.join(DATA, 'elecciones.csv'), index=False)
    pd.DataFrame(PROVINCIAS, columns=['id_prov', 'provincia', 'nombre_corto', 'region']).to_csv(
        os.path.join(DATA, 'provincias.csv'), index=False)
    print('listas:', listas.shape, '· totales:', totales.shape)
    print(listas.groupby('id_eleccion').id_prov.nunique().to_string())


if __name__ == '__main__':
    main()
