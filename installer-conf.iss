; Script generated by the Inno Setup Script Wizard.
; SEE THE DOCUMENTATION FOR DETAILS ON CREATING INNO SETUP SCRIPT FILES!

#define MyAppName "Anti-Scalp"
#define MyAppVersion "1.0"
#define MyAppPublisher "ToasterUwU"
#define MyAppURL "https://github.com/ToasterUwU/Anti-Scalp"
#define MyAppExeName "anti-scalp.exe"

[Setup]
; NOTE: The value of AppId uniquely identifies this application. Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{37B94FD7-D7FA-43B2-8AF3-983F071FE8A6}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
;AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableDirPage=yes
DisableProgramGroupPage=yes
LicenseFile=C:\Users\Aki\Desktop\anti-scalp\LICENSE
; Remove the following line to run in administrative install mode (install for all users.)
PrivilegesRequired=lowest
OutputDir=C:\Users\Aki\Desktop\anti-scalp\dist
OutputBaseFilename=installer
SetupIconFile=C:\Users\Aki\Desktop\anti-scalp\icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "C:\Users\Aki\Desktop\anti-scalp\dist\anti-scalp\anti-scalp.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Aki\Desktop\anti-scalp\dist\anti-scalp\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "C:\Users\Aki\Desktop\anti-scalp\links\*"; DestDir: "{app}\links"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "C:\Users\Aki\Desktop\anti-scalp\chromedriver.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Aki\Desktop\anti-scalp\geckodriver.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Aki\Desktop\anti-scalp\icon.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Aki\Desktop\anti-scalp\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Aki\Desktop\anti-scalp\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Aki\Desktop\anti-scalp\selectors.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Aki\Desktop\anti-scalp\standard_alert.mp3"; DestDir: "{app}"; Flags: ignoreversion
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
