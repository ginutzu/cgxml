# -*- coding: utf-8 -*-
"""Generează manualul PDF CGXML2SHP v3 (română)."""
import sys
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Frame, Image, KeepTogether, PageBreak, PageTemplate,
                                Paragraph, Preformatted, Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

OUT, SHOT, ICON, VERSION = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
MANUAL_NAME = 'CGXML2SHP_v%s_Manual.pdf' % VERSION

F = '/usr/share/fonts/truetype/dejavu/'
pdfmetrics.registerFont(TTFont('Sans', F + 'DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('Sans-Bold', F + 'DejaVuSans-Bold.ttf'))
pdfmetrics.registerFont(TTFont('Sans-Oblique', F + 'DejaVuSans-Oblique.ttf'))
pdfmetrics.registerFont(TTFont('Mono', F + 'DejaVuSansMono.ttf'))
pdfmetrics.registerFontFamily('Sans', normal='Sans', bold='Sans-Bold', italic='Sans-Oblique',
                              boldItalic='Sans-Bold')

INK = colors.HexColor('#1b2430')
ACC = colors.HexColor('#007f9e')
ACC_L = colors.HexColor('#e6f6fa')
GRID = colors.HexColor('#c9d6e0')
MUTE = colors.HexColor('#5a6b7b')
WARN_BG = colors.HexColor('#fff4e0')
WARN_BD = colors.HexColor('#e0a030')

st = {
    'body': ParagraphStyle('body', fontName='Sans', fontSize=9.6, leading=14, textColor=INK, spaceAfter=5),
    'h1': ParagraphStyle('h1', fontName='Sans-Bold', fontSize=16, leading=20, textColor=ACC,
                         spaceBefore=4, spaceAfter=8),
    'h2': ParagraphStyle('h2', fontName='Sans-Bold', fontSize=11.5, leading=15, textColor=INK,
                         spaceBefore=10, spaceAfter=4),
    'cell': ParagraphStyle('cell', fontName='Sans', fontSize=8.4, leading=11, textColor=INK),
    'cellb': ParagraphStyle('cellb', fontName='Sans-Bold', fontSize=8.4, leading=11, textColor=colors.white),
    'code': ParagraphStyle('code', fontName='Mono', fontSize=8.2, leading=11, textColor=INK),
    'bullet': ParagraphStyle('bullet', fontName='Sans', fontSize=9.6, leading=14, textColor=INK,
                             leftIndent=14, bulletIndent=4, spaceAfter=2),
    'note': ParagraphStyle('note', fontName='Sans', fontSize=9, leading=13, textColor=INK),
    'cap': ParagraphStyle('cap', fontName='Sans-Oblique', fontSize=8.4, leading=11, textColor=MUTE,
                          alignment=TA_CENTER, spaceAfter=8),
    'toc1': ParagraphStyle('toc1', fontName='Sans', fontSize=10, leading=17, textColor=INK),
}

story = []


def P(t, s='body'):
    story.append(Paragraph(t, st[s]))


def H1(t):
    story.append(CondPageBreak(70 * mm))   # nu lăsa titlul singur la final de pagină
    p = Paragraph(t, st['h1'])
    p._toc = t
    story.append(p)


def H2(t):
    story.append(CondPageBreak(30 * mm))
    story.append(Paragraph(t, st['h2']))


def B(items):
    for t in items:
        story.append(Paragraph(t, st['bullet'], bulletText='•'))
    story.append(Spacer(1, 4))


def CODE(t):
    pre = Preformatted(t, st['code'])
    tb = Table([[pre]], colWidths=[170 * mm])
    tb.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f2f5f7')),
                            ('BOX', (0, 0), (-1, -1), 0.5, GRID),
                            ('LEFTPADDING', (0, 0), (-1, -1), 8), ('TOPPADDING', (0, 0), (-1, -1), 6),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 6)]))
    story.append(tb)
    story.append(Spacer(1, 6))


def NOTE(t, warn=False):
    tb = Table([[Paragraph(t, st['note'])]], colWidths=[170 * mm])
    tb.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), WARN_BG if warn else ACC_L),
                            ('LINEBEFORE', (0, 0), (0, -1), 3, WARN_BD if warn else ACC),
                            ('LEFTPADDING', (0, 0), (-1, -1), 10), ('TOPPADDING', (0, 0), (-1, -1), 6),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 6)]))
    story.append(tb)
    story.append(Spacer(1, 6))


def T(rows, widths, mono_cols=()):
    data = [[Paragraph(c, st['cellb']) for c in rows[0]]]
    for r in rows[1:]:
        cells = []
        for i, c in enumerate(r):
            if i in mono_cols:
                cells.append(Paragraph('<font name="Mono">%s</font>' % c, st['cell']))
            else:
                cells.append(Paragraph(c, st['cell']))
        data.append(cells)
    tb = Table(data, colWidths=[w * mm for w in widths], repeatRows=1)
    tb.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), ACC),
                            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f8fa')]),
                            ('GRID', (0, 0), (-1, -1), 0.4, GRID), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                            ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]))
    story.append(tb)
    story.append(Spacer(1, 8))


def M(t):
    return '<font name="Mono">%s</font>' % t


# ── Copertă ────────────────────────────────────────────────
story.append(Spacer(1, 40 * mm))
story.append(Image(ICON, width=36 * mm, height=36 * mm))
story.append(Spacer(1, 10 * mm))
story.append(Paragraph('CGXML2SHP %s' % VERSION, ParagraphStyle('t', fontName='Sans-Bold', fontSize=30,
                                                                leading=36, textColor=ACC, alignment=TA_CENTER)))
story.append(Spacer(1, 4 * mm))
story.append(Paragraph('Conversie fișiere cadastrale CGXML în Shapefile', ParagraphStyle(
    's', fontName='Sans', fontSize=14, leading=18, textColor=INK, alignment=TA_CENTER)))
story.append(Spacer(1, 3 * mm))
story.append(Paragraph('Manual de instalare și utilizare · Windows 10 / 11, 64 de biți', ParagraphStyle(
    's2', fontName='Sans', fontSize=10.5, leading=14, textColor=MUTE, alignment=TA_CENTER)))
story.append(Spacer(1, 60 * mm))
story.append(Paragraph('EPSG:3844 · Stereo70 · Pulkovo 1942 (Adj 1958) · CGXMLSchema_new_v3.xsd',
                       ParagraphStyle('c1', fontName='Sans', fontSize=9, textColor=MUTE, alignment=TA_CENTER)))
story.append(Spacer(1, 2 * mm))
story.append(Paragraph('Octombrie 2026 · Contact: ginu.popescu@gmail.com',
                       ParagraphStyle('c2', fontName='Sans', fontSize=9, textColor=MUTE, alignment=TA_CENTER)))
story.append(PageBreak())

# ── Cuprins ────────────────────────────────────────────────
story.append(Paragraph('Cuprins', st['h1']))
toc = TableOfContents()
toc.levelStyles = [st['toc1']]
toc.dotsMinLevel = 0
story.append(toc)
story.append(PageBreak())

# ── 1 ─────────────────────────────────────────────────────
H1('1. Despre aplicație')
P('<b>CGXML2SHP</b> convertește fișierele cadastrale <b>CGXML</b> (schema <i>CGXMLSchema_new_v3.xsd</i>) '
  'într-un <b>shapefile Esri</b> de poligoane, în proiecția națională <b>Stereo70 (EPSG:3844)</b>. '
  'Pentru fiecare teren se construiește conturul din punctele lui, se recunosc enclavele și terenurile '
  'formate din mai multe părți, iar tabelul de atribute primește datele cadastrale: număr cadastral, '
  'acte, proprietari, categorii de folosință, arie măsurată și arie calculată.')
P('Versiunea 3 este o aplicație desktop pentru Windows, scrisă în Python. Aplicația <b>are propriul Python inclus</b>: '
  'nu trebuie instalat nimic altceva, nu sunt necesare drepturi de administrator și nu are nevoie de internet. '
  'Toate fișierele sunt prelucrate local, pe calculatorul utilizatorului.')
H2('Ce este nou în versiunea 3')
B(['Aplicație Windows independentă: interfață grafică și linie de comandă, cu Python 3.12 inclus.',
   'Funcționează complet fără internet (versiunea web încărca biblioteci de pe internet).',
   'Intrări multiple într-o singură rulare: arhive ZIP, foldere întregi (inclusiv subfoldere și ZIP-urile din ele) '
   'și fișiere .cgxml individuale.',
   'Ieșire ca arhivă ZIP sau direct într-un folder cu fișierele shapefile.',
   'Un fișier CGXML defect este semnalat în jurnal și sărit; restul lotului se procesează în continuare.',
   'Setările se păstrează între rulări; jurnalul poate fi salvat ca fișier text.',
   'Rezultatul este identic cu cel produs de versiunea web 2.1 pentru aceleași date (singura diferență este data de creare din antetul DBF).'])

H2('Pachetele livrate')
T([['Fișier', 'Ce este'],
   ['CGXML2SHP_%s_Setup_win64.exe' % VERSION, 'Kit de instalare. Instalează aplicația pentru utilizatorul curent, '
    'creează scurtături în meniul Start (și opțional pe Desktop) și se poate dezinstala din Setări Windows.'],
   ['CGXML2SHP_%s_portabil_win64.zip' % VERSION, 'Versiune portabilă. Se dezarhivează oriunde (inclusiv pe un stick USB) '
    'și se rulează direct, fără instalare.'],
   [MANUAL_NAME, 'Acest manual. Este inclus și în aplicație, în folderul docs.']],
  [62, 108], mono_cols=(0,))

# ── 2 ─────────────────────────────────────────────────────
H1('2. Cerințe de sistem')
T([['Element', 'Cerință'],
   ['Sistem de operare', 'Windows 10 sau Windows 11, 64 de biți (și Windows Server 2016 sau mai nou)'],
   ['Spațiu pe disc', 'aproximativ 50 MB'],
   ['Memorie', 'orice calculator actual; lotul cu mii de fișiere CGXML necesită câteva sute de MB RAM'],
   ['Drepturi', 'utilizator obișnuit; nu sunt necesare drepturi de administrator'],
   ['Programe suplimentare', 'niciunul — Python 3.12 și Tcl/Tk sunt incluse în aplicație'],
   ['Internet', 'nu este necesar']],
  [45, 125])
NOTE('Windows pe 32 de biți și Windows 7 sau mai vechi nu sunt suportate, deoarece Python 3.12 nu mai rulează pe ele. '
     'Kit-ul de instalare refuză instalarea pe Windows pe 32 de biți, cu un mesaj explicit.')

# ── 3 ─────────────────────────────────────────────────────
H1('3. Instalare')
H2('3.1 Cu kit-ul de instalare')
B(['Rulați <b>CGXML2SHP_%s_Setup_win64.exe</b>.' % VERSION,
   'Dacă apare fereastra albastră <i>Windows a protejat computerul</i> (SmartScreen), apăsați '
   '<b>Mai multe informații</b> → <b>Rulează oricum</b>. Mesajul apare pentru că fișierul nu este semnat digital, '
   'nu pentru că ar conține ceva periculos.',
   'Urmați pașii: alegeți dacă doriți scurtătură pe Desktop și, opțional, alt folder de instalare.',
   'Folderul implicit este %s — nu necesită drepturi de administrator.' % M('%LOCALAPPDATA%\\Programs\\CGXML2SHP'),
   'La final puteți porni aplicația direct și deschide manualul.'])
P('În meniul Start apar: <b>CGXML2SHP</b>, <b>Manual CGXML2SHP</b>, <b>Linie de comandă CGXML2SHP</b> și '
  '<b>Dezinstalare CGXML2SHP</b>.')
H2('3.2 Instalare automată (administratori IT)')
P('Kit-ul acceptă instalarea fără ferestre, utilă pentru distribuirea pe mai multe calculatoare:')
CODE('CGXML2SHP_%s_Setup_win64.exe /S\n'
     'CGXML2SHP_%s_Setup_win64.exe /S /D=D:\\Aplicatii\\CGXML2SHP' % (VERSION, VERSION))
P('Parametrul %s trebuie să fie ultimul și fără ghilimele. Dezinstalarea automată: %s.' % (
    M('/D='), M('"%LOCALAPPDATA%\\Programs\\CGXML2SHP\\Dezinstalare.exe" /S')))
H2('3.3 Versiunea portabilă')
B(['Dezarhivați <b>CGXML2SHP_%s_portabil_win64.zip</b> în orice folder (de exemplu pe un stick USB). '
   'Folosiți <i>Extragere totală</i> — aplicația nu pornește direct din interiorul arhivei.' % VERSION,
   'Porniți <b>CGXML2SHP.exe</b> din folderul CGXML2SHP.',
   'Setările se salvează în %s, în același folder, deci aplicația nu lasă urme pe calculator.' % M('settings.json')])
NOTE('Dacă ați descărcat arhiva de pe internet sau din e-mail, Windows o poate marca drept „descărcată”. '
     'Înainte de dezarhivare: clic dreapta pe ZIP → <b>Proprietăți</b> → bifați <b>Deblocare</b> → OK. '
     'Astfel nu mai apar avertismente la fiecare pornire.', warn=True)
H2('3.4 Actualizare și dezinstalare')
P('Pentru actualizare rulați kit-ul noii versiuni peste cea existentă; setările se păstrează. '
  'Dezinstalarea se face din <b>Setări Windows → Aplicații → CGXML2SHP → Dezinstalare</b> sau din meniul Start. '
  'Dezinstalarea șterge fișierele aplicației și setările ei; fișierele dumneavoastră, chiar dacă au fost salvate în folderul '
  'aplicației, rămân neatinse. Versiunea portabilă se elimină ștergând folderul.')

# ── 4 ─────────────────────────────────────────────────────
H1('4. Utilizare — interfața grafică')
story.append(KeepTogether([Image(SHOT, width=150 * mm, height=150 * mm * 900 / 920),
                           Paragraph('Fereastra principală după o conversie (captură ilustrativă; fonturile '
                                     'pot arăta ușor diferit pe calculatorul dumneavoastră).', st['cap'])]))
H2('Pași')
B(['<b>Intrare</b> — adăugați una sau mai multe surse: <b>Adaugă ZIP…</b> (arhive cu fișiere .cgxml), '
   '<b>Adaugă folder…</b> (toate fișierele .cgxml din folder și subfoldere, inclusiv cele din arhivele ZIP aflate acolo) '
   'sau <b>Adaugă .cgxml…</b>. <b>Elimină</b> scoate intrările selectate din listă.',
   'Mai rapid: trageți o arhivă ZIP sau un folder direct peste pictograma <b>CGXML2SHP.exe</b> '
   '(sau peste scurtătura de pe Desktop) — aplicația se deschide cu intrarea deja adăugată.',
   '<b>Ieșire</b> — alegeți <b>Arhivă ZIP</b> sau <b>Folder cu fișiere SHP</b>. Locația se propune automat lângă '
   'prima intrare (de exemplu %s); o puteți schimba cu <b>Alege…</b>.' % M('date_SHP.zip'),
   '<b>Opțiuni de procesare</b> — vezi capitolul 7.',
   'Apăsați <b>Procesează fișierele CGXML</b>. Bara de progres avansează pe fișiere; <b>Oprește</b> întrerupe lotul.',
   'Urmăriți jurnalul și statisticile, apoi <b>Deschide rezultatul</b> afișează fișierul în Explorer.'])
H2('Jurnalul')
P('Fiecare teren apare pe un rând, cu numărul de inele, punctele, aria calculată (%s), diferența față de aria '
  'măsurată și numărul cadastral. Culorile au semnificație:' % M('S_calc'))
T([['Culoare', 'Semnificație'],
   ['verde', 'teren convertit fără observații'],
   ['portocaliu', 'teren cu enclave sau din mai multe părți, diferență de arie peste 1%, valori trunchiate în DBF, '
                  'puncte ignorate'],
   ['roșu', 'eroare: fișier CGXML invalid, nicio intrare validă etc.'],
   ['albastru', 'titluri: fișierul curent, totalurile']], [30, 140])
P('Butonul <b>Salvează jurnalul…</b> scrie jurnalul într-un fișier text (UTF-8), util pentru arhivare sau raportare.')
H2('Ce se reține între rulări')
P('Opțiunile bifate, tipul ieșirii și ultimul folder folosit se salvează automat: în %s pentru versiunea instalată, '
  'respectiv în %s din folderul aplicației pentru versiunea portabilă.' % (
      M('%APPDATA%\\CGXML2SHP\\settings.json'), M('settings.json')))

# ── 5 ─────────────────────────────────────────────────────
H1('5. Linie de comandă')
P('Pentru procesări automate (scripturi, sarcini programate) folosiți %s, aflat în folderul aplicației. '
  'Din meniul Start, <b>Linie de comandă CGXML2SHP</b> deschide o consolă direct în acel folder.' % M('cgxml2shp-cli.cmd'))
CODE('cgxml2shp-cli.cmd INTRARE [INTRARE ...] [-o IESIRE] [opțiuni]')
T([['Opțiune', 'Efect'],
   ['-o, --iesire CALE', 'fișierul .zip sau folderul de ieșire; implicit lângă intrare, &lt;nume&gt;_SHP.zip'],
   ['--folder', 'scrie fișierele shapefile într-un folder în loc de arhivă ZIP'],
   ['--constructii', 'generează și stratul constructii.shp'],
   ['--inversare-xy', 'inversează axele (CGXML cu X=Nord, Y=Est)'],
   ['--dbf-simplu', 'doar atributele de bază în DBF'],
   ['--fara-inchidere', 'nu închide automat inelele poligoanelor'],
   ['--cnp', 'include IDCODE (CNP/CUI) în PROPRIETAR'],
   ['-q, --silentios', 'afișează doar erorile și rezumatul final'],
   ['--version, --help', 'versiunea, respectiv ajutorul complet']], [48, 122], mono_cols=(0,))
H2('Exemple')
CODE('cd /d "%LOCALAPPDATA%\\Programs\\CGXML2SHP"\n\n'
     'cgxml2shp-cli.cmd "D:\\Cadastru\\export.zip"\n'
     'cgxml2shp-cli.cmd "D:\\Cadastru\\UAT_Comana" -o "D:\\GIS\\comana_teren.zip" --constructii\n'
     'cgxml2shp-cli.cmd a.cgxml b.cgxml --folder -o "D:\\GIS\\rezultat"\n'
     'cgxml2shp-cli.cmd "D:\\Cadastru\\export.zip" -q > raport.txt')
H2('Coduri de ieșire')
T([['Cod', 'Semnificație'],
   ['0', 'conversie reușită'],
   ['1', 'eroare (nicio intrare validă, niciun poligon) sau cel puțin un fișier CGXML nu a putut fi citit'],
   ['2', 'parametri greșiți sau intrare inexistentă']], [20, 150], mono_cols=(0,))
H2('Procesare în lot pe UAT-uri')
P('Exemplu de fișier .bat care convertește fiecare subfolder dintr-un director într-un shapefile separat:')
CODE('@echo off\n'
     'set APP=%LOCALAPPDATA%\\Programs\\CGXML2SHP\\cgxml2shp-cli.cmd\n'
     'for /d %%D in ("D:\\Cadastru\\UAT\\*") do (\n'
     '    call "%APP%" "%%D" -o "D:\\GIS\\%%~nxD_teren.zip" --constructii -q\n'
     ')')
P('Pentru versiunea portabilă, înlocuiți calea din %s cu folderul în care ați dezarhivat aplicația.' % M('APP'))

# ── 6 ─────────────────────────────────────────────────────
H1('6. Formatul CGXML și logica de conversie')
P('Fișierul CGXML este un <b>XML DataSet plat de tip ADO.NET</b>: toate tabelele sunt elemente de același nivel sub '
  'rădăcina &lt;CGXML&gt;, legate prin chei. Aplicația citește următoarele tabele și câmpuri:')
T([['Tabel', 'Câmpuri citite', 'Relație'],
   ['FileDescription', 'FILEID, FILENAME, EXPORTDATE, OPERATIONTYPE', '—'],
   ['Land', 'LANDID, FILEID, MEASUREDAREA, PAPERCADNO, CADSECTOR, E2IDENTIFIER, TOPONO', 'Land.FILEID → FileDescription'],
   ['Points', 'IMMOVABLEID, BUILDINGID, NO, X, Y', 'IMMOVABLEID → Land; BUILDINGID → Building'],
   ['Parcel', 'LANDID, USECATEGORY', 'Parcel.LANDID → Land'],
   ['Deed', 'FILEID, DEEDTYPE, DEEDNUMBER, DEEDDATE', 'Deed.FILEID → FileDescription'],
   ['Person', 'FILEID, FIRSTNAME, LASTNAME, IDCODE', 'Person.FILEID → FileDescription'],
   ['Building', 'BUILDINGID, LANDID, BUILDNO, MEASUREDAREA', 'Building.LANDID → Land']],
  [28, 82, 60])
NOTE('ACTE și PROPRIETAR se leagă prin FILEID, nu prin teren. Dacă un fișier CGXML conține mai multe terenuri, '
     'fiecare primește toate actele și persoanele din fișier. Pentru fișierele obișnuite (un imobil per fișier) '
     'rezultatul este corect.')
H2('Pașii conversiei')
B(['<b>Colectare</b>: se acceptă doar fișierele care se termină în .cgxml; se ignoră %s și fișierele %s create de macOS.'
   % (M('__MACOSX/'), M('._*')),
   '<b>Grupare</b>: un punct cu BUILDINGID aparține construcției și <b>nu intră</b> în conturul terenului, chiar '
   'dacă are și IMMOVABLEID. Celelalte puncte se grupează după IMMOVABLEID.',
   '<b>Ordonare</b>: punctele se sortează crescător după NO; duplicatele consecutive se elimină '
   '(toleranță 0,5 mm). Dacă NO lipsește, se folosește ordinea din fișier.',
   '<b>Inele</b>: un inel se încheie când secvența revine la <i>primul punct al inelului curent</i>; următorul punct '
   'începe un inel nou. Punctele rămase după ultimul inel închis formează un inel dacă sunt cel puțin 3.',
   '<b>Clasificare</b>: inelele se ordonează după arie; un inel conținut de un număr impar de inele mai mari este '
   '<b>enclavă</b>, altfel este <b>parte exterioară</b>. Inelele disjuncte devin părți multiple (multipart).',
   '<b>Orientare</b> conform specificației ESRI: exterior în sens orar, enclave în sens trigonometric.',
   '<b>Arie</b>: AREA_CALC = suma părților exterioare minus enclavele; AREA_DIFF = diferența procentuală față de '
   'MEASUREDAREA.',
   '<b>Scriere</b>: toate poligoanele din toate fișierele se adună în stratul <i>teren</i> (și <i>constructii</i>, '
   'la cerere).'])
P('Convenția așteptată pentru un teren cu enclavă:')
CODE('NO 1 .. n      conturul exterior, ultimul punct = primul punct\n'
     'NO n+1 .. m    conturul enclavei, ultimul punct = primul punct al enclavei')

# ── 7 ─────────────────────────────────────────────────────
H1('7. Opțiuni de procesare')
T([['Opțiune', 'Implicit', 'Efect'],
   ['Închide inelul poligon', 'activ', 'repetă primul punct la finalul inelului dacă lipsește'],
   ['Atribute extinse DBF', 'activ', 'include toate câmpurile din capitolul 8; dezactivat: doar câmpurile de bază'],
   ['Include construcții', 'inactiv', 'generează stratul separat constructii (din punctele cu BUILDINGID); '
                                      'punctele de construcție sunt excluse din teren în orice caz'],
   ['Forțează inversare X↔Y', 'inactiv', 'shp_x ← Y, shp_y ← X; se bifează când poligoanele apar rotite sau '
                                          'oglindite (vezi capitolul 9)'],
   ['Include CNP/CUI în PROPRIETAR', 'inactiv', 'adaugă IDCODE după numele fiecărui proprietar. Aplicația cere '
                                                 'confirmare înainte de procesare.']],
  [50, 20, 100])
NOTE('CNP-ul și CUI-ul sunt date cu caracter personal (GDPR). Activați opțiunea doar dacă toți cei care vor primi '
     'shapefile-ul au dreptul să acceseze aceste date.', warn=True)

# ── 8 ─────────────────────────────────────────────────────
H1('8. Tabelul de atribute (DBF)')
P('Textul este codificat în <b>UTF-8</b> (declarat în fișierul .cpg), deci diacriticele se păstrează. Lungimea '
  'câmpurilor text se măsoară în <b>bytes</b>: o literă cu diacritic ocupă 2 bytes. Valorile prea lungi se '
  'trunchiază fără a tăia un caracter, iar jurnalul arată câte au fost trunchiate. Numerele prea mari pentru câmp '
  'se scriu ca *** și sunt semnalate.')
H2('Strat teren — atribute extinse')
T([['Câmp', 'Tip', 'Lung.', 'Sursă'],
   ['ID', 'N', '10', 'număr de ordine generat'],
   ['LANDID', 'N', '10', 'Land.LANDID'],
   ['MEAS_AREA', 'N', '16.3', 'Land.MEASUREDAREA'],
   ['AREA_CALC', 'N', '16.3', 'aria netă calculată din geometrie (m²)'],
   ['AREA_DIFF', 'N', '10.2', '|AREA_CALC − MEAS_AREA| / MEAS_AREA × 100 (%)'],
   ['PAPERCADNO', 'C', '50', 'Land.PAPERCADNO'],
   ['E2IDENTIF', 'C', '50', 'Land.E2IDENTIFIER'],
   ['CADSECTOR', 'C', '50', 'Land.CADSECTOR'],
   ['TOPONO', 'C', '50', 'Land.TOPONO'],
   ['CATFOLOS', 'C', '50', 'valorile distincte Parcel.USECATEGORY, separate prin virgulă'],
   ['ACTE', 'C', '254', 'Deed: TIP/NUMĂR/DATA, separate prin „; ”'],
   ['PROPRIETAR', 'C', '254', 'Person: Prenume Nume [(IDCODE)], separate prin „; ”'],
   ['FILENAME', 'C', '100', 'FileDescription.FILENAME sau numele fișierului'],
   ['OPERTYPE', 'C', '50', 'FileDescription.OPERATIONTYPE'],
   ['EXPORTDATE', 'C', '10', 'FileDescription.EXPORTDATE (AAAA-LL-ZZ)']],
  [28, 12, 18, 112], mono_cols=(0,))
H2('Strat teren — atribute de bază (opțiunea extinsă dezactivată)')
P('ID, LANDID, PAPERCADNO, CATFOLOS, ACTE, PROPRIETAR, FILENAME — cu aceleași tipuri și lungimi ca mai sus.')
H2('Strat construcții')
T([['Câmp', 'Tip', 'Lung.', 'Sursă'],
   ['ID', 'N', '10', 'număr de ordine generat'],
   ['BUILDINGID', 'N', '10', 'Building.BUILDINGID'],
   ['LANDID', 'N', '10', 'Building.LANDID'],
   ['BUILDNO', 'N', '6', 'Building.BUILDNO'],
   ['MEAS_AREA', 'N', '16.3', 'Building.MEASUREDAREA'],
   ['AREA_CALC', 'N', '16.3', 'aria calculată din geometrie (m²)'],
   ['FILENAME', 'C', '100', 'numele fișierului CGXML']],
  [28, 12, 18, 112], mono_cols=(0,))
H2('Fișierele de ieșire')
CODE('teren.shp  teren.shx  teren.dbf  teren.prj  teren.cpg\n'
     'constructii.shp  constructii.shx  constructii.dbf  constructii.prj  constructii.cpg   (opțional)')

# ── 9 ─────────────────────────────────────────────────────
H1('9. Proiecția și convenția axelor')
P('Fișierul .prj definește <b>Stereo70 (EPSG:3844)</b>: datum Pulkovo 1942 (Adj 1958), elipsoid Krassowsky 1940, '
  'proiecție stereografică dublă, meridian central 25° E, latitudine de origine 46° N, factor de scară 0,99975, '
  'False Easting / Northing 500 000 m. Coordonatele din CGXML se presupun deja în acest sistem; aplicația '
  '<b>nu reproiectează</b>.')
P('Implicit, X din CGXML devine coordonata Est a shapefile-ului, iar Y coordonata Nord. În geodezia românească '
  'convenția este adesea inversă (X = Nord). Verificați primul rezultat în QGIS sau ArcGIS peste un strat de '
  'referință (ortofotoplan, limite UAT). Dacă poligoanele apar rotite cu 90° sau oglindite, bifați '
  '<b>Forțează inversare X↔Y</b>.')

# ── 10 ────────────────────────────────────────────────────
H1('10. Depanare')
T([['Problemă', 'Cauză probabilă', 'Ce faceți'],
   ['Windows afișează „Windows a protejat computerul”', 'fișierul nu este semnat digital',
    'Mai multe informații → Rulează oricum'],
   ['Antivirusul blochează CGXML2SHP.exe', 'lansatoarele nesemnate sunt uneori semnalate fals',
    'adăugați folderul aplicației la excepții sau porniți direct runtime\\pythonw.exe app\\main.pyw'],
   ['Aplicația nu pornește', 'arhiva portabilă nu a fost dezarhivată complet sau lipsește folderul runtime',
    'dezarhivați din nou cu „Extragere totală”; detaliile erorii sunt în %TEMP%\\cgxml2shp_eroare.txt'],
   ['„Nu există fișiere .cgxml”', 'intrarea nu conține fișiere cu extensia .cgxml', 'verificați arhiva sau folderul'],
   ['„Niciun poligon Land valid”', 'punctele nu au IMMOVABLEID, au toate BUILDINGID sau sunt sub 3',
    'verificați fișierul; jurnalul arată câte puncte de construcție au fost excluse'],
   ['Poligoane rotite / oglindite', 'convenția de axe este inversă', 'bifați Forțează inversare X↔Y'],
   ['AREA_DIFF mare', 'puncte lipsă, enclavă nedetectată sau axe inversate', 'verificați terenul în jurnal și în GIS'],
   ['Teren cu enclavă afișat auto-intersectat', 'inelele nu sunt închise explicit în CGXML',
    'verificați ordinea NO a punctelor în fișier'],
   ['„valori trunchiate la 254 bytes”', 'multe acte sau proprietari în același fișier',
    'normal pentru fișiere mari; textul complet rămâne în CGXML'],
   ['Diacritice afișate greșit în GIS', 'programul nu citește fișierul .cpg', 'setați manual codificarea UTF-8 la import']],
  [48, 58, 64])

# ── 11 ────────────────────────────────────────────────────
H1('11. Informații tehnice')
H2('Structura folderului aplicației')
CODE('CGXML2SHP\\\n'
     '  CGXML2SHP.exe          lansatorul interfeței grafice\n'
     '  cgxml2shp-cli.cmd      linia de comandă\n'
     '  consola.cmd            deschide o consolă în folderul aplicației\n'
     '  CITESTE.txt            informații rapide\n'
     '  app\\                   codul aplicației (Python) și pictograma\n'
     '  runtime\\               Python 3.12 inclus, cu Tcl/Tk (nu modificați)\n'
     '  docs\\                  acest manual\n'
     '  portable.txt           doar în versiunea portabilă\n'
     '  Dezinstalare.exe       doar în versiunea instalată')
H2('Componente')
B(['Python 3.12.11 pentru Windows x64 (distribuția portabilă <i>python-build-standalone</i>), cu Tcl/Tk 8.6 pentru '
   'interfața grafică. Licențele componentelor se află în %s.' % M('runtime\\LICENSE.txt'),
   'Codul aplicației folosește doar biblioteca standard Python — fără dependențe externe.',
   'Kit-ul de instalare și lansatorul sunt construite cu NSIS 3.',
   'Python-ul inclus pornește în mod izolat (%s): variabilele PYTHONPATH/PYTHONHOME și alte instalări Python de pe '
   'calculator nu îl influențează.' % M('-I')])
H2('Verificare')
P('Logica de conversie a fost comparată cu versiunea web 2.1 pe 40 de fișiere CGXML generate aleator (enclave, '
  'insule în enclave, terenuri din mai multe părți, construcții, diacritice, valori lipsă sau invalide), cu patru '
  'combinații de opțiuni: fișierele SHP, SHX și DBF au ieșit identice byte cu byte (DBF-urile fiind create în aceeași zi). Rezultatul produs cu Python-ul '
  'Windows inclus este identic cu cel de pe alte platforme, iar geometriile au fost validate cu GDAL.')
H2('Istoric versiuni')
T([['Versiune', 'Modificări'],
   ['3.0', 'aplicație Windows cu Python inclus: interfață grafică, linie de comandă, kit de instalare, versiune '
           'portabilă; intrări multiple (ZIP, foldere, fișiere); ieșire ZIP sau folder; procesare fără internet'],
   ['2.1', 'DBF în UTF-8, MEAS_AREA, AREA_CALC, clasificare enclave/multipart, orientare ESRI, excluderea punctelor de '
           'construcție din teren, CNP opțional'],
   ['2.0', 'atribute ACTE, PROPRIETAR, CATFOLOS, AREA_DIFF; poligoane cu mai multe inele']], [22, 148])
P('Întrebări și raportări: <b>ginu.popescu@gmail.com</b>')


# ── Șablon pagină ─────────────────────────────────────────
class Doc(BaseDocTemplate):
    def afterFlowable(self, f):
        if isinstance(f, Paragraph) and hasattr(f, '_toc'):
            key = 'h%d' % id(f)
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(f._toc, key, 0, 0)
            self.notify('TOCEntry', (0, f._toc, self.page, key))


def on_page(c, d):
    if d.page == 1:
        return
    c.saveState()
    c.setStrokeColor(GRID)
    c.setLineWidth(0.5)
    c.line(20 * mm, 282 * mm, 190 * mm, 282 * mm)
    c.setFont('Sans', 7.5)
    c.setFillColor(MUTE)
    c.drawString(20 * mm, 284 * mm, 'CGXML2SHP %s — Manual de instalare și utilizare' % VERSION)
    c.drawRightString(190 * mm, 12 * mm, 'Pagina %d' % d.page)
    c.restoreState()


doc = Doc(OUT, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=22 * mm, bottomMargin=20 * mm,
          title='CGXML2SHP %s — Manual' % VERSION, author='Ginu Popescu',
          subject='Conversie CGXML în Shapefile (EPSG:3844)')
frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='f')
doc.addPageTemplates([PageTemplate(id='p', frames=[frame], onPage=on_page)])
doc.multiBuild(story)
print('ok', OUT)
