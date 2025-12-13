var Safe = (System.Func<string, string>)(s => string.IsNullOrWhiteSpace(s) ? "" : s.Trim());

var definitionFolder = @"C:\Users\user\Downloads\Power BI Project\Playground.SemanticModel\definition";

// Output file
var outputPath = @"C:\Users\user\Downloads\Power BI Project\model_export.txt";

// Definition-level files (optional)
var functionsFile = System.IO.Path.Combine(definitionFolder, "functions.tmdl");
var rolesFolder = System.IO.Path.Combine(definitionFolder, "roles");

using (var writer = new System.IO.StreamWriter(outputPath, false))
{
    // =========================
    // Model metadata (from TOM)
    // =========================

    writer.WriteLine("Tables:");
    writer.WriteLine(new string('=', 50));
    foreach (var table in Model.Tables)
    {
        writer.WriteLine("  - " + table.Name);
    }
    writer.WriteLine(new string('-', 50));
    writer.WriteLine();

    foreach (var table in Model.Tables)
    {
        writer.WriteLine("Table: " + table.Name);
        writer.WriteLine(new string('=', 50));

        // Table Description
        var tableDesc = Safe(table.Description);
        if (tableDesc != "")
        {
            writer.WriteLine("Description:");
            writer.WriteLine("  " + tableDesc);
            writer.WriteLine();
        }

        // Regular Columns (non-calculated)
        writer.WriteLine("Columns:");
        foreach (var column in table.Columns)
        {
            if (!(column is CalculatedColumn))
            {
                writer.WriteLine("  - " + column.Name + " (" + column.DataType.ToString() + ")");

                var colDesc = Safe(column.Description);
                if (colDesc != "")
                {
                    writer.WriteLine("    Description: " + colDesc);
                }
            }
        }

        // Calculated Columns
        if (table.CalculatedColumns.Count() > 0)
        {
            writer.WriteLine("Calculated Columns:");
            foreach (var calc in table.CalculatedColumns)
            {
                writer.WriteLine("  - " + calc.Name);

                var calcDesc = Safe(calc.Description);
                if (calcDesc != "")
                {
                    writer.WriteLine("    Description: " + calcDesc);
                }

                writer.WriteLine("    DAX: " + calc.Expression);
            }
        }

        // Measures
        if (table.Measures.Count() > 0)
        {
            writer.WriteLine("Measures:");
            foreach (var measure in table.Measures)
            {
                writer.WriteLine("  - " + measure.Name);

                var msrDesc = Safe(measure.Description);
                if (msrDesc != "")
                {
                    writer.WriteLine("    Description: " + msrDesc);
                }

                writer.WriteLine("    DAX: " + measure.Expression);
            }
        }

        // Partitions (Data Source Queries)
        if (table.Partitions.Count() > 0)
        {
            writer.WriteLine("Partitions:");
            int partIndex = 1;
            foreach (var partition in table.Partitions)
            {
                writer.WriteLine("  Partition " + partIndex + " Query:");
                writer.WriteLine(partition.Query);
                partIndex++;
            }
        }

        writer.WriteLine(new string('-', 50));
        writer.WriteLine();
    }

    // Relationships (TE2 SingleColumnRelationship has no Description)
    writer.WriteLine("Relationships:");
    writer.WriteLine(new string('=', 50));
    foreach (var rel in Model.Relationships)
    {
        writer.WriteLine("  - " + rel.FromTable.Name + "[" + rel.FromColumn.Name + "]" +
                         " -> " + rel.ToTable.Name + "[" + rel.ToColumn.Name + "]");
        writer.WriteLine("    Active: " + rel.IsActive.ToString());
        writer.WriteLine("    Cardinality: " + rel.FromCardinality.ToString() + " : " + rel.ToCardinality.ToString());
        writer.WriteLine("    CrossFilterDirection: " + rel.CrossFilteringBehavior.ToString());
        writer.WriteLine();
    }

    // =========================
    // Definition-level files
    // =========================

    writer.WriteLine();
    writer.WriteLine("Definition Files:");
    writer.WriteLine(new string('=', 50));
    writer.WriteLine("Definition folder: " + definitionFolder);
    writer.WriteLine();

    // functions.tmdl (optional)
    writer.WriteLine("functions.tmdl:");
    writer.WriteLine(new string('-', 50));
    if (System.IO.File.Exists(functionsFile))
    {
        writer.WriteLine(System.IO.File.ReadAllText(functionsFile));
    }
    else
    {
        writer.WriteLine("Not found (skipped): " + functionsFile);
    }
    writer.WriteLine(new string('-', 50));
    writer.WriteLine();

    // roles\*.tmdl (optional)
    writer.WriteLine("roles:");
    writer.WriteLine(new string('-', 50));
    if (System.IO.Directory.Exists(rolesFolder))
    {
        var roleFiles = System.IO.Directory.GetFiles(rolesFolder, "*.tmdl", System.IO.SearchOption.TopDirectoryOnly);
        if (roleFiles.Length == 0)
        {
            writer.WriteLine("No .tmdl files found in roles folder.");
        }
        else
        {
            System.Array.Sort(roleFiles, System.StringComparer.OrdinalIgnoreCase);
            foreach (var rf in roleFiles)
            {
                writer.WriteLine("File: " + System.IO.Path.GetFileName(rf));
                writer.WriteLine(new string('.', 50));
                writer.WriteLine(System.IO.File.ReadAllText(rf));
                writer.WriteLine(new string('.', 50));
                writer.WriteLine();
            }
        }
    }
    else
    {
        writer.WriteLine("Not found (skipped): " + rolesFolder);
    }
    writer.WriteLine(new string('-', 50));
}

Output("Exported model metadata + optional definition files to: " + outputPath);
