# Automatización de los tableros Macro AR y Energía AR

Este repo corre solo los días hábiles: el ETL Macro cada 30 minutos de 8 a 20 h y el de Energía dos veces por día
(sus datos son mensuales). Los notebooks están en `notebooks/` y actualizan las planillas **Macro AR - Datos limpios** y **Energía AR - Datos limpios** en Google Drive.
Power BI (web) después se refresca contra esas planillas con su propia actualización programada.

```
APIs oficiales (INDEC, BCRA, Sec. Energía, ArgentinaDatos)
        │  (GitHub Actions, cada 30 min, lun-vie 8 a 20 h)
        ▼
Notebooks ETL  ──escriben──►  Google Sheets  ──refresco programado──►  Power BI Service (web)
```

Los mismos notebooks siguen funcionando en Colab (para desarrollar o correr a mano):
detectan solos dónde están corriendo y eligen la autenticación correcta.

## Puesta en marcha (una sola vez, ~20 minutos)

### 1. Crear la cuenta de servicio de Google
1. Entrá a [console.cloud.google.com](https://console.cloud.google.com) con tu cuenta (camilofiocca@gmail.com).
2. Creá un proyecto (ej. `tableros-ar`) si no tenés uno.
3. **APIs y servicios → Habilitar APIs**: habilitá **Google Sheets API** y **Google Drive API**.
4. **IAM y administración → Cuentas de servicio → Crear cuenta de servicio** (ej. `etl-tableros`). No hace falta darle roles.
5. Entrá a la cuenta creada → pestaña **Claves → Agregar clave → Crear clave nueva → JSON**. Se descarga un archivo `.json`: esa es la credencial.

### 2. Compartir las planillas con la cuenta de servicio
La cuenta de servicio tiene un mail propio (algo como `etl-tableros@tableros-ar.iam.gserviceaccount.com`, figura en el JSON como `client_email`).
Compartí **las dos planillas** con ese mail como **Editor** (botón Compartir, igual que con una persona).

### 3. Crear el repo en GitHub y cargar el secreto
1. Creá un repositorio en GitHub (ej. `tableros-ar`; si es público, los minutos de Actions son ilimitados) y subí el contenido de esta carpeta.
2. En el repo: **Settings → Secrets and variables → Actions → New repository secret**.
   - Name: `GOOGLE_SA_JSON`
   - Secret: pegá el **contenido completo** del archivo JSON de la cuenta de servicio.
3. En la pestaña **Actions**, habilitá los workflows si GitHub lo pide.

### 4. Probar
En **Actions → Actualizar tableros → Run workflow**: corré una vez a mano y verificá que las dos
planillas tengan la `ultima_actualizacion` de recién (hojas `metadata` e `info`).

## Horarios
Definidos en `.github/workflows/actualizar.yml` (en UTC; Argentina es UTC-3):
- Macro: cada 30 minutos de 08:00 a 20:00 (hora argentina), de lunes a viernes (25 corridas por día).
- Energía: 09:10 y 18:10, de lunes a viernes.
GitHub puede demorar los crons algunos minutos; es normal. Feriados: corre igual (no molesta).

## Refresco de Power BI web (importante: depende de la licencia)
Las planillas se actualizan cada 30 minutos, pero Power BI web tiene que volver a leerlas:
**Área de trabajo → modelo semántico → Configuración → Actualización programada**.
- **Power BI Pro / gratuito**: máximo **8 actualizaciones por día** por modelo. Horarios sugeridos:
  08:30, 10:00, 11:30, 13:00, 14:30, 16:00, 17:30 y 20:00.
- **Premium por usuario (PPU)**: hasta 48 por día → se puede poner cada 30 minutos de 08:00 a 20:00.
En ambos casos, en **Credenciales del origen de datos** la planilla tiene que poder leerse: lo más simple es
compartir cada planilla como "Cualquier persona con el enlace: lector" (son datos públicos) y elegir
autenticación **Anónima**.

## Avisos si algo falla
GitHub te manda un mail automáticamente cuando un workflow falla (configurable en tu cuenta de
GitHub → Settings → Notifications → Actions). Además, los propios ETL dejan registrado en las
planillas (`metadata` / `info` y `cobertura`) qué series fallaron o quedaron atrasadas, así el
problema se ve en el tablero y no pasa inadvertido.

## Mantener los notebooks sincronizados
El notebook "de verdad" es el de este repo. Si lo editás en Colab, usá
**Archivo → Guardar una copia en GitHub** para actualizar el repo (Colab se conecta a GitHub desde
esa misma opción la primera vez). Si preferís seguir trabajando desde Drive, acordate de subir la
versión nueva al repo cuando cambies algo.

## Alternativa sin GitHub
Si en algún momento pagás **Colab Pro**, podés programar los notebooks directamente desde Colab
(Entorno de ejecución → Programar) y este repo deja de ser necesario. La ventaja de GitHub Actions
es que es gratis y queda un historial de corridas.
