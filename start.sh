#!/bin/bash

echo "========================================"
echo "  Restaurante PDV - Inicio del Sistema"
echo "========================================"
echo ""

echo "Iniciando Backend (Flask)..."
cd backend
echo "Instalando dependencias..."
pip install -r requirements.txt > /dev/null 2>&1
echo "Backend iniciando en puerto 5000..."
python app.py &
BACKEND_PID=$!

echo ""
echo "Esperando 3 segundos..."
sleep 3

echo ""
echo "Iniciando Frontend (React + Vite)..."
cd ../frontend
echo "Instalando dependencias..."
npm install > /dev/null 2>&1
echo "Frontend iniciando en puerto 5173..."
npm run dev &
FRONTEND_PID=$!

echo ""
echo "========================================"
echo "Sistema iniciado!"
echo ""
echo "Backend:  http://localhost:5000"
echo "Frontend: http://localhost:5173"
echo ""
echo "Presiona Ctrl+C para detener..."
echo "========================================"

wait $BACKEND_PID $FRONTEND_PID
