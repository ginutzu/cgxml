; Lansator CGXML2SHP.exe — pornește interfața grafică cu Python-ul inclus (runtime\pythonw.exe).
; Fișierele/folderele trase peste CGXML2SHP.exe sunt trimise aplicației ca intrări.
Unicode true
!include FileFunc.nsh

Name "CGXML2SHP"
OutFile "${OUTFILE}"
Icon "${ICON}"
SilentInstall silent
RequestExecutionLevel user
SetCompressor /SOLID lzma

VIProductVersion "${VERSION4}"
VIAddVersionKey /LANG=0 "ProductName" "CGXML2SHP"
VIAddVersionKey /LANG=0 "FileDescription" "CGXML2SHP - conversie CGXML in Shapefile"
VIAddVersionKey /LANG=0 "FileVersion" "${VERSION}"
VIAddVersionKey /LANG=0 "ProductVersion" "${VERSION}"
VIAddVersionKey /LANG=0 "CompanyName" "${PUBLISHER}"
VIAddVersionKey /LANG=0 "LegalCopyright" "${PUBLISHER}"

Section
  ${GetParameters} $R0
  IfFileExists "$EXEDIR\runtime\pythonw.exe" +3 0
    MessageBox MB_ICONSTOP "Nu găsesc runtime\pythonw.exe lângă CGXML2SHP.exe.$\r$\nReinstalați aplicația sau dezarhivați din nou versiunea portabilă."
    Abort
  SetOutPath "$EXEDIR"
  Exec '"$EXEDIR\runtime\pythonw.exe" -I "$EXEDIR\app\main.pyw" $R0'
SectionEnd
