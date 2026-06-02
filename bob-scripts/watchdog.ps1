$logFile = "C:\Users\amich\.openclaw\logs\watchdog.log"
New-Item -ItemType Directory -Force -Path (Split-Path $logFile) | Out-Null

function Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $logFile -Value "$ts $msg"
}

# Read gateway token from config
$tok = $null
try {
    $conf = Get-Content "C:\Users\amich\.openclaw\openclaw.json" -Raw | ConvertFrom-Json
    $tok = $conf.gateway.auth.token
} catch {}

# Check if gateway is alive using openclaw health (token-aware)
$alive = $false
if ($tok) {
    $result = & openclaw health --token $tok 2>&1
    if ($LASTEXITCODE -eq 0) { $alive = $true }
}

# Fallback: check if port 18789 is bound by a node process
if (-not $alive) {
    $portLine = netstat -ano 2>$null | Select-String "127.0.0.1:18789\s+.*LISTENING" | Select-Object -First 1
    if ($portLine) {
        $pid_ = ($portLine.Line.Trim() -split '\s+')[-1]
        $proc = Get-Process -Id $pid_ -ErrorAction SilentlyContinue
        if ($proc -and $proc.Name -eq "node") { $alive = $true }
    }
}

if ($alive) { exit 0 }

# Gateway is not responding — restart it
Log "Gateway not responding. Restarting..."
$procs = Get-CimInstance Win32_Process -Filter "Name='node.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*openclaw*" }
if ($procs) {
    $procs | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 2
}
$openclaw = "C:\Users\amich\AppData\Roaming\npm\openclaw.cmd"
Start-Process -FilePath "cmd.exe" -ArgumentList "/c $openclaw gateway --force" -WorkingDirectory "C:\Users\amich" -WindowStyle Hidden
Log "Gateway restarted."
