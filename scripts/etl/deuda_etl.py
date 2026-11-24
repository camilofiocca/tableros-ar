"""ETL de la deuda bruta de la Administración Central (Secretaría de Finanzas).

Lee el Excel mensual (hojas A.1, A.2, A.3 y A.5) y devuelve una tabla larga con las columnas
fecha, id, grupo, serie, valor (millones de U$S, fin de mes) y orden.

Definiciones:
- Interna / externa: dos cortes. Por legislación (A.2: argentina / extranjera) y por moneda
  (A.3: moneda local / moneda extranjera).
- Con intereses / sin intereses: Tasa fija + Tasa variable contra Tasa cero (A.3). La deuda a tasa cero
  son instrumentos que no pagan cupón (Letras, LECAP, BONCER, etc.). Los ajustables por CER igual se
  actualizan por inflación.
- Pagos (A.5): capital e intereses pagados en el mes, por moneda de pago.
"""
import datetime as dt
import re

import openpyxl

MESES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
         "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12}


def _fecha(x):
    if isinstance(x, dt.datetime):
        return dt.date(x.year, x.month, 1)
    if isinstance(x, dt.date):
        return dt.date(x.year, x.month, 1)
    if isinstance(x, str):
        m = re.match(r"\s*([a-záéíóú]{3})[a-z]*[-/ ](\d{2,4})", x.strip().lower())
        if m and m.group(1) in MESES:
            y = int(m.group(2))
            y += 2000 if y < 100 else 0
            return dt.date(y, MESES[m.group(1)], 1)
    return None


def _hoja(wb, nombre, fila_hdr_hint=None):
    """Devuelve (filas, {col: fecha}, lista de bloques de encabezado)."""
    filas = [list(r) for r in wb[nombre].iter_rows(values_only=True)]
    bloques = []
    for i, r in enumerate(filas):
        cols = {j: _fecha(c) for j, c in enumerate(r) if _fecha(c)}
        if len(cols) >= 20:
            bloques.append((i, cols))
    return filas, bloques


def _etiqueta(r):
    for x in r[:3]:
        if isinstance(x, str) and x.strip():
            return x.strip()
    return ""


def _etiquetas(r):
    return [x.strip() for x in r[:3] if isinstance(x, str) and x.strip()]


def _fila(filas, idx, cols):
    r = filas[idx]
    out = {}
    for j, f in cols.items():
        v = r[j] if j < len(r) else None
        if isinstance(v, (int, float)):
            out[f] = float(v)
    return out


def _suma(*series):
    fechas = set().union(*[set(s) for s in series])
    return {f: sum(s.get(f, 0.0) for s in series) for f in fechas}


def _resta(a, *bs):
    return {f: a[f] - sum(b.get(f, 0.0) for b in bs) for f in a}


def construir(ruta_xlsx):
    wb = openpyxl.load_workbook(ruta_xlsx, data_only=True, read_only=True)
    filas = []

    def agregar(id_, grupo, nombre, orden, serie):
        for f, v in sorted(serie.items()):
            filas.append({"fecha": f.isoformat(), "id": id_, "grupo": grupo, "serie": nombre,
                          "valor": round(v, 3), "orden": orden})

    # ---- A.1: total e instrumentos -------------------------------------------------------
    f1, b1 = _hoja(wb, "A.1")
    c1 = b1[0][1]

    def fila_por_etiqueta(filas_, cols, etiqueta, desde=0, hasta=None, exacta=True):
        for i in range(desde, hasta or len(filas_)):
            es = _etiquetas(filas_[i])
            if any((e == etiqueta) if exacta else e.startswith(etiqueta) for e in es):
                return _fila(filas_, i, cols)
        raise KeyError(etiqueta)

    total = fila_por_etiqueta(f1, c1, "A- DEUDA BRUTA ( I + II  + III)", exacta=False)
    normal = fila_por_etiqueta(f1, c1, "I- DEUDA EN SITUACIÓN DE PAGO NORMAL")
    titulos = fila_por_etiqueta(f1, c1, "TÍTULOS PÚBLICOS")
    # Letras del Tesoro: mediano y largo plazo + corto plazo
    idx_letras = [i for i, r in enumerate(f1) if _etiqueta(r) == "LETRAS DEL TESORO"]
    letras = _suma(*[_fila(f1, i, c1) for i in idx_letras[:2]])
    org_int = fila_por_etiqueta(f1, c1, "ORGANISMOS INTERNACIONALES")
    fmi = fila_por_etiqueta(f1, c1, "FMI")
    org_sin_fmi = _resta(org_int, fmi)
    otros = _resta(normal, titulos, letras, org_int)

    g = "Total"
    agregar("deuda_total", g, "Deuda bruta total", 1, total)
    agregar("deuda_pago_normal", g, "Deuda en situación de pago normal", 2, normal)
    g = "Instrumento o acreedor"
    agregar("inst_titulos", g, "Títulos públicos", 1, titulos)
    agregar("inst_letras", g, "Letras del Tesoro", 2, letras)
    agregar("inst_org_sin_fmi", g, "Organismos internacionales (sin FMI)", 3, org_sin_fmi)
    agregar("inst_fmi", g, "FMI", 4, fmi)
    agregar("inst_otros", g, "Otros préstamos, adelantos BCRA y avales", 5, otros)

    # ---- A.2: legislación -------------------------------------------------------------------
    f2, b2 = _hoja(wb, "A.2")
    c2 = b2[0][1]
    leg_arg = fila_por_etiqueta(f2, c2, "I- LEGISLACIÓN ARGENTINA")
    leg_ext = fila_por_etiqueta(f2, c2, "II- LEGISLACIÓN EXTRANJERA")
    g = "Legislación"
    agregar("leg_arg", g, "Legislación argentina (interna)", 1, leg_arg)
    agregar("leg_ext", g, "Legislación extranjera (externa)", 2, leg_ext)

    # ---- A.3: moneda y tasa (deuda en situación de pago normal) ------------------------------
    f3, b3 = _hoja(wb, "A.3")
    c3 = b3[0][1]
    ini = b3[0][0]

    def bloque(desde_etq, hasta_etq):
        i0 = next(i for i in range(ini, len(f3)) if _etiqueta(f3[i]).startswith(desde_etq))
        i1 = next(i for i in range(i0 + 1, len(f3)) if _etiqueta(f3[i]).startswith(hasta_etq))
        return i0, i1

    i_loc, i_ext = bloque("Moneda local", "Moneda extranjera")
    i_fin = next(i for i in range(i_ext + 1, len(f3)) if _etiqueta(f3[i]).startswith("COMPOSICIÓN POR MONEDA"))

    def tasas(i0, i1):
        """Dentro de [i0, i1) suma las filas 'Tasa ...' por tipo (fija, cero, variable)."""
        res = {"fija": {}, "cero": {}, "variable": {}}
        for i in range(i0, i1):
            e = _etiqueta(f3[i]).lower()
            for k in res:
                if e == "tasa " + k:
                    res[k] = _suma(res[k], _fila(f3, i, c3)) if res[k] else _fila(f3, i, c3)
        return res

    loc = tasas(i_loc, i_ext)
    ext = tasas(i_ext, i_fin)
    loc_con = _suma(loc["fija"], loc["variable"])
    loc_sin = loc["cero"]
    ext_con = _suma(ext["fija"], ext["variable"])
    ext_sin = ext["cero"]
    g = "Moneda y tasa"
    agregar("mt_loc_con", g, "Moneda local, con intereses (tasa fija o variable)", 1, loc_con)
    agregar("mt_loc_sin", g, "Moneda local, sin intereses (tasa cero)", 2, loc_sin)
    agregar("mt_ext_con", g, "Moneda extranjera, con intereses (tasa fija o variable)", 3, ext_con)
    agregar("mt_ext_sin", g, "Moneda extranjera, sin intereses (tasa cero)", 4, ext_sin)

    # control: las cuatro partes deben sumar la deuda en pago normal
    for f, v in normal.items():
        s = loc_con.get(f, 0) + loc_sin.get(f, 0) + ext_con.get(f, 0) + ext_sin.get(f, 0)
        assert abs(s - v) < 5, ("A.3 no cierra", f, s, v)

    # ---- A.5: pagos de capital e intereses por moneda de pago -----------------------------
    f5, b5 = _hoja(wb, "A.5")
    c5 = b5[0][1]
    i_mn = next(i for i, r in enumerate(f5) if _etiqueta(r).startswith("- MONEDA NACIONAL"))
    i_me = next(i for i, r in enumerate(f5) if _etiqueta(r).startswith("- MONEDA EXTRANJERA"))

    def pago(i0, nombre):
        for i in range(i0 + 1, i0 + 6):
            if _etiqueta(f5[i]) == nombre:
                return _fila(f5, i, c5)
        raise KeyError(nombre)

    g = "Pagos del mes"
    agregar("pago_mn_capital", g, "Capital en moneda nacional", 1, pago(i_mn, "CAPITAL"))
    agregar("pago_mn_interes", g, "Intereses en moneda nacional", 2, pago(i_mn, "INTERES"))
    agregar("pago_me_capital", g, "Capital en moneda extranjera", 3, pago(i_me, "CAPITAL"))
    agregar("pago_me_interes", g, "Intereses en moneda extranjera", 4, pago(i_me, "INTERES"))

    return filas


if __name__ == "__main__":
    import csv
    import sys

    datos = construir(sys.argv[1])
    with open(sys.argv[2], "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["fecha", "id", "grupo", "serie", "valor", "orden"])
        w.writeheader()
        w.writerows(datos)
    print(len(datos), "filas")
