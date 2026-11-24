# -*- coding: utf-8 -*-
"""Convierte scripts/etl/elecciones_etl_fuente.py (celdas marcadas con '# %%') en el notebook del repo.
Uso: python scripts/etl/elecciones_a_notebook.py"""
import os, re, nbformat
AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(AQUI, '..', '..'))
src = open(os.path.join(AQUI, 'elecciones_etl_fuente.py'), encoding='utf-8').read()
partes = re.split(r'^# %%(.*)$', src, flags=re.M)
nb = nbformat.v4.new_notebook()
for i in range(1, len(partes), 2):
    marca, cuerpo = partes[i], partes[i + 1].strip('\n')
    if '[markdown]' in marca:
        md = '\n'.join(l[2:] if l.startswith('# ') else l.lstrip('#') for l in cuerpo.split('\n'))
        nb.cells.append(nbformat.v4.new_markdown_cell(md.strip()))
    else:
        nb.cells.append(nbformat.v4.new_code_cell(cuerpo))
nb.metadata = {'colab': {'provenance': [], 'name': 'Tablero Elecciones AR - ETL v1.ipynb'},
               'kernelspec': {'name': 'python3', 'display_name': 'Python 3'}, 'language_info': {'name': 'python'}}
nbformat.validate(nb)
nbformat.write(nb, os.path.join(REPO, 'notebooks', 'Tablero Elecciones AR - ETL v1.ipynb'))
print(len(nb.cells), 'celdas')
