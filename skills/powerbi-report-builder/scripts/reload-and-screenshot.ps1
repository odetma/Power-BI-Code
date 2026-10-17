# Reload the report open in Power BI Desktop and capture screenshots of the given pages.
#
# Reload once through the Desktop Bridge (pbir-reload.mjs, so it also works for reports opened from definition.pbir),
# then for each page: select its page tab in Desktop through UI Automation, wait for the render, and capture the
# window with capture-window.ps1 (Windows PrintWindow). With -ConfirmMultipleSourceWarning,
# only the authorized warning is invoked through UIA; other dialogs require manual handling.
# The bridge's own screenshot is never used: it can leave Desktop's window stuck (see references/gotchas.md).
# No report file is changed.
#
# Usage:
#   .\reload-and-screenshot.ps1 [-Pages <id1>,<id2>] [-OutDir <dir>] [-ProcessId <pid>] [-NoReload] [-Model] [-ConfirmMultipleSourceWarning]
#   -Pages      page ids = folder names under <name>.Report\definition\pages\. Omit to capture the current page.
#   -NoReload   capture without reloading first
#   -Model      also reload the semantic model definition
# Output: one JSON line per step; screenshots in <OutDir>\<pageId or 'current'>.png
param(
    [string[]]$Pages = @(),
    [string]$OutDir = (Join-Path $env:TEMP 'pbi-screenshots'),
    [int]$ProcessId = 0,
    [switch]$NoReload,
    [switch]$Model,
    [switch]$ConfirmMultipleSourceWarning,
    [switch]$AllowDiscardUnsavedChanges,
    [switch]$RestoreMinimized,
    [int]$RenderWaitSeconds = 10,
    [int]$PageWaitSeconds = 6
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\runtime.ps1"
. "$PSScriptRoot\confirm-source-warning.ps1"
$Pages = @($Pages | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ })   # "a,b" arrives as one string via -File

$node = Get-PbiNode
$env:Path = "$(Split-Path $node);$env:Path"   # so powerbi-desktop (next to node or in npm's global bin) resolves
$bridge = Get-PbiBridge

$statusText = & $bridge status
if ($LASTEXITCODE -ne 0) { throw 'Desktop Bridge status failed. Check Desktop for loading or a blocking dialog.' }
$status = $statusText | ConvertFrom-Json
$instances = @($status.instances)
if ($ProcessId -eq 0) {
    if ($instances.Count -eq 0) { throw 'No Power BI Desktop instance with the bridge is running. Open the report first.' }
    if ($instances.Count -gt 1) {
        throw "Several Desktop instances are open; pass -ProcessId. $(($instances | ForEach-Object { "$($_.pid): $($_.currentFilePath)" }) -join '; ')"
    }
    $ProcessId = [int]$instances[0].pid
}
$current = ($instances | Where-Object { [int]$_.pid -eq $ProcessId } | Select-Object -First 1).currentFilePath
if (-not ($instances | Where-Object { [int]$_.pid -eq $ProcessId })) { throw 'Selected Desktop process is not available through the bridge.' }
if (-not $NoReload) {
    $selected = $instances | Where-Object { [int]$_.pid -eq $ProcessId } | Select-Object -First 1
    if ($selected.hasUnsavedChanges -ne $false -and -not $AllowDiscardUnsavedChanges) {
        throw 'Desktop has unsaved or unknown state. Resolve manually; pass -AllowDiscardUnsavedChanges only after user authorization.'
    }
}

function Get-PagesDir([string]$currentFile) {
    # currentFile is <name>.Report\definition.pbir, <name>.Report, or <name>.pbip
    $reportDir = Get-PbiReportDirectory $currentFile
    $dir = Join-Path $reportDir 'definition\pages'
    if (-not (Test-Path -LiteralPath $dir)) { throw "Pages folder not found for $currentFile" }
    return $dir
}

function Select-PageTab([string]$pagesDir, [string]$pageId) {
    # Desktop ignores pages.json activePageName on reload, so switch pages by selecting the page tab
    # (a UI Automation TabItem named after the page's displayName, with SelectionItemPattern).
    $pageJson = Join-Path $pagesDir "$pageId\page.json"
    $resolvedPage = [IO.Path]::GetFullPath($pageJson)
    $prefix = [IO.Path]::GetFullPath($pagesDir).TrimEnd('\') + '\'
    if (-not $resolvedPage.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) { throw 'Page ID escapes the report pages directory.' }
    if (-not (Test-Path -LiteralPath $pageJson)) { throw "Page '$pageId' not found in $pagesDir" }
    $name = ([IO.File]::ReadAllText($pageJson) | ConvertFrom-Json).displayName
    Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
    $AE = [System.Windows.Automation.AutomationElement]
    $win = $AE::FromHandle((Get-Process -Id $ProcessId).MainWindowHandle)
    # Page tabs are TabItems whose class contains 'section'. Desktop prefixes some names:
    # "Report landing page <name>" for the landing page, "Hidden <name>" for hidden pages.
    $cond = New-Object System.Windows.Automation.PropertyCondition($AE::ControlTypeProperty, [System.Windows.Automation.ControlType]::TabItem)
    $tabs = @($win.FindAll([System.Windows.Automation.TreeScope]::Descendants, $cond) |
        Where-Object { $_.Current.ClassName -like '*section*' -and ($_.Current.Name -eq $name -or $_.Current.Name -eq "Hidden $name" -or $_.Current.Name -eq "Report landing page $name") })
    if ($tabs.Count -ne 1) { throw "Expected one page tab '$name', found $($tabs.Count). Check dialogs or duplicate display names." }
    $tab = $tabs[0]
    $tab.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern).Select()
    Write-Output (@{ step = 'page'; page = $pageId; name = $name } | ConvertTo-Json -Compress)
    Start-Sleep -Seconds $PageWaitSeconds   # let the page render
}

function Restore-Window {
    # UI Automation can't reach the page tabs of a minimized window
    if (-not ('PbiReloadShot.Win' -as [type])) { Add-Type -Namespace PbiReloadShot -Name Win -MemberDefinition '[DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h); [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);' }
    $h = (Get-Process -Id $ProcessId).MainWindowHandle
    if ([PbiReloadShot.Win]::IsIconic($h)) {
        if (-not $RestoreMinimized) { throw 'Desktop is minimized. Restore manually or pass -RestoreMinimized.' }
        [void][PbiReloadShot.Win]::ShowWindow($h, 9); Start-Sleep -Seconds 2
    }
}

function Invoke-Reload {
    $reloadArgs = @("$PSScriptRoot\pbir-reload.mjs", "$ProcessId") + $(if ($Model) { @('--model') } else { @() })
    if ($AllowDiscardUnsavedChanges) { $reloadArgs += '--allow-unsaved' }
    for ($attempt = 1; $attempt -le 2; $attempt++) {
        $job = Start-Job -ScriptBlock { param($n, $a) & $n @a 2>&1 } -ArgumentList $node, $reloadArgs
        try {
            $deadline = [DateTime]::UtcNow.AddSeconds(120)
            $confirmed = $false
            while ($job.State -in @('NotStarted', 'Running')) {
                if ([DateTime]::UtcNow -ge $deadline) { throw 'Reload timed out; inspect Desktop manually.' }
                if ($ConfirmMultipleSourceWarning -and -not $confirmed) {
                    $confirmed = Confirm-PbiMultipleSourceWarning -TargetProcessId $ProcessId
                    if ($confirmed) { Write-Output '{"step":"dialog","method":"InvokePattern","confirmed":true}' }
                }
                Wait-Job $job -Timeout 1 | Out-Null
            }
            $out = (Receive-Job $job) -join "`n"
        } finally {
            if ($job.State -in @('NotStarted', 'Running')) { Stop-Job $job }
            Remove-Job $job -Force
        }
        # right after a file change Desktop is often still noticing it; one retry is enough
        if ($attempt -eq 1 -and $out -match 'Host is not ready') {
            Write-Output '{"step":"reload","retry":"host not ready"}'
            Start-Sleep -Seconds 8
            continue
        }
        break
    }
    if ($out -notmatch '"success":\s*true') { throw "Reload failed: $out" }
    Write-Output '{"step":"reload","success":true}'
    Start-Sleep -Seconds $RenderWaitSeconds   # let the page render before capturing
}

function Save-Capture([string]$name) {
    $file = Join-Path $OutDir "$name.png"
    $shot = & "$PSScriptRoot\capture-window.ps1" -ProcessId $ProcessId -OutFile $file -RestoreMinimized:$RestoreMinimized | ConvertFrom-Json
    Write-Output (@{ step = 'screenshot'; page = $name; status = $shot.status; size = $shot.size; path = $shot.path } | ConvertTo-Json -Compress)
}

New-Item -ItemType Directory -Force $OutDir | Out-Null
if (-not $NoReload) { Invoke-Reload }
if ($Pages.Count -eq 0) {
    Save-Capture 'current'
} else {
    $pagesDir = Get-PagesDir $current
    Restore-Window
    foreach ($page in $Pages) {
        Select-PageTab $pagesDir $page
        Save-Capture $page
    }
}
