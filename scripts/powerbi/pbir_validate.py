# -*- coding: utf-8 -*-
"""Valida los JSON de un proyecto PBIP contra los esquemas oficiales de Microsoft (copia local de microsoft/json-schemas).

Uso: python scripts/powerbi/pbir_validate.py <carpeta del proyecto> [carpeta de json-schemas]
"""
import json, glob, os, sys, warnings, collections
warnings.filterwarnings('ignore')
from jsonschema import Draft7Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT7

ROOT = (sys.argv[2] if len(sys.argv) > 2 else '/home/claude/schemas/json-schemas').rstrip('/') + '/'
PREFIX = 'https://developer.microsoft.com/json-schemas/'


def _path(url):
    p = ROOT + url[len(PREFIX):]
    if not os.path.exists(p):
        for a, b in (('schema.embedded.json', 'schema-embedded.json'), ('schema-embedded.json', 'schema.embedded.json')):
            if os.path.exists(p.replace(a, b)):
                return p.replace(a, b)
    return p


def _retrieve(url):
    d = json.load(open(_path(url), encoding='utf-8-sig'))
    d.pop('$id', None)
    return Resource(contents=d, specification=DRAFT7)


REG = Registry(retrieve=_retrieve)
_cache = {}


def validator_for(url):
    if url not in _cache:
        _cache[url] = Draft7Validator({'$ref': url}, registry=REG) if os.path.exists(_path(url)) else None
    return _cache[url]


def validate_tree(base, verbose=True):
    res = collections.Counter(); bad = []
    for f in sorted(glob.glob(os.path.join(base, '**/*.json'), recursive=True) + glob.glob(os.path.join(base, '**/*.pbi*'), recursive=True)):
        try:
            d = json.load(open(f, encoding='utf-8-sig'))
        except Exception as e:
            bad.append((f, 'JSON: %s' % e)); res['BADJSON'] += 1; continue
        sc = d.get('$schema') if isinstance(d, dict) else None
        if not sc:
            res['sin $schema'] += 1; continue
        v = validator_for(sc)
        if v is None:
            res['esquema no disponible ' + sc.split('/json-schemas/')[1]] += 1; continue
        errs = sorted(v.iter_errors(d), key=lambda e: len(e.path))
        res['ok' if not errs else 'ERR'] += 1
        for e in errs[:3]:
            bad.append((f[len(base):], '/'.join(map(str, e.absolute_path))[:90] + ' :: ' + e.message[:240]))
    if verbose:
        for b in bad:
            print(' !!', b[0], '\n   ', b[1])
        print(dict(res))
    return res, bad


if __name__ == '__main__':
    validate_tree(sys.argv[1])
