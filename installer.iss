; ==============================================================
;  CleanMyCompu — Installer script para Inno Setup 6.
;  Genera CleanMyCompu-Setup-vX.Y.Z.exe con wizard, atajos y desinstalador.
;
;  Requisitos:
;   1. Windows con la build ya hecha (dist\CleanMyCompu\CleanMyCompu.exe existe)
;   2. Inno Setup 6 instalado (https://jrsoftware.org/isdl.php)
;
;  Como armar el installer:
;   - Doble click en build_installer.bat
;   - O compilar con "ISCC.exe installer.iss" desde la linea de comandos
;
;  El .exe resultante queda en installer_output\CleanMyCompu-Setup-vX.Y.Z.exe
; ==============================================================

#define AppName "CleanMyCompu"
#define AppVersion "1.5.2"
#define AppPublisher "CleanMyCompu"
#define AppExeName "CleanMyCompu.exe"

[Setup]
AppId={{5B7A8F3E-9C4D-4A7A-B8E1-CC1E1B2D5F70}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL=https://github.com/mogwai-arg/CleanMyCompu
AppSupportURL=https://github.com/mogwai-arg/CleanMyCompu/issues
AppUpdatesURL=https://github.com/mogwai-arg/CleanMyCompu/releases

; Directorio por defecto: Program Files
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}

; No forzar admin — se instala por usuario si no puede en Program Files
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Salida
OutputDir=installer_output
OutputBaseFilename=CleanMyCompu-Setup-v{#AppVersion}

; Compresión (más chico = más tiempo de build)
Compression=lzma2/max
SolidCompression=yes

; UI moderna
WizardStyle=modern
WizardResizable=no

; Iconos del installer + del uninstaller (usa el ícono de la app)
SetupIconFile=assets\AppIcon.ico
UninstallDisplayIcon={app}\{#AppExeName}

; Info del programa (aparece en "Programas instalados" de Windows)
UninstallDisplayName={#AppName} {#AppVersion}
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} Installer
VersionInfoProductName={#AppName}

; Verificar arquitectura
ArchitecturesInstallIn64BitMode=x64

; Mensajes en español
ShowLanguageDialog=no

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el &Escritorio"; GroupDescription: "Accesos directos:"; Flags: checkedonce
Name: "quicklaunchicon"; Description: "Crear acceso directo en la barra de tareas"; GroupDescription: "Accesos directos:"; Flags: unchecked

[Files]
; Empaqueta TODO lo que hay en dist\CleanMyCompu\ (PyInstaller onedir).
Source: "dist\CleanMyCompu\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Menu Inicio
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\Desinstalar {#AppName}"; Filename: "{uninstallexe}"

; Escritorio (opcional segun task)
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
; Opcion "Ejecutar {#AppName}" al final del wizard
Filename: "{app}\{#AppExeName}"; Description: "Ejecutar {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Al desinstalar, borrar la config del usuario (evitamos dejar basura)
Type: filesandordirs; Name: "{userappdata}\CleanMyCompu"
Type: filesandordirs; Name: "{localappdata}\CleanMyCompu"
