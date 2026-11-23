param(
    [Parameter(Mandatory = $true)][string]$ByteAudit,
    [Parameter(Mandatory = $true)][string]$Server14,
    [Parameter(Mandatory = $true)][string]$Server15,
    [string]$Output
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
Add-Type -ReferencedAssemblies System.Drawing -TypeDefinition @'
using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;

public static class PngPixelCompare {
    public static bool Same(string left, string right) {
        using (var a = new Bitmap(left))
        using (var b = new Bitmap(right)) {
            if (a.Width != b.Width || a.Height != b.Height) return false;
            var rect = new Rectangle(0, 0, a.Width, a.Height);
            using (var aa = a.Clone(rect, PixelFormat.Format32bppArgb))
            using (var bb = b.Clone(rect, PixelFormat.Format32bppArgb)) {
                var ad = aa.LockBits(rect, ImageLockMode.ReadOnly, PixelFormat.Format32bppArgb);
                var bd = bb.LockBits(rect, ImageLockMode.ReadOnly, PixelFormat.Format32bppArgb);
                try {
                    int rowBytes = a.Width * 4;
                    byte[] ab = new byte[Math.Abs(ad.Stride) * a.Height];
                    byte[] bytesB = new byte[Math.Abs(bd.Stride) * b.Height];
                    Marshal.Copy(ad.Scan0, ab, 0, ab.Length);
                    Marshal.Copy(bd.Scan0, bytesB, 0, bytesB.Length);
                    for (int y = 0; y < a.Height; y++) {
                        int ai = y * Math.Abs(ad.Stride);
                        int bi = y * Math.Abs(bd.Stride);
                        for (int x = 0; x < rowBytes; x++) {
                            if (ab[ai + x] != bytesB[bi + x]) return false;
                        }
                    }
                    return true;
                } finally {
                    aa.UnlockBits(ad);
                    bb.UnlockBits(bd);
                }
            }
        }
    }
}
'@

$root = Split-Path -Parent $PSScriptRoot
$audit = Get-Content -LiteralPath $ByteAudit -Raw | ConvertFrom-Json
$summary = [ordered]@{ icon = [ordered]@{}; data = [ordered]@{} }
foreach ($zoom in 1..4) {
    $ids = $audit.icon."$zoom".tracked_different
    $same = 0
    $different = [System.Collections.Generic.List[int]]::new()
    $empty = [System.Collections.Generic.List[int]]::new()
    $unreadable = [System.Collections.Generic.List[int]]::new()
    foreach ($id in $ids) {
        $source14 = Join-Path $Server14 "image/zoom$zoom/icon/$id.png"
        $source = if (Test-Path -LiteralPath $source14) { $source14 } else { Join-Path $Server15 "image/zoom$zoom/icon/$id.png" }
        $target = Join-Path $root "Server/resources/normal/image/$zoom/icon/$id.png"
        if ((Get-Item -LiteralPath $target).Length -eq 0) { $empty.Add([int]$id); continue }
        try { $pixelSame = [PngPixelCompare]::Same($source, $target) }
        catch { $unreadable.Add([int]$id); continue }
        if ($pixelSame) { $same++ } else { $different.Add([int]$id) }
    }
    $summary.icon["$zoom"] = [ordered]@{ compared = $ids.Count; pixel_same = $same; pixel_different = $different.Count; empty = $empty.Count; unreadable = $unreadable.Count; different_ids = @($different); empty_ids = @($empty); unreadable_ids = @($unreadable) }
    Write-Output "Icon x$zoom`: $same pixel-identical, $($different.Count) pixel-different, $($empty.Count) empty, $($unreadable.Count) unreadable of $($ids.Count) differing PNG files"
    Write-Output "  Different IDs sample: $(@($different | Select-Object -First 20) -join ', ')"

    $paths = $audit.data."$zoom".tracked_different
    $dataSame = 0
    $dataDifferent = [System.Collections.Generic.List[string]]::new()
    $dataEmpty = [System.Collections.Generic.List[string]]::new()
    $dataUnreadable = [System.Collections.Generic.List[string]]::new()
    foreach ($relative in $paths) {
        $suffix = $relative -replace '^Server/resources/normal/data/\d+/', ''
        $source = Join-Path $Server15 "data/zoom$zoom/$suffix"
        $target = Join-Path $root $relative
        if ((Get-Item -LiteralPath $target).Length -eq 0) { $dataEmpty.Add($relative); continue }
        try { $pixelSame = [PngPixelCompare]::Same($source, $target) }
        catch { $dataUnreadable.Add($relative); continue }
        if ($pixelSame) { $dataSame++ } else { $dataDifferent.Add($relative) }
    }
    $summary.data["$zoom"] = [ordered]@{ compared = $paths.Count; pixel_same = $dataSame; pixel_different = $dataDifferent.Count; empty = $dataEmpty.Count; unreadable = $dataUnreadable.Count; different_paths = @($dataDifferent); empty_paths = @($dataEmpty); unreadable_paths = @($dataUnreadable) }
    Write-Output "Data x$zoom`: $dataSame pixel-identical, $($dataDifferent.Count) pixel-different, $($dataEmpty.Count) empty, $($dataUnreadable.Count) unreadable of $($paths.Count) differing PNG files"
}
if ($Output) {
    $summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $Output -Encoding utf8
}
