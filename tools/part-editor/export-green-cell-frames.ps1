param(
    [string]$OutputDir = (Join-Path $PSScriptRoot 'output/xen-con-xanh'),
    [int]$HeadPartId = 234,
    [int]$BodyPartId = 235,
    [int]$LegPartId = 236
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

$serverRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../Server')).Path
$iconDir = Join-Path $serverRoot 'resources/normal/image/4/icon'
$sql = [System.IO.File]::ReadAllText((Join-Path $PSScriptRoot '../../ngocrong-clean.sql'))
$charInfo = Get-Content (Join-Path $PSScriptRoot 'char-info.json') -Raw | ConvertFrom-Json
$partIds = @{ head = $HeadPartId; body = $BodyPartId; leg = $LegPartId }
$parts = @{}
foreach ($slot in $partIds.Keys) {
    $id = $partIds[$slot]
    $match = [regex]::Match($sql, '(?m)^\(' + $id + ',\s*\d+,\s*''(\[\[.*?\]\])''\),?$')
    if (-not $match.Success) { throw "Cannot find part $id in ngocrong-clean.sql" }
    $parts[$slot] = ConvertFrom-Json -InputObject $match.Groups[1].Value -NoEnumerate
}

[void][System.IO.Directory]::CreateDirectory($OutputDir)
$poses = @(
    @{ Name = '00-dung'; Red = 17125; Frame = 0; BodyOnly = $true },
    @{ Name = '01-chan-dung'; Red = 17126; LegOnly = 1 },
    @{ Name = '02-chay'; Red = 17127; Frame = 2 },
    @{ Name = '03-chay'; Red = 17128; Frame = 3 },
    @{ Name = '04-chay'; Red = 17129; Frame = 4 },
    @{ Name = '05-chay'; Red = 17130; Frame = 5 },
    @{ Name = '06-chay'; Red = 17131; Frame = 6 },
    @{ Name = '07-nhay'; Red = 17132; Frame = 7 },
    @{ Name = '08-roi'; Red = 17133; Frame = 12 },
    @{ Name = '09-dau'; Red = 17134; HeadOnly = 0 }
)

$manifest = [System.Collections.Generic.List[object]]::new()
foreach ($pose in $poses) {
    $canvas = [System.Drawing.Bitmap]::new(512, 512, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $graphics = [System.Drawing.Graphics]::FromImage($canvas)
    $graphics.Clear([System.Drawing.Color]::Transparent)
    $graphics.CompositingMode = [System.Drawing.Drawing2D.CompositingMode]::SourceOver
    $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::NearestNeighbor
    $layers = [System.Collections.Generic.List[object]]::new()
    if ($pose.ContainsKey('LegOnly')) {
        $layers.Add(@{ Slot = 'leg'; PartFrame = $pose.LegOnly; X = 0; Y = 0 })
    } elseif ($pose.ContainsKey('HeadOnly')) {
        $layers.Add(@{ Slot = 'head'; PartFrame = $pose.HeadOnly; X = 0; Y = 0 })
    } else {
        $info = $charInfo.frames[$pose.Frame]
        # Same layer order and coordinates as the costume renderer in Part Studio.
        $layers.Add(@{ Slot = 'head'; PartFrame = [int]$info[0][0]; X = [int]$info[0][1]; Y = [int]$info[0][2] })
        if (-not $pose.ContainsKey('BodyOnly')) {
            $layers.Add(@{ Slot = 'leg'; PartFrame = [int]$info[1][0]; X = [int]$info[1][1]; Y = [int]$info[1][2] })
        }
        $layers.Add(@{ Slot = 'body'; PartFrame = [int]$info[2][0]; X = [int]$info[2][1]; Y = [int]$info[2][2] })
    }
    $used = [System.Collections.Generic.List[object]]::new()
    foreach ($layer in $layers) {
        $piece = $parts[$layer.Slot][$layer.PartFrame]
        $imageId = [int]$piece[0]
        $source = Join-Path $iconDir "$imageId.png"
        if (-not (Test-Path -LiteralPath $source)) { throw "Missing source image: $source" }
        $image = [System.Drawing.Image]::FromFile($source)
        try {
            $x = (64 + $layer.X + [int]$piece[1]) * 4
            $y = (64 - $layer.Y + [int]$piece[2]) * 4
            $graphics.DrawImage($image, [System.Drawing.Rectangle]::new($x, $y, $image.Width, $image.Height))
            $used.Add([pscustomobject]@{ slot = $layer.Slot; frame = $layer.PartFrame; imageId = $imageId })
        } finally {
            $image.Dispose()
        }
    }
    $graphics.Dispose()
    $minX = $canvas.Width; $minY = $canvas.Height; $maxX = -1; $maxY = -1
    for ($y = 0; $y -lt $canvas.Height; $y++) {
        for ($x = 0; $x -lt $canvas.Width; $x++) {
            if ($canvas.GetPixel($x, $y).A -gt 0) {
                if ($x -lt $minX) { $minX = $x }; if ($x -gt $maxX) { $maxX = $x }
                if ($y -lt $minY) { $minY = $y }; if ($y -gt $maxY) { $maxY = $y }
            }
        }
    }
    if ($maxX -lt 0) { $canvas.Dispose(); throw "Empty frame: $($pose.Name)" }
    # Keep dimensions divisible by four for the client's x1-x4 image scale.
    $left = [int][Math]::Floor($minX / 4) * 4
    $top = [int][Math]::Floor($minY / 4) * 4
    $right = [int][Math]::Ceiling(($maxX + 1) / 4) * 4
    $bottom = [int][Math]::Ceiling(($maxY + 1) / 4) * 4
    $rect = [System.Drawing.Rectangle]::new($left, $top, $right - $left, $bottom - $top)
    $cropped = $canvas.Clone($rect, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $filename = "$($pose.Name).png"
    try { $cropped.Save((Join-Path $OutputDir $filename), [System.Drawing.Imaging.ImageFormat]::Png) }
    finally { $cropped.Dispose(); $canvas.Dispose() }
    $manifest.Add([pscustomobject]@{ file = $filename; redReference = $pose.Red; clientFrame = $(if ($pose.ContainsKey('Frame')) { $pose.Frame } else { $null }); sizeX4 = @($rect.Width, $rect.Height); sources = @($used) })
}
$manifest | ConvertTo-Json -Depth 8 | Set-Content (Join-Path $OutputDir 'manifest.json') -Encoding UTF8
Write-Output "Exported $($manifest.Count) Cell frames to $OutputDir"
