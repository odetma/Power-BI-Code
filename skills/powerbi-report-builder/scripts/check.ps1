# Read-only environment check. Does not open, reload, or modify any report.
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\runtime.ps1"
$results = [ordered]@{}
$ok = $true
if ($env:OS -ne 'Windows_NT') { Write-Error 'Desktop helpers require Windows.'; exit 1 }
$versions = @()
$exe = Join-Path $env:ProgramFiles 'Microsoft Power BI Desktop\bin\PBIDesktop.exe'
if (Test-Path -LiteralPath $exe) { $versions += [version](Get-Item -LiteralPath $exe).VersionInfo.ProductVersion.Split(' ')[0] }
if (Get-Command Get-AppxPackage -ErrorAction SilentlyContinue) {
    $versions += @(Get-AppxPackage -Name '*MicrosoftPowerBIDesktop*' -ErrorAction SilentlyContinue | ForEach-Object { [version]$_.Version })
}
if (-not $versions -or ($versions | Sort-Object -Descending | Select-Object -First 1) -lt [version]'2.159.0.0') {
    $results['Power BI Desktop'] = 'MISSING/OLD: install Desktop 2.159+ with the Desktop Bridge'; $ok = $false
} else { $results['Power BI Desktop'] = "OK $(($versions | Sort-Object -Descending)[0])" }
try {
    $node = Get-PbiNode
    $version = & $node --version
    if ([int]($version.TrimStart('v').Split('.')[0]) -lt 20) { throw 'Node.js 20+ required.' }
    $results['Node.js'] = "OK $version"
} catch { $results['Node.js'] = $_.Exception.Message; $ok = $false }
try {
    $python = Get-PbiPython
    & $python -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)'
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.10+ required.' }
    $results['Python'] = "OK $(& $python --version)"
    & $python "$PSScriptRoot\confirm-source-warning.py" --check-dependencies
    if ($LASTEXITCODE -ne 0) { throw 'Native UIA dependency missing or unavailable; run setup.ps1.' }
    $results['Native UIA'] = 'OK CUIAutomation8 + comtypes'
} catch { $results['Python / UIA'] = $_.Exception.Message; $ok = $false }
try { $results['Desktop Bridge'] = "OK $(Get-PbiBridge)" } catch { $results['Desktop Bridge'] = $_.Exception.Message; $ok = $false }
$author = Join-Path $PbiBuilderRoot '.runtime\node\node_modules\.bin\powerbi-report-author.cmd'
$results['Authoring metadata'] = if (Test-Path -LiteralPath $author) { 'OK (skill-local)' } else { 'Optional CLI absent; use an installed metadata/schema tool before authoring' }
if (Get-Command git -ErrorAction SilentlyContinue) { $results['Git'] = 'OK' } else { $results['Git'] = 'MISSING'; $ok = $false }
$results.GetEnumerator() | ForEach-Object { '{0,-22} {1}' -f $_.Key, $_.Value }
if ($ok) { 'All required local prerequisites passed. Check modeling MCP availability in your AI client separately.' }
exit ([int](-not $ok))
