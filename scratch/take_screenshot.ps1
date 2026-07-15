Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms
$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
$graphics = [System.Drawing.Graphics]::FromImage($bmp)
try {
    $graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
    $bmp.Save("C:\Users\abdul\.jules\temp_screen.png", [System.Drawing.Imaging.ImageFormat]::Png)
    Write-Host "Success"
} catch {
    Write-Host "Failed: $_"
} finally {
    $graphics.Dispose()
    $bmp.Dispose()
}
