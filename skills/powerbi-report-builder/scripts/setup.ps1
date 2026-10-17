# Installs pinned dependencies inside this skill. Desktop, Node and Python are prerequisites.
[CmdletBinding()]
param([switch]$SkipAuthoringCli)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\runtime.ps1"
if ($env:OS -ne 'Windows_NT') { throw 'Desktop authoring helpers require Windows.' }
$python = Get-PbiPython
& $python -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)'
if ($LASTEXITCODE -ne 0) { throw 'Python 3.10+ is required.' }
$node = Get-PbiNode
$nodeVersion = & $node --version
if ($LASTEXITCODE -ne 0 -or [int]$nodeVersion.TrimStart('v').Split('.')[0] -lt 20) { throw 'Node.js 20+ is required.' }
$npmPath = Join-Path (Split-Path $node -Parent) 'npm.cmd'
if (-not (Test-Path -LiteralPath $npmPath)) {
    $npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if (-not $npmCommand) { throw 'npm.cmd not found. Install the Node.js distribution including npm.' }
    $npmPath = $npmCommand.Source
}
$venvPython = Join-Path $PbiBuilderRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    & $python -m venv (Join-Path $PbiBuilderRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the skill-local Python environment.' }
}
& $venvPython -m pip install --disable-pip-version-check -r "$PSScriptRoot\requirements.txt"
if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
$prefix = Join-Path $PbiBuilderRoot '.runtime\node'
$packages = @('@microsoft/powerbi-desktop-bridge-cli@1.0.0')
if (-not $SkipAuthoringCli) { $packages += '@microsoft/powerbi-report-authoring-cli@0.5.0' }
# CLI shebangs need the selected Node for this process; never persist PATH changes.
$env:Path = "$(Split-Path $node -Parent);$env:Path"
& $npmPath install --prefix $prefix --no-fund --no-audit --no-package-lock @packages
if ($LASTEXITCODE -ne 0) { throw 'CLI dependency installation failed.' }
& "$PSScriptRoot\check.ps1"
if ($LASTEXITCODE -ne 0) { throw 'Installed dependencies, but a prerequisite check failed. See the output above.' }
