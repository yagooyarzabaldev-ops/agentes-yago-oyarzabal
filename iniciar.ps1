param([Parameter(ValueFromRemainingArguments = $true)][string[]]$CommandArgs)
$ErrorActionPreference = 'Stop'
$previousToolEnvironment = @{}
foreach ($name in @('Path', 'TEMP', 'TMP', 'PIP_CACHE_DIR', 'npm_config_cache')) {
    $previousToolEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
}
$resultCode = 1
Push-Location -LiteralPath $PSScriptRoot
try {
    . (Join-Path $PSScriptRoot 'scripts/activar-herramientas.ps1')
    if ($CommandArgs.Count -eq 0) { python -m marketing menu }
    else { python -m marketing @CommandArgs }
    $resultCode = $LASTEXITCODE
} finally {
    foreach ($name in $previousToolEnvironment.Keys) {
        [Environment]::SetEnvironmentVariable($name, $previousToolEnvironment[$name], 'Process')
    }
    Pop-Location
}
exit $resultCode
