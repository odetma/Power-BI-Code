# Copies source files only. Setup is a separate, explicit step.
[CmdletBinding()]
param([string]$Destination)
$ErrorActionPreference = 'Stop'
$source = Join-Path (Split-Path $PSScriptRoot -Parent) 'skills\powerbi-report-builder'
if (-not $Destination) {
    $skillHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE '.codex' }
    $Destination = Join-Path $skillHome 'skills\powerbi-report-builder'
}
$Destination = [IO.Path]::GetFullPath($Destination)
if (Test-Path -LiteralPath $Destination) { throw 'Destination already exists. Back it up and choose a new empty destination; installation never overwrites an existing skill.' }
if (-not (Test-Path -LiteralPath (Join-Path $source 'SKILL.md'))) { throw 'Run this installer from a complete Power-BI-Code checkout.' }
$files = @(Get-ChildItem -LiteralPath $source -Recurse -File | Where-Object {
    $_.FullName.Substring($source.Length).Split('\') -notcontains '.venv' -and
    $_.FullName.Substring($source.Length).Split('\') -notcontains '.runtime' -and
    $_.FullName.Substring($source.Length).Split('\') -notcontains 'node_modules' -and
    $_.FullName.Substring($source.Length).Split('\') -notcontains '__pycache__' -and
    $_.Extension -ne '.pyc'
})
foreach ($file in $files) {
    $relative = $file.FullName.Substring($source.Length).TrimStart('\')
    $target = Join-Path $Destination $relative
    New-Item -ItemType Directory -Force -Path (Split-Path $target -Parent) | Out-Null
    Copy-Item -LiteralPath $file.FullName -Destination $target
}
Write-Output "Installed source files to $Destination"
Write-Output "Next: & '$Destination\scripts\setup.ps1'"
Write-Output 'Restart your AI client or reload its skills after installation.'
