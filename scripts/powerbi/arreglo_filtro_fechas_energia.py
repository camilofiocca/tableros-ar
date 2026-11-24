#!/usr/bin/env python3
"""Transforma el modelo de Energía AR para que el filtro de fechas funcione.

Uso: python3 -I fix_energia.py <carpeta definition origen> <carpeta destino>

- Medidas.tmdl: "último dato" como-de (as-of) a la fecha de fin de la ventana.
- Calendario / series / empresas / cuencas: columna 'Año-Mes'.
- relationships.tmdl: series/empresas/cuencas -> Calendario por 'Año-Mes' (muchos a muchos).
"""
import os
import re
import sys

RM = "REMOVEFILTERS ( Calendario ), REMOVEFILTERS ( Rangos )"
FIN_MEASURE = [
    "\tmeasure 'Fin del período' = CALCULATE ( MAX ( Calendario[Fecha] ), REMOVEFILTERS ( Rangos[Rango] ) )",
    "\t\tformatString: dd/mm/yyyy",
    "\t\tdisplayFolder: Fechas",
    "\t\tlineageTag: 8d3b6f52-1c4e-4a7b-9e20-5f6a7b8c9d01",
    "",
]
PROP = re.compile(r"^\t\t(formatString|displayFolder|lineageTag|dataCategory|description|isHidden|annotation)\b")


def read(p):
    with open(p, encoding="utf-8", newline="") as f:
        return f.read().replace("\r", "")


def write(p, text):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(text.replace("\n", "\r\n"))


def split_args(inner):
    args, depth, cur, q = [], 0, "", False
    for ch in inner:
        if ch == '"':
            q = not q
        if not q:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            elif ch == "," and depth == 0:
                args.append(cur)
                cur = ""
                continue
        cur += ch
    args.append(cur)
    return [a.strip() for a in args]


def rewrite_calls(body):
    out, i, changed, needfin = "", 0, False, False
    tok = "CALCULATE ("
    while True:
        k = body.find(tok, i)
        if k < 0:
            out += body[i:]
            break
        j, depth, q = k + len(tok), 1, False
        while depth:
            c = body[j]
            if c == '"':
                q = not q
            if not q:
                if c == "(":
                    depth += 1
                elif c == ")":
                    depth -= 1
            j += 1
        call = body[k:j]
        inner = call[len(tok):-1]
        args = split_args(inner)
        a0 = args[0]
        neu = call
        has_cal = any("Calendario" in a for a in args)
        has_rm_cal = any(a == "REMOVEFILTERS ( Calendario )" for a in args)
        has_rm_ran = any("Rangos" in a for a in args)
        if has_rm_cal and not has_rm_ran:
            neu = call.replace("REMOVEFILTERS ( Calendario )", RM, 1)
        elif not has_cal:
            m_max = re.fullmatch(r"MAX \( (series|empresas)\[fecha\] \)", a0)
            m_pot = re.fullmatch(r"MAX \( potencia\[anio\] \)", a0)
            m_sum = re.fullmatch(r"SUM \( (series|empresas|potencia)\[\w+\] \)", a0)
            m_msr = re.fullmatch(r"\[[^\]]+\]", a0)
            eq_fecha = any(re.fullmatch(r"(series|empresas)\[fecha\] = \w+", a) for a in args)
            eq_anio = any(re.fullmatch(r"potencia\[anio\] = \w+", a) for a in args)
            head = call[:-1].rstrip()
            if m_max:
                t = m_max.group(1)
                add = ", " + RM
                if not any(a.startswith(t + "[fecha] <=") for a in args):
                    add += ", %s[fecha] <= fin" % t
                    needfin = True
                neu = head + add + " )"
            elif m_pot:
                neu = head + ", " + RM + ", potencia[anio] <= YEAR ( fin ) )"
                needfin = True
            elif (m_sum or m_msr) and (eq_fecha or eq_anio):
                neu = head + ", " + RM + " )"
        if neu != call:
            changed = True
        out += body[i:k] + neu
        i = j
    return out, changed, needfin


def transform_medidas(src, dst):
    L = read(src).split("\n")
    starts = [i for i, l in enumerate(L) if l.startswith("\tmeasure ")]
    last_end = next(i for i in range(starts[-1] + 1, len(L)) if L[i].startswith("\tcolumn "))
    ends = starts[1:] + [last_end]
    res = L[: starts[0]] + FIN_MEASURE
    cambiadas = []
    for s, e in zip(starts, ends):
        blk = L[s:e]
        first = blk[0]
        name = first[len("\tmeasure "):].split(" = ")[0].strip().strip("'")
        pi = next((t for t in range(1, len(blk)) if PROP.match(blk[t])), len(blk))
        expr, props = "\n".join(blk[:pi]), blk[pi:]
        neu, ch, needfin = rewrite_calls(expr)
        if needfin and "VAR fin" not in neu:
            k = neu.index("VAR ")
            pre = neu[:k]
            line_start = pre.rfind("\n") + 1
            ind = re.match(r"[\t ]*", neu[line_start:]).group(0) if "\n" in pre else ""
            sep = ("\n" + ind) if "\n" in pre else " "
            neu = pre + "VAR fin = [Fin del período]" + sep + neu[k:]
        if ch or needfin:
            cambiadas.append(name)
        res += neu.split("\n") + props
    res += L[last_end:]
    write(dst, "\n".join(res))
    return cambiadas


def add_ym_column(src, dst, tabla):
    t = read(src)
    col = (
        "\tcolumn 'Año-Mes' = FORMAT ( %s[fecha], \"yyyy-mm\" )\n"
        "\t\tdataType: string\n\t\tisHidden\n\t\tlineageTag: %s\n\t\tsummarizeBy: none\n\n"
    )
    guid = {
        "series": "5a1c7e92-4b3d-4f60-8a17-2c9d0e6b7f31",
        "empresas": "6b2d8fa3-5c4e-4071-9b28-3dae1f7c8042",
        "cuencas": "7c3e90b4-6d5f-4182-8c39-4ebf2a8d9153",
    }[tabla]
    k = t.index("\tpartition ")
    t = t[:k] + col % (tabla, guid) + t[k:]
    write(dst, t)


def transform_calendario(src, dst):
    t = read(src)
    col = (
        "\tcolumn 'Año-Mes'\n\t\tdataType: string\n"
        "\t\tlineageTag: 9d4fa1c5-7e60-4293-8d4a-5fc03b9ea264\n\t\tsummarizeBy: none\n"
        "\t\tisNameInferred\n\t\tsourceColumn: [Año-Mes]\n\n"
    )
    k = t.index("\tpartition ")
    t = t[:k] + col + t[k:]
    old = '\t\t\t\t    "Año", YEAR ( [Date] )\n'
    assert old in t
    t = t.replace(old, '\t\t\t\t    "Año", YEAR ( [Date] ),\n\t\t\t\t    "Año-Mes", FORMAT ( [Date], "yyyy-mm" )\n')
    write(dst, t)


def transform_relationships(src, dst):
    t = read(src)
    for rid, tabla in (
        ("e2a6ff66-77b1-434a-8034-abdf6be71ec8", "series"),
        ("1f64ae4c-7d96-46c3-863b-58475303977c", "empresas"),
        ("6e4dfabe-eaf7-4e6b-b20f-cefc0e863c6a", "cuencas"),
    ):
        old = "relationship %s\n\tfromColumn: %s.fecha\n\ttoColumn: Calendario.Fecha\n" % (rid, tabla)
        new = (
            "relationship %s\n\tfromCardinality: many\n\ttoCardinality: many\n"
            "\tfromColumn: %s.'Año-Mes'\n\ttoColumn: Calendario.'Año-Mes'\n" % (rid, tabla)
        )
        assert old in t, rid
        t = t.replace(old, new)
    old = "relationship 97c8cabf-d956-481b-a525-ad5967a369fa\n\tfromColumn: potencia.fecha_anio\n\ttoColumn: Calendario.Fecha\n"
    new = (
        "relationship 97c8cabf-d956-481b-a525-ad5967a369fa\n\tfromCardinality: many\n\ttoCardinality: many\n"
        "\tfromColumn: potencia.anio\n\ttoColumn: Calendario.Año\n"
    )
    assert old in t, "potencia"
    t = t.replace(old, new)
    write(dst, t)


def main(src, dst):
    ch = transform_medidas(os.path.join(src, "tables/Medidas.tmdl"), os.path.join(dst, "tables/Medidas.tmdl"))
    for tabla in ("series", "empresas", "cuencas"):
        add_ym_column(os.path.join(src, "tables/%s.tmdl" % tabla), os.path.join(dst, "tables/%s.tmdl" % tabla), tabla)
    transform_calendario(os.path.join(src, "tables/Calendario.tmdl"), os.path.join(dst, "tables/Calendario.tmdl"))
    transform_relationships(os.path.join(src, "relationships.tmdl"), os.path.join(dst, "relationships.tmdl"))
    print("medidas modificadas: %d" % len(ch))
    for n in ch:
        print(" -", n)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
