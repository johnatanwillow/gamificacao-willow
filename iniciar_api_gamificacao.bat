@echo off
REM Define o diretório raiz do projeto (onde este .bat está, e onde a pasta 'gamificacao_willow' e 'venv' devem estar)
set PROJECT_ROOT=%~dp0

REM Navega para a pasta da aplicação FastAPI
cd /d "%PROJECT_ROOT%gamificacao_willow"

REM Ativa o ambiente virtual 'venv'. Ele deve estar na pasta raiz do projeto.
call "%PROJECT_ROOT%venv\Scripts\activate.bat"

REM Inicia a API FastAPI na porta 8000
echo Iniciando a API FastAPI na porta 8000... (Acesse http://127.0.0.1:8000/docs no navegador)
uvicorn app:app --host 0.0.0.0 --port 8000 --reload

REM Descomente a linha abaixo (remova o REM) se quiser que a janela do terminal permaneça aberta
REM pause