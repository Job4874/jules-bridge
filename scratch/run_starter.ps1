$p = Start-Process -FilePath "C:\Quantower\TradingPlatform\v1.146.13\Starter.exe" -WorkingDirectory "C:\Quantower\TradingPlatform\v1.146.13" -PassThru
Start-Sleep -Seconds 5
$running = Get-Process -Id $p.Id -ErrorAction SilentlyContinue
if ($running) {
    Write-Host "Still running: PID $($p.Id)"
} else {
    Write-Host "Process exited immediately"
}
