using Microsoft.AnalysisServices.Tabular;
var carpeta = args[0];
try {
    var db = TmdlSerializer.DeserializeDatabaseFromFolder(carpeta);
    var m = db.Model;
    Console.WriteLine($"OK · compat {db.CompatibilityLevel} · tablas {m.Tables.Count} · relaciones {m.Relationships.Count} · medidas {m.Tables.Sum(t => t.Measures.Count)} · expresiones {m.Expressions.Count}");
    foreach (var t in m.Tables) Console.WriteLine($"  {t.Name}: {t.Columns.Count} columnas, {t.Measures.Count} medidas, particiones {t.Partitions.Count} ({string.Join(",", t.Partitions.Select(p => p.SourceType.ToString()))})");
    foreach (var c in m.Tables.SelectMany(t => t.Columns).Where(c => c.SortByColumn != null)) Console.WriteLine($"  orden: {c.Table.Name}[{c.Name}] por [{c.SortByColumn.Name}]");
} catch (Exception e) {
    Console.WriteLine("ERROR: " + e.GetType().Name + ": " + e.Message);
    if (e.InnerException != null) Console.WriteLine("  " + e.InnerException.Message);
    Environment.Exit(1);
}
