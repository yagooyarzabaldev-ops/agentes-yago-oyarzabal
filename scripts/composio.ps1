# Local Composio entry point. Keep binaries, authentication and session artifacts on D:.
# Native CLI exit codes are preserved; credentials never appear in this wrapper.
[CmdletBinding(PositionalBinding = $false)]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ComposioArguments
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'activar-herramientas.ps1')
$composioRoot = 'D:\Herramientas\marketing\composio'
$composioExecutable = Join-Path $composioRoot 'composio-windows-x64\composio.exe'
if (-not (Test-Path -LiteralPath $composioExecutable -PathType Leaf)) {
    throw 'Falta la CLI oficial de Composio en D:. Consultar production/COMPOSIO-INSTAGRAM.md.'
}
$env:COMPOSIO_CACHE_DIR = Join-Path $composioRoot 'config'
$env:COMPOSIO_SESSION_DIR = Join-Path $composioRoot 'sessions'
$env:COMPOSIO_CLI_TELEMETRY_DISABLED = '1'
& $composioExecutable @ComposioArguments
exit $LASTEXITCODE
