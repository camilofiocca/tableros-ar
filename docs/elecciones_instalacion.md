# Tablero Elecciones AR — Instructivo de instalación y publicación

Paso a paso para dejar el tablero igual que Macro AR y Energía AR: un solo `.pbix` en la PC, publicado en Power BI web y con actualización automática.

## 0. Antes de empezar (una sola vez)

1. **Mergear el PR #1** en GitHub: https://github.com/camilofiocca/tableros-ar/pull/1 → botón verde *Merge pull request* → *Confirm merge*. Esto deja en `main` el notebook, el workflow con la opción `elecciones` y el archivo del mapa (`data/elecciones/mapa/provincias_ar.topojson`), que Power BI lee por URL.
2. Comprobar que la planilla **Elecciones AR - Datos limpios** esté compartida con `etl-tableros@tableros-ar.iam.gserviceaccount.com` como editor y con "cualquier persona con el enlace" como lector (ya está hecho).

## 1. Carpeta en la PC

Crear `C:\Users\Usuario\OneDrive\Documentos\BI INTELLIGENCE\POWER BI\Tableros Argentina\04 Elecciones AR` con la misma estructura que Macro y Energía:

```
04 Elecciones AR\
  Tablero Elecciones AR.pbix        ← el único archivo de Power BI del tablero
  ETL\Tablero Elecciones AR - ETL v1.ipynb
  Documentacion\ (este instructivo y la documentación técnica)
  _proyecto\ (el PBIP descomprimido; se puede borrar una vez guardado el .pbix)
```

Archivos en Drive (Tableros AR → Elecciones AR):
- 02 Power BI → `Tablero Elecciones AR (PBIP).zip`
- 01 Datos y automatización → `Tablero Elecciones AR - ETL v1.ipynb` y la planilla
- 03 Scripts de construcción → `Scripts y datos de construcción - Elecciones AR.zip`

## 2. Abrir y actualizar en Power BI Desktop

1. Descomprimir `Tablero Elecciones AR (PBIP).zip` en `04 Elecciones AR\_proyecto`.
2. Abrir `_proyecto\Tablero Elecciones Argentina\Tablero Elecciones AR.pbip` (doble clic).
3. Inicio → **Actualizar**. Si pide credenciales para `docs.google.com`: **Anónimo** → Conectar. Nivel de privacidad: **Público**.
4. Revisar las 8 páginas (Resumen, Mapa, Por espacio, Presidenciales, Intermedias, Evolución, Participación, Datos).
   - Si un **mapa de formas** aparece vacío: seleccionarlo → Formato → *Configuración del mapa* → Tipo: **URL** → pegar
     `https://raw.githubusercontent.com/camilofiocca/tableros-ar/main/data/elecciones/mapa/provincias_ar.topojson`.
   - Si las provincias salen grises: Formato → *Colores* → *Predeterminado* → **fx** → Estilo: *Valor del campo* → medida `Color ganador` (en "Por espacio": `Color intensidad del espacio`; en "Participación": `Color participación`).
   - Si en tu versión de Power BI no aparece el mapa de formas: Archivo → Opciones → Características en versión preliminar → *Objeto visual de mapa de formas* → reiniciar.
5. **Archivo → Guardar como** → `04 Elecciones AR\Tablero Elecciones AR.pbix` (tipo: archivo de Power BI .pbix). Desde ahí se trabaja siempre con ese `.pbix`.

## 3. Publicar en Power BI web

1. Con el `.pbix` abierto: Inicio → **Publicar** → *Mi área de trabajo*.
2. En app.powerbi.com → Mi área de trabajo → modelo semántico **Tablero Elecciones AR** → ⋯ → *Configuración*:
   - *Credenciales del origen de datos* → Editar → Método: **Anónimo**, Privacidad: **Pública** → Iniciar sesión.
   - *Actualización programada*: activar; zona horaria Buenos Aires; lunes a viernes a las **10:30** (con una por día alcanza: los resultados solo cambian cuando hay elecciones).
3. Probar con *Actualizar ahora* y abrir el informe.

## 4. Automatización (GitHub Actions)

- El workflow **Actualizar tableros** corre el notebook de Elecciones los lunes 09:47.
- A mano: GitHub → Actions → *Actualizar tableros* → *Run workflow* → opción **elecciones** (o **todos**).
- Después de la primera corrida, revisar en la planilla las hojas `info` (última actualización y errores), `control` y `control_dine`.

## 5. Regla de sincronización (igual que los otros tableros)

Power BI web y Desktop no se sincronizan solos. Si se edita en la web, bajar de nuevo el `.pbix` (Archivo → Descargar este archivo → copia con datos) y reemplazar el de `04 Elecciones AR`. Si se edita en Desktop, abrir el `.pbix` de `04 Elecciones AR` y publicar desde ahí. Nunca publicar un archivo viejo.
