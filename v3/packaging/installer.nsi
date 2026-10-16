; Kit de instalare CGXML2SHP — instalare pe utilizator, fără drepturi de administrator.
Unicode true
!include MUI2.nsh
!include x64.nsh
!include FileFunc.nsh
!include LogicLib.nsh

!define APPNAME "CGXML2SHP"
!define UNINSTKEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\CGXML2SHP"
!define MANUAL "docs\${MANUALNAME}"

Name "${APPNAME} ${VERSION}"
Caption "Instalare ${APPNAME} ${VERSION}"
OutFile "${OUTFILE}"
InstallDir "$LOCALAPPDATA\Programs\${APPNAME}"
InstallDirRegKey HKCU "${UNINSTKEY}" "InstallLocation"
RequestExecutionLevel user
SetCompressor /SOLID lzma
BrandingText "${APPNAME} ${VERSION}"

VIProductVersion "${VERSION4}"
VIAddVersionKey /LANG=0 "ProductName" "${APPNAME}"
VIAddVersionKey /LANG=0 "FileDescription" "Instalare ${APPNAME} ${VERSION}"
VIAddVersionKey /LANG=0 "FileVersion" "${VERSION}"
VIAddVersionKey /LANG=0 "ProductVersion" "${VERSION}"
VIAddVersionKey /LANG=0 "CompanyName" "${PUBLISHER}"
VIAddVersionKey /LANG=0 "LegalCopyright" "${PUBLISHER}"

!define MUI_ICON "${SRC}/app/app.ico"
!define MUI_UNICON "${SRC}/app/app.ico"
!define MUI_ABORTWARNING
!define MUI_COMPONENTSPAGE_SMALLDESC
!define MUI_WELCOMEPAGE_TITLE "Instalare ${APPNAME} ${VERSION}"
!define MUI_WELCOMEPAGE_TEXT "Acest program instalează ${APPNAME} ${VERSION} — conversie fișiere cadastrale CGXML în shapefile (EPSG:3844 Stereo70).$\r$\n$\r$\nAplicația include propriul Python; nu este nevoie de alte programe și nici de drepturi de administrator.$\r$\n$\r$\nApăsați Înainte pentru a continua."
!define MUI_FINISHPAGE_RUN "$INSTDIR\CGXML2SHP.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Pornește ${APPNAME}"
!define MUI_FINISHPAGE_SHOWREADME "$INSTDIR\${MANUAL}"
!define MUI_FINISHPAGE_SHOWREADME_TEXT "Deschide manualul (PDF)"
!define MUI_FINISHPAGE_SHOWREADME_NOTCHECKED

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "Romanian"

Function .onInit
  ${IfNot} ${RunningX64}
    MessageBox MB_ICONSTOP "${APPNAME} necesită Windows pe 64 de biți." /SD IDOK
    Abort
  ${EndIf}
FunctionEnd

Section "${APPNAME} (obligatoriu)" SecMain
  SectionIn RO
  ; la reinstalare/actualizare se curăță doar folderele proprii ale aplicației
  RMDir /r "$INSTDIR\runtime"
  RMDir /r "$INSTDIR\app"
  RMDir /r "$INSTDIR\docs"
  SetOutPath "$INSTDIR"
  File /r "${SRC}/*.*"
  WriteUninstaller "$INSTDIR\Dezinstalare.exe"

  CreateDirectory "$SMPROGRAMS\${APPNAME}"
  CreateShortcut "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk" "$INSTDIR\CGXML2SHP.exe" "" "$INSTDIR\app\app.ico" 0
  CreateShortcut "$SMPROGRAMS\${APPNAME}\Manual ${APPNAME}.lnk" "$INSTDIR\${MANUAL}"
  CreateShortcut "$SMPROGRAMS\${APPNAME}\Linie de comandă ${APPNAME}.lnk" "$INSTDIR\consola.cmd" "" "$INSTDIR\app\app.ico" 0
  CreateShortcut "$SMPROGRAMS\${APPNAME}\Dezinstalare ${APPNAME}.lnk" "$INSTDIR\Dezinstalare.exe"

  WriteRegStr HKCU "${UNINSTKEY}" "DisplayName" "${APPNAME} ${VERSION}"
  WriteRegStr HKCU "${UNINSTKEY}" "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "${UNINSTKEY}" "Publisher" "${PUBLISHER}"
  WriteRegStr HKCU "${UNINSTKEY}" "DisplayIcon" "$INSTDIR\app\app.ico"
  WriteRegStr HKCU "${UNINSTKEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${UNINSTKEY}" "UninstallString" '"$INSTDIR\Dezinstalare.exe"'
  WriteRegStr HKCU "${UNINSTKEY}" "QuietUninstallString" '"$INSTDIR\Dezinstalare.exe" /S'
  WriteRegDWORD HKCU "${UNINSTKEY}" "NoModify" 1
  WriteRegDWORD HKCU "${UNINSTKEY}" "NoRepair" 1
  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  WriteRegDWORD HKCU "${UNINSTKEY}" "EstimatedSize" $0
SectionEnd

Section "Scurtătură pe Desktop" SecDesktop
  CreateShortcut "$DESKTOP\${APPNAME}.lnk" "$INSTDIR\CGXML2SHP.exe" "" "$INSTDIR\app\app.ico" 0
SectionEnd

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SecMain} "Aplicația, Python-ul inclus, manualul și scurtăturile din meniul Start."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop} "Pune o scurtătură CGXML2SHP pe Desktop."
!insertmacro MUI_FUNCTION_DESCRIPTION_END

Section "Uninstall"
  Delete "$DESKTOP\${APPNAME}.lnk"
  RMDir /r "$SMPROGRAMS\${APPNAME}"
  ; se șterg doar fișierele și folderele instalate, niciodată tot folderul ales
  RMDir /r "$INSTDIR\runtime"
  RMDir /r "$INSTDIR\app"
  RMDir /r "$INSTDIR\docs"
  Delete "$INSTDIR\CGXML2SHP.exe"
  Delete "$INSTDIR\cgxml2shp-cli.cmd"
  Delete "$INSTDIR\consola.cmd"
  Delete "$INSTDIR\CITESTE.txt"
  Delete "$INSTDIR\Dezinstalare.exe"
  RMDir "$INSTDIR"
  Delete "$APPDATA\${APPNAME}\settings.json"
  RMDir "$APPDATA\${APPNAME}"
  DeleteRegKey HKCU "${UNINSTKEY}"
SectionEnd
