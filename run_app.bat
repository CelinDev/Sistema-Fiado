@echo off
title Fiado Manager - Sistema de Gestao de Fiados
cd /d "%~dp0"

if exist "dist\FiadoManager\FiadoManager.exe" (
    start "" "dist\FiadoManager\FiadoManager.exe"
) else if exist ".venv\Scripts\python.exe" (
    start "" ".venv\Scripts\python.exe" main.py
) else (
    start "" python main.py
)
exit
