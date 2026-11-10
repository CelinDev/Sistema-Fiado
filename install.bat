@echo off
setlocal
cd /d "%~dp0"
title Instalador - Fiado Manager

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"

pause
