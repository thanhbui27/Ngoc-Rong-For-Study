$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$serverJar = Join-Path $repoRoot 'Server\target\TeaMobi-1.0-RELEASE-jar-with-dependencies.jar'
$output = Join-Path $repoRoot 'Server\target\part-editor-classes'
$source = @(
    (Join-Path $repoRoot 'Server\src\main\java\nro\tools\PartEditorServer.java'),
    (Join-Path $repoRoot 'Server\src\main\java\nro\tools\GamePartEditorClient.java')
)
if (-not (Test-Path -LiteralPath $serverJar)) {
    throw "Không thấy $serverJar. Hãy build Server trước."
}
New-Item -ItemType Directory -Force -Path $output | Out-Null
& javac -encoding UTF-8 -cp $serverJar -d $output $source
if ($LASTEXITCODE -ne 0) { throw 'Biên dịch PartEditorServer thất bại' }
Push-Location $repoRoot
try {
    $gameHost = Read-Host 'Game server IP [103.116.52.124]'
    if ([string]::IsNullOrWhiteSpace($gameHost)) { $gameHost = '103.116.52.124' }
    $gamePort = Read-Host 'Game server port [14445]'
    if ([string]::IsNullOrWhiteSpace($gamePort)) { $gamePort = '14445' }
    if ($gamePort -notmatch '^\d{1,5}$' -or [int]$gamePort -lt 1 -or [int]$gamePort -gt 65535) {
        throw 'Cổng game không hợp lệ'
    }
    & java -cp "$output;$serverJar" nro.tools.PartEditorServer $gameHost $gamePort
} finally {
    Pop-Location
}
