$dir = "C:\Users\abdul\.jules\jules_inbox\gcp_boot"
$files = Get-ChildItem $dir -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending
if (-not $files) {
    Write-Output "No log files found in $dir"
    exit 0
}
$latest = $files[0]
Write-Output "=== Latest log: $($latest.FullName) ==="
Get-Content $latest.FullName
