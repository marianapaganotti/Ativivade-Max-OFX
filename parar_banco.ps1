$ErrorActionPreference = 'Stop'
$pgCtlProjeto = Join-Path $PSScriptRoot '.runtime\pgsql\bin\pg_ctl.exe'
$dadosProjeto = Join-Path $PSScriptRoot '.local\pgdata'
if (Test-Path -LiteralPath $pgCtlProjeto) {
    & $pgCtlProjeto -D $dadosProjeto -m fast -w stop
}
