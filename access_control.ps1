# Automated access enforcement for Jules Bridge

param (
    [string]$Action = "check"  # check, allow, block
)

$bridgeToken = $env:BRIDGE_TOKEN
$bridgeUrl = "http://localhost:5000"

function Check-Access {
    $mst = [System.TimeZoneInfo]::FindSystemTimeZoneById("Mountain Standard Time")
    $now = [System.TimeZoneInfo]::ConvertTime([DateTime]::Now, $mst)
    $dayOfWeek = $now.DayOfWeek
    $hour = $now.Hour
    
    # Weekends always open
    if ($dayOfWeek -eq 0 -or $dayOfWeek -eq 6) {
        return $true
    }
    
    # Friday 3 PM+
    if ($dayOfWeek -eq 5 -and $hour -ge 15) {
        return $true
    }
    
    # Mon-Thu 8 AM - 4 PM
    if ($dayOfWeek -gt 0 -and $dayOfWeek -lt 5) {
        if ($hour -ge 8 -and $hour -lt 16) {
            return $true
        }
    }
    
    return $false
}

if ($Action -eq "check") {
    if (Check-Access) {
        Write-Output "Access: ALLOWED"
        exit 0
    } else {
        Write-Output "Access: BLOCKED"
        exit 1
    }
}
