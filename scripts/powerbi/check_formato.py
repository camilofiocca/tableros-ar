# -*- coding: utf-8 -*-
"""Controla que los objetos/propiedades de formato de cada visual existan en el esquema de temas de Power BI.
Uso: python check_formato.py <carpeta .Report> <reportThemeSchema.json>"""
import json, glob, os, sys, collections
rep, sch = sys.argv[1], sys.argv[2]
t = json.load(open(sch)); D = t['definitions']
def res(o): return D[o['$ref'].split('/')[-1]] if isinstance(o, dict) and '$ref' in o else o
cache = {}
def permitidos(vt):
    if vt in cache: return cache[vt]
    k = 'visual-' + vt
    if k not in D: cache[vt] = None; return None
    v = res(D[k]); props = dict(v.get('properties') or {})
    for a in v.get('allOf', []): props.update(res(a).get('properties', {}))
    out = {}
    for ob, p in props.items():
        it = res(res(p).get('items', {})); sub = dict(it.get('properties', {}))
        for a in it.get('allOf', []): sub.update(res(a).get('properties', {}))
        out[ob] = set(sub)
    cache[vt] = out; return out
probl = collections.Counter(); n = 0
for f in glob.glob(os.path.join(rep, 'definition', 'pages', '*', 'visuals', '*', 'visual.json')):
    d = json.load(open(f, encoding='utf-8-sig')); v = d['visual']; vt = v['visualType']; n += 1
    ok = permitidos(vt)
    if ok is None: probl[('tipo desconocido', vt)] += 1; continue
    for grupo in ('objects', 'visualContainerObjects'):
        for ob, entradas in (v.get(grupo) or {}).items():
            if ob not in ok: probl[(vt, grupo, ob, '(objeto)')] += 1; continue
            for e in entradas:
                for prop in e.get('properties', {}):
                    if prop not in ok[ob]: probl[(vt, grupo, ob, prop)] += 1
print('visuales revisados:', n)
for k, c in sorted(probl.items()): print('  ✗', k, c)
print('sin problemas' if not probl else '%d tipos de problema' % len(probl))
