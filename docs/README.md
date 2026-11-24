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
