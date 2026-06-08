# Bob Startup Script - kills any existing openclaw instance before starting fresh
$logFile = "C:\Users\amich\.openclaw\logs\startup-bob.log"

function Log($msg) {
    $ts = Get-Date -Format "HH:mm:ss"
    $line = "$ts $msg"
    Add-Content -Path $logFile -Value $line
}

New-Item -ItemType Directory -Force -Path (Split-Path $logFile) | Out-Null
Log "=== Bob Startup $(Get-Date -Format 'yyyy-MM-dd') ==="

$procs = Get-CimInstance Win32_Process -Filter "Name='node.exe'" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*clawdbot*" -or $_.CommandLine -like "*openclaw*" }

if ($procs) {
    $count = ($procs | Measure-Object).Count
    Log "Found $count existing openclaw process(es) - killing..."
    $procs | ForEach-Object {
        Log "  Killing PID $($_.ProcessId)"
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
    Log "Killed existing processes"
} else {
    Log "No existing openclaw processes found"
}

Log "Starting Bob..."
$openclaw = "C:\Users\amich\AppData\Roaming\npm\openclaw.cmd"
Start-Process -FilePath "cmd.exe" -ArgumentList "/c $openclaw gateway --force" -WorkingDirectory "C:\Users\amich" -WindowStyle Normal
Log "Bob started"
