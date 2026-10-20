$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$pythonProjeto = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonProjeto)) {
    py -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Instale Python para continuar.' }
    & $pythonProjeto -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Falha na instalação das dependências.' }
}
& $pythonProjeto preparar_banco.py
if ($LASTEXITCODE -ne 0) { throw 'Não foi possível iniciar o banco.' }
& $pythonProjeto -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
