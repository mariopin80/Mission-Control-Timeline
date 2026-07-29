#define MyAppName "Mission Control Timeline"
#define MyAppVersion "0.9.0"
#define MyAppPublisher "Mario Pin - PU2PTU"
#define MyAppExeName "MissionControlTimeline.exe"

[Setup]
AppId={{91E5B23B-8D48-4D9D-A65E-A8EAD09E7B62}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
VersionInfoVersion=0.9.0.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Satellite pass timeline for ground stations
VersionInfoProductName={#MyAppName}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist-installer
OutputBaseFilename=MissionControlTimeline_Setup_0.9.0
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

[Registry]
Root: HKCU; Subkey: "Software\Mario Pin\Mission Control Timeline"; ValueType: string; ValueName: "DataDirectory"; ValueData: "{code:GetDataDirectory}"

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

[CustomMessages]
en.DataLocationTitle=User data location
en.DataLocationDescription=Choose where Mission Control Timeline will store its settings and orbital cache.
en.DataLocationPrompt=The default AppData location is recommended. You can change it later in Setup.
en.DataLocationError=The selected folder could not be created. Choose another location.
pt.DataLocationTitle=Local dos dados do usuário
pt.DataLocationDescription=Escolha onde o Mission Control Timeline armazenará configurações e cache orbital.
pt.DataLocationPrompt=O local padrão no AppData é recomendado. Você poderá alterá-lo posteriormente em Ajustes.
pt.DataLocationError=Não foi possível criar a pasta selecionada. Escolha outro local.
es.DataLocationTitle=Ubicación de datos del usuario
es.DataLocationDescription=Elija dónde se guardarán los ajustes y la caché orbital.
es.DataLocationPrompt=Se recomienda AppData. Puede cambiar la ubicación más tarde en Ajustes.
es.DataLocationError=No se pudo crear la carpeta seleccionada. Elija otra ubicación.
it.DataLocationTitle=Posizione dei dati utente
it.DataLocationDescription=Scegli dove salvare impostazioni e cache orbitale.
it.DataLocationPrompt=È consigliato AppData. La posizione può essere modificata in seguito.
it.DataLocationError=Impossibile creare la cartella selezionata. Scegli un’altra posizione.
fr.DataLocationTitle=Emplacement des données utilisateur
fr.DataLocationDescription=Choisissez où stocker les réglages et le cache orbital.
fr.DataLocationPrompt=L’emplacement AppData est recommandé. Il pourra être modifié ultérieurement.
fr.DataLocationError=Impossible de créer le dossier sélectionné. Choisissez un autre emplacement.
de.DataLocationTitle=Speicherort der Benutzerdaten
de.DataLocationDescription=Wählen Sie den Speicherort für Einstellungen und Orbitalcache.
de.DataLocationPrompt=Der AppData-Standard wird empfohlen. Der Ort kann später geändert werden.
de.DataLocationError=Der ausgewählte Ordner konnte nicht erstellt werden. Wählen Sie einen anderen Ort.

[Code]
var
  DataDirectoryPage: TInputDirWizardPage;

procedure InitializeWizard;
var
  ExistingDirectory: String;
begin
  DataDirectoryPage := CreateInputDirPage(
    wpSelectDir,
    CustomMessage('DataLocationTitle'),
    CustomMessage('DataLocationDescription'),
    CustomMessage('DataLocationPrompt'),
    False,
    ''
  );
  DataDirectoryPage.Add('');
  if RegQueryStringValue(
    HKCU,
    'Software\Mario Pin\Mission Control Timeline',
    'DataDirectory',
    ExistingDirectory
  ) and (ExistingDirectory <> '') then
    DataDirectoryPage.Values[0] := ExistingDirectory
  else
    DataDirectoryPage.Values[0] :=
      ExpandConstant('{localappdata}\MissionControlTimeline');
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = DataDirectoryPage.ID then
  begin
    if (Trim(DataDirectoryPage.Values[0]) = '') or
       not ForceDirectories(DataDirectoryPage.Values[0]) then
    begin
      MsgBox(CustomMessage('DataLocationError'), mbError, MB_OK);
      Result := False;
    end;
  end;
end;

function GetDataDirectory(Param: String): String;
begin
  Result := DataDirectoryPage.Values[0];
end;
