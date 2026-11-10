@echo off
setlocal
cd /d "%~dp0"
title Compilar Instalador Inno Setup - Fiado Manager

echo ========================================================
echo    PROCURANDO COMPILADOR DO INNO SETUP (ISCC.EXE)
echo ========================================================
echo.

set "ISCC="

if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" (
    set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
) else if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" (
    set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
) else if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" (
    set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
) else (
    where iscc.exe >nul 2>&1
    if %ERRORLEVEL% EQU 0 set "ISCC=iscc.exe"
)

if "%ISCC%"=="" (
    echo [AVISO] Inno Setup 6 nao foi encontrado no sistema!
    echo.
    echo Para gerar o instalador em arquivo unico (.exe profissional):
    echo 1. Baixe gratuitamente o Inno Setup 6 em: https://jrsoftware.org/isdl.php
    echo 2. Instale o Inno Setup e rode este arquivo novamente (build_installer.bat).
    echo.
    echo Pressione qualquer tecla para sair...
    pause >nul
    exit /b 1
)

echo Encontrado compilador: "%ISCC%"
echo Compilando instalador...
echo.

"%ISCC%" installer_inno.iss

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================================
    echo  INSTALADOR GERADO COM SUCESSO!
    echo  Arquivo gerado em: dist\installer\Instalador_FiadoManager_v1.0.0.exe
    echo ========================================================
) else (
    echo.
    echo [ERRO] Ocorreu uma falha durante a compilacao do instalador.
)

pause
