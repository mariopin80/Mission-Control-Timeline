#define MyAppName "Mission Control Timeline"
#define MyAppVersion "0.8.2"
#define MyAppPublisher "Mario Pin - PU2PTU"
#define MyAppExeName "MissionControlTimeline.exe"

[Setup]
AppId={{91E5B23B-8D48-4D9D-A65E-A8EAD09E7B62}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
VersionInfoVersion=0.8.2.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Satellite pass timeline for ground stations
VersionInfoProductName={#MyAppName}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist-installer
OutputBaseFilename=MissionControlTimeline_Setup_0.8.2
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\assets\mission-control-timeline-setup.ico
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\MissionControlTimeline.ico
SetupLogging=yes

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"; LicenseFile: "..\licenses\EULA-en.txt"
Name: "pt"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"; LicenseFile: "..\licenses\EULA-pt.txt"
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"; LicenseFile: "..\licenses\EULA-es.txt"
Name: "it"; MessagesFile: "compiler:Languages\Italian.isl"; LicenseFile: "..\licenses\EULA-it.txt"
Name: "fr"; MessagesFile: "compiler:Languages\French.isl"; LicenseFile: "..\licenses\EULA-fr.txt"
Name: "de"; MessagesFile: "compiler:Languages\German.isl"; LicenseFile: "..\licenses\EULA-de.txt"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\MissionControlTimeline\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\assets\mission-control-timeline.ico"; DestDir: "{app}"; DestName: "MissionControlTimeline.ico"; Flags: ignoreversion
Source: "..\LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\TERMS_OF_USE.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\PRIVACY_NOTICE.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\licenses\LICENSE-*.txt"; DestDir: "{app}\licenses"; Flags: ignoreversion
Source: "..\licenses\TERMS-*.txt"; DestDir: "{app}\licenses"; Flags: ignoreversion
Source: "..\licenses\PRIVACY-*.txt"; DestDir: "{app}\licenses"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\MissionControlTimeline.ico"; IconIndex: 0
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\MissionControlTimeline.ico"; IconIndex: 0; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
