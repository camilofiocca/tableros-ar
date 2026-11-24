# %% [markdown]
# # 🗳️ Elecciones Argentina — ETL (v1)
#
# **Qué hace:** arma los datos del *Tablero Elecciones AR* — presidenciales (primera vuelta, balotaje y PASO) y
# diputados nacionales, con foco en las **elecciones intermedias** — por provincia, de 1983 a 2025, y los escribe
# en la planilla **"Elecciones AR - Datos limpios"**, que lee Power BI.
#
# **Fuentes:** escrutinio definitivo del Atlas Electoral de Andy Tow (vía PolAr) para las presidenciales
# 1983-2019; Cámara Nacional Electoral para 2023; Dirección Nacional Electoral (escrutinio provisorio) para
# diputados 2011-2025 y PASO, y bases académicas para diputados 1983-2009 (compiladas en el repositorio 257arg).
# El detalle y los controles están en `data/elecciones/` y `docs/elecciones.md` del repo.
#
# **Cómo corre:** en GitHub Actions (cuenta de servicio, automático) o en Colab (pide permiso de Google).
# Los resultados históricos no cambian: la base (`data/elecciones/base_*.csv`) se rehace solo cuando hay una
# elección nueva, con `scripts/etl/elecciones_base.py`. Este notebook clasifica, calcula y publica.

# %%
# =============================================================
# 1) CONFIGURACIÓN
# =============================================================
import io, os, re, json, unicodedata
import numpy as np, pandas as pd, requests

SPREADSHEET_ID = os.environ.get("ELECCIONES_SHEET_ID", "1gD1noYKGiWRA_XywAkbpqzelKTGvAwEzuoikLlu1KE8")   # "Elecciones AR - Datos limpios"
REPO_RAW = "https://raw.githubusercontent.com/camilofiocca/tableros-ar/main/"
AUTO = bool(os.environ.get("GITHUB_ACTIONS"))      # True cuando corre en GitHub Actions
VERIFICAR_DINE = True                              # comparar los últimos resultados con la API de la DINE (no frena nada)
SOLO_LOCAL = bool(os.environ.get("ELECCIONES_SOLO_LOCAL"))  # para pruebas: escribe CSV en vez de la planilla

errores = []  # (paso, mensaje) -> hoja "info"

def ruta_repo():
    """Carpeta raíz del repo si el notebook corre dentro de él (GitHub Actions o local)."""
    for base in (os.getcwd(), os.path.dirname(os.getcwd())):
        if os.path.exists(os.path.join(base, "data", "elecciones", "base_listas.csv")):
            return base
    return None

RAIZ = ruta_repo()

def leer_csv(rel, **kw):
    """Lee un CSV del repo: del disco si está, si no desde GitHub (Colab)."""
    if RAIZ:
        return pd.read_csv(os.path.join(RAIZ, rel), **kw)
    r = requests.get(REPO_RAW + rel, timeout=(15, 120)); r.raise_for_status()
    return pd.read_csv(io.BytesIO(r.content), **kw)

def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()

def fmt(x, d=1):
    return "s/d" if x is None or pd.isna(x) else f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")

print("Configuración lista · repo local:", RAIZ or "no (se lee de GitHub)")

# %% [markdown]
# ## Carga de la base

# %%
# =============================================================
# 2) CARGA
# =============================================================
S = {"dtype": {"id_prov": str}}
listas = leer_csv("data/elecciones/base_listas.csv", **S)
totales = leer_csv("data/elecciones/base_totales.csv", **S)
elecciones = leer_csv("data/elecciones/elecciones.csv")
provincias = leer_csv("data/elecciones/provincias.csv", **S)
espacios = leer_csv("data/elecciones/espacios.csv")
reglas = leer_csv("data/elecciones/reglas_espacios.csv").sort_values("orden")
svg = leer_csv("data/elecciones/mapa/provincias_svg.csv", **S)
# tonos de cada espacio para el mapa de intensidad (de casi blanco al color pleno)
def mezclar(hexc, t):
    r, g, b = (int(hexc[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02X%02X%02X" % tuple(round(255 + (c - 255) * t) for c in (r, g, b))
for i, t in enumerate((0.15, 0.35, 0.55, 0.78, 1.0), start=1):
    espacios[f"tono{i}"] = espacios.color.map(lambda c: mezclar(c, t))
print(f"listas: {len(listas):,} · totales: {len(totales)} · elecciones: {len(elecciones)} · reglas: {len(reglas)}")

# %% [markdown]
# ## Clasificación: fórmula presidencial y espacio político
# Cada lista se asigna con la primera regla de `reglas_espacios.csv` que coincide (por nombre de la lista o por el
# bloque que trae la fuente). En las presidenciales, las reglas `PRES` la asignan además a una fórmula.

# %%
# =============================================================
# 3) CLASIFICACIÓN
# =============================================================
reglas["rx"] = reglas.patron.map(re.compile)
listas["anio"] = listas.id_eleccion.str[:4].astype(int)
listas["es_pres"] = listas.id_eleccion.str.contains("PRES")
listas["es_paso"] = listas.id_eleccion.str.endswith("PASO")
listas["textos"] = listas.fuerza.map(norm) + " || " + listas.bloque_fuente.fillna("").map(norm)

def clasificar(anio, es_pres, es_paso, textos):
    partes = [t for t in textos.split(" || ") if t]
    for q in reglas.itertuples():
        if not (q.desde <= anio <= q.hasta):
            continue
        if (q.ambito == "PRES" and not es_pres) or (q.ambito == "DIP" and es_pres):
            continue
        if any(q.rx.search(t) for t in partes):
            if q.ambito == "PRES":
                # en las PASO la "fórmula" es el frente (puede tener varias listas internas)
                nota = q.nota if isinstance(q.nota, str) and q.nota else q.formula
                return (nota if es_paso else q.formula), q.id_espacio, int(q.orden)
            return ("Otras fórmulas" if es_pres else None), q.id_espacio, int(q.orden)
    return ("Otras fórmulas" if es_pres else None), "OTR", None

claves = listas[["anio", "es_pres", "es_paso", "textos"]].drop_duplicates()
claves[["formula", "id_espacio", "regla"]] = [clasificar(*k) for k in claves.itertuples(index=False)]
listas = listas.merge(claves, on=["anio", "es_pres", "es_paso", "textos"], how="left")

# Nombre presentable de cada lista de diputados
CODIGOS = {"pj": "Partido Justicialista", "ucr": "Unión Cívica Radical", "ali": "Alianza (UCR-FREPASO)",
           "acjc": "Concertación Justicialista para el Cambio", "cjc": "Concertación Justicialista para el Cambio",
           "afpaso": "Alianza FREPASO", "fpaso": "FREPASO", "ucd": "UCeDé", "apr": "Acción por la República",
           "aapr": "Alianza Acción por la República", "mod": "MODIN", "po": "Partido Obrero", "mas": "MAS",
           "mst": "MST", "aiu": "Izquierda Unida", "ph": "Partido Humanista", "mpn": "Movimiento Popular Neuquino",
           "fr": "Fuerza Republicana", "prs": "Partido Renovador de Salta", "blo": "Partido Bloquista",
           "afjufe": "Frente Justicialista Federal", "afjbo": "Frente Justicialista Bonaerense",
           "pd": "Partido Demócrata", "fg": "Frente Grande", "psa": "Partido Socialista Auténtico",
           "pdp": "Partido Demócrata Progresista", "acha": "Acción Chaqueña", "ach": "Acción Chubutense",
           "mpf": "Movimiento Popular Fueguino", "mpj": "Movimiento Popular Jujeño", "fpanu": "Partido Nuevo",
           "palpdp": "Pacto Autonomista Liberal - PDP", "palucd": "Pacto Autonomista Liberal - UCeDé",
           "aaprnd": "Acción por la República - Nueva Dirigencia", "pts": "PTS", "aiumst": "Izquierda Unida - MST",
           "aciu": "Izquierda Unida", "afj": "Frente Justicialista", "fj": "Frente Justicialista", "mid": "MID",
           "adp": "Alianza (UCR-FREPASO) Santa Fe", "aftod": "Frente de Todos (Chaco)", "fpv": "Frente para la Victoria (Formosa)",
           "frejupo": "FREJUPO", "afjupo": "Frente Justicialista Popular", "apj": "Alianza Justicialista",
           "cjcer": "Concertación Justicialista (Entre Ríos)", "cjccha": "Concertación Justicialista (Chaco)",
           "cjccat": "Concertación Justicialista (Catamarca)", "afjen": "Frente Justicialista Entrerriano",
           "alisal": "Alianza (Salta)", "alisj": "Alianza (San Juan)", "ucd19": "UCeDé", "pc": "Partido Comunista",
           "cpl": "Corriente Patria Libre", "asur": "Alianza Sur", "fed": "Partido Federal", "pheco": "Partido Humanista"}
MINUS = {"de", "del", "la", "las", "los", "y", "e", "para", "por", "el", "en", "a", "con", "al"}

def presentable(nombre):
    s = str(nombre).strip()
    if s.startswith("cod:"):
        c = s[4:]
        return CODIGOS.get(c, f"Lista '{c}' (base de Calvo)")
    if s.isupper() or s.islower():
        pal = s.lower().split()
        s = " ".join(p if (i and p in MINUS) else (p.upper() if len(p) <= 3 and p.isalpha() and p not in MINUS and p in ("ucr", "pro", "pj", "fit", "mst", "mas", "ari", "frc", "mpn", "una") else p.capitalize())
                     for i, p in enumerate(pal))
    return re.sub(r"\s+", " ", s)

listas["opcion"] = np.where(listas.es_pres, listas.formula, listas.fuerza.map(presentable))
sin_clasificar = listas.groupby("id_eleccion").apply(lambda g: g.loc[g.id_espacio == "OTR", "votos"].sum() / g.votos.sum() * 100)
print("Voto en 'Otros' por elección (%):\n", sin_clasificar.round(1).to_string())

# %% [markdown]
# ## Cálculos: resultados, ganadores, márgenes, participación y comparación con la elección anterior

# %%
# =============================================================
# 4) CÁLCULOS
# =============================================================
el = elecciones.copy()
el["fecha"] = pd.to_datetime(el.fecha)
el["es_intermedia"] = el.tipo.eq("Legislativa")
inst_orden = {"PASO": 1, "Primera vuelta": 2, "General": 3, "Balotaje": 4}
el["orden"] = (el.fecha.rank(method="dense").astype(int) * 10 + el.instancia.map(inst_orden)).rank(method="dense").astype(int)
el["categoria"] = np.select([el.cargo.eq("Presidente") & el.instancia.eq("Primera vuelta"),
                             el.cargo.eq("Presidente") & el.instancia.eq("Balotaje"),
                             el.cargo.eq("Presidente") & el.instancia.eq("PASO"),
                             el.es_intermedia], ["Presidente 1ra vuelta", "Presidente balotaje", "Presidente PASO",
                                                 "Diputados (intermedia)"], "Diputados (año presidencial)")
el["etiqueta"] = el.anio.astype(str) + " · " + el.categoria
# etiqueta corta única (Power BI la ordena por "orden"): intermedias = solo el año
el["etiqueta_corta"] = el.anio.astype(str) + np.select(
    [el.instancia.eq("Balotaje"), el.instancia.eq("PASO"), el.cargo.eq("Presidente"), ~el.es_intermedia],
    [" bal.", " PASO", " pres.", " dip."], "")
assert el.etiqueta_corta.is_unique and el.etiqueta.is_unique
el = el.sort_values("orden")
# elección comparable anterior (misma categoría)
el["anterior"] = el.groupby("categoria").id_eleccion.shift(1)
# en diputados conviene comparar intermedia con intermedia y también contra la elección de diputados anterior
dip = el[el.cargo.eq("Diputados nacionales")]
el["anterior_dip"] = el.id_eleccion.map(dict(zip(dip.id_eleccion, dip.id_eleccion.shift(1))))

# --- resultados por provincia y opción (fórmula o lista) ---
res = (listas.groupby(["id_eleccion", "id_prov", "opcion"], dropna=False)
       .apply(lambda g: pd.Series({"votos": g.votos.sum(),
                                   "id_espacio": g.loc[g.votos.idxmax(), "id_espacio"],
                                   "listas": "; ".join(sorted(set(g.fuerza.map(presentable))))[:240]}))
       .reset_index())
res["positivos_prov"] = res.groupby(["id_eleccion", "id_prov"]).votos.transform("sum")
res["pct"] = res.votos / res.positivos_prov * 100
res["posicion"] = res.groupby(["id_eleccion", "id_prov"]).votos.rank(ascending=False, method="first").astype(int)
res = res.drop(columns="positivos_prov").sort_values(["id_eleccion", "id_prov", "posicion"])

# --- resultados nacionales: por opción y por espacio ---
nac_op = res.groupby(["id_eleccion", "opcion"]).agg(votos=("votos", "sum")).reset_index()
nac_op = nac_op.merge(res.groupby(["id_eleccion", "opcion"]).apply(lambda g: g.groupby("id_espacio").votos.sum().idxmax()).rename("id_espacio").reset_index(), on=["id_eleccion", "opcion"])
nac_op["nivel"] = "opcion"
nac_es = res.groupby(["id_eleccion", "id_espacio"]).votos.sum().reset_index()
nac_es["opcion"] = nac_es.id_espacio.map(dict(zip(espacios.id_espacio, espacios.espacio)))
nac_es["nivel"] = "espacio"
nacional = pd.concat([nac_op, nac_es], ignore_index=True)
nacional["pct"] = nacional.votos / nacional.groupby(["id_eleccion", "nivel"]).votos.transform("sum") * 100
nacional["posicion"] = nacional.groupby(["id_eleccion", "nivel"]).votos.rank(ascending=False, method="first").astype(int)
# en diputados, las listas sueltas no tienen sentido a nivel nacional: se dejan solo los espacios
nacional = nacional[~((nacional.nivel == "opcion") & ~nacional.id_eleccion.str.contains("PRES"))]
# variación contra la elección comparable anterior (puntos porcentuales)
prev = nacional[nacional.nivel == "espacio"][["id_eleccion", "id_espacio", "pct"]]
ant = el.set_index("id_eleccion").anterior
x = nacional[nacional.nivel == "espacio"].assign(anterior=lambda d: d.id_eleccion.map(ant))
x = x.merge(prev.rename(columns={"id_eleccion": "anterior", "pct": "pct_anterior"}), on=["anterior", "id_espacio"], how="left")
nacional = nacional.merge(x[["id_eleccion", "id_espacio", "pct_anterior"]], on=["id_eleccion", "id_espacio"], how="left")
nacional.loc[nacional.nivel != "espacio", "pct_anterior"] = np.nan
nacional["var_pp"] = nacional.pct - nacional.pct_anterior
nacional = nacional.sort_values(["id_eleccion", "nivel", "posicion"])

# --- provincia × elección: participación, ganador, margen, fragmentación ---
pos = res.groupby(["id_eleccion", "id_prov"]).votos.sum().rename("positivos")
nep = res.groupby(["id_eleccion", "id_prov"]).pct.apply(lambda p: 1 / ((p / 100) ** 2).sum()).rename("nep")
g1 = res[res.posicion == 1].set_index(["id_eleccion", "id_prov"])[["opcion", "id_espacio", "pct", "votos"]]
g1.columns = ["ganador", "ganador_espacio", "ganador_pct", "ganador_votos"]
g2 = res[res.posicion == 2].set_index(["id_eleccion", "id_prov"])[["opcion", "id_espacio", "pct"]]
g2.columns = ["segundo", "segundo_espacio", "segundo_pct"]
pe = totales.set_index(["id_eleccion", "id_prov"])[["electores", "votantes"]].join(pos, how="outer").join(nep).join(g1).join(g2).reset_index()
pe["segundo_pct"] = pe.segundo_pct.fillna(0)
pe["margen_pp"] = pe.ganador_pct - pe.segundo_pct
pe["votantes"] = pe.votantes.where(pe.votantes >= pe.positivos, np.nan)
pe["blancos_nulos"] = pe.votantes - pe.positivos
pe["blancos_nulos_pct"] = pe.blancos_nulos / pe.votantes * 100
pe["participacion"] = pe.votantes / pe.electores * 100
# electores faltantes o inconsistentes en la fuente (p. ej. Buenos Aires 1987): sin participación
malos = ~pe.participacion.between(35, 100)
pe.loc[malos, "participacion"] = np.nan
pe["peso_padron"] = pe.electores / pe.groupby("id_eleccion").electores.transform("sum") * 100
# ¿cambió el espacio ganador respecto de la elección comparable anterior?
ga = pe[["id_eleccion", "id_prov", "ganador_espacio"]].rename(columns={"id_eleccion": "anterior", "ganador_espacio": "ganador_espacio_anterior"})
pe["anterior"] = pe.id_eleccion.map(ant)
pe = pe.merge(ga, on=["anterior", "id_prov"], how="left")
pe["cambio_ganador"] = np.where(pe.ganador_espacio_anterior.isna(), "", np.where(pe.ganador_espacio == pe.ganador_espacio_anterior, "Repite", "Cambia"))
pe = pe.drop(columns="anterior")

# --- datos nacionales en la tabla de elecciones ---
tn = pe.groupby("id_eleccion").agg(provincias=("id_prov", "nunique"), positivos=("positivos", "sum"),
                                   votantes=("votantes", "sum"), electores=("electores", "sum"),
                                   electores_ok=("participacion", lambda s: s.notna().all()))
tn["participacion"] = np.where(tn.electores_ok, tn.votantes / tn.electores * 100, np.nan)
ganan = pe.groupby(["id_eleccion", "ganador_espacio"]).size().rename("prov_ganadas").reset_index()
top = nacional[nacional.posicion.le(2) & ((nacional.nivel == "opcion") | ~nacional.id_eleccion.str.contains("PRES"))]
t1 = top[top.posicion == 1].set_index("id_eleccion")[["opcion", "id_espacio", "pct"]].rename(columns={"opcion": "ganador", "id_espacio": "ganador_espacio", "pct": "ganador_pct"})
t2 = top[top.posicion == 2].set_index("id_eleccion")[["opcion", "id_espacio", "pct"]].rename(columns={"opcion": "segundo", "id_espacio": "segundo_espacio", "pct": "segundo_pct"})
el = el.set_index("id_eleccion").join(tn.drop(columns="electores_ok")).join(t1).join(t2).reset_index()
el["margen_pp"] = el.ganador_pct - el.segundo_pct
el = el.merge(ganan.rename(columns={"ganador_espacio": "ganador_espacio_g"}), left_on=["id_eleccion", "ganador_espacio"], right_on=["id_eleccion", "ganador_espacio_g"], how="left").drop(columns="ganador_espacio_g")
el["prov_ganadas"] = el.prov_ganadas.fillna(0).astype(int)
el["sin_clasificar_pct"] = el.id_eleccion.map(sin_clasificar)
FUENTE = {"PolAr": "Andy Tow / PolAr (definitivo)", "CNE": "CNE (definitivo)", "DINE": "DINE (provisorio)"}
el["recuento"] = np.where(el.cargo.eq("Presidente") & ~el.instancia.eq("PASO"), "Definitivo", "Provisorio")
el.loc[el.id_eleccion.eq("2015-PRES-BAL"), "recuento"] = "Definitivo (Tucumán: provisorio)"
el["fuente"] = np.select([el.cargo.eq("Presidente") & el.anio.lt(2023) & ~el.instancia.eq("PASO"),
                          el.cargo.eq("Presidente") & el.anio.eq(2023) & ~el.instancia.eq("PASO"),
                          el.anio.ge(2011)],
                         ["Atlas Electoral de Andy Tow (vía PolAr)", "Cámara Nacional Electoral",
                          "Dirección Nacional Electoral"],
                         np.where(el.anio.between(2003, 2009), "PolAr / Andy Tow", "Base de Ernesto Calvo"))
NOTAS = {
    "1983-PRES-1V": "Elección indirecta (colegio electoral): se muestran los votos populares de cada lista de electores.",
    "1989-PRES-1V": "Elección indirecta (colegio electoral). Algunas listas provinciales que apoyaron a Menem no se le atribuyen: su total queda ~0,7 pp debajo del oficial (47,5%).",
    "1995-PRES-1V": "Primera elección directa. Las listas provinciales aliadas que no se pueden atribuir con certeza quedan en 'Otras fórmulas': Menem suma 47,0% contra 49,9% oficial.",
    "1997-DIP": "Base de Calvo sin corregir; faltan San Luis y algunas listas sin nombre (9% en 'Otros').",
    "1999-DIP": "Base de Calvo sin corregir; faltan San Luis y Santa Cruz.",
    "2003-DIP": "Las provincias votaron en fechas distintas; falta La Pampa. Un 20% de los votos son listas provinciales que no se pueden atribuir a un espacio con certeza.",
    "1987-DIP": "Falta Tierra del Fuego (era territorio nacional).",
}
el["nota"] = el.id_eleccion.map(NOTAS).fillna("")
FALTA_2001 = "No hay datos por provincia de las legislativas de 2001 en las fuentes usadas."

# --- provincias: geometría SVG y peso en el padrón de la última elección ---
ult_id = el[el.provincias.eq(24)].sort_values("orden").id_eleccion.iloc[-1]
prov = provincias.merge(svg, on="id_prov", how="left").merge(
    pe[pe.id_eleccion == ult_id][["id_prov", "electores", "peso_padron"]].rename(columns={"electores": "electores_ultimo"}), on="id_prov", how="left")
prov["orden"] = range(1, len(prov) + 1)
prov["provincia_mapa"] = prov.provincia   # clave que usa el mapa de formas (propiedad "name" del TopoJSON)

print(el[["id_eleccion", "ganador", "ganador_pct", "segundo", "segundo_pct", "participacion", "prov_ganadas"]].tail(8).round(1).to_string(index=False))

# %% [markdown]
# ## KPIs y lectura automática

# %%
# =============================================================
# 5) KPIs Y TEXTOS
# =============================================================
NOMBRE_ESP = dict(zip(espacios.id_espacio, espacios.espacio_corto))
NOMBRE_PROV = dict(zip(provincias.id_prov, provincias.provincia))
fila = lambda i: el[el.id_eleccion == i].iloc[0]

ult_pres = el[el.cargo.eq("Presidente") & el.instancia.eq("Primera vuelta")].iloc[-1]
ult_bal = el[el.instancia.eq("Balotaje")].iloc[-1]
ult_int = el[el.es_intermedia].iloc[-1]
ant_int = el[el.es_intermedia & (el.orden < ult_int.orden)].iloc[-1]

def esp_pct(i, e):
    v = nacional[(nacional.id_eleccion == i) & (nacional.nivel == "espacio") & (nacional.id_espacio == e)].pct
    return float(v.iloc[0]) if len(v) else np.nan

kpis = pd.DataFrame([
    ("ult_presidencial", ult_bal.id_eleccion, ult_bal.etiqueta, ult_bal.ganador, ult_bal.ganador_pct, ult_bal.margen_pp, ult_bal.participacion, ult_bal.prov_ganadas),
    ("ult_presidencial_1v", ult_pres.id_eleccion, ult_pres.etiqueta, ult_pres.ganador, ult_pres.ganador_pct, ult_pres.margen_pp, ult_pres.participacion, ult_pres.prov_ganadas),
    ("ult_intermedia", ult_int.id_eleccion, ult_int.etiqueta, NOMBRE_ESP.get(ult_int.ganador_espacio), esp_pct(ult_int.id_eleccion, ult_int.ganador_espacio), ult_int.margen_pp, ult_int.participacion, ult_int.prov_ganadas),
    ("intermedia_anterior", ant_int.id_eleccion, ant_int.etiqueta, NOMBRE_ESP.get(ant_int.ganador_espacio), esp_pct(ant_int.id_eleccion, ant_int.ganador_espacio), ant_int.margen_pp, ant_int.participacion, ant_int.prov_ganadas),
], columns=["clave", "id_eleccion", "etiqueta", "ganador", "ganador_pct", "margen_pp", "participacion", "prov_ganadas"])

textos = []
textos.append(("Última presidencial",
    f"En el balotaje de {ult_bal.anio} ganó {ult_bal.ganador} con {fmt(ult_bal.ganador_pct)}% de los votos positivos, "
    f"{fmt(ult_bal.margen_pp)} puntos sobre {ult_bal.segundo}; ganó en {ult_bal.prov_ganadas} de 24 distritos. "
    f"En la primera vuelta había quedado {'primero' if ult_pres.ganador == ult_bal.ganador else 'segundo'} "
    f"({fmt(nacional[(nacional.id_eleccion == ult_pres.id_eleccion) & (nacional.opcion == ult_bal.ganador)].pct.max())}%)."))
var_int = esp_pct(ult_int.id_eleccion, ult_int.ganador_espacio) - esp_pct(ant_int.id_eleccion, ult_int.ganador_espacio)
textos.append(("Última intermedia",
    f"En las legislativas de {ult_int.anio} el espacio más votado fue {NOMBRE_ESP.get(ult_int.ganador_espacio)} con "
    f"{fmt(esp_pct(ult_int.id_eleccion, ult_int.ganador_espacio))}% de los votos para diputados nacionales"
    + (f" ({'+' if var_int >= 0 else ''}{fmt(var_int)} pp contra {ant_int.anio})" if pd.notna(var_int) else "")
    + f"; su lista ganó en {ult_int.prov_ganadas} de 24 distritos. Segundo: {NOMBRE_ESP.get(ult_int.segundo_espacio)} "
    f"({fmt(esp_pct(ult_int.id_eleccion, ult_int.segundo_espacio))}%)."))
part = el[el.participacion.notna() & el.cargo.eq("Diputados nacionales")]
minp = part.loc[part.participacion.idxmin()]
textos.append(("Participación",
    f"Votó el {fmt(ult_int.participacion)}% del padrón en {ult_int.anio}"
    + (" — la participación más baja en una elección nacional desde 1983" if minp.id_eleccion == ult_int.id_eleccion else
       f"; el mínimo de la serie fue {fmt(minp.participacion)}% en {minp.anio}")
    + f". En la presidencial de {ult_pres.anio} había votado el {fmt(ult_pres.participacion)}%."))
pe_int = pe[pe.id_eleccion == ult_int.id_eleccion]
cambian = pe_int[pe_int.cambio_ganador == "Cambia"]
textos.append(("Mapa",
    f"Respecto de {ant_int.anio}, cambió el espacio ganador en {len(cambian)} de 24 distritos"
    + (": " + ", ".join(NOMBRE_PROV[p] for p in cambian.id_prov) + "." if 0 < len(cambian) <= 10 else ".")
    + f" La provincia más reñida fue {NOMBRE_PROV[pe_int.loc[pe_int.margen_pp.idxmin(), 'id_prov']]} "
      f"({fmt(pe_int.margen_pp.min())} pp de diferencia)."))
pj = nacional[(nacional.nivel == "espacio") & (nacional.id_espacio == "PJ")].merge(el[["id_eleccion", "es_intermedia", "anio"]], on="id_eleccion")
pj_int = pj[pj.es_intermedia]
textos.append(("Histórico",
    f"En las {len(pj_int)} intermedias con datos desde 1985, el peronismo promedió {fmt(pj_int.pct.mean())}% para diputados; "
    f"su mejor elección fue {int(pj_int.loc[pj_int.pct.idxmax(), 'anio'])} ({fmt(pj_int.pct.max())}%) y la peor "
    f"{int(pj_int.loc[pj_int.pct.idxmin(), 'anio'])} ({fmt(pj_int.pct.min())}%). {FALTA_2001}"))
resumen = pd.DataFrame(textos, columns=["tema", "texto"])
for t in textos:
    print("■", t[0] + ":", t[1])

# %% [markdown]
# ## Controles

# %%
# =============================================================
# 6) CONTROLES (resultado oficial conocido vs. base)
# =============================================================
OFICIAL = {  # % del ganador sobre votos positivos (fuente: CNE / Ministerio del Interior; legislativas: Wikipedia)
    "1983-PRES-1V": ("Alfonsín - Martínez", 51.75), "1989-PRES-1V": ("Menem - Duhalde", 47.49),
    "1995-PRES-1V": ("Menem - Ruckauf", 49.94), "1999-PRES-1V": ("De la Rúa - Álvarez", 48.37),
    "2003-PRES-1V": ("Menem - Romero", 24.45), "2007-PRES-1V": ("Fernández de Kirchner - Cobos", 45.29),
    "2011-PRES-1V": ("Fernández de Kirchner - Boudou", 54.11), "2015-PRES-1V": ("Scioli - Zannini", 37.08),
    "2015-PRES-BAL": ("Macri - Michetti", 51.34), "2019-PRES-1V": ("Fernández - Fernández de Kirchner", 48.24),
    "2023-PRES-1V": ("Massa - Rossi", 36.78), "2023-PRES-BAL": ("Milei - Villarruel", 55.65),
}
filas = []
for i, (op, ofi) in OFICIAL.items():
    v = nacional[(nacional.id_eleccion == i) & (nacional.opcion == op)].pct
    calc = float(v.iloc[0]) if len(v) else np.nan
    estado = "ok" if abs(calc - ofi) <= 1.0 else ("explicado en la nota" if i in NOTAS else "⚠ revisar")
    filas.append((i, op, ofi, round(calc, 2), round(calc - ofi, 2), estado))
control = pd.DataFrame(filas, columns=["id_eleccion", "control", "oficial_pct", "tablero_pct", "diferencia_pp", "estado"])
# consistencia interna: cada provincia suma 100%, votantes >= positivos, 24 distritos
cons = res.groupby(["id_eleccion", "id_prov"]).pct.sum()
extra = [("todas", "suma de % por provincia = 100", 100.0, round(cons.mean(), 4), round(cons.max() - cons.min(), 4),
          "ok" if (cons - 100).abs().max() < 1e-6 else "⚠ revisar"),
         ("todas", "elecciones con 24 distritos", len(el), int((el.provincias == 24).sum()), None,
          "ok" if (el.provincias >= 22).all() else "⚠ revisar")]
control = pd.concat([control, pd.DataFrame(extra, columns=control.columns)], ignore_index=True)
print(control.to_string(index=False))
mal = control[control.estado.str.startswith("⚠")]
if len(mal):
    errores.append(("controles", "; ".join(mal.id_eleccion + " " + mal.control)))

# %% [markdown]
# ## Verificación con la API de la DINE (opcional)
# Compara el último escrutinio con la API oficial de resultados. Si la API no responde o cambia, se registra y sigue.

# %%
# =============================================================
# 7) VERIFICACIÓN CON LA DINE (no modifica los datos)
# =============================================================
control_dine = pd.DataFrame(columns=["id_eleccion", "fuente", "agrupacion", "votos", "pct", "estado"])
if VERIFICAR_DINE and AUTO:
    # API pública del Sistema de Publicación de Resultados (sin distrito = total del país).
    # tipoEleccion 2 = generales; categoriaId 3 = diputados nacionales; tipoRecuento 1 = provisorio.
    try:
        r = requests.get("https://resultados.mininterior.gob.ar/api/resultados/getResultados",
                         params={"anioEleccion": int(ult_int.anio), "tipoRecuento": 1, "tipoEleccion": 2, "categoriaId": 3},
                         headers={"User-Agent": "tableros-ar ETL"}, timeout=(10, 40))
        r.raise_for_status()
        pos_dine = sorted(r.json().get("valoresTotalizadosPositivos", []), key=lambda a: -float(a.get("votos") or 0))
        tot = sum(float(a.get("votos") or 0) for a in pos_dine)
        filas = [(ult_int.id_eleccion, "DINE (API)", a.get("nombreAgrupacion"), float(a.get("votos") or 0),
                  float(a.get("votos") or 0) / tot * 100 if tot else np.nan, "ok") for a in pos_dine[:5]]
    except Exception as e:
        filas = [(ult_int.id_eleccion, "DINE (API)", "", np.nan, np.nan, f"sin respuesta: {str(e)[:120]}")]
    nuestra = nacional[(nacional.id_eleccion == ult_int.id_eleccion) & (nacional.nivel == "espacio")].head(5)
    filas += [(ult_int.id_eleccion, "Tablero (espacios)", r_.opcion, r_.votos, r_.pct, "ok") for r_ in nuestra.itertuples()]
    control_dine = pd.DataFrame(filas, columns=control_dine.columns)
    print(control_dine.to_string(index=False))
else:
    print("Verificación DINE salteada (solo corre en GitHub Actions).")

# %% [markdown]
# ## Guardado en Google Sheets

# %%
# =============================================================
# 8) GUARDADO
# =============================================================
clasificacion = listas[["id_eleccion", "id_prov", "fuerza", "bloque_fuente", "opcion", "id_espacio", "regla", "votos", "fuente"]].rename(columns={"fuerza": "lista"})
res_out = res[["id_eleccion", "id_prov", "opcion", "id_espacio", "votos", "pct", "posicion", "listas"]]
pe_out = pe[["id_eleccion", "id_prov", "electores", "votantes", "positivos", "blancos_nulos", "blancos_nulos_pct", "participacion",
             "ganador", "ganador_espacio", "ganador_pct", "ganador_votos", "segundo", "segundo_espacio", "segundo_pct", "margen_pp",
             "nep", "peso_padron", "ganador_espacio_anterior", "cambio_ganador"]]
el_out = el[["id_eleccion", "anio", "fecha", "tipo", "instancia", "cargo", "categoria", "es_intermedia", "etiqueta", "etiqueta_corta",
             "orden", "anterior", "provincias", "electores", "votantes", "positivos", "participacion", "ganador", "ganador_espacio",
             "ganador_pct", "segundo", "segundo_espacio", "segundo_pct", "margen_pp", "prov_ganadas", "sin_clasificar_pct",
             "recuento", "fuente", "nota"]]
nac_out = nacional[["id_eleccion", "nivel", "opcion", "id_espacio", "votos", "pct", "posicion", "pct_anterior", "var_pp"]]
prov_out = prov[["id_prov", "provincia", "nombre_corto", "provincia_mapa", "region", "orden", "electores_ultimo", "peso_padron", "svg_path", "label_x", "label_y"]]
info = pd.DataFrame([{
    "ultima_actualizacion": pd.Timestamp.now(tz="America/Argentina/Buenos_Aires").strftime("%Y-%m-%d %H:%M"),
    "cobertura": f"{len(el)} elecciones: presidenciales 1983-2023 (con balotajes 2015 y 2023 y PASO 2011-2023) y diputados nacionales 1983-2025 (falta 2001)",
    "fuentes": "Atlas Electoral de Andy Tow vía PolAr (presidenciales 1983-2019, definitivo); Cámara Nacional Electoral (2023, definitivo); "
               "Dirección Nacional Electoral (diputados 2011-2025 y PASO, provisorio); PolAr y base de Ernesto Calvo (diputados 1983-2009); compilación por departamento: repositorio 257arg",
    "mapa": REPO_RAW + "data/elecciones/mapa/provincias_ar.topojson",
    "errores": "; ".join(f"{a}: {b}" for a, b in errores) or "ninguno"}])

HOJAS = {"elecciones": el_out, "provincias": prov_out, "espacios": espacios, "resultados": res_out,
         "prov_eleccion": pe_out, "nacional": nac_out, "kpis": kpis, "resumen": resumen, "control": control,
         "control_dine": control_dine, "clasificacion": clasificacion, "info": info}

def preparar(data):
    d_ = data.copy()
    for c in d_.columns:
        t = d_[c].dtype
        if pd.api.types.is_datetime64_any_dtype(t): d_[c] = d_[c].dt.strftime("%Y-%m-%d")
        elif pd.api.types.is_bool_dtype(t): d_[c] = d_[c].map({True: "TRUE", False: "FALSE"})
        elif pd.api.types.is_float_dtype(t): d_[c] = d_[c].round(6)
    return d_.astype(object).where(pd.notna(d_), "")

if SOLO_LOCAL:
    os.makedirs("salida_elecciones", exist_ok=True)
    for n_, d_ in HOJAS.items():
        preparar(d_).to_csv(f"salida_elecciones/{n_}.csv", index=False)
    print("CSV escritos en salida_elecciones/")
else:
    import gspread
    try:
        from google.colab import auth
        auth.authenticate_user()
        from google.auth import default
        creds, _ = default()
    except ImportError:          # fuera de Colab (GitHub Actions): cuenta de servicio
        from google.oauth2.service_account import Credentials
        creds = Credentials.from_service_account_file(
            os.environ["GOOGLE_SA_JSON"],
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SPREADSHEET_ID)

    def a_hoja(nombre, data):
        d_ = preparar(data)
        vals = [list(d_.columns)] + d_.values.tolist()
        try:
            ws = sh.worksheet(nombre); ws.clear(); ws.resize(rows=max(len(vals), 2), cols=max(len(d_.columns), 1))
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=nombre, rows=len(vals) + 10, cols=len(d_.columns) + 2)
        for i in range(0, len(vals), 20000):
            ws.update(values=vals[i:i + 20000], range_name=f"A{i + 1}", value_input_option="RAW")
        print(f"✔ hoja '{nombre}': {len(d_)} filas")

    for n_, d_ in HOJAS.items():
        a_hoja(n_, d_)
    for h in ("Hoja 1", "Sheet1"):
        try: sh.del_worksheet(sh.worksheet(h))
        except Exception: pass
    print("\nListo ✅  →", f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
