# Checks every PBIP text file changed vs a base ref (committed, staged, unstaged and new untracked files):
# conflict markers, unparseable JSON, duplicate keys, BOMs. Wrapper around validate.py (stdlib Python only).
# Usage (from anywhere inside the repo): .\validate.ps1 [-Base origin/main]
#        .\validate.ps1 -All <folder>     check every file under a folder instead
param([string]$Base = 'origin/main', [string]$All = '')
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\runtime.ps1"
$python = Get-PbiPython
if ($All) {
    & $python "$PSScriptRoot\validate.py" --all $All
} else {
    & $python "$PSScriptRoot\validate.py" --base $Base --root (Get-Location).Path
}
exit $LASTEXITCODE
