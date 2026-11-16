if (Get-Variable nptSavedProxy -Scope Global -ErrorAction SilentlyContinue) {
    foreach ($nptKey in $global:nptSavedProxy.Keys) {
        [Environment]::SetEnvironmentVariable($nptKey, $global:nptSavedProxy[$nptKey])
    }
    Remove-Variable nptSavedProxy -Scope Global
}
