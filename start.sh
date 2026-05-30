#!/bin/bash

echo "========================================"
echo "  Restaurante PDV - Inicio del Sistema (Servicios Distribuidos)"
echo "========================================"
echo ""

echo "1. Iniciando Inventory.Api (Puerto 5143)..."
cd Inventory.Api
pip install -r requirements.txt > /dev/null 2>&1
python app.py &
INV_PID=$!
cd ..

echo "2. Iniciando Sales.Api (Puerto 5074)..."
cd Sales.Api
pip install -r requirements.txt > /dev/null 2>&1
python app.py &
SAL_PID=$!
cd ..

echo "3. Iniciando Purchases.Api (Puerto 5229)..."
cd Purchases.Api
pip install -r requirements.txt > /dev/null 2>&1
python app.py &
PUR_PID=$!
cd ..

echo ""
echo "Esperando 3 segundos..."
sleep 3

echo ""
echo "4. Iniciando Frontend (React + Vite)..."
cd frontend
npm install > /dev/null 2>&1
npm run dev &
FRONT_PID=$!
cd ..

echo ""
echo "========================================"
echo "Sistema iniciado!"
echo ""
echo "Inventario API: http://localhost:5143"
echo "Ventas API:     http://localhost:5074"
echo "Compras API:    http://localhost:5229"
echo "Frontend:       http://localhost:5173"
echo ""
echo "Presiona Ctrl+C para detener..."
echo "========================================"

# Handle shutdown
trap "kill $INV_PID $SAL_PID $PUR_PID $FRONT_PID; exit" INT TERM
wait
