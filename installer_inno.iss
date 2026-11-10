; Script Inno Setup para Fiado Manager
; Como usar:
; 1. Baixe e instale o Inno Setup 6 (gratuito): https://jrsoftware.org/isdl.php
; 2. Abra este arquivo (installer_inno.iss) no Inno Setup Compiler e clique em "Compile" (F9),
;    ou execute via linha de comando: iscc installer_inno.iss

#define MyAppName "Fiado Manager"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Fiado Manager Software"
#define MyAppExeName "FiadoManager.exe"
#define MyAppSourceDir "dist\FiadoManager"

[Setup]
AppId={{C78E49D3-421F-4B89-982F-1A2D99E4B821}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=dist\installer
OutputBaseFilename=Instalador_FiadoManager_v{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#MyAppSourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
