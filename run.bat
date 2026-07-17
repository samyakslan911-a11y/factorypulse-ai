@echo off
cd /d "%~dp0"

echo Activando entorno virtual...
call .venv\Scripts\activate.bat

echo Instalando dependencias...
pip install -r backend/requirements.txt -q

echo Iniciando FactoryPulse AI backend...
set PYTHONPATH=%~dp0
python -m uvicorn backend.main:app --reload --port 8000
