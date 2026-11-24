# tmdlcheck

Valida una carpeta TMDL (`<modelo>.SemanticModel/definition`) con la librería oficial de Microsoft (TOM), la misma que usa Power BI Desktop para leerla.

Las DLL de TOM vienen dentro del paquete de Python `semantic-link-sempy` (`pip install --no-deps semantic-link-sempy`), en `sempy/lib`. Con .NET 8:

```bash
dotnet run -p:TOM_LIB=/ruta/a/sempy/lib -- "out/Tablero Elecciones Argentina/Tablero Elecciones AR.SemanticModel/definition"
```

`nuget.config` deja la restauración sin fuentes externas (no hace falta NuGet).
