# CGXML2SHP — Documentație tehnică

**Versiune aplicație:** 2.1 (fișier `cgxml2shp_v2.1.html`)
**Schema suportată:** CGXMLSchema_new_v3.xsd
**Sistem de proiecție ieșire:** EPSG:3844 (Stereo70 / Pulkovo 1942, Adjustment 1958)
**Contact:** ginu.popescu@gmail.com

---

## 1. Descriere generală

**CGXML2SHP** este o aplicație web care rulează integral în browser, fără server și fără instalare. Convertește fișierele cadastrale CGXML într-un shapefile Esri (`.shp`), generând poligoane din punctele de contur ale fiecărui teren, inclusiv terenuri cu enclave și terenuri formate din mai multe părți disjuncte.

Toată procesarea are loc **local, în browserul utilizatorului**. Niciun fișier nu este încărcat pe un server extern.

### Ce face aplicația

- Citește o arhivă ZIP care conține unul sau mai multe fișiere `.cgxml`
- Interpretează fiecare fișier ca XML nativ, conform schemei `CGXMLSchema_new_v3.xsd`
- Extrage punctele de contur ale fiecărui teren, le ordonează după numărul de ordine și le împarte în inele
- Identifică enclavele și părțile multiple și orientează inelele conform specificației ESRI
- Atașează atribute cadastrale: acte, proprietari, categorii de folosință, arie măsurată vs. arie calculată
- Agregă toate poligoanele într-un singur shapefile și livrează rezultatul ca arhivă ZIP

---

## 2. Structura fișierului CGXML

Fișierul CGXML este un **XML DataSet plat de tip Microsoft ADO.NET**. Toate tabelele apar ca elemente **sibling** sub rădăcina `<CGXML>`, legate prin chei.

```
CGXML  (rădăcină)
  ├─ FileDescription   FILEID · FILENAME · EXPORTDATE · OPERATIONTYPE
  ├─ Land              LANDID · FILEID · MEASUREDAREA · PAPERCADNO · CADSECTOR · E2IDENTIFIER · TOPONO
  ├─ Points            IMMOVABLEID · BUILDINGID · NO · X · Y
  ├─ Parcel            LANDID · USECATEGORY
  ├─ Deed              FILEID · DEEDTYPE · DEEDNUMBER · DEEDDATE
  ├─ Person            FILEID · FIRSTNAME · LASTNAME · IDCODE
  └─ Building          BUILDINGID · LANDID · BUILDNO · MEASUREDAREA
```

Sunt listate doar câmpurile citite de aplicație; celelalte câmpuri din schemă sunt ignorate.

### Relații folosite de aplicație

| Relație | Utilizare |
|---|---|
| `Points.IMMOVABLEID → Land.LANDID` | Punctele de contur ale terenului |
| `Points.BUILDINGID → Building.BUILDINGID` | Punctele de contur ale construcției |
| `Land.FILEID → FileDescription.FILEID` | Metadatele fișierului sursă |
| `Parcel.LANDID → Land.LANDID` | Categoriile de folosință ale terenului |
| `Deed.FILEID → FileDescription.FILEID` | Actele (toate actele din fișier) |
| `Person.FILEID → FileDescription.FILEID` | Proprietarii (toate persoanele din fișier) |

> **Atenție:** `ACTE` și `PROPRIETAR` se leagă prin `FILEID`, nu prin teren. Dacă un fișier CGXML conține mai multe terenuri, fiecare primește **toate** actele și persoanele din fișier. Pentru fișierele obișnuite (un imobil per fișier) rezultatul este corect.

### Câmpuri de coordonate

În tabelul `Points`:

- `NO` — numărul de ordine al punctului (sortare crescătoare)
- `X`, `Y` — coordonatele Stereo70; implicit `X` → axa Est a shapefile-ului, `Y` → axa Nord (vezi secțiunea 7)

---

## 3. Logica de conversie

### Pasul 1 — Colectarea fișierelor

Sunt acceptate doar fișierele al căror nume se termină în `.cgxml` (fără deosebire între majuscule și minuscule), din orice folder al arhivei. Sunt ignorate automat resursele adăugate de macOS: folderul `__MACOSX/` și fișierele care încep cu `._`.

### Pasul 2 — Parsarea fiecărui fișier

Se construiesc dicționare de căutare pentru `FileDescription`, `Land`, `Parcel`, `Deed`, `Person` și (opțional) `Building`, apoi punctele se grupează:

- un punct cu `BUILDINGID` completat aparține **construcției** și **nu intră** în conturul terenului, chiar dacă are și `IMMOVABLEID`;
- un punct fără `BUILDINGID` și cu `IMMOVABLEID` aparține terenului.

Jurnalul afișează câte puncte de construcție au fost excluse din contururile de teren.

Dacă un punct nu are `NO`, se folosește ordinea de citire din fișier.

### Pasul 3 — Ordonarea punctelor

Punctele fiecărui teren se sortează **crescător după `NO`**. Punctele duplicate consecutive (aceeași coordonată de două ori la rând) se elimină. Coordonatele se compară cu o toleranță de 0,5 mm.

### Pasul 4 — Împărțirea în inele

Secvența de puncte se parcurge în ordine. Un inel se încheie când secvența **revine la primul punct al inelului curent**; următorul punct începe un inel nou.

Convenția așteptată pentru un teren cu enclavă este deci:

```
NO 1..n      conturul exterior, cu ultimul punct = primul punct
NO n+1..m    conturul enclavei, cu ultimul punct = primul punct al enclavei
```

Punctele rămase după ultimul inel închis formează un inel separat dacă sunt cel puțin 3. Dacă sunt mai puține, sunt ignorate și semnalate în jurnal. Un teren fără niciun punct repetat este tratat ca un singur inel.

### Pasul 5 — Clasificarea inelelor: exterior, enclavă, părți multiple

Inelele se ordonează descrescător după arie. Pentru fiecare inel se numără câte inele mai mari îl conțin (test de incluziune pe vârfuri, cu majoritate; vârfurile comune cu inelul exterior sunt ignorate):

| Inel conținut de… | Clasificare |
|---|---|
| niciun inel (0) | **inel exterior** — o parte a poligonului |
| un inel (1) | **enclavă** (gaură) |
| două inele (2) | insulă în enclavă — din nou inel exterior |

Inelele care nu se conțin unul pe altul devin **părți separate (multipart)** ale aceluiași poligon, nu găuri.

### Pasul 6 — Orientarea inelelor

Conform specificației ESRI Shapefile:

- inelele exterioare sunt scrise în **sens orar (CW)**;
- enclavele sunt scrise în **sens trigonometric (CCW)**.

Orientarea din fișierul CGXML nu contează; aplicația inversează inelele unde este necesar.

### Pasul 7 — Închiderea inelului

Dacă opțiunea „Închide inelul poligon" este activă și ultimul punct al unui inel diferă de primul, primul punct se repetă la final. Inelele detectate la pasul 4 sunt deja închise.

### Pasul 8 — Calculul ariei și verificarea

`AREA_CALC` este aria netă calculată din geometrie: suma inelelor exterioare minus suma enclavelor. `AREA_DIFF` este diferența procentuală absolută față de `MEASUREDAREA`. Valorile peste 1% sunt evidențiate în jurnal.

`AREA_DIFF` este un indicator de control, nu o eroare în sine: o diferență mare indică de obicei puncte lipsă, o enclavă nedetectată sau o convenție de axe greșită.

### Pasul 9 — Scrierea shapefile-ului

Toate poligoanele din toate fișierele sunt reunite în stratul `teren`:

- `teren.shp` — geometrii poligon (Shape Type 5), cu `NumParts > 1` pentru enclave și părți multiple
- `teren.shx` — indexul înregistrărilor
- `teren.dbf` — atributele (dBASE III+, text codificat UTF-8)
- `teren.prj` — definiția proiecției EPSG:3844
- `teren.cpg` — declară codificarea UTF-8

---

## 4. Opțiuni de procesare

| Opțiune | Implicit | Descriere |
|---|---|---|
| **Închide inelul poligon** | Activ | Repetă primul punct la finalul inelului dacă lipsește |
| **Atribute extinse DBF** | Activ | Include câmpurile suplimentare din secțiunea 5 |
| **Include construcții** | Inactiv | Generează stratul separat `constructii` din punctele grupate după `BUILDINGID` |
| **Forțează inversare X↔Y** | Inactiv | `shp_x ← Y`, `shp_y ← X`. Se bifează când poligoanele apar rotite sau oglindite (fișiere cu X = Nord, Y = Est) |
| **Include CNP/CUI în PROPRIETAR** | Inactiv | Adaugă `Person.IDCODE` după numele fiecărui proprietar. Este dată cu caracter personal (GDPR) — activați doar dacă destinatarii shapefile-ului au dreptul să o primească |

Punctele de construcție sunt excluse din contururile de teren indiferent dacă opțiunea „Include construcții" este activă.

---

## 5. Structura tabelului de atribute (DBF)

Numele câmpurilor au maximum 10 caractere, conform formatului dBASE. Lungimea câmpurilor text se măsoară în **bytes**: în UTF-8, o literă cu diacritic (ă, â, î, ș, ț) ocupă 2 bytes. Textele mai lungi decât câmpul sunt trunchiate fără a tăia un caracter la jumătate, iar jurnalul arată câte valori au fost trunchiate pe fiecare câmp.

### Strat teren — atribute extinse

| Câmp | Tip | Lungime | Sursă |
|---|---|---|---|
| `ID` | Numeric | 10 | Index secvențial generat |
| `LANDID` | Numeric | 10 | `Land.LANDID` |
| `MEAS_AREA` | Numeric | 16.3 | `Land.MEASUREDAREA` |
| `AREA_CALC` | Numeric | 16.3 | Aria netă calculată din geometrie (m²) |
| `AREA_DIFF` | Numeric | 10.2 | \|AREA_CALC − MEAS_AREA\| / MEAS_AREA × 100 (%) |
| `PAPERCADNO` | Text | 50 | `Land.PAPERCADNO` |
| `E2IDENTIF` | Text | 50 | `Land.E2IDENTIFIER` |
| `CADSECTOR` | Text | 50 | `Land.CADSECTOR` |
| `TOPONO` | Text | 50 | `Land.TOPONO` |
| `CATFOLOS` | Text | 50 | Valorile distincte `Parcel.USECATEGORY`, separate prin virgulă |
| `ACTE` | Text | 254 | `Deed`: `TIP/NUMĂR/DATA`, separate prin `; ` |
| `PROPRIETAR` | Text | 254 | `Person`: `Prenume Nume`, opțional `(IDCODE)`, separate prin `; ` |
| `FILENAME` | Text | 100 | `FileDescription.FILENAME`; dacă lipsește, numele fișierului din ZIP |
| `OPERTYPE` | Text | 50 | `FileDescription.OPERATIONTYPE` |
| `EXPORTDATE` | Text | 10 | `FileDescription.EXPORTDATE` (AAAA-LL-ZZ) |

### Strat teren — atribute simple (opțiunea extinsă dezactivată)

| Câmp | Tip | Lungime |
|---|---|---|
| `ID` | Numeric | 10 |
| `LANDID` | Numeric | 10 |
| `PAPERCADNO` | Text | 50 |
| `CATFOLOS` | Text | 50 |
| `ACTE` | Text | 254 |
| `PROPRIETAR` | Text | 254 |
| `FILENAME` | Text | 100 |

### Strat construcții

| Câmp | Tip | Lungime | Sursă |
|---|---|---|---|
| `ID` | Numeric | 10 | Index secvențial |
| `BUILDINGID` | Numeric | 10 | `Building.BUILDINGID` |
| `LANDID` | Numeric | 10 | `Building.LANDID` |
| `BUILDNO` | Numeric | 6 | `Building.BUILDNO` |
| `MEAS_AREA` | Numeric | 16.3 | `Building.MEASUREDAREA` |
| `AREA_CALC` | Numeric | 16.3 | Aria calculată din geometrie (m²) |
| `FILENAME` | Text | 100 | Numele fișierului CGXML din ZIP |

Un număr care nu încape în lățimea câmpului numeric este scris ca `***` (convenția dBASE) și semnalat în jurnal, în loc să fie trunchiat silențios.

---

## 6. Sistemul de proiecție — EPSG:3844

Fișierul `.prj` definește proiecția **Stereo70**:

- **Datum:** Pulkovo 1942, Adjustment 1958
- **Elipsoid:** Krassowsky 1940 (a = 6378245 m, 1/f = 298.3)
- **Proiecție:** Double Stereographic
- **Meridian central:** 25° E
- **Latitudine de origine:** 46° N
- **Factor de scară:** 0.99975
- **False Easting / Northing:** 500000 / 500000 m

Coordonatele CGXML se presupun deja în acest sistem; aplicația **nu reproiectează**.

---

## 7. Convenția axelor — de verificat

Aplicația presupune implicit că `X` din CGXML este coordonata Est și `Y` este coordonata Nord. În geodezia românească și în definiția EPSG:3844, convenția este adesea inversă (X = Nord, Y = Est). Verificați pe un fișier real: încărcați rezultatul în QGIS peste un strat de referință (ortofotoplan, limite UAT). Dacă poligoanele apar rotite cu 90° sau oglindite, bifați „Forțează inversare X↔Y".

---

## 8. Mod de utilizare

1. Deschideți `cgxml2shp_v2.1.html` în browser
2. Trageți arhiva ZIP în zona de încărcare sau apăsați pentru a o selecta
3. Ajustați opțiunile de procesare
4. Apăsați **„Procesează fișierele CGXML"**
5. Urmăriți jurnalul: pentru fiecare teren apar numărul de inele, punctele, aria calculată, diferența față de aria măsurată și marcajele `[ENCLAVE: n]` / `[MULTIPART: n]`
6. Verificați panoul de statistici (fișiere, terenuri, poligoane, poligoane cu enclave, puncte)
7. Apăsați **„Descarcă arhiva ZIP cu fișierele SHP"**
8. Extrageți arhiva și încărcați shapefile-ul în QGIS, ArcGIS etc.

---

## 9. Compatibilitate

Funcționează în versiunile actuale de Chrome, Edge, Firefox, Opera și Safari. Cerințe: `DataView`, `ArrayBuffer`, `FileReader`, `Blob`, `TextEncoder` (există și o variantă de rezervă pentru UTF-8).

Biblioteca **JSZip 3.10.1** și fonturile se încarcă de pe internet. Este necesară conexiunea la fiecare deschidere a paginii, cu excepția cazului în care sunt deja în cache-ul browserului.

---

## 10. Depanare

| Problemă | Cauză posibilă | Soluție |
|---|---|---|
| „Nu există fișiere .cgxml în arhivă" | Arhiva nu conține fișiere cu extensia `.cgxml` | Verificați conținutul arhivei |
| „Niciun poligon Land valid" | Punctele nu au `IMMOVABLEID`, au toate `BUILDINGID`, sau au sub 3 puncte | Verificați fișierele față de schemă; jurnalul arată câte puncte de construcție au fost excluse |
| Poligoane rotite / oglindite | Convenția de axe este inversă | Bifați „Forțează inversare X↔Y" (secțiunea 7) |
| `AREA_DIFF` mare | Puncte lipsă, enclavă nedetectată, axe inversate | Verificați terenul în jurnal și în GIS |
| Teren cu enclavă afișat ca poligon auto-intersectat | Inelele nu sunt închise explicit în CGXML (secțiunea 3, pasul 4) | Verificați ordinea `NO` a punctelor în fișier |
| „Puncte rămase în afara unui inel valid" | Mai puțin de 3 puncte după ultimul inel închis | Verificați punctele terenului respectiv |
| „Valori trunchiate la 254 bytes" | Multe acte sau proprietari în același fișier | Normal pentru fișiere mari; textul complet rămâne în CGXML |
| Diacritice afișate greșit | Programul GIS nu citește fișierul `.cpg` | Setați manual codificarea UTF-8 la import |

---

## 11. Structura arhivei de ieșire

```
cgxml_to_shp.zip
  ├─ teren.shp          geometrii poligon
  ├─ teren.shx          index
  ├─ teren.dbf          atribute (UTF-8)
  ├─ teren.prj          proiecție EPSG:3844
  ├─ teren.cpg          codificare UTF-8
  │
  └─ (dacă opțiunea "Include construcții" este activă:)
     ├─ constructii.shp
     ├─ constructii.shx
     ├─ constructii.dbf
     ├─ constructii.prj
     └─ constructii.cpg
```

---

## 12. Istoric versiuni

**2.1**
- DBF codificat corect în UTF-8; diacriticele nu se mai pierd
- `MEASRD_AREA` redenumit `MEAS_AREA` (numele vechi depășea limita de 10 caractere dBASE și era citit trunchiat de unele programe)
- Câmpuri noi: `AREA_CALC`; `AREA_DIFF` devine numeric
- Punctele cu `BUILDINGID` nu mai intră în conturul terenului (înainte apăreau ca inel suplimentar)
- Inelele disjuncte devin părți multiple, nu enclave; clasificarea folosește testul de incluziune
- Un inel se închide doar la revenirea în primul punct al inelului
- `IDCODE` (CNP/CUI) inclus doar la cerere
- `ACTE` și `PROPRIETAR` extinse la 254 bytes; `FILENAME` la 100 bytes
- Avertismente pentru valori trunchiate și numere prea lungi; marcaj de sfârșit de fișier în DBF
- Filtrare strictă a fișierelor `.cgxml`

**2.0**
- Atribute `ACTE`, `PROPRIETAR`, `CATFOLOS`, `AREA_DIFF`
- Poligoane cu mai multe inele

---

*Documentație pentru aplicația CGXML2SHP. Întrebări și raportări: ginu.popescu@gmail.com*
