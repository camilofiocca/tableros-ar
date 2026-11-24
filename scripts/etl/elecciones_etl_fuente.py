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
# TopoJSON de provincias fijado a un commit (no depende de la rama ni de main)
URL_MAPA = ("https://raw.githubusercontent.com/camilofiocca/tableros-ar/57ffa60d5570d5fd331581972481f727e112f239/"
            "data/elecciones/mapa/provincias_ar.topojson")

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
gob_listas = leer_csv("data/elecciones/base_gob_listas.csv", **S)
gob_totales = leer_csv("data/elecciones/base_gob_totales.csv", **S)
gob_electos = leer_csv("data/elecciones/manual/gobernadores_electos.csv", **S)
sen_listas = leer_csv("data/elecciones/base_sen_listas.csv", **S)
sen_totales = leer_csv("data/elecciones/base_sen_totales.csv", **S)
for d_ in (gob_listas, gob_totales, gob_electos, sen_listas, sen_totales):
    d_["id_prov"] = d_.id_prov.str.zfill(2)
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
# ## Gobernadores, Senado, bancas y presidentes
# - **Gobernadores**: resultados por elección (con balotaje cuando lo hubo) y quién gobierna cada provincia año por año.
#   El gobernador electo y su espacio salen de `manual/gobernadores_electos.csv` (resuelve colegios electorales,
#   intervenciones y frentes con nombre de candidato).
# - **Bancas**: diputados por sistema D'Hondt en cada distrito con piso del 3% del padrón (Ley 19.945, art. 160) y
#   la cantidad de bancas que renueva cada provincia; senadores: 2 a la lista más votada y 1 a la segunda.
#   Son bancas *obtenidas en la elección*: no reflejan cambios posteriores de bloque.

# %%
# =============================================================
# 4b) GOBERNADORES, SENADO, BANCAS Y PRESIDENTES
# =============================================================
def espacio_de(anio, *textos):
    return clasificar(int(anio), False, False, " || ".join(norm(t) for t in textos if isinstance(t, str) and t))[1]

# --- Gobernadores: resultados ---
g = gob_listas.copy()
ROTOS = {"C?Vica": "Cívica", "Coalici?N": "Coalición", "Uni?N": "Unión"}   # tildes perdidas en la fuente
g["opcion"] = g.opcion.astype(str).replace(ROTOS, regex=True).str.replace(r"\s+", " ", regex=True).str.strip()
g["partido"] = g.partido.fillna("").astype(str).replace(ROTOS, regex=True).str.replace(r"\s+", " ", regex=True).str.strip()
g["candidato"] = g.candidato.fillna("").astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
g["id_espacio"] = g.id_espacio_fijo
sin_esp = g.id_espacio.isna()
g.loc[sin_esp, "id_espacio"] = [espacio_de(a, p, o) for a, p, o in zip(g.loc[sin_esp, "anio"], g.loc[sin_esp, "partido"], g.loc[sin_esp, "opcion"])]
g["pct"] = g.pct_fuente
falta = g.pct.isna()
g.loc[falta, "pct"] = g.votos / g.groupby(["anio", "id_prov", "vuelta"]).votos.transform("sum") * 100
g = g.sort_values(["anio", "id_prov", "vuelta", "pct"], ascending=[True, True, True, False])
g["posicion"] = g.groupby(["anio", "id_prov", "vuelta"]).cumcount() + 1
g["id_gob"] = g.anio.astype(str) + "-" + g.id_prov
g["final"] = g.groupby("id_gob").vuelta.transform(lambda s: "BAL" if (s == "BAL").any() else "1V")
electos = gob_electos.assign(id_gob=lambda d: d.anio.astype(str) + "-" + d.id_prov)
# la lista ganadora toma el espacio del gobernador electo (salvo colegio electoral / sin gobernador)
gan = (g.vuelta == g.final) & (g.posicion == 1)
esp_electo = g.id_gob.map(dict(zip(electos.id_gob, electos.id_espacio)))
corrige = gan & esp_electo.notna() & ~g.id_gob.isin(["1987-90", "1991-18"])
g.loc[corrige, "id_espacio"] = esp_electo[corrige]
g["vuelta_txt"] = g.vuelta.map({"1V": "Primera vuelta", "BAL": "Balotaje"})
# nombre presentable: partido o frente (los códigos de Calvo se traducen) y, aparte, el candidato
g["lista"] = [presentable(p_ if p_ else o_) for p_, o_ in zip(g.partido, g.opcion)]
g["etiqueta"] = np.where(g.candidato != "", g.candidato.str.split(r"\s*-\s*").str[0] + " (" + g.lista + ")", g.lista)
gob_res = g[["id_gob", "anio", "id_prov", "vuelta", "vuelta_txt", "etiqueta", "lista", "candidato", "id_espacio", "votos", "pct", "posicion", "fuente"]].copy()

# --- Gobernadores: una fila por elección ---
fin = g[g.vuelta == g.final]
p1 = fin[fin.posicion == 1].set_index("id_gob")
p2 = fin[fin.posicion == 2].set_index("id_gob")
ge = electos.set_index("id_gob")[["anio", "id_prov", "gobernador", "id_espacio", "nota"]].copy()
ge["vuelta_final"] = ge.index.map(p1.vuelta)
ge["hubo_balotaje"] = ge.vuelta_final.eq("BAL")
ge["lista_ganadora"] = ge.index.map(p1.lista)
ge["ganador_pct"] = ge.index.map(p1.pct)
ge["segundo"] = ge.index.map(p2.etiqueta)
ge["segundo_espacio"] = ge.index.map(p2.id_espacio)
ge["segundo_pct"] = ge.index.map(p2.pct)
ge["margen_pp"] = ge.ganador_pct - ge.segundo_pct
t1 = gob_totales[gob_totales.vuelta == "1V"].assign(id_gob=lambda d: d.anio.astype(str) + "-" + d.id_prov).set_index("id_gob")
ge["electores"] = ge.index.map(t1.electores)
ge["participacion"] = (ge.index.map(t1.votantes) / ge.electores * 100)
ge.loc[~ge.participacion.between(35, 100), "participacion"] = np.nan
ge["fuente"] = ge.index.map(fin.groupby("id_gob").fuente.first())
ge = ge.reset_index().sort_values(["id_prov", "anio"])
ge["gobernador_anterior"] = ge.groupby("id_prov").gobernador.shift(1)
ge["espacio_anterior"] = ge.groupby("id_prov").id_espacio.shift(1)
ge["cambio"] = np.where(ge.espacio_anterior.isna(), "", np.where(ge.id_espacio == ge.espacio_anterior, "Continuidad", "Alternancia"))
ge["reelecto"] = ge.gobernador.eq(ge.gobernador_anterior)
ge["hasta"] = ge.groupby("id_prov").anio.shift(-1).astype("Int64")
ge["mandato"] = ge.anio.astype(str) + "–" + ge.hasta.map(lambda x: str(int(x)) if pd.notna(x) else "hoy")
ge["foto_url"] = ""   # opcional: link a una foto (lo completa el usuario; el tablero la muestra si existe)
ge["etiqueta"] = ge.gobernador + " (" + ge.mandato + ")"
gob_el = ge[["id_gob", "anio", "id_prov", "gobernador", "id_espacio", "mandato", "hasta", "vuelta_final", "hubo_balotaje",
             "lista_ganadora", "ganador_pct", "segundo", "segundo_espacio", "segundo_pct", "margen_pp", "participacion",
             "electores", "cambio", "reelecto", "gobernador_anterior", "espacio_anterior", "nota", "fuente", "foto_url", "etiqueta"]]

# --- Quién gobierna cada provincia al cierre de cada año ---
filas = []
for a in range(1983, int(max(el.anio.max(), ge.anio.max())) + 1):
    vig = ge[ge.anio <= a].sort_values("anio").groupby("id_prov").tail(1).set_index("id_prov")
    for p in provincias.id_prov:
        if p in vig.index:
            v = vig.loc[p]
            filas.append((a, p, v.id_gob, v.gobernador, v.id_espacio, int(v.anio), v.mandato))
        else:
            filas.append((a, p, None, "Sin gobernador electo" if p != "94" else "Territorio nacional", None, None, ""))
gob_mapa = pd.DataFrame(filas, columns=["anio_corte", "id_prov", "id_gob", "gobernador", "id_espacio", "electo_en", "mandato"])
gob_mapa["electo_en"] = gob_mapa.electo_en.astype("Int64")
gob_mapa.loc[(gob_mapa.id_prov == "02") & gob_mapa.id_gob.isna(), "gobernador"] = "Intendente designado"
# Corrientes 1991-1993: intervención federal
gob_mapa.loc[gob_mapa.id_gob.eq("1991-18"), ["gobernador", "id_espacio"]] = ["Intervención federal", None]
gob_mapa["etiqueta_anio"] = gob_mapa.anio_corte.astype(str)

# --- Senado: resultados y bancas (2 + 1) ---
s = sen_listas.copy()
s["anio"] = s.id_eleccion.str[:4].astype(int)
s["textos"] = s.fuerza.map(norm) + " || " + s.bloque_fuente.fillna("").map(norm)
s["id_espacio"] = [clasificar(a, False, False, t)[1] for a, t in zip(s.anio, s.textos)]
s["opcion"] = s.fuerza.map(presentable)
sen = (s.groupby(["id_eleccion", "anio", "id_prov", "opcion"])
       .apply(lambda q: pd.Series({"votos": q.votos.sum(), "id_espacio": q.loc[q.votos.idxmax(), "id_espacio"]}))
       .reset_index())
sen["pct"] = sen.votos / sen.groupby(["id_eleccion", "id_prov"]).votos.transform("sum") * 100
sen["posicion"] = sen.groupby(["id_eleccion", "id_prov"]).votos.rank(ascending=False, method="first").astype(int)
sen["bancas"] = sen.posicion.map({1: 2, 2: 1}).fillna(0).astype(int)

# --- Diputados: bancas por D'Hondt ---
BANCAS_PROV = {"02": 25, "06": 70, "10": 5, "14": 18, "18": 7, "22": 7, "26": 5, "30": 9, "34": 5, "38": 6, "42": 5, "46": 5,
               "50": 10, "54": 7, "58": 5, "62": 5, "66": 7, "70": 6, "74": 5, "78": 5, "82": 19, "86": 7, "90": 9, "94": 5}
# bancas que renueva cada distrito en los años 1985, 1989, ..., 2025 (127 en total); el resto renueva en los otros años (130)
MITAD_A = {"02": 13, "06": 35, "10": 3, "14": 9, "18": 3, "22": 4, "26": 2, "30": 5, "34": 2, "38": 3, "42": 3, "46": 2,
           "50": 5, "54": 3, "58": 3, "62": 2, "66": 3, "70": 3, "74": 2, "78": 3, "82": 9, "86": 4, "90": 4, "94": 2}

def bancas_en_juego(anio, p):
    if anio == 1983:
        return 2 if p == "94" else BANCAS_PROV[p]           # renovación total (Tierra del Fuego era territorio: 2)
    if p == "94" and anio < 1991:
        return 1
    return MITAD_A[p] if anio % 4 == 1 else BANCAS_PROV[p] - MITAD_A[p]

def dhondt(votos, n):
    cocientes = sorted(((v / d, i) for i, v in enumerate(votos) for d in range(1, n + 1)), key=lambda t: -t[0])
    out = [0] * len(votos)
    for _, i in cocientes[:n]:
        out[i] += 1
    return out

dip = res[res.id_eleccion.str.endswith("-DIP")].copy()
dip["bancas"] = 0
elec_prov = pe.set_index(["id_eleccion", "id_prov"]).electores
for (e, p), q in dip.groupby(["id_eleccion", "id_prov"]):
    n = bancas_en_juego(int(e[:4]), p)
    ele = elec_prov.get((e, p), np.nan)
    ok = q.votos >= 0.03 * ele if pd.notna(ele) else q.votos > 0
    if not ok.any():
        ok = q.votos > 0
    dip.loc[q.index[ok.values], "bancas"] = dhondt(q.votos[ok].tolist(), n)
dip["anio"] = dip.id_eleccion.str[:4].astype(int)
bancas = pd.concat([
    dip.assign(camara="Diputados")[["camara", "id_eleccion", "anio", "id_prov", "opcion", "id_espacio", "votos", "pct", "posicion", "bancas"]],
    sen.assign(camara="Senado")[["camara", "id_eleccion", "anio", "id_prov", "opcion", "id_espacio", "votos", "pct", "posicion", "bancas"]],
], ignore_index=True)
bancas["id_camara_anio"] = bancas.camara + " " + bancas.anio.astype(str)

# --- Composición de cada cámara (bancas obtenidas en las elecciones que siguen en curso) ---
comp = []
for cam, ventana, total in (("Diputados", 2, 257), ("Senado", 3, 72)):
    b = bancas[bancas.camara == cam]
    anios = sorted(b.anio.unique())
    for a in anios:
        previos = [a - 2 * k for k in range(ventana)]
        if not all(x in anios for x in previos):
            continue      # falta una elección de la ventana (2001, o 1983 para diputados)
        if 1983 in previos and a > 1983:
            continue      # en 1983 se renovó toda la Cámara y la mitad sorteó mandato de 2 años: no se puede reconstruir 1985
        x = b[b.anio.isin(previos)].groupby("id_espacio").bancas.sum()
        for esp, n in x.items():
            if n > 0:
                comp.append((cam, a, esp, int(n), int(x.sum())))
composicion = pd.DataFrame(comp, columns=["camara", "anio", "id_espacio", "bancas", "total_bancas"])
composicion["pct"] = composicion.bancas / composicion.total_bancas * 100
composicion["mayoria"] = np.where(composicion.camara == "Diputados", 129, 37)
composicion["id_camara_anio"] = composicion.camara + " " + composicion.anio.astype(str)

# Bancas que siguen en la cámara hoy (diputados: últimas 2 elecciones; senado: últimas 3)
ult = bancas.groupby("camara").anio.max()
bancas["vigente"] = [a > ult[c] - (4 if c == "Diputados" else 6) for c, a in zip(bancas.camara, bancas.anio)]

# Dimensión cámara-año (la usan los segmentadores de la página Congreso)
camara_anio = (pd.concat([bancas[["camara", "anio"]], composicion[["camara", "anio"]]]).drop_duplicates()
               .sort_values(["camara", "anio"]).reset_index(drop=True))
camara_anio["id_camara_anio"] = camara_anio.camara + " " + camara_anio.anio.astype(str)
camara_anio["etiqueta"] = camara_anio.id_camara_anio
camara_anio["orden"] = range(1, len(camara_anio) + 1)
camara_anio["tiene_composicion"] = camara_anio.id_camara_anio.isin(composicion.id_camara_anio)
camara_anio = camara_anio[["id_camara_anio", "camara", "anio", "etiqueta", "orden", "tiene_composicion"]]

# Posiciones de las bancas en el hemiciclo (dibujo SVG de la composición): x, y, radio en píxeles enteros
def hemiciclo_pos(n, filas, ancho=600, r_min=0.38):
    radios = [r_min + (1 - r_min) * i / (filas - 1) for i in range(filas)]
    por_fila = [round(n * r / sum(radios)) for r in radios]
    por_fila[-1] += n - sum(por_fila)
    R = ancho / 2 - 20
    paso = min([R * (1 - r_min) / (filas - 1)] + [np.pi * R * r / (k - 1) for r, k in zip(radios, por_fila) if k > 1])
    radio = max(3, int(paso * 0.42))
    pts = []
    for r, k in zip(radios, por_fila):
        for j in range(k):
            t = np.pi * (1 - j / (k - 1)) if k > 1 else np.pi / 2
            pts.append((t, r, ancho / 2 + R * r * np.cos(t), R + 20 - R * r * np.sin(t)))
    pts.sort(key=lambda q: (-round(q[0], 6), q[1]))
    return [(i + 1, int(round(x)), int(round(y)), radio) for i, (t, r, x, y) in enumerate(pts)]

hemiciclo = pd.DataFrame(
    [("Diputados",) + q for q in hemiciclo_pos(257, 9)] + [("Senado",) + q for q in hemiciclo_pos(72, 5)],
    columns=["camara", "asiento", "x", "y", "r"])

def iniciales(nombre):
    if nombre == "Cristina Fernández de Kirchner":
        return "CFK"
    w = [x for x in str(nombre).split() if x[:1].isupper()]
    return (w[0][0] + w[-1][0]).upper() if len(w) >= 2 else str(nombre)[:2].upper()

# --- Presidentes electos ---
PRESIDENTES = [  # (id_eleccion donde se define, fórmula como figura en la base, presidente, desde, hasta, nota)
    ("1983-PRES-1V", "Alfonsín - Martínez", "Raúl Alfonsín", "1983-12-10", "1989-07-08", "Entregó el mando cinco meses antes, en medio de la hiperinflación."),
    ("1989-PRES-1V", "Menem - Duhalde", "Carlos Menem", "1989-07-08", "1995-07-08", ""),
    ("1995-PRES-1V", "Menem - Ruckauf", "Carlos Menem", "1995-07-08", "1999-12-10", "Reelecto tras la reforma constitucional de 1994."),
    ("1999-PRES-1V", "De la Rúa - Álvarez", "Fernando de la Rúa", "1999-12-10", "2001-12-21", "Renunció en la crisis de 2001; lo sucedieron Puerta, Rodríguez Saá, Camaño y Duhalde (designados por el Congreso)."),
    ("2003-PRES-1V", "Kirchner - Scioli", "Néstor Kirchner", "2003-05-25", "2007-12-10", "Segundo en primera vuelta (22,2%); asumió porque Menem no se presentó al balotaje."),
    ("2007-PRES-1V", "Fernández de Kirchner - Cobos", "Cristina Fernández de Kirchner", "2007-12-10", "2011-12-10", ""),
    ("2011-PRES-1V", "Fernández de Kirchner - Boudou", "Cristina Fernández de Kirchner", "2011-12-10", "2015-12-10", "Reelecta con más del 54%, el mayor porcentaje en primera vuelta desde 1983."),
    ("2015-PRES-BAL", "Macri - Michetti", "Mauricio Macri", "2015-12-10", "2019-12-10", "Primer balotaje presidencial de la historia."),
    ("2019-PRES-1V", "Fernández - Fernández de Kirchner", "Alberto Fernández", "2019-12-10", "2023-12-10", ""),
    ("2023-PRES-BAL", "Milei - Villarruel", "Javier Milei", "2023-12-10", "", "Ganó el balotaje con el 55,7%."),
]
pres = []
for i, (ide, formula, nombre, desde, hasta, nota) in enumerate(PRESIDENTES, start=1):
    v = nacional[(nacional.id_eleccion == ide) & (nacional.opcion == formula)]
    if v.empty:
        errores.append(("presidentes", f"no se encontró {formula} en {ide}"))
        continue
    pres.append({"orden": i, "anio": int(ide[:4]), "id_eleccion": ide, "presidente": nombre, "formula": formula,
                 "id_espacio": v.id_espacio.iloc[0], "pct": float(v.pct.iloc[0]),
                 "instancia": "Balotaje" if ide.endswith("BAL") else "Primera vuelta",
                 "desde": desde, "hasta": hasta, "mandato": desde[:4] + "–" + (hasta[:4] if hasta else "hoy"),
                 "nota": nota, "foto_url": "",
                 "iniciales": iniciales(nombre)})
presidentes = pd.DataFrame(pres)
gob_el = gob_el.assign(iniciales=gob_el.gobernador.map(iniciales))
gob_mapa = gob_mapa.merge(gob_el[["id_gob", "iniciales", "foto_url"]], on="id_gob", how="left")

print(f"gobernadores: {len(gob_el)} elecciones · senado: {sen.groupby(['id_eleccion', 'id_prov']).ngroups} distritos · "
      f"bancas diputados por año: {dip.groupby('anio').bancas.sum().to_dict()}")
print(composicion[composicion.anio == composicion.anio.max()].sort_values(["camara", "bancas"], ascending=[True, False]).to_string(index=False))

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
# bancas: cada renovación de diputados debe repartir 127 o 130 (o 254 en 1983) salvo distritos sin datos
for a, n in dip.groupby("anio").bancas.sum().items():
    esperado = sum(bancas_en_juego(a, p_) for p_ in dip[dip.anio == a].id_prov.unique())
    extra.append((f"{a}-DIP", "bancas repartidas = bancas en juego", esperado, int(n), int(n - esperado),
                  "ok" if n == esperado else "⚠ revisar"))
for e, n in sen.groupby("id_eleccion").bancas.sum().items():
    esperado = 3 * sen[sen.id_eleccion == e].id_prov.nunique()
    extra.append((e, "bancas de senador = 3 por provincia", esperado, int(n), int(n - esperado), "ok" if n == esperado else "⚠ revisar"))
ult_corte = gob_mapa[gob_mapa.anio_corte == gob_mapa.anio_corte.max()]
extra.append(("gobernadores", "provincias con gobernador electo hoy", 24, int(ult_corte.id_espacio.notna().sum()), None,
              "ok" if ult_corte.id_espacio.notna().sum() == 24 else "⚠ revisar"))
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
    "cobertura": f"{len(el)} elecciones nacionales: presidenciales 1983-2023 (con balotajes 2015 y 2023 y PASO 2011-2023) y diputados "
                 f"nacionales 1983-2025 (falta 2001); {len(gob_el)} elecciones de gobernador 1983-2025; senadores 2003-2025",
    "fuentes": "Atlas Electoral de Andy Tow vía PolAr (presidenciales 1983-2019, definitivo); Cámara Nacional Electoral (2023, definitivo); "
               "Dirección Nacional Electoral (diputados y senadores 2011-2025 y PASO, provisorio); PolAr y base de Ernesto Calvo (diputados 1983-2009); "
               "gobernadores: Atlas de Andy Tow vía PolAr (1983-2019) y carga manual verificada (2013, 2021-2025); compilación por departamento: repositorio 257arg",
    "mapa": URL_MAPA,
    "errores": "; ".join(f"{a}: {b}" for a, b in errores) or "ninguno"}])

HOJAS = {"elecciones": el_out, "provincias": prov_out, "espacios": espacios, "resultados": res_out,
         "prov_eleccion": pe_out, "nacional": nac_out, "kpis": kpis, "resumen": resumen, "control": control,
         "control_dine": control_dine, "clasificacion": clasificacion, "info": info,
         "gob_elecciones": gob_el, "gob_resultados": gob_res, "gob_mapa": gob_mapa, "bancas": bancas,
         "composicion": composicion, "presidentes": presidentes,
         "camara_anio": camara_anio, "hemiciclo": hemiciclo}

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
