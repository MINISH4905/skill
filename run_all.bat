@echo off
title SkillForge Production Hub
echo ===========================================
echo SkillForge - startup order: AI Engine -^> Django -^> browser
echo ===========================================
cd /d %~dp0

echo [1/3] Launching AI Engine (FastAPI on 8001)...
start "SkillForge AI Engine" cmd /k "cd /d %~dp0ai_engine && ..\pytorch_env\Scripts\activate.bat && python -m uvicorn main:app --host 127.0.0.1 --port 8001"

echo Waiting for AI Engine health (max 90s)...
set /a _w=0
:wait_ai
powershell -NoProfile -Command "try { (Invoke-WebRequest -UseBasicParsing -Uri http://127.0.0.1:8001/api/v1/health -TimeoutSec 2).StatusCode } catch { exit 1 }" | findstr /r "^200" >nul
if %errorlevel%==0 goto ai_ok
set /a _w+=1
if %_w% GEQ 45 goto ai_skip
timeout /t 2 /nobreak >nul
goto wait_ai
:ai_ok
echo AI Engine is healthy.
goto start_django
:ai_skip
echo WARNING: AI Engine did not respond in time. Django will still start; generation may fall back to vault.

:start_django
echo [2/3] Launching Django (port 8000)...
start "SkillForge Django Backend" cmd /k "cd /d %~dp0backend && ..\pytorch_env\Scripts\activate.bat && python manage.py runserver 8000"

echo [3/3] Opening UI (served by Django static/templates)...
timeout /t 3 /nobreak >nul
start http://127.0.0.1:8000/

echo ===========================================
echo READY. API: Django http://127.0.0.1:8000/api/v1/health/
echo        AI   http://127.0.0.1:8001/api/v1/health
echo ===========================================
pause
