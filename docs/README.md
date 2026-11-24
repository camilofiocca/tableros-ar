# Documentación del Tablero Macro AR

Documentación completa del tablero: cada indicador, cada página, cada gráfico y cómo se construyó.

- Documento: https://docs.google.com/document/d/1DvXD3ywDbrLYq5D66CuIxoI8_MFSLe1BjqymKWDIn9Y/edit
- Carpeta única de Drive de los dos tableros (Macro AR y Energía AR): https://drive.google.com/drive/folders/1UhbLEthqxTQK40QCZrO1fIqJNuWRzMV-
- Subcarpeta Macro AR (documento, scripts, modelo y medidas): https://drive.google.com/drive/folders/1N162eY2ohutksyt7h38ZllfohoE5Ina1
- Subcarpeta Energía AR: https://drive.google.com/drive/folders/1T0DfaLjMJgTn0NtxW7Qt2gbf-emBTO1_
- Planilla de datos: https://docs.google.com/spreadsheets/d/1JkyIFA9AQt4_txuVIHwI9zfNR99iUHNzsujTBAlT_m8
- Notebook de referencia: [notebooks/Tablero Macro AR - ETL v3.ipynb](../notebooks/Tablero%20Macro%20AR%20-%20ETL%20v3.ipynb)

El repo es la versión de referencia de los notebooks y del workflow. La carpeta de Drive guarda el proyecto de Power BI, las medidas DAX y los scripts de construcción.

## Filtro de fechas (23/11/2026)

Las tablas mensuales (`series` en Macro; `series`, `empresas` y `cuencas` en Energía) tienen una columna oculta `'Año-Mes'` y se relacionan con `Calendario['Año-Mes']` de muchos a muchos, con filtro en un solo sentido. En Energía, la potencia instalada se relaciona por año. Las tarjetas de "último dato" muestran el último dato hasta el fin de la ventana elegida, con la medida:

```dax
Fin del período = CALCULATE ( MAX ( Calendario[Fecha] ), REMOVEFILTERS ( Rangos[Rango] ) )
```

No usar `REMOVEFILTERS ( Rangos )` entera: también tira el filtro de fechas del segmentador. Los scripts que generan el `Medidas.tmdl` nuevo están en `scripts/powerbi/`. Límites: el segmentador "desde/hasta" y los botones de período se intersectan (usar uno u otro), y el semáforo y los textos del Resumen muestran siempre el último dato publicado.

## Página Deuda (24/11/2026)

Deuda pública bruta de la Administración Central, externa e interna, con y sin intereses. Fuente: Boletín Mensual de la Secretaría de Finanzas (cuadros A.2, A.3 y A.5), en millones de dólares; la deuda en pesos se convierte al tipo de cambio de cada fecha.

- **ETL:** `scripts/etl/deuda_etl.py`, ejecutado por el notebook de Macro (celdas del paso de deuda). Escribe dos pestañas en la planilla de datos: `deuda` (fecha, id, valor) y `deuda_series` (id, grupo, serie, orden).
- **Modelo:** tablas `deuda` y `deuda_series`, relacionadas por `id`; `deuda['Año-Mes']` (oculta) se relaciona con `Calendario['Año-Mes']` igual que el resto de las series, así que el filtro de fechas funciona igual. 36 medidas nuevas en las carpetas "Deuda" y "Etiquetas" de `Medidas`.
- **Interpretación:** externa = legislación extranjera, interna = legislación argentina (no depende de quién tiene el bono). "Con intereses" = tasa fija o variable; "sin intereses" = tasa cero (LECAP, letras y bonos CER sin cupón), que no paga cupón pero rinde por descuento o inflación. Los intereses pagados son solo los intereses en efectivo: en cupón cero todo el pago figura como capital.
- **Control:** a octubre de 2026 el total es USD 489,6 mil M (externa 162,9; interna 326,7; con intereses 348,4; sin intereses 138,7).
- **Página (publicada y guardada el 24/11/2026, antes de "Mapa"):** 8 tarjetas (deuda total, % externa, % interna, % con intereses, % sin intereses, intereses pagados en 12 meses, % en moneda extranjera y variación interanual), 4 gráficos (interna vs. externa; por moneda y tasa; por instrumento; intereses pagados por mes), un cuadro de lectura automática (`Lectura de la deuda`) y las notas "Cómo leer esta página". Los botones de período (3 m / 1 año / 3 años / Todo) cambian los gráficos; las tarjetas muestran el último dato de la ventana elegida.
- **Pendiente:** el PBIP local no es idéntico a la versión publicada (los respaldos están en `_respaldo\antes de Deuda 2026-11-24` en la carpeta local del tablero); Power BI Desktop muestra "Aplicar cambios externos" y conviene no aplicarlo hasta decidir cuál es la versión buena. Falta sumar el Boletín Mensual al texto de "Datos y fuentes".

## Página Actividad con todos los sectores del EMAE (24/11/2026)

La página Actividad muestra ahora los 16 sectores del EMAE (INDEC) y no solo industria, construcción y agro.

- **ETL:** el notebook de Macro suma 13 series sectoriales (`emae_pesca`, `emae_minas`, `emae_electricidad`, `emae_comercio`, `emae_hoteles`, `emae_transporte`, `emae_financiero`, `emae_inmobiliario`, `emae_admin_publica`, `emae_ensenianza`, `emae_salud`, `emae_serv_comunitarios`, `emae_impuestos`) con sus rezagos tolerados (commit 1c25fa8). Se verificó que la hoja `kpis` de la planilla trae los 16 sectores (último dato: 2026-08-01).
- **Modelo:** medida `'Var. interanual sectores' = AVERAGE ( kpis[var_interanual] )` en la carpeta "Actividad" de `Medidas`; columnas calculadas `indicadores['Grupo actividad']` ("Sector EMAE" u "Otro") e `indicadores['Sector EMAE corto']` (nombre sin el prefijo "EMAE "). Las columnas calculadas necesitan un refresco del modelo antes de poder usarse en un visual.
- **Visual principal:** barras horizontales "¿Qué sectores crecen y cuáles caen?" con la variación interanual de cada sector, filtro de nivel de objeto visual `Grupo actividad = Sector EMAE`, etiquetas de datos, letra 10 y nombres completos (sin puntos suspensivos). Reemplaza al gráfico de 3 líneas (industria, construcción, agro), que se eliminó.
- **Distribución:** a la izquierda el gráfico de sectores; a la derecha una grilla de 2 × 2 (EMAE desestacionalizado, EMAE interanual, mercado laboral EPH y salario real), cada uno de 340 × 244 px.

## Glosario y ayuda "?" en todos los tableros (24/11/2026)

**Glosario (Macro AR):** página **Glosario** (la última, después de "Datos") con 63 términos agrupados en 7 bloques (conceptos generales, precios, actividad y empleo, dólar y reservas, tasas y dinero, externo y fiscal, deuda pública): qué significa cada indicador, sigla o concepto del tablero. Vive en una tabla calculada `Glosario` del modelo (`DATATABLE` con las columnas término, grupo y definición); no está en la planilla de datos, así que **solo existe en el modelo de Power BI**. Al escribirla en la vista TMDL de Power BI web, la tabla calculada tiene que llevar `source = ```` con las tres comillas invertidas en la **misma línea** que `source =`; si el bloque empieza en la línea siguiente, el modelo no valida. Respaldo del contenido: [`docs/glosario_macro.tmdl`](glosario_macro.tmdl) (script `createOrReplace` listo para pegar en la vista TMDL: Abrir modelo semántico → Vista TMDL → pegar → Aplicar). Para sacar una copia nueva: clic derecho en la tabla `Glosario` del panel Datos → Script de TMDL a → Pestaña Script. Si se agrega o cambia un término, actualizar el modelo y también este archivo.

**Ayuda "?" en cada tarjeta, gráfico y tabla:** al pasar el mouse por el "?" del encabezado aparece un texto con tres partes: *Qué mide*, *Cómo leerlo* y *Comparación* (contra qué se compara el dato). Cobertura:

| Tablero | Páginas con "?" |
|---|---|
| Macro AR | las 12 páginas de contenido (Resumen, Pulso, Precios, Actividad, Dólar, Convertibilidad, Monetario, Externo y fiscal, Deuda, Mapa, Explorador, Datos) |
| Energía AR | las 7 (Resumen, Matriz eléctrica, Petróleo y gas, Empresas, Electricidad, Gas natural, Comercio exterior) |

No llevan "?" los segmentadores, el navegador de páginas, los cuadros de texto, la tarjeta "Actualizado", la lectura de la deuda (visual "Tarjeta" nuevo, sin encabezado) ni los dos objetos de la página Glosario.

**Verificación (Macro, 24/11/2026):** se descargó el `.pbix` y se revisó por dentro. En ese formato (PBIR) cada visual es `Report/definition/pages/<página>/visuals/<visual>/visual.json` y el texto de la ayuda está en `visual.visualContainerObjects.visualHeaderTooltip[0].properties.text`. La primera descarga mostró 97 visuales con ayuda y 5 sin texto, aunque se habían escrito (tarjeta de salario real de Actividad, lectura y velocímetro de Pulso, cascada y lectura de Convertibilidad). Se corrigieron y la copia final tiene 102 visuales con ayuda; solo quedan sin ella los excluidos de arriba y la página oculta de tooltip. **Energía todavía no se auditó así**: se verificó solo una muestra en vista de lectura. Para auditarlo hay que bajar el `.pbix` de Energía y contar los `visualHeaderTooltip`.

**Causa de los textos perdidos:** escribir en el cuadro "Texto de información" y no confirmar. Lo que funcionó: después de escribir, presionar **Tab** (o hacer clic en una zona neutra del panel, como la etiqueta "Formato visual") y recién ahí Ctrl+S; hacer clic en los encabezados del panel (por ejemplo "Visualizaciones" o la sección "Íconos de encabezado") contrae la sección o el panel y puede perder el texto. Después de guardar hay que comprobarlo en vista de lectura o, mejor, en el `.pbix` descargado.

**Convención de los textos:** `Qué mide: … (fuente: …). Cómo leerlo: … Comparación: …`. No se escriben valores que se desactualicen (los números cambian con cada corrida del ETL); la fuente se cita al final de "Qué mide". Si cambia la definición de un indicador, hay que actualizar también su texto de ayuda y la entrada del Glosario.

**Cómo se configura (a mano, en Power BI web):** seleccionar el visual → Formato → General → buscar "Información sobre" → activar **Íconos de encabezado** (si está apagado) → dentro de **Íconos**, activar **Información sobre herramientas** → en la sección "Información sobre herramientas" de esos íconos, cuadro **Texto de información en…** (triple clic dentro y escribir) → clic en otra parte del panel para confirmar → Ctrl+S. No confundir con la sección "Información sobre herramientas" de General de arriba (tooltip al pasar sobre los datos) ni con el campo "Información so…" de la sección Acción de las imágenes. El texto se guarda con el informe y se ve en la vista de lectura.

**Trucos para hacerlo por automatización del navegador** (ventana de 1424 × 613, zoom 61 % en el editor):
- El panel Selección (Vista → Panel de selección) lista los visuales de arriba hacia abajo en la pila (no en el orden de la página), a 24 px de separación desde y ≈ 206; sirve para elegir cada visual sin errores.
- Gráficos y tablas (íconos de encabezado ya activos): clic en el visual del panel Selección → pestaña Formato → General → buscar "Información sobre" → activar el interruptor de **Información sobre herramientas** de la sección Íconos → colapsar Íconos → expandir la sección del texto → desplazar 2 pasos → triple clic en el cuadro y escribir.
- Tarjetas: igual, pero primero hay que activar **Íconos de encabezado** y expandir **Íconos**.
- Imágenes (por ejemplo el mapa): usan el panel "Formato de imagen", con otros controles; no tocar el campo de la sección Acción.
- Si el texto escrito no se confirma, volver a escribirlo: poner el foco con JavaScript sobre el `textarea` (`t.scrollIntoView(); t.focus(); t.select()`), escribir y soltar el foco (`t.blur()`); después Ctrl+S. Verificar siempre en vista de lectura que el tooltip no salga vacío.
- Si el visual ya tiene el ícono activado, el panel se ve distinto (el interruptor ya está en "Activado"): mirar antes de hacer clic para no apagarlo.

## Archivos locales y sincronización (24/11/2026)

Carpeta única en la computadora de Camilo: `Documentos\BI INTELLIGENCE\POWER BI\Tableros Argentina` (01 Macro AR, 02 Energia AR, 03 Automatizacion GitHub y `LEEME.md`). Los `.pbix` son copias completas (informe y datos) de la versión publicada. La versión principal es la de Power BI web; web y Desktop no se sincronizan solos:

- Si se edita en la web: descargar de nuevo el `.pbix` (Archivo → Descargar este archivo → copia con datos) y reemplazar el de la carpeta.
- Si se edita en Desktop: abrir el `.pbix` de esa carpeta y publicar desde ahí.
- No publicar nunca un archivo viejo. Las carpetas `Documentos\Tablero Macro Argentina` y `Documentos\Tablero Energia Argentina` son versiones viejas.
- **Estado al 24/11/2026:** el `.pbix` de `01 Macro AR` es la copia descargada de la web después del Glosario y de todos los "?" (995.174 bytes); la copia anterior quedó en `01 Macro AR\_respaldo`. El `.pbix` de `02 Energia AR` sigue siendo la copia anterior a los "?" de Energía: falta volver a bajarlo.
