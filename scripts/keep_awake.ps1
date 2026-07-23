$wscript = New-Object -ComObject WScript.Shell
$interval = 540
Write-Host "Keep-awake PowerShell script started (interval: ${interval}s / 9m)."
$count = 0
while ($true) {
    $count++
    # Send harmless F15 key to keep idle timer reset
    $wscript.SendKeys("{F15}")
    $time = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$time] Keep-awake pulse #$count"
    Start-Sleep -Seconds $interval
}
