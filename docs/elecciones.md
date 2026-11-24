# Tablero Elecciones AR

Tercer tablero de la serie (junto a Macro AR y Energía AR). Muestra las elecciones **presidenciales** (primera vuelta 1983-2023, balotajes 2015 y 2023, PASO 2011-2023), las de **diputados nacionales** 1983-2025 (con foco en las **intermedias**), **senadores** 2003-2025 y **gobernadores** 1983-2025, por provincia y con mapas interactivos. Calcula además las **bancas** de cada elección y la **composición de las dos cámaras**.

```
Fuentes (PolAr / Andy Tow, CNE, DINE, 257arg)
   │  scripts/etl/elecciones_base.py   (a mano, una vez por elección nueva)
   ▼
data/elecciones/base_*.csv  +  reglas_espacios.csv  +  mapa/
   │  notebooks/Tablero Elecciones AR - ETL v1.ipynb   (GitHub Actions, lunes 09:47, o a mano)
   ▼
Google Sheets "Elecciones AR - Datos limpios"  ──►  Power BI (Tablero Elecciones AR)
```

| Pieza | Dónde está |
|---|---|
| Planilla | https://docs.google.com/spreadsheets/d/1gD1noYKGiWRA_XywAkbpqzelKTGvAwEzuoikLlu1KE8 |
| Notebook | `notebooks/Tablero Elecciones AR - ETL v1.ipynb` (se genera desde `scripts/etl/elecciones_etl_fuente.py` con `scripts/etl/elecciones_a_notebook.py`) |
| Base histórica | `data/elecciones/base_listas.csv` y `base_totales.csv` (`scripts/etl/elecciones_base.py`) |
| Reglas de espacios | `data/elecciones/reglas_espacios.csv` y `espacios.csv` |
| Mapa | `data/elecciones/mapa/provincias_ar.topojson` (lo lee Power BI por URL) y `provincias_svg.csv` (mapa SVG) |
| Proyecto Power BI | se genera con `scripts/powerbi/build_elecciones.py`; copia en Drive: Tableros AR → Elecciones AR → 02 Power BI |

## Fuentes y cobertura

| Elecciones | Fuente | Recuento |
|---|---|---|
| Presidente 1ra vuelta 1983-2019, balotaje 2015 | Atlas Electoral de Andy Tow, vía PolAr (`PoliticaArgentina/data_warehouse`, commit `9304ac9`) | Definitivo (Tucumán 2015: DINE) |
| Presidente 2023 (1ra vuelta y balotaje) | Cámara Nacional Electoral (tabla por provincia; `data/elecciones/manual/`) | Definitivo |
| PASO presidenciales 2011-2023 | Dirección Nacional Electoral | Provisorio |
| Diputados 2011-2025 | Dirección Nacional Electoral | Provisorio |
| Diputados 2003-2009 | PolAr / Andy Tow (por mesa) | Provisorio |
| Diputados 1983-1999 | Base de Ernesto Calvo | Sin corregir |
| Senadores 2003-2025 | 257arg (DINE / Andy Tow) | Provisorio |
| Gobernadores 1983-2025 | Atlas de Andy Tow vía PolAr (242 archivos) y 257arg; 2013-2025 faltantes en `data/elecciones/manual/gobernadores_manual.csv` (informes provinciales y prensa) | Definitivo o provisorio según la fuente |

Las bases por departamento 1983-2025 se toman de la compilación `azha2005/257arg` (`MASTER_resultados.xlsx`, commit `573038a`, CC BY 4.0). Todas las descargas están fijadas a un commit para que el resultado sea reproducible.

**Huecos conocidos:** no hay datos por provincia de las legislativas de 2001; faltan Tierra del Fuego en 1987, San Luis en 1997 y 1999, Santa Cruz en 1999 y La Pampa en 2003.

## Espacios políticos

Cada lista (diputados) o fórmula (presidente) se asigna a uno de diez espacios comparables en el tiempo: Peronismo, Peronismo federal y terceras vías, UCR y aliados, PRO / Cambiemos / Juntos por el Cambio, La Libertad Avanza, Centroderecha, Centroizquierda, Izquierda, Partidos provinciales y Otros. Las reglas están en `reglas_espacios.csv` (columna `patron`, expresión regular sobre el nombre de la lista o el bloque que trae la fuente; gana la primera que coincide, en orden). Para las presidenciales, las reglas `PRES` asignan además la fórmula. La hoja `clasificacion` de la planilla deja registrada la regla que tocó a cada lista.

Voto que queda en "Otros" por no poder atribuirlo con certeza: menos de 4% en casi todas las elecciones; 9% en diputados 1997 (códigos sin nombre de la base de Calvo) y 23% en diputados 2003 (listas provinciales abreviadas).

## Controles

El notebook compara el porcentaje del ganador con el resultado oficial (hoja `control`). Coinciden exactamente 1983, 1999, 2003, 2007, 2015 (con balotaje), 2019 y 2023 (con balotaje); 2011 difiere 0,5 pp y 1989 0,7 pp. En **1995** Menem queda en 47,0% contra 49,9% oficial porque algunas listas provinciales que llevaban su fórmula no se pueden atribuir con certeza (quedan en "Otras fórmulas"); está anotado en la elección. En las legislativas 2025, La Libertad Avanza suma 40,66% de los votos para diputados, igual al total publicado.

Además, en GitHub Actions el notebook consulta la API pública de resultados de la DINE (último escrutinio, total del país) y deja la comparación en la hoja `control_dine`; si la API no responde, lo registra y sigue.

## Bancas, composición y gobernadores

- **Diputados:** las bancas de cada distrito se reparten por D'Hondt entre las listas que superan el 3% del padrón (Ley 19.945, art. 160). Bancas por provincia: 257 en total; la mitad A (127 bancas) se renueva en 1989, 1993, ..., 2021 y 2025, y la otra (130) en 1987, 1991, ..., 2023 (`MITAD_A` en el notebook). 1983 renovó toda la Cámara.
- **Senado:** 2 bancas para la lista más votada y 1 para la segunda.
- **Composición:** Diputados = bancas de las últimas 2 elecciones (desde 1987; no hay 2001 ni composición de 2001-2003); Senado = últimas 3 (desde 2007). Es la composición **según la lista que ganó la banca**, no según los bloques: puede diferir del conteo oficial de bloques (p. ej. 2025: LLA 98 y Peronismo 102 en Diputados). Control: las bancas repartidas son iguales a las bancas en juego en cada año.
- **Gobernadores:** `gobernadores_electos.csv` fija el gobernador y el espacio de cada elección (colegios electorales 1983-87, intervención de Corrientes 1991, frentes de Cambiemos/JxC como PRO-JxC aunque el gobernador sea radical). `gob_mapa` dice quién gobernaba cada provincia al cierre de cada año (CABA con intendente designado hasta 1996, Tierra del Fuego como territorio hasta 1991).
- **Fotos:** el tablero no trae fotos. Las hojas `presidentes`, `gob_elecciones` y `gob_mapa` tienen una columna `foto_url`: si se completa con un enlace a una imagen, el tablero la muestra en lugar del círculo con iniciales.

## Modelo de Power BI

- Conexión a la planilla por enlace público (`UrlPlanilla` = export xlsx), como Macro y Energía. En Power BI web: credencial **Anónima**, privacidad **Pública**.
- Tablas: `elecciones`, `provincias`, `espacios`, `resultados` (provincia × lista o fórmula), `prov_eleccion` (provincia × elección: participación, ganador, margen, NEP), `nacional` (país × espacio o fórmula), `kpis`, `resumen`, `control`, `info`, `gob_elecciones`, `gob_resultados`, `gob_mapa`, `bancas`, `composicion`, `camara_anio`, `hemiciclo`, `presidentes` y `Medidas` (142 medidas; las nuevas están en `scripts/powerbi/elecciones_medidas_nuevas.py`).
- Relaciones: `resultados`, `prov_eleccion` y `nacional` → `elecciones`; `resultados`, `prov_eleccion`, `gob_elecciones`, `gob_mapa` y `bancas` → `provincias`; `resultados`, `nacional`, `gob_elecciones`, `gob_mapa`, `bancas`, `composicion` y `presidentes` → `espacios`; `gob_resultados` → `gob_elecciones`; `bancas` y `composicion` → `camara_anio`.
- **Segmentador de provincia** en Mapa, Provincia, Presidenciales, Intermedias, Congreso, Gobernadores, Por espacio, Evolución y Participación, sincronizado entre páginas (grupo `provincia`). Vacío = todo el país. Las series por espacio y la participación siguen a la provincia elegida (segmentador o clic en el mapa).
- La elección elegida sale de `[Id elección]` (la de mayor `orden` dentro del filtro); los segmentadores son de selección única y arrancan en la última elección.
- **Mapas interactivos:** mapa de formas con el TopoJSON del repo por URL (`shape.datasourceType = url`) y el color de cada provincia por medida (`[Color ganador]`, `[Color intensidad del espacio]`, `[Color participación]`). Al hacer clic en una provincia se filtra toda la página. La Ciudad de Buenos Aires se dibuja además ampliada en un recuadro sobre el Atlántico.
- **Mapa SVG** (Resumen): medida `[SVG mapa ganadores]`, igual técnica que el mapa provincial de Macro; se ve siempre aunque el mapa de formas no cargue.

## Páginas

1. **Resumen**: balotaje 2023 y legislativas 2025 en tarjetas, mapa SVG de la última intermedia, evolución de los espacios en las intermedias, votos por espacio, lectura automática y tabla por provincia.
2. **Mapa**: elegís cualquier elección; mapa de ganadores, tarjetas, votos por espacio y tabla de provincias.
3. **Por espacio**: mapa de intensidad (cinco tonos, escalones de 10 puntos) del espacio elegido y ranking de provincias.
4. **Presidenciales**: resultado por fórmula, mapa, tabla por provincia y evolución 1983-2023.
5. **Intermedias**: diputados por espacio, mapa, lista ganadora y cambio respecto de la elección anterior, evolución 1985-2025.
6. **Evolución**: matriz provincia × elección coloreada por espacio ganador y cantidad de cambios.
7. **Participación**: participación 1983-2025, blancos y nulos, mapa y tabla por provincia.
8. **Datos**: fuentes, método, controles y definición de los espacios.
9. **Provincia**: gobernador actual, último balotaje y última elección de diputados, diputados y senadores en ejercicio, evolución por espacio (diputados y presidente), historia de gobernadores y última elección a gobernador.
10. **Congreso**: hemiciclo con la composición de la cámara (Diputados o Senado, año elegido), evolución de las bancas por espacio, mapa del espacio que más bancas ganó en cada distrito, bancas ganadas y listas que obtuvieron bancas.
11. **Gobernadores**: mapa de quién gobernaba cada provincia en el año elegido, provincias por espacio, gobernadores en ejercicio, historia de las elecciones a gobernador y evolución 1983-2025.
12. **Presidentes**: tarjetas de los diez mandatos surgidos de las urnas, detalle de cada uno y años de gobierno por espacio.

Orden en el navegador: Resumen, Mapa, Provincia, Presidenciales, Intermedias, Congreso, Gobernadores, Presidentes, Por espacio, Evolución, Participación, Datos.

Página oculta `tt_provincia`: información emergente del mapa (resultado de la provincia).

## Instalación y publicación

Paso a paso en [elecciones_instalacion.md](elecciones_instalacion.md): carpeta `04 Elecciones AR` en la PC, abrir el PBIP, guardar como `.pbix`, publicar en Mi área de trabajo y configurar credenciales y actualización.

## Cómo regenerar

```bash
python scripts/etl/elecciones_base.py --cache /tmp/cache     # base histórica (solo si hay elección nueva)
python scripts/etl/elecciones_mapa.py                        # geometría (una vez)
python scripts/etl/elecciones_a_notebook.py                  # notebook desde el .py
python scripts/powerbi/build_elecciones.py "out/Tablero Elecciones Argentina"
python scripts/powerbi/pbir_validate.py "out/Tablero Elecciones Argentina" /ruta/json-schemas
```

`scripts/powerbi/tmdlcheck/` valida el modelo con la librería oficial de Microsoft (TOM): `dotnet run -- "<carpeta>/definition"`.

## Para sumar una elección nueva (p. ej. 2027)

1. Agregar la elección en `ELECCIONES` de `scripts/etl/elecciones_base.py` y su fuente (DINE para diputados y PASO; CNE para el definitivo presidencial).
2. Agregar las reglas `PRES` de las fórmulas nuevas en `reglas_espacios.csv` y revisar el voto en "Otros".
3. Correr el armado de la base, subir los CSV y disparar el workflow (opción *elecciones*).
