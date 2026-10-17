# Synthetic PBIR/PBIP resolution and installer checks; no Desktop mutations.
$ErrorActionPreference = 'Stop'
$repo = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
. "$repo\skills\powerbi-report-builder\scripts\runtime.ps1"
$fixture = Join-Path ([IO.Path]::GetTempPath()) ('PBIR runtime ' + [guid]::NewGuid().ToString('N'))
$report = Join-Path $fixture 'Different Name.Report'
New-Item -ItemType Directory -Force (Join-Path $report 'definition\pages') | Out-Null
$pbip = Join-Path $fixture 'Launcher.pbip'
[IO.File]::WriteAllText($pbip, '{"artifacts":[{"report":{"path":"Different Name.Report"}}]}')
$actual = Get-PbiReportDirectory $pbip
if ($actual -ne $report) { throw 'PBIP artifact path was not resolved correctly.' }
[IO.File]::WriteAllText((Join-Path $report 'definition.pbir'), '{}')
if ((Get-PbiReportDirectory (Join-Path $report 'definition.pbir')) -ne $report) { throw 'PBIR path resolution failed.' }
$missing = Join-Path $fixture 'Missing.pbip'
[IO.File]::WriteAllText($missing, '{"artifacts":[{"report":{"path":"Missing.Report"}}]}')
$rejected = $false
try { Get-PbiReportDirectory $missing | Out-Null } catch { $rejected = $true }
if (-not $rejected) { throw 'Missing report path was not rejected.' }
$install = Join-Path $fixture 'New user skill'
& "$repo\scripts\install-powerbi-report-builder.ps1" -Destination $install
if (-not (Test-Path -LiteralPath "$install\SKILL.md")) { throw 'Installer omitted SKILL.md.' }
$rejected = $false
try { & "$repo\scripts\install-powerbi-report-builder.ps1" -Destination $install } catch { $rejected = $true }
if (-not $rejected) { throw 'Installer overwrote an existing skill.' }
if (Test-Path -LiteralPath "$install\.runtime") { throw 'Installer copied generated dependencies.' }
Write-Output 'PASS: PBIR/PBIP paths with spaces, nonmatching launcher name, missing path, source-only install, existing destination refusal.'
Write-Output "Synthetic fixtures retained at $fixture"
