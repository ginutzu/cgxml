#!/usr/bin/env bash
# Construiește CGXML2SHP v3 pentru Windows 64-bit:
#   dist/CGXML2SHP_<ver>_portabil_win64.zip   — versiune portabilă (dezarhivează și rulează)
#   dist/CGXML2SHP_<ver>_Setup_win64.exe      — kit de instalare (fără drepturi de admin)
# Necesită: makensis (NSIS 3), python3, runtime Python Windows în build/pyrt/python
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$(pwd)
VERSION=$(python3 -c "import sys; sys.path.insert(0,'src'); from cgxml2shp.core import __version__; print(__version__)")
VERSION4="${VERSION}.0.0"; VERSION4=$(echo "$VERSION4" | cut -d. -f1-4)
PUBLISHER="Ginu Popescu"
MANUAL="CGXML2SHP_v${VERSION}_Manual.pdf"
STAGE="$ROOT/build/stage/CGXML2SHP"
DIST="$ROOT/dist"

rm -rf "$ROOT/build/stage" "$DIST"; mkdir -p "$STAGE" "$DIST"

echo "== runtime Python (redus)"
cp -a "$ROOT/build/pyrt/python" "$STAGE/runtime"
R="$STAGE/runtime"
find "$R" -name '*.pdb' -delete
rm -f "$R"/DLLs/_test*.pyd "$R"/DLLs/_ctypes_test.pyd "$R"/DLLs/_msi.pyd
rm -rf "$R/include" "$R/libs" "$R/Scripts" "$R/Lib/test" "$R/Lib/idlelib" "$R/Lib/ensurepip" \
       "$R/Lib/venv" "$R/Lib/lib2to3" "$R/Lib/turtledemo" "$R/Lib/tkinter/test" "$R/Lib/unittest/test" \
       "$R/Lib/site-packages/pip" "$R"/Lib/site-packages/pip-*.dist-info \
       "$R/tcl/nmake" "$R/tcl/tix8.4.3" "$R/tcl/tk8.6/demos"
rm -f "$R"/tcl/*.lib "$R"/tcl/*.sh

echo "== aplicație"
mkdir -p "$STAGE/app" "$STAGE/docs"
cp -a "$ROOT/src/cgxml2shp" "$STAGE/app/"
find "$STAGE/app" -name '__pycache__' -prune -exec rm -rf {} +
cp "$ROOT/src/main.pyw" "$ROOT/src/cli.py" "$ROOT/src/app.ico" "$STAGE/app/"
cp "$ROOT/build/$MANUAL" "$STAGE/docs/$MANUAL"
printf '@echo off\r\nsetlocal\r\n"%%~dp0runtime\\python.exe" -I "%%~dp0app\\cli.py" %%*\r\nexit /b %%ERRORLEVEL%%\r\n' > "$STAGE/cgxml2shp-cli.cmd"
printf '@echo off\r\ncd /d "%%~dp0"\r\ntitle CGXML2SHP - linie de comanda\r\ncall cgxml2shp-cli.cmd --help\r\necho.\r\necho Exemplu: cgxml2shp-cli.cmd "D:\\date\\arhiva.zip" --constructii\r\ncmd /k\r\n' > "$STAGE/consola.cmd"
python3 - "$STAGE/CITESTE.txt" "$VERSION" "$MANUAL" <<'EOF'
import sys
p, ver, manual = sys.argv[1:]
t = f"""CGXML2SHP {ver} — conversie fișiere cadastrale CGXML în shapefile (EPSG:3844 Stereo70)

Pornire
  CGXML2SHP.exe            interfața grafică (puteți trage o arhivă ZIP peste pictogramă)
  cgxml2shp-cli.cmd        linie de comandă; rulați "cgxml2shp-cli.cmd --help"

Conținut
  runtime\\                 Python 3.12 inclus (nu modificați)
  app\\                     codul aplicației
  docs\\{manual}   manualul complet

Cerințe: Windows 10 sau 11, 64 de biți. Nu necesită instalarea altor programe.

Contact: ginu.popescu@gmail.com
"""
open(p, 'w', encoding='utf-8-sig', newline='\r\n').write(t)
EOF

echo "== precompilare bytecode (verificare sintaxă)"
python3 -m py_compile "$STAGE"/app/cgxml2shp/*.py "$STAGE/app/main.pyw" "$STAGE/app/cli.py"
find "$STAGE/app" -name '__pycache__' -prune -exec rm -rf {} +

for f in launcher installer; do   # makensis citește corect diacriticele doar din UTF-8 cu BOM
  printf '\xef\xbb\xbf' > "$ROOT/build/$f.nsi"; cat "$ROOT/packaging/$f.nsi" >> "$ROOT/build/$f.nsi"
done

echo "== lansator CGXML2SHP.exe"
makensis -V2 -DOUTFILE="$STAGE/CGXML2SHP.exe" -DICON="$ROOT/src/app.ico" -DVERSION="$VERSION" \
  -DVERSION4="$VERSION4" -DPUBLISHER="$PUBLISHER" "$ROOT/build/launcher.nsi"

echo "== kit de instalare"
SETUP="$DIST/CGXML2SHP_${VERSION}_Setup_win64.exe"
makensis -V2 -DOUTFILE="$SETUP" -DSRC="$STAGE" -DVERSION="$VERSION" -DVERSION4="$VERSION4" \
  -DPUBLISHER="$PUBLISHER" -DMANUALNAME="$MANUAL" "$ROOT/build/installer.nsi"

echo "== versiune portabilă"
touch "$STAGE/portable.txt"
printf 'Versiune portabilă: setările se salvează în settings.json, în acest folder.\r\n' > "$STAGE/portable.txt"
PORT="$DIST/CGXML2SHP_${VERSION}_portabil_win64.zip"
(cd "$ROOT/build/stage" && python3 - "$PORT" <<'EOF'
import os, sys, zipfile
out = sys.argv[1]
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for dp, dn, fn in os.walk('CGXML2SHP'):
        dn.sort()
        for f in sorted(fn):
            p = os.path.join(dp, f)
            z.write(p, p)
EOF
)
rm "$STAGE/portable.txt"
cp "$ROOT/build/$MANUAL" "$DIST/$MANUAL"

ls -la "$DIST"
du -sh "$STAGE"
