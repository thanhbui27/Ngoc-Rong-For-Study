param(
    [int]$FirstImageId = 32582,
    [string]$SourceDir = (Join-Path $PSScriptRoot 'output/xen-con-xanh-minipet')
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

$imageRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../Server/resources/normal/image')).Path
$sourceDir = (Resolve-Path $SourceDir).Path
$sources = @(
    'body-01-dung.png',
    'leg-01-chan-dung.png',
    'leg-02-chay.png',
    'leg-03-chay.png',
    'leg-04-chay.png',
    'leg-05-chay.png',
    'leg-06-chay.png',
    'leg-07-nhay.png',
    'leg-08-roi.png',
    'icon-dau.png'
)
if ($FirstImageId -lt 1 -or $FirstImageId + $sources.Count - 1 -gt 32767) {
    throw 'Image IDs must be between 1 and 32767.'
}

# Check every source and destination before changing any resource file.
foreach ($index in 0..($sources.Count - 1)) {
    $sourcePath = Join-Path $sourceDir $sources[$index]
    if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) { throw "Missing source: $sourcePath" }
    $image = [System.Drawing.Image]::FromFile($sourcePath)
    try {
        if ($image.Width % 4 -ne 0 -or $image.Height % 4 -ne 0) {
            throw "x4 size must divide by four: $sourcePath"
        }
    } finally { $image.Dispose() }
    $id = $FirstImageId + $index
    foreach ($zoom in 1..4) {
        $destination = Join-Path $imageRoot "$zoom/icon/$id.png"
        if (Test-Path -LiteralPath $destination) { throw "Image ID $id is already in use at x$zoom`: $destination" }
    }
}

$manifest = [System.Collections.Generic.List[object]]::new()
foreach ($index in 0..($sources.Count - 1)) {
    $id = $FirstImageId + $index
    $sourcePath = Join-Path $sourceDir $sources[$index]
    $source = [System.Drawing.Bitmap]::new($sourcePath)
    try {
        foreach ($zoom in 1..4) {
            $destination = Join-Path $imageRoot "$zoom/icon/$id.png"
            if ($zoom -eq 4) {
                [System.IO.File]::Copy($sourcePath, $destination, $false)
                continue
            }
            $width = [int]($source.Width * $zoom / 4)
            $height = [int]($source.Height * $zoom / 4)
            $scaled = [System.Drawing.Bitmap]::new($width, $height, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
            $graphics = [System.Drawing.Graphics]::FromImage($scaled)
            try {
                $graphics.Clear([System.Drawing.Color]::Transparent)
                $graphics.CompositingMode = [System.Drawing.Drawing2D.CompositingMode]::SourceCopy
                $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::NearestNeighbor
                $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::Half
                $graphics.DrawImage($source, [System.Drawing.Rectangle]::new(0, 0, $width, $height))
                $scaled.Save($destination, [System.Drawing.Imaging.ImageFormat]::Png)
            } finally {
                $graphics.Dispose()
                $scaled.Dispose()
            }
        }
        $manifest.Add([pscustomobject]@{ imageId = $id; source = $sources[$index]; sizeX4 = @($source.Width, $source.Height) })
    } finally { $source.Dispose() }
}

$manifestPath = Join-Path $sourceDir 'installed-image-ids.json'
$manifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
Write-Output "Installed $($sources.Count) unique icons at x1-x4: $FirstImageId..$($FirstImageId + $sources.Count - 1)"
