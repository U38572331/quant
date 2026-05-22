
Add-Type -AssemblyName System.Drawing

$pngPath = "C:\Users\user\.gemini\antigravity\scratch\binance-orderflow\btc_highres.png"
$icoPath = "C:\Users\user\.gemini\antigravity\scratch\binance-orderflow\bitcoin_hd.ico"

$bytes = [System.IO.File]::ReadAllBytes($pngPath)
$stream = [System.IO.MemoryStream]::new($bytes)
$img = [System.Drawing.Image]::FromStream($stream)

# ICO Header (6 bytes)
# Reserved (2) | Type (2, 1=Icon) | Count (2)
$header = [byte[]]@(0, 0, 1, 0, 1, 0)

# Entry (16 bytes)
# Width (1) | Height (1) | Colors (1) | Reserved (1) | Planes (2) | BPP (2) | Size (4) | Offset (4)
$width = $img.Width
if ($width -eq 256) { $width = 0 }
$height = $img.Height
if ($height -eq 256) { $height = 0 }

$size = $bytes.Length
$offset = 6 + 16 # Header + 1 Entry

$entry = [byte[]]@(
    $width, $height, 0, 0, 
    1, 0, 32, 0, 
    [BitConverter]::GetBytes([int]$size)[0],
    [BitConverter]::GetBytes([int]$size)[1],
    [BitConverter]::GetBytes([int]$size)[2],
    [BitConverter]::GetBytes([int]$size)[3],
    [BitConverter]::GetBytes([int]$offset)[0],
    [BitConverter]::GetBytes([int]$offset)[1],
    [BitConverter]::GetBytes([int]$offset)[2],
    [BitConverter]::GetBytes([int]$offset)[3]
)

# Write File
$fs = [System.IO.File]::Create($icoPath)
$fs.Write($header, 0, $header.Length)
$fs.Write($entry, 0, $entry.Length)
$fs.Write($bytes, 0, $bytes.Length)
$fs.Close()
$img.Dispose()
$stream.Dispose()
Write-Host "ICO Created: $icoPath"
