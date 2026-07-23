# Jules Bridge Access Controller
# Mountain Standard Time Schedule

function Get-MST-Time {
    $mst = [System.TimeZoneInfo]::FindSystemTimeZoneById("Mountain Standard Time")
    return [System.TimeZoneInfo]::ConvertTime([DateTime]::Now, $mst)
}

function Is-Access-Allowed {
    $now = Get-MST-Time
    $dayOfWeek = $now.DayOfWeek  # 0=Sunday, 5=Friday, 6=Saturday
    $hour = $now.Hour
    $minute = $now.Minute
    
    # Weekends (Saturday & Sunday) - ALWAYS OPEN
    if ($dayOfWeek -eq 0 -or $dayOfWeek -eq 6) {
        return $true, "WEEKEND - Open"
    }
    
    # Fridays: Open 3 PM - Close at end of day (stay open)
    if ($dayOfWeek -eq 5) {
        if ($hour -ge 15) {  # 3 PM or later
            return $true, "FRIDAY (3 PM+) - Open"
        } else {
            return $false, "FRIDAY Before 3 PM - Blocked"
        }
    }
    
    # Mon-Thu: Open 8 AM - 4 PM (16:00)
    if ($hour -ge 8 -and $hour -lt 16) {
        return $true, "WEEKDAY (8 AM - 4 PM) - Open"
    }
    
    # All other times - BLOCKED
    if ($hour -lt 8) {
        $hoursUntilOpen = 8 - $hour
        return $false, "BLOCKED - Opens in $hoursUntilOpen hours (8 AM)"
    } else {
        return $false, "BLOCKED - Opens tomorrow at 8 AM"
    }
}

# Display current status
$allowed, $reason = Is-Access-Allowed
$mstTime = Get-MST-Time
$dayName = $mstTime.DayOfWeek

Write-Output "`n?? CURRENT TIME: $($mstTime.ToString('ddd MMM dd, hh:mm tt MST'))"
Write-Output "?? TIMEZONE: Mountain Standard Time (MST)"
Write-Output ""

if ($allowed) {
    Write-Output "? ACCESS STATUS: ALLOWED"
    Write-Output "   $reason"
} else {
    Write-Output "?? ACCESS STATUS: BLOCKED"
    Write-Output "   $reason"
}
