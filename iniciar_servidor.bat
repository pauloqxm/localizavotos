@echo off
title LocalizaVotos — Servidor Local
echo.
echo  ==============================
echo    LocalizaVotos - FastAPI
echo  ==============================
echo.
echo  Iniciando servidor em http://localhost:8000
echo  Pressione CTRL+C para parar.
echo.

cd /d "%~dp0app\backend"

C:\Users\paulo.ferreira\AppData\Local\anaconda3\python.exe -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

pause
