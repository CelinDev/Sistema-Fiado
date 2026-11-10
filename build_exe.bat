@echo off
echo ===================================================
echo   COMPILANDO FIADO MANAGER COM PYINSTALLER
echo ===================================================
echo.

cd /d "%~dp0"

if exist ".venv\Scripts\pyinstaller.exe" (
    set "PYINSTALLER=.venv\Scripts\pyinstaller.exe"
) else (
    set "PYINSTALLER=pyinstaller"
)

echo Executando PyInstaller...
"%PYINSTALLER%" --noconfirm --clean fiado_manager.spec

echo.
if %ERRORLEVEL% EQU 0 (
    echo ===================================================
    echo  COMPILACAO CONCLUIDA COM SUCESSO!
    echo  O executavel esta localizado em:
    echo  dist\FiadoManager\FiadoManager.exe
    echo ===================================================
) else (
    echo ERRO: Falha na compilacao com PyInstaller.
)
pause
