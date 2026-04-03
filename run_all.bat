@echo off
title GSDS Service Launcher
echo ===================================
echo Starting GSDS Task Management Suite
echo ===================================
cd %~dp0

echo Launching Django Backend (Core)...
start "GSDS Django Backend" cmd /k "cd backend && ..\venv\Scripts\activate.bat && python manage.py runserver 8000"

echo Launching FastAPI (AI Engine)...
start "GSDS FastAPI Engine" cmd /k "cd ai_engine && ..\venv\Scripts\activate.bat && python -m uvicorn main:app --reload --port 8001"

echo Launching Frontend UI Server...
start "GSDS Frontend UI" cmd /k "cd frontend && python -m http.server 3000"

echo.
echo All 3 services have been launched in separate terminal windows!
echo Waiting for servers to initialize...
timeout /t 3 /nobreak > nul

echo Opening dashboard in your default browser...
start http://127.0.0.1:3000/
