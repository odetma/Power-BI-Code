# Caller must have explicit user authorization before calling this function.
function Confirm-PbiMultipleSourceWarning([int]$TargetProcessId) {
    $process = Get-Process -Id $TargetProcessId -ErrorAction Stop
    if ($process.ProcessName -ne 'PBIDesktop') { throw 'Target is not Power BI Desktop.' }
    $python = Get-PbiPython
    $helper = Join-Path $PSScriptRoot 'confirm-source-warning.py'
    $start = New-Object System.Diagnostics.ProcessStartInfo
    $start.FileName = $python
    $start.Arguments = '"{0}" --pid {1} --handle {2} --confirm' -f $helper, $TargetProcessId, $process.MainWindowHandle.ToInt64()
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $worker = New-Object System.Diagnostics.Process
    $worker.StartInfo = $start
    try {
        [void]$worker.Start()
        $output = $worker.StandardOutput.ReadToEndAsync()
        $errors = $worker.StandardError.ReadToEndAsync()
        if (-not $worker.WaitForExit(20000)) {
            $worker.Kill()
            throw 'Native UIA handler timed out. Invocation outcome may be unknown; inspect Desktop manually.'
        }
        $resultText = $output.GetAwaiter().GetResult()
        if ($worker.ExitCode -ne 0) { throw "Native UIA warning handler failed: $resultText $($errors.GetAwaiter().GetResult())" }
        $result = $resultText | ConvertFrom-Json
        if ($result.confirmed) {
            Write-Host $resultText
            if (-not $result.boundsUnchanged) { throw 'Warning confirmed but Desktop bounds changed; inspect manually.' }
        }
        return [bool]$result.confirmed
    } finally { $worker.Dispose() }
}
