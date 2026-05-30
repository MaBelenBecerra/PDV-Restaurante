@echo off
echo ========================================
echo   Restaurante PDV - Inicio del Sistema (Servicios Distribuidos)
echo ========================================
echo.

echo 1. Iniciando Inventory.Api (Puerto 5143)...
cd Inventory.Api
pip install -r requirements.txt > nul 2>&1
start cmd /k "title Inventory API && python app.py"

cd ..
echo 2. Iniciando Sales.Api (Puerto 5074)...
cd Sales.Api
pip install -r requirements.txt > nul 2>&1
start cmd /k "title Sales API && python app.py"

cd ..
echo 3. Iniciando Purchases.Api (Puerto 5229)...
cd Purchases.Api
pip install -r requirements.txt > nul 2>&1
start cmd /k "title Purchases API && python app.py"

cd ..
echo.
echo Esperando 3 segundos...
timeout /t 3 /nobreak

echo.
echo 4. Iniciando Frontend (React + Vite)...
cd frontend
echo Instalando dependencias...
call npm install > nul 2>&1
echo Frontend iniciando en puerto 5173...
start cmd /k "npm run dev"

cd ..
echo.
echo ========================================
echo Sistema iniciado!
echo.
echo Inventario API: http://localhost:5143
echo Ventas API:     http://localhost:5074
echo Compras API:    http://localhost:5229
echo Frontend:       http://localhost:5173
echo.
echo Cierra las ventanas individuales cuando termines.
echo ========================================
pause
