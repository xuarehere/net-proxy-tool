$nptRoot = Split-Path -Parent $PSScriptRoot
$nptPython = Join-Path $nptRoot 'runtime/python.exe'
if (Test-Path -LiteralPath $nptPython) {
    & $nptPython (Join-Path $nptRoot 'with_proxy.py') @args
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 (Join-Path $nptRoot 'with_proxy.py') @args
} else {
    & python (Join-Path $nptRoot 'with_proxy.py') @args
}
exit $LASTEXITCODE
