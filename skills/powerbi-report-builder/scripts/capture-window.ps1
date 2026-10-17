# Captures the Power BI Desktop window as the developer sees it, using Windows (PrintWindow), without asking Desktop
# to render anything. The Desktop Bridge snapshot (report.snapshot.capture) is NOT used: it can leave Desktop's
# window stuck in its capture layout (canvas zoomed, no ribbon, unclickable until the file is reopened).
#
# No foreground/keyboard input. A minimized window is restored only with -RestoreMinimized.
#
# Usage: .\capture-window.ps1 -OutFile <png> [-ProcessId <pid>]
#   Without -ProcessId, the single running PBIDesktop is used (error if several are open).
# Output: one JSON line {"status":"ok","size":"WxH","path":"..."}; exit 1 on failure.
param(
    [Parameter(Mandatory)][string]$OutFile,
    [int]$ProcessId = 0,
    [switch]$RestoreMinimized
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
if (-not ('PbiWindowCapture.Win' -as [type])) { Add-Type -Namespace PbiWindowCapture -Name Win -MemberDefinition @'
[DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr hwnd, IntPtr hdc, uint flags);
[DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hwnd, out RECT rect);
[DllImport("user32.dll")] public static extern bool IsIconic(IntPtr hwnd);
[DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hwnd, int cmd);
[DllImport("user32.dll")] public static extern IntPtr SetThreadDpiAwarenessContext(IntPtr context);
public struct RECT { public int Left, Top, Right, Bottom; }
'@
}
$W = [PbiWindowCapture.Win]

if ($ProcessId -eq 0) {
    $procs = @(Get-Process PBIDesktop -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne [IntPtr]::Zero })
    if ($procs.Count -eq 0) { throw 'Power BI Desktop is not running.' }
    if ($procs.Count -gt 1) { throw "Several Power BI Desktop windows are open; pass -ProcessId ($(($procs | ForEach-Object { "$($_.Id): $($_.MainWindowTitle)" }) -join '; '))." }
    $ProcessId = $procs[0].Id
}
$process = Get-Process -Id $ProcessId
if ($process.ProcessName -ne 'PBIDesktop') { throw 'Target must be Power BI Desktop.' }
$h = $process.MainWindowHandle
if ($h -eq [IntPtr]::Zero) { throw "Process $ProcessId has no window." }

# Restore only when explicitly requested; no foreground activation.
if ($W::IsIconic($h)) {
    if (-not $RestoreMinimized) { throw 'Desktop is minimized. Restore manually or pass -RestoreMinimized.' }
    [void]$W::ShowWindow($h, 9)                 # SW_RESTORE: back to the previous state (maximized stays maximized)
    Start-Sleep -Seconds 2                      # let the report re-render after restore
}
# No keyboard events, foreground activation, movement, or resizing.
$previousDpi = $W::SetThreadDpiAwarenessContext([IntPtr](-4))
try {

$r = New-Object PbiWindowCapture.Win+RECT
[void]$W::GetWindowRect($h, [ref]$r)
$width = $r.Right - $r.Left; $height = $r.Bottom - $r.Top
if ($width -lt 800 -or $height -lt 500) { throw "Desktop window is too small to capture (${width}x${height}); is it still minimized?" }

$bmp = New-Object System.Drawing.Bitmap $width, $height
try {
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    try {
        $hdc = $g.GetHdc()
        try { $ok = $W::PrintWindow($h, $hdc, 2) } finally { $g.ReleaseHdc($hdc) }
    } finally { $g.Dispose() }
    if (-not $ok) { throw 'PrintWindow failed.' }
    $dir = Split-Path -Parent ([IO.Path]::GetFullPath($OutFile))
    New-Item -ItemType Directory -Force $dir | Out-Null
    $bmp.Save([IO.Path]::GetFullPath($OutFile), [System.Drawing.Imaging.ImageFormat]::Png)
} finally { $bmp.Dispose() }

@{ status = 'ok'; size = "${width}x${height}"; path = [IO.Path]::GetFullPath($OutFile) } | ConvertTo-Json -Compress
} finally {
    if ($previousDpi -ne [IntPtr]::Zero) { [void]$W::SetThreadDpiAwarenessContext($previousDpi) }
}
