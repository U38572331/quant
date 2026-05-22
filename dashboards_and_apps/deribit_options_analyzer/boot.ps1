$ErrorActionPreference = "Stop"

Write-Host "[BOOT] Starting Deribit Options Analyzer..." -ForegroundColor Cyan

# 1. Start Server
Write-Host "[BOOT] Launching Quant Engine (FastAPI)..." -ForegroundColor Yellow
$serverProcess = Start-Process -FilePath "python" -ArgumentList "server.py" -PassThru -NoNewWindow

# 2. Wait for Port 8000
Write-Host "[BOOT] Waiting for Server Connection..." -ForegroundColor Yellow
$maxRetries = 10
$retryCount = 0
$connected = $false

while (-not $connected -and $retryCount -lt $maxRetries) {
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $tcp.Connect("127.0.0.1", 8000)
        $connected = $true
        $tcp.Close()
        Write-Host "[BOOT] Server Online!" -ForegroundColor Green
    }
    catch {
        $retryCount++
        Start-Sleep -Seconds 1
        Write-Host "." -NoNewline
    }
}

if (-not $connected) {
    Write-Host "`n[ERROR] Server failed to start." -ForegroundColor Red
    if ($serverProcess) { Stop-Process -Id $serverProcess.Id -Force }
    exit 1
}

# 3. Launch Browser
Write-Host "`n[BOOT] Opening Interface..." -ForegroundColor Cyan
try {
    Start-Process "http://127.0.0.1:8000/"
}
catch {
    Write-Host "[WARN] Could not auto-launch browser." -ForegroundColor Yellow
}

Write-Host "===================================================" -ForegroundColor Green
Write-Host "   DASHBOARD READY: http://127.0.0.1:8000/" -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Green

# 4. Keep alive (Optional, but the server process is separate)
Write-Host "[BOOT] System Ready. Converting to Server Monitor..."
Write-Host "Press Ctrl+C to shutdown."

# Wait for server to exit
$serverProcess.WaitForExit()
