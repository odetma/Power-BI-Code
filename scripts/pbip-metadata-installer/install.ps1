#requires -Version 5.1
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)][string]$RepositoryPath,
    [string[]]$SourceDirectories,
    [string]$DocumentationBranch,
    [switch]$WithService,
    [switch]$WithoutService,
    [switch]$Upgrade,
    [string]$PythonExecutable = 'python'
)

$ErrorActionPreference = 'Stop'
if ($WithService -and $WithoutService) {
    throw 'Choose either -WithService or -WithoutService.'
}
$installer = Join-Path $PSScriptRoot 'install.py'
$installerArgs = @($installer, '--repository', $RepositoryPath)
foreach ($sourceDirectory in $SourceDirectories) { $installerArgs += @('--source', $sourceDirectory) }
if ($DocumentationBranch) { $installerArgs += @('--documentation-branch', $DocumentationBranch) }
if ($WithService) { $installerArgs += '--with-service' }
if ($WithoutService) { $installerArgs += '--without-service' }
if ($Upgrade) { $installerArgs += '--upgrade' }

if ($WhatIfPreference) {
    $installerArgs += '--dry-run'
} elseif (-not $PSCmdlet.ShouldProcess($RepositoryPath, 'Install the PBIP metadata documentation pipeline')) {
    return
}

& $PythonExecutable @installerArgs
if ($LASTEXITCODE -ne 0) { throw "Installation failed (exit code $LASTEXITCODE)." }
