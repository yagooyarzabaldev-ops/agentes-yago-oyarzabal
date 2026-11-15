param([Parameter(ValueFromRemainingArguments = $true)][string[]]$CommandArgs)
$ErrorActionPreference = 'Stop'
Push-Location -LiteralPath $PSScriptRoot
try {
    if ($CommandArgs.Count -eq 0) { python -m marketing menu }
    else { python -m marketing @CommandArgs }
    $resultCode = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $resultCode
