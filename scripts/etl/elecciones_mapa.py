# -*- coding: utf-8 -*-
"""Geometría de provincias para el Tablero Elecciones AR.

Genera, a partir de los límites provinciales del INDEC (versión simplificada de geoAr/PolAr):
  data/elecciones/mapa/provincias_ar.geojson   (con la Ciudad de Buenos Aires ampliada en un recuadro)
  data/elecciones/mapa/provincias_ar.topojson  (lo lee el mapa de formas de Power BI por URL)
  data/elecciones/mapa/provincias_svg.csv      (trazados SVG por provincia para el mapa de respaldo en DAX)

La Ciudad de Buenos Aires mide 200 km²: a escala país no se ve. Por eso se dibuja además una copia
ampliada 12 veces en el Atlántico, frente a la costa bonaerense, con el mismo código: al hacer clic en
cualquiera de las dos se selecciona la Ciudad.

Uso:  python scripts/etl/elecciones_mapa.py   (necesita shapely; para el TopoJSON, node con topojson-server)
"""
import json, math, os, subprocess, sys
import requests
from shapely.geometry import shape, mapping, MultiPolygon, Polygon
from shapely import affinity

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from elecciones_base import PROVINCIAS, SHA_POLAR  # noqa: E402

REPO = os.path.abspath(os.path.join(AQUI, '..', '..'))
OUT = os.path.join(REPO, 'data', 'elecciones', 'mapa')
URL_GEO = ('https://raw.githubusercontent.com/PoliticaArgentina/data_warehouse/%s/'
           'geoAr/data/provincias_simplified.geojson' % SHA_POLAR)

INSET_CENTRO = (-54.6, -37.6)   # lon, lat donde se dibuja la Ciudad ampliada
INSET_ESCALA = 12
TOL_SVG = 0.03                  # grados: simplificación de los trazados SVG
W_SVG = 360                     # ancho del lienzo SVG (el alto sale de la proporción)


def cargar():
    g = requests.get(URL_GEO, timeout=(15, 120)).json()
    nombres = {c: (n, corto) for c, n, corto, _ in PROVINCIAS}
    feats = []
    for f in g['features']:
        cod = f['properties']['codprov_censo']
        geom = shape(f['geometry']).buffer(0)
        if cod == '02':
            c = geom.centroid
            ins = affinity.scale(geom, INSET_ESCALA, INSET_ESCALA, origin=c)
            ins = affinity.translate(ins, INSET_CENTRO[0] - c.x, INSET_CENTRO[1] - c.y)
            partes = list(geom.geoms) if geom.geom_type == 'MultiPolygon' else [geom]
            partes += list(ins.geoms) if ins.geom_type == 'MultiPolygon' else [ins]
            geom = MultiPolygon(partes)
        n, corto = nombres[cod]
        feats.append({'cod': cod, 'name': n, 'corto': corto, 'geom': geom})
    return feats


def proyectar(lon, lat, lat0=-38.0):
    return lon * math.cos(math.radians(lat0)), lat


def svg(feats):
    allb = [f['geom'].bounds for f in feats]
    minx = min(b[0] for b in allb); maxx = max(b[2] for b in allb)
    miny = min(b[1] for b in allb); maxy = max(b[3] for b in allb)
    x0, _ = proyectar(minx, 0); x1, _ = proyectar(maxx, 0)
    k = W_SVG / (x1 - x0)
    h = round((maxy - miny) * k)

    def pt(lon, lat):
        x, y = proyectar(lon, lat)
        return round((x - x0) * k, 1), round((maxy - y) * k, 1)

    filas = []
    for f in feats:
        g = f['geom'].simplify(TOL_SVG, preserve_topology=True)
        polys = list(g.geoms) if g.geom_type == 'MultiPolygon' else [g]
        d = []
        for p in polys:
            if p.area < 0.002 and f['cod'] != '02':
                continue  # islotes minúsculos
            for ring in [p.exterior] + list(p.interiors):
                cs = [pt(*c) for c in ring.coords]
                d.append('M' + ' '.join('%g %g' % c for c in cs) + 'Z')
        # etiqueta: punto interior de la parte más grande (para la Ciudad, el recuadro)
        mayor = max(polys, key=lambda p: p.area)
        rp = mayor.representative_point()
        lx, ly = pt(rp.x, rp.y)
        filas.append({'id_prov': f['cod'], 'svg_path': ''.join(d), 'label_x': lx, 'label_y': ly})
    return filas, W_SVG, h


def main():
    os.makedirs(OUT, exist_ok=True)
    feats = cargar()
    gj = {'type': 'FeatureCollection', 'features': [
        {'type': 'Feature', 'id': f['name'], 'properties': {'id_prov': f['cod'], 'name': f['name'], 'nombre_corto': f['corto']},
         'geometry': mapping(f['geom'].simplify(0.004, preserve_topology=True))} for f in feats]}
    p_geo = os.path.join(OUT, 'provincias_ar.geojson')
    json.dump(gj, open(p_geo, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    p_topo = os.path.join(OUT, 'provincias_ar.topojson')
    js = ("const fs=require('fs');const t=require('topojson-server');"
          "const g=JSON.parse(fs.readFileSync(process.argv[1],'utf8'));"
          "const o=t.topology({provincias:g},1e5);fs.writeFileSync(process.argv[2],JSON.stringify(o));")
    subprocess.run(['node', '-e', js, p_geo, p_topo], check=True, cwd=os.environ.get('NODE_DIR', '.'))
    filas, w, h = svg(feats)
    import csv
    with open(os.path.join(OUT, 'provincias_svg.csv'), 'w', newline='', encoding='utf-8') as fh:
        wr = csv.DictWriter(fh, fieldnames=['id_prov', 'svg_path', 'label_x', 'label_y'])
        wr.writeheader(); wr.writerows(filas)
    json.dump({'viewBox': [0, 0, w, h]}, open(os.path.join(OUT, 'svg_viewbox.json'), 'w'))
    print('ok', w, h, os.path.getsize(p_geo), os.path.getsize(p_topo), max(len(f['svg_path']) for f in filas))


if __name__ == '__main__':
    main()
