@echo off
echo ========================================
echo   Restaurante PDV - Inicio del Sistema
echo ========================================
echo.

echo Iniciando Backend (Flask)...
cd backend
echo Instalando dependencias...
pip install -r requirements.txt > nul 2>&1
echo Backend iniciando en puerto 5000...
start cmd /k "python app.py"

echo.
echo Esperando 3 segundos...
timeout /t 3 /nobreak

echo.
echo Iniciando Frontend (React + Vite)...
cd ..\frontend
echo Instalando dependencias...
call npm install > nul 2>&1
echo Frontend iniciando en puerto 5173...
start cmd /k "npm run dev"

echo.
echo ========================================
echo Sistema iniciado!
echo.
echo Backend:  http://localhost:5000
echo Frontend: http://localhost:5173
echo.
echo Cierra esta ventana cuando termines.
echo ========================================
pause
