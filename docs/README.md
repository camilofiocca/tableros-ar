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
