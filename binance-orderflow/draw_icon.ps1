
Add-Type -AssemblyName System.Drawing

$icoPath = "C:\Users\user\.gemini\antigravity\scratch\binance-orderflow\u3_custom.ico"
$size = 256

# Create Bitmap
$bmp = New-Object System.Drawing.Bitmap($size, $size)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAlias

# Background (Dark Circle)
$bgBrush = New-Object System.Drawing.SolidBrush([System.Drawing.ColorTranslator]::FromHtml("#161a1e"))
$g.FillEllipse($bgBrush, 0, 0, $size, $size)

# Ring Accent
$pen = New-Object System.Drawing.Pen([System.Drawing.ColorTranslator]::FromHtml("#2b3139"), 10)
$g.DrawEllipse($pen, 5, 5, $size - 10, $size - 10)

# Text "U3"
$font = New-Object System.Drawing.Font("Arial", 90, [System.Drawing.FontStyle]::Bold)
$textBrush = New-Object System.Drawing.SolidBrush([System.Drawing.ColorTranslator]::FromHtml("#2ecc71")) # Buy Green
$format = New-Object System.Drawing.StringFormat
$format.Alignment = [System.Drawing.StringAlignment]::Center
$format.LineAlignment = [System.Drawing.StringAlignment]::Center

$g.DrawString("U3", $font, $textBrush, $size / 2, $size / 2 - 20, $format)

# Subtext "TRADER"
$fontSub = New-Object System.Drawing.Font("Arial", 30, [System.Drawing.FontStyle]::Bold)
$textBrushSub = New-Object System.Drawing.SolidBrush([System.Drawing.ColorTranslator]::FromHtml("#ffffff"))
$g.DrawString("TRADER", $fontSub, $textBrushSub, $size / 2, $size / 2 + 60, $format)

# Save as PNG (Temporary) then Convert manually to ICO bytes
# Simplified approach: Save PNG, then use the byte-header method from before

$pngPath = "C:\Users\user\.gemini\antigravity\scratch\binance-orderflow\temp_icon.png"
$bmp.Save($pngPath, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose()
$bmp.Dispose()

# Convert PNG to ICO
$bytes = [System.IO.File]::ReadAllBytes($pngPath)

# ICO Header (6 bytes)
$header = [byte[]]@(0, 0, 1, 0, 1, 0)

# Entry (16 bytes)
$width = 0 # 256
$height = 0 # 256
$fileSize = $bytes.Length
$offset = 6 + 16

$entry = [byte[]]@(
    $width, $height, 0, 0, 
    1, 0, 32, 0, 
    [BitConverter]::GetBytes([int]$fileSize)[0],
    [BitConverter]::GetBytes([int]$fileSize)[1],
    [BitConverter]::GetBytes([int]$fileSize)[2],
    [BitConverter]::GetBytes([int]$fileSize)[3],
    [BitConverter]::GetBytes([int]$offset)[0],
    [BitConverter]::GetBytes([int]$offset)[1],
    [BitConverter]::GetBytes([int]$offset)[2],
    [BitConverter]::GetBytes([int]$offset)[3]
)

$fs = [System.IO.File]::Create($icoPath)
$fs.Write($header, 0, $header.Length)
$fs.Write($entry, 0, $entry.Length)
$fs.Write($bytes, 0, $bytes.Length)
$fs.Close()

Write-Host "Custom Icon Created: $icoPath"
