# Dependency discovery only. No PATH, registry, or machine configuration changes.
$PbiBuilderRoot = Split-Path -Parent $PSScriptRoot

function Get-PbiPython {
    $local = Join-Path $PbiBuilderRoot '.venv\Scripts\python.exe'
    if (Test-Path -LiteralPath $local) { return $local }
    if ($env:PBI_BUILDER_PYTHON) {
        if (-not (Test-Path -LiteralPath $env:PBI_BUILDER_PYTHON)) { throw 'PBI_BUILDER_PYTHON must name a Python executable.' }
        return (Resolve-Path -LiteralPath $env:PBI_BUILDER_PYTHON).Path
    }
    foreach ($name in @('python.exe', 'python')) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command -and $command.Source -notlike '*\Microsoft\WindowsApps\*') { return $command.Source }
    }
    $launcher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($launcher) {
        $path = & $launcher.Source -3 -c 'import sys; print(sys.executable)'
        if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $path)) { return $path }
    }
    throw 'Python 3.10+ not found. Install Python on PATH, or set PBI_BUILDER_PYTHON to its executable.'
}

function Get-PbiNode {
    if ($env:PBI_BUILDER_NODE) {
        if (-not (Test-Path -LiteralPath $env:PBI_BUILDER_NODE)) { throw 'PBI_BUILDER_NODE must name a Node executable.' }
        return (Resolve-Path -LiteralPath $env:PBI_BUILDER_NODE).Path
    }
    $command = Get-Command node -ErrorAction SilentlyContinue
    if (-not $command) { throw 'Node.js 20+ not found. Install Node.js on PATH, or set PBI_BUILDER_NODE.' }
    return $command.Source
}

function Get-PbiBridge {
    $local = Join-Path $PbiBuilderRoot '.runtime\node\node_modules\.bin\powerbi-desktop.cmd'
    if (Test-Path -LiteralPath $local) { return $local }
    $command = Get-Command powerbi-desktop.cmd -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    throw 'Desktop Bridge CLI not found. Run scripts/setup.ps1.'
}

function Get-PbiReportDirectory([string]$CurrentFile) {
    if (-not $CurrentFile) { throw 'Desktop did not return a report path. Wait for loading or handle the blocking dialog.' }
    $path = [IO.Path]::GetFullPath($CurrentFile)
    if ($path -like '*.pbip') {
        $project = [IO.File]::ReadAllText($path) | ConvertFrom-Json
        $reports = @($project.artifacts | Where-Object { $_.report.path })
        if ($reports.Count -ne 1) { throw 'PBIP must contain exactly one report artifact.' }
        $path = [IO.Path]::GetFullPath((Join-Path (Split-Path $path -Parent) $reports[0].report.path))
    } elseif ((Split-Path $path -Leaf) -eq 'definition.pbir') {
        $path = Split-Path $path -Parent
    }
    if (-not (Test-Path -LiteralPath (Join-Path $path 'definition\pages'))) { throw "PBIR pages not found under $path" }
    return $path
}
