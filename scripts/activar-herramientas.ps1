# Dot-source before running production scripts directly. No configuration means
# the existing environment is preserved, so other checkouts remain portable.
param(
    [string]$ConfigPath = (Join-Path (Split-Path -Parent $PSScriptRoot) 'runtime/herramientas-locales.json')
)

if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) { return }
$localTools = Get-Content -LiteralPath $ConfigPath -Raw -ErrorAction Stop | ConvertFrom-Json -ErrorAction Stop
$toolDirectories = @($localTools.python, $localTools.node, $localTools.ffmpeg)
$requiredExecutables = @(
    (Join-Path $localTools.python 'python.exe'),
    (Join-Path $localTools.node 'node.exe'),
    (Join-Path $localTools.ffmpeg 'ffmpeg.exe'),
    (Join-Path $localTools.ffmpeg 'ffprobe.exe')
)
foreach ($executable in $requiredExecutables) {
    if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) {
        throw "Falta una herramienta configurada: $executable"
    }
}
foreach ($directory in @($localTools.temp, $localTools.pip_cache, $localTools.npm_cache)) {
    if ([string]::IsNullOrWhiteSpace($directory)) { throw 'Falta una carpeta de temporales o cache en la configuracion local.' }
    New-Item -ItemType Directory -Path $directory -Force -ErrorAction Stop | Out-Null
}
$remainingPath = @($env:Path -split ';' | Where-Object { $_ -and $toolDirectories -notcontains $_.TrimEnd('\') })
$env:Path = (@($toolDirectories) + $remainingPath) -join ';'
$env:TEMP = $localTools.temp
$env:TMP = $localTools.temp
$env:PIP_CACHE_DIR = $localTools.pip_cache
$env:npm_config_cache = $localTools.npm_cache
