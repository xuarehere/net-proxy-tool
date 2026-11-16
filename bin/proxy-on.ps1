$nptRoot = Split-Path -Parent $PSScriptRoot
$nptPython = Join-Path $nptRoot 'runtime/python.exe'
$nptScript = Join-Path $PSScriptRoot 'session_env.py'
if (Test-Path -LiteralPath $nptPython) {
    $nptJson = & $nptPython $nptScript --json
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $nptJson = & py -3 $nptScript --json
} else {
    $nptJson = & python $nptScript --json
}
if ($LASTEXITCODE -ne 0) { return }
$nptValues = $nptJson | ConvertFrom-Json
if ($null -eq (Get-Variable nptSavedProxy -Scope Global -ErrorAction SilentlyContinue)) {
    $global:nptSavedProxy = @{}
    foreach ($nptKey in $nptValues.PSObject.Properties.Name) {
        $global:nptSavedProxy[$nptKey] = [Environment]::GetEnvironmentVariable($nptKey)
    }
}
foreach ($nptProperty in $nptValues.PSObject.Properties) {
    [Environment]::SetEnvironmentVariable($nptProperty.Name, $nptProperty.Value)
}
