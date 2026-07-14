# CGXML to SHP — Documentație tehnică

**Versiune aplicație:** 3.0
**Schema suportată:** CGXMLSchema_new_v3.xsd
**Sistem de proiecție ieșire:** EPSG:3844 (Stereo70 / Pulkovo 1942, Adjustment 1958)
**Contact:** ginu.popescu@gmail.com

---

## 1. Descriere generală

**CGXML to SHP** este o aplicație web care rulează integral în browser, fără server și fără instalare. Convertește fișierele cadastrale în format CGXML într-un shapefile Esri (`.shp`), generând poligoane din punctele de contur ale fiecărui teren.

Toată procesarea are loc **local, în browserul utilizatorului**. Niciun fișier nu este încărcat pe un server extern, ceea ce asigură confidențialitatea datelor cadastrale.

### Ce face aplicația

- Citește o arhivă ZIP care conține unul sau mai multe fișiere `.cgxml`
- Interpretează fiecare fișier CGXML ca XML nativ, conform schemei `CGXMLSchema_new_v3.xsd`
- Extrage punctele de contur ale fiecărui teren și le ordonează crescător după numărul de ordine
- Construiește poligoane și le agregă într-un singur shapefile
- Livrează rezultatul într-o arhivă ZIP care conține setul complet de fișiere shapefile

---

## 2. Structura fișierului CGXML

Fișierul CGXML este un **XML DataSet plat de tip Microsoft ADO.NET**. Spre deosebire de un XML ierarhic clasic, toate tabelele apar ca elemente **sibling** (frați) sub rădăcina `<CGXML>`, legate între ele prin chei (relații de tip cheie primară / cheie externă).

```
CGXML  (rădăcină)
  ├─ FileDescription   FILEID · FILENAME · EXPORTDATE · OPERATIONTYPE · LICENSEDNAME
  ├─ Land              LANDID · FILEID · MEASUREDAREA · PAPERCADNO · CADSECTOR · E2IDENTIFIER · TOPONO
  ├─ Points            POINTID · IMMOVABLEID · BUILDINGID · NO · X · Y
  ├─ Parcel            PARCELID · LANDID · NUMBER · USECATEGORY · MEASUREDAREA
  └─ Building          BUILDINGID · LANDID · BUILDNO · MEASUREDAREA
```

### Relații cheie folosite de aplicație

| Relație | Descriere |
|---|---|
| `Points.IMMOVABLEID → Land.LANDID` | Leagă fiecare punct de conturul terenului căruia îi aparține |
| `Points.BUILDINGID → Building.BUILDINGID` | Leagă punctele de conturul unei construcții (opțional) |
| `Land.FILEID → FileDescription.FILEID` | Corelează terenul cu metadatele fișierului sursă |

### Câmpuri de coordonate

În tabelul `Points`:

- `NO` — numărul de ordine al punctului (folosit pentru sortare crescătoare)
- `X` — coordonata Est (Easting) în sistem Stereo70
- `Y` — coordonata Nord (Northing) în sistem Stereo70

---

## 3. Logica de conversie

### Pasul 1 — Colectarea fișierelor

Aplicația parcurge arhiva ZIP și identifică toate fișierele cu extensia `.cgxml`, indiferent de folderul în care se află în interiorul arhivei.

### Pasul 2 — Parsarea fiecărui fișier

Pentru fiecare fișier CGXML se construiesc structuri de căutare rapidă:

1. `FileDescription` → dicționar indexat după `FILEID`
2. `Land` → dicționar indexat după `LANDID`
3. `Building` → dicționar indexat după `BUILDINGID` (dacă opțiunea este activă)
4. `Points` → grupate după `IMMOVABLEID` (pentru terenuri) și după `BUILDINGID` (pentru construcții)

### Pasul 3 — Ordonarea punctelor

Punctele fiecărui teren se sortează **crescător după valoarea `NO`**. Aceasta asigură că poligonul se închide urmând ordinea corectă a vârfurilor de contur.

### Pasul 4 — Construirea geometriei

Fiecare punct se mapează la o coordonată de shapefile:

```
shp_x  ←  X  (Easting / Est)
shp_y  ←  Y  (Northing / Nord)
```

Aceasta este maparea implicită, corectă pentru fișiere CGXML unde `X=Est` și `Y=Nord`.

### Pasul 5 — Închiderea inelului

Dacă opțiunea „Închide inelul poligon" este activă și ultimul punct diferă de primul, primul punct este repetat la finalul geometriei. Standardul shapefile cere ca inelele poligonale să înceapă și să se termine cu aceeași coordonată.

### Pasul 6 — Agregarea și scrierea shapefile-ului

Toate poligoanele din toate fișierele CGXML sunt reunite într-un singur strat `teren.shp`. Se generează în format binar Esri:

- `teren.shp` — geometriile poligon (Shape Type 5)
- `teren.shx` — indexul de înregistrări
- `teren.dbf` — tabelul de atribute (dBASE III+)
- `teren.prj` — definiția proiecției EPSG:3844
- `teren.cpg` — codificarea caracterelor (UTF-8)

---

## 4. Opțiuni de procesare

| Opțiune | Implicit | Descriere |
|---|---|---|
| **Închide inelul poligon** | Activ | Repetă primul punct la finalul geometriei dacă lipsește, pentru validarea inelului |
| **Atribute extinse DBF** | Activ | Include câmpuri suplimentare în tabelul de atribute (vezi secțiunea 5) |
| **Include construcții** | Inactiv | Generează un strat separat `constructii.shp` din punctele grupate după `BUILDINGID` |
| **Forțează inversare X↔Y** | Inactiv | Inversează axele (`shp_x←Y`, `shp_y←X`). Se bifează **doar** pentru fișiere vechi unde convenția este X=Nord, Y=Est |

---

## 5. Structura tabelului de atribute (DBF)

### Strat teren — atribute extinse

| Câmp | Tip | Lungime | Sursă |
|---|---|---|---|
| `ID` | Numeric | 10 | Index secvențial generat |
| `LANDID` | Numeric | 10 | `Land.LANDID` |
| `MEASRD_AREA` | Numeric | 16.3 | `Land.MEASUREDAREA` |
| `PAPERCADNO` | Text | 50 | `Land.PAPERCADNO` |
| `E2IDENTIF` | Text | 50 | `Land.E2IDENTIFIER` |
| `CADSECTOR` | Text | 50 | `Land.CADSECTOR` |
| `TOPONO` | Text | 50 | `Land.TOPONO` |
| `FILENAME` | Text | 50 | `FileDescription.FILENAME` |
| `OPERTYPE` | Text | 50 | `FileDescription.OPERATIONTYPE` |
| `EXPORTDATE` | Text | 12 | `FileDescription.EXPORTDATE` |

### Strat teren — atribute simple (opțiune extinsă dezactivată)

| Câmp | Tip | Lungime |
|---|---|---|
| `ID` | Numeric | 10 |
| `LANDID` | Numeric | 10 |
| `PAPERCADNO` | Text | 50 |
| `FILENAME` | Text | 50 |

### Strat construcții

| Câmp | Tip | Lungime | Sursă |
|---|---|---|---|
| `ID` | Numeric | 10 | Index secvențial |
| `BUILDINGID` | Numeric | 10 | `Building.BUILDINGID` |
| `LANDID` | Numeric | 10 | `Building.LANDID` |
| `BUILDNO` | Numeric | 6 | `Building.BUILDNO` |
| `MEASRD_AREA` | Numeric | 16.3 | `Building.MEASUREDAREA` |
| `FILENAME` | Text | 50 | Numele fișierului CGXML |

---

## 6. Sistemul de proiecție — EPSG:3844

Fișierul `.prj` generat definește proiecția **Stereo70**, standardul cadastral din România:

- **Datum:** Pulkovo 1942, Adjustment 1958
- **Elipsoid:** Krassowsky 1940 (a = 6378245 m, 1/f = 298.3)
- **Proiecție:** Double Stereographic (stereografică dublă)
- **Meridian central:** 25° E
- **Latitudine de origine:** 46° N
- **Factor de scară:** 0.99975
- **False Easting / Northing:** 500000 / 500000 metri

Coordonatele din fișierele CGXML se presupun deja exprimate în acest sistem; aplicația **nu efectuează reproiectare**, ci doar transferă coordonatele în geometria shapefile-ului.

---

## 7. Mod de utilizare

1. Deschide fișierul `cgxml_to_shp.html` în browser (dublu-click sau deschidere din browser)
2. Trage arhiva ZIP în zona de încărcare, sau apasă pentru a o selecta
3. Ajustează opțiunile de procesare dacă este nevoie
4. Apasă **„Procesează fișierele CGXML"**
5. Urmărește jurnalul de procesare — sunt afișate fișierele găsite, terenurile identificate și eventualele avertismente
6. Verifică panoul de statistici (număr de fișiere, terenuri, poligoane, puncte)
7. Apasă **„Descarcă arhiva ZIP cu fișierele SHP"**
8. Extrage arhiva și încarcă shapefile-ul în software-ul GIS (QGIS, ArcGIS etc.)

---

## 8. Compatibilitate

Aplicația funcționează în toate browserele moderne:

| Browser | Suport |
|---|---|
| Google Chrome | Da |
| Microsoft Edge | Da |
| Mozilla Firefox | Da |
| Opera | Da |
| Safari | Da |

Cerințe minime: suport pentru `DataView`, `ArrayBuffer`, `FileReader` și `Blob` — disponibile în toate versiunile de browser din ultimii ani. Aplicația folosește biblioteca **JSZip 3.10.1** pentru citirea și scrierea arhivelor ZIP, încărcată din CDN, deci este necesară o conexiune la internet la prima deschidere.

---

## 9. Depanare (troubleshooting)

| Problemă | Cauză posibilă | Soluție |
|---|---|---|
| „Nu există fișiere .cgxml în arhivă" | Arhiva nu conține fișiere cu extensia `.cgxml` | Verifică conținutul arhivei ZIP |
| „Niciun poligon Land valid" | Punctele nu au relația `IMMOVABLEID` completată, sau au mai puțin de 3 puncte | Verifică structura fișierelor CGXML față de schemă |
| Poligoane răsturnate / oglindite | Convenția de axe X/Y a fișierelor este inversată | Bifează opțiunea „Forțează inversare X↔Y" |
| Teren ignorat („< 3 puncte") | Un teren are mai puțin de 3 puncte de contur | Normal — un poligon necesită minimum 3 vârfuri |
| Caractere diacritice deformate în DBF | Codificare specială | Fișierul `.cpg` indică UTF-8; setează codificarea corespunzătoare la import în GIS |

---

## 10. Structura arhivei de ieșire

```
cgxml_to_shp.zip
  ├─ teren.shp          geometrii poligon
  ├─ teren.shx          index
  ├─ teren.dbf          atribute
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

*Documentație generată pentru aplicația CGXML to SHP. Pentru întrebări sau raportări: ginu.popescu@gmail.com*
