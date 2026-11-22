param(
    [int]$Port = 4178,
    [string]$ExportPath = ''
)

$projectRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'activar-herramientas.ps1')
Push-Location -LiteralPath $projectRoot
try {
    if ($ExportPath) {
        python -m marketing.office --export $ExportPath
    } else {
        python -m marketing.office --host 127.0.0.1 --port $Port --site-dir (Join-Path $projectRoot 'sites/oficina-agentes/dist')
    }
    if ($LASTEXITCODE -ne 0) { throw 'La oficina de agentes no pudo iniciarse.' }
} finally {
    Pop-Location
}
