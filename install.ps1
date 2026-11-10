[CmdletBinding()]
param (
    [string]$InstallPath = "$env:LOCALAPPDATA\Programs\FiadoManager",
    [switch]$CreateDesktopShortcut = $true,
    [switch]$CreateStartMenuShortcut = $true,
    [switch]$LaunchAfterInstall = $true
)

$ErrorActionPreference = "Stop"

function Show-Header {
    Write-Host "==========================================================" -ForegroundColor Cyan
    Write-Host "         INSTALADOR - FIADO MANAGER v1.0.0               " -ForegroundColor Yellow
    Write-Host "==========================================================" -ForegroundColor Cyan
    Write-Host ""
}

Show-Header

# Localizar a pasta de origem dos arquivos
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$SourceDir = Join-Path $ScriptDir "dist\FiadoManager"

if (-not (Test-Path -Path $SourceDir)) {
    # Tenta verificar se o script está rodando dentro da própria pasta dist/installer ou raiz
    if (Test-Path -Path (Join-Path $ScriptDir "FiadoManager.exe")) {
        $SourceDir = $ScriptDir
    } else {
        Write-Host "ERRO: Pasta de origem nao encontrada!" -ForegroundColor Red
        Write-Host "Certifique-se de que o executavel foi compilado com 'build_exe.bat' e os arquivos estao em: $SourceDir" -ForegroundColor Yellow
        Read-Host "Pressione Enter para sair..."
        exit 1
    }
}

$ExeSource = Join-Path $SourceDir "FiadoManager.exe"
if (-not (Test-Path $ExeSource)) {
    Write-Host "ERRO: FiadoManager.exe nao encontrado em: $SourceDir" -ForegroundColor Red
    Read-Host "Pressione Enter para sair..."
    exit 1
}

# Fechar processo em execução caso esteja aberto
$running = Get-Process -Name "FiadoManager" -ErrorAction SilentlyContinue
if ($running) {
    Write-Host "O Fiado Manager esta em execucao. Finalizando processo para atualizar..." -ForegroundColor Yellow
    Stop-Process -Name "FiadoManager" -Force
    Start-Sleep -Seconds 1
}

Write-Host "Destino da Instalacao: $InstallPath" -ForegroundColor Green
Write-Host "Copiando arquivos, aguarde..." -ForegroundColor Cyan

if (-not (Test-Path $InstallPath)) {
    New-Item -ItemType Directory -Path $InstallPath -Force | Out-Null
}

# Copiar arquivos
Copy-Item -Path "$SourceDir\*" -Destination $InstallPath -Recurse -Force

Write-Host "Arquivos copiados com sucesso!" -ForegroundColor Green

$TargetExe = Join-Path $InstallPath "FiadoManager.exe"
$WshShell = New-Object -ComObject WScript.Shell

# Criar atalho no Menu Iniciar
if ($CreateStartMenuShortcut) {
    $StartMenuPath = [System.IO.Path]::Combine($env:APPDATA, "Microsoft\Windows\Start Menu\Programs")
    $ShortcutPath = Join-Path $StartMenuPath "Fiado Manager.lnk"
    
    $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = $TargetExe
    $Shortcut.WorkingDirectory = $InstallPath
    $Shortcut.Description = "Fiado Manager - Gestao de Credito e Clientes"
    $Shortcut.IconLocation = "$TargetExe,0"
    $Shortcut.Save()
    Write-Host "[x] Atalho criado no Menu Iniciar" -ForegroundColor Cyan
}

# Criar atalho na Área de Trabalho
if ($CreateDesktopShortcut) {
    $DesktopPath = [System.Environment]::GetFolderPath("Desktop")
    $ShortcutPath = Join-Path $DesktopPath "Fiado Manager.lnk"
    
    $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = $TargetExe
    $Shortcut.WorkingDirectory = $InstallPath
    $Shortcut.Description = "Fiado Manager - Gestao de Credito e Clientes"
    $Shortcut.IconLocation = "$TargetExe,0"
    $Shortcut.Save()
    Write-Host "[x] Atalho criado na Area de Trabalho" -ForegroundColor Cyan
}

# Criar desinstalador básico
$UninstallerScript = @"
@echo off
title Desinstalador - Fiado Manager
echo ==========================================================
echo        DESINSTALADOR - FIADO MANAGER
echo ==========================================================
echo.
set /p CONFIRM="Deseja realmente remover o Fiado Manager? (S/N): "
if /i not "%CONFIRM%"=="S" exit /b

echo Fechando aplicacao se estiver rodando...
taskkill /f /im FiadoManager.exe 2>nul

echo Removendo atalhos...
del /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Fiado Manager.lnk" 2>nul
del /q "%USERPROFILE%\Desktop\Fiado Manager.lnk" 2>nul

echo Removendo arquivos do programa...
cd /d "%TEMP%"
rd /s /q "$InstallPath" 2>nul

echo.
echo Desinstalacao concluida!
echo Nota: O banco de dados e dados do usuario em '%APPDATA%\FiadoManager' foram preservados.
pause
"@

Set-Content -Path (Join-Path $InstallPath "uninstall.bat") -Value $UninstallerScript -Encoding ASCII
Write-Host "[x] Desinstalador gerado em: $(Join-Path $InstallPath 'uninstall.bat')" -ForegroundColor Cyan

# Registro no Painel de Controle (Adicionar/Remover Programas do Usuário)
try {
    $RegPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\FiadoManager"
    if (-not (Test-Path $RegPath)) {
        New-Item -Path $RegPath -Force | Out-Null
    }
    Set-ItemProperty -Path $RegPath -Name "DisplayName" -Value "Fiado Manager"
    Set-ItemProperty -Path $RegPath -Name "DisplayVersion" -Value "1.0.0"
    Set-ItemProperty -Path $RegPath -Name "Publisher" -Value "Fiado Manager Software"
    Set-ItemProperty -Path $RegPath -Name "InstallLocation" -Value $InstallPath
    Set-ItemProperty -Path $RegPath -Name "DisplayIcon" -Value "$TargetExe,0"
    Set-ItemProperty -Path $RegPath -Name "UninstallString" -Value """$InstallPath\uninstall.bat"""
    Set-ItemProperty -Path $RegPath -Name "NoModify" -Value 1 -Type DWord
    Set-ItemProperty -Path $RegPath -Name "NoRepair" -Value 1 -Type DWord
    Write-Host "[x] Registrado no 'Configuracoes > Aplicativos Instalados' do Windows" -ForegroundColor Cyan
} catch {
    # Ignora caso haja restrição de registro
}

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "          INSTALACAO CONCLUIDA COM SUCESSO!               " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host ""

if ($LaunchAfterInstall) {
    $runNow = Read-Host "Deseja iniciar o Fiado Manager agora? (S/N) [S]"
    if ($runNow -eq "" -or $runNow -match "^[sSyY]") {
        Start-Process -FilePath $TargetExe -WorkingDirectory $InstallPath
    }
}
