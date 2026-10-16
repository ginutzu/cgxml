# -*- coding: utf-8 -*-
"""
CGXML2SHP — nucleul de conversie (fără dependențe externe, doar biblioteca standard Python).

Portare fidelă a logicii din cgxml2shp_v2.1.html:
  * parsare CGXML (XML DataSet plat ADO.NET, CGXMLSchema_new_v3.xsd)
  * împărțirea punctelor în inele, clasificare exterior / enclavă / multipart
  * orientare inele conform specificației ESRI (exterior CW, enclave CCW)
  * scriere SHP / SHX / DBF (dBASE III+, text UTF-8) / PRJ (EPSG:3844) / CPG
"""

import datetime
import io
import math
import os
import re
import struct
import xml.etree.ElementTree as ET
import zipfile

__version__ = "3.0"

PRJ = ('PROJCS["Pulkovo_1942_Adj_1958_Stereo70",'
       'GEOGCS["GCS_Pulkovo_1942_Adj_1958",'
       'DATUM["D_Pulkovo_1942_Adj_1958",'
       'SPHEROID["Krassowsky_1940",6378245.0,298.3]],'
       'PRIMEM["Greenwich",0.0],'
       'UNIT["Degree",0.0174532925199433]],'
       'PROJECTION["Double_Stereographic"],'
       'PARAMETER["False_Easting",500000.0],'
       'PARAMETER["False_Northing",500000.0],'
       'PARAMETER["Central_Meridian",25.0],'
       'PARAMETER["Scale_Factor",0.99975],'
       'PARAMETER["Latitude_Of_Origin",46.0],'
       'UNIT["Meter",1.0]]')

COORD_EPS = 0.0005  # toleranță la compararea coordonatelor (m)


class Options(object):
    """Opțiunile de procesare (aceleași ca în aplicația web)."""

    def __init__(self, close_ring=True, rich_dbf=True, buildings=False,
                 swap_xy=False, id_code=False):
        self.close_ring = close_ring
        self.rich_dbf = rich_dbf
        self.buildings = buildings
        self.swap_xy = swap_xy
        self.id_code = id_code


class ConversionError(Exception):
    pass


# ════════════════════════════════════════════════════════════
#  Conversii numerice cu semantica JavaScript (parseInt / parseFloat)
# ════════════════════════════════════════════════════════════
_INT_RE = re.compile(r'^\s*([+-]?\d+)')
_FLOAT_RE = re.compile(r'^\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)')


def js_int(s):
    m = _INT_RE.match(s or '')
    return int(m.group(1)) if m else None


def js_float(s):
    m = _FLOAT_RE.match(s or '')
    if m:
        return float(m.group(1))
    t = (s or '').strip()
    if t.startswith('Infinity') or t.startswith('+Infinity'):
        return math.inf
    if t.startswith('-Infinity'):
        return -math.inf
    return None


# ════════════════════════════════════════════════════════════
#  Parsare CGXML
# ════════════════════════════════════════════════════════════
def _local(tag):
    if not isinstance(tag, str):
        return ''
    return tag.rsplit('}', 1)[-1] if '}' in tag else tag


class _Row(object):
    """Un rând de tabel CGXML: textul elementelor copil, după numele local."""
    __slots__ = ('v',)

    def __init__(self, el):
        v = {}
        for ch in el:
            name = _local(ch.tag)
            if name and name not in v:
                v[name] = ''.join(ch.itertext()).strip()
        self.v = v

    def ct(self, tag):
        return self.v.get(tag, '')

    def ci(self, tag):
        t = self.v.get(tag, '')
        return js_int(t) if t != '' else None

    def cf(self, tag):
        t = self.v.get(tag, '')
        return js_float(t) if t != '' else None


def _tables(root, names):
    out = dict((n, []) for n in names)
    for el in root.iter():
        n = _local(el.tag)
        if n in out:
            out[n].append(_Row(el))
    return out


def _js_key_order(d):
    """Ordinea de iterare a cheilor numerice dintr-un obiect JavaScript."""
    nonneg = sorted(k for k in d if k >= 0)
    neg = [k for k in d if k < 0]
    return nonneg + neg


def parse_cgxml(data, filename, opts):
    """Parsează conținutul (bytes) unui fișier CGXML. Returnează un dict cu poligoane și statistici."""
    try:
        root = ET.fromstring(data)
    except ET.ParseError as e:
        raise ConversionError('XML invalid: %s' % e)

    t = _tables(root, ('FileDescription', 'Deed', 'Person', 'Land', 'Parcel', 'Building', 'Points'))

    fd_map = {}
    for r in t['FileDescription']:
        fid = r.ci('FILEID')
        if fid is not None:
            fd_map[fid] = {'FILENAME': r.ct('FILENAME'),
                           'EXPORTDATE': r.ct('EXPORTDATE')[:10],
                           'OPERATIONTYPE': r.ct('OPERATIONTYPE')}

    deeds_by_file = {}
    for r in t['Deed']:
        fid = r.ci('FILEID')
        if fid is None:
            continue
        s = '/'.join(x for x in (r.ct('DEEDTYPE'), r.ct('DEEDNUMBER'), r.ct('DEEDDATE')[:10]) if x)
        if not s:
            continue
        deeds_by_file.setdefault(fid, []).append(s)

    persons_by_file = {}
    for r in t['Person']:
        fid = r.ci('FILEID')
        if fid is None:
            continue
        s = ' '.join(x for x in (r.ct('FIRSTNAME'), r.ct('LASTNAME')) if x)
        idc = r.ct('IDCODE')
        if idc and opts.id_code:
            s += (' ' if s else '') + '(' + idc + ')'
        if not s:
            continue
        persons_by_file.setdefault(fid, []).append(s)

    land_map = {}
    for r in t['Land']:
        lid = r.ci('LANDID')
        if lid is not None:
            land_map[lid] = {'LANDID': lid, 'FILEID': r.ci('FILEID'),
                             'CADSECTOR': r.ct('CADSECTOR'), 'MEASUREDAREA': r.cf('MEASUREDAREA'),
                             'PAPERCADNO': r.ct('PAPERCADNO'), 'E2IDENTIFIER': r.ct('E2IDENTIFIER'),
                             'TOPONO': r.ct('TOPONO')}

    parcels_by_land = {}
    for r in t['Parcel']:
        lid = r.ci('LANDID')
        if lid is None:
            continue
        uc = r.ct('USECATEGORY')
        lst = parcels_by_land.setdefault(lid, [])
        if uc and uc not in lst:
            lst.append(uc)

    bld_map = {}
    if opts.buildings:
        for r in t['Building']:
            bid = r.ci('BUILDINGID')
            if bid is not None:
                bld_map[bid] = {'BUILDINGID': bid, 'LANDID': r.ci('LANDID'),
                                'BUILDNO': r.ci('BUILDNO'), 'MEASUREDAREA': r.cf('MEASUREDAREA')}

    # Puncte: cele cu BUILDINGID aparțin construcției și nu intră în conturul terenului.
    pts_by_land, pts_by_bld = {}, {}
    n_raw = n_bld_pts = 0
    for r in t['Points']:
        imm = r.ci('IMMOVABLEID')
        bid = r.ci('BUILDINGID')
        no_s = r.ct('NO')
        x = r.cf('X')
        y = r.cf('Y')
        if x is None or y is None or math.isnan(x) or math.isnan(y):
            continue
        n_raw += 1
        no = js_float(no_s) if no_s != '' else n_raw
        if no is None or (isinstance(no, float) and math.isnan(no)):
            no = n_raw
        pt = (no, y, x) if opts.swap_xy else (no, x, y)
        if bid is not None and bid != 0:
            n_bld_pts += 1
            if opts.buildings:
                pts_by_bld.setdefault(bid, []).append(pt)
            continue
        if imm is not None:
            pts_by_land.setdefault(imm, []).append(pt)

    def to_coords(pts):
        pts = sorted(pts, key=lambda p: p[0])
        return [[p[1], p[2]] for p in pts]

    land_polys = []
    n_skipped = n_dropped = 0
    for lid in _js_key_order(pts_by_land):
        land = land_map.get(lid) or {'LANDID': lid}
        fd = fd_map.get(land.get('FILEID')) or {}
        geom = build_polygon_rings(to_coords(pts_by_land[lid]), opts.close_ring)
        n_dropped += geom['n_dropped']
        if not geom['rings']:
            n_skipped += 1
            continue
        meas = land.get('MEASUREDAREA')
        if meas is None or math.isnan(meas):
            meas = 0.0
        diff = abs(geom['area'] - meas) / meas * 100 if meas > 0 else 0.0
        land_polys.append({
            'rings': geom['rings'], 'n_outer': geom['n_outer'], 'n_holes': geom['n_holes'],
            'attrs': {
                'LANDID': lid, 'MEAS_AREA': meas, 'AREA_CALC': geom['area'], 'AREA_DIFF': diff,
                'PAPERCADNO': land.get('PAPERCADNO') or '',
                'E2IDENTIF': land.get('E2IDENTIFIER') or '',
                'CADSECTOR': land.get('CADSECTOR') or '',
                'TOPONO': land.get('TOPONO') or '',
                'CATFOLOS': ','.join(parcels_by_land.get(lid, [])),
                'ACTE': '; '.join(deeds_by_file.get(land.get('FILEID'), [])),
                'PROPRIETAR': '; '.join(persons_by_file.get(land.get('FILEID'), [])),
                'FILENAME': fd.get('FILENAME') or filename,
                'OPERTYPE': fd.get('OPERATIONTYPE') or '',
                'EXPORTDATE': fd.get('EXPORTDATE') or '',
            }})

    bld_polys = []
    if opts.buildings:
        for bid in _js_key_order(pts_by_bld):
            b = bld_map.get(bid) or {'BUILDINGID': bid}
            geom = build_polygon_rings(to_coords(pts_by_bld[bid]), opts.close_ring)
            n_dropped += geom['n_dropped']
            if not geom['rings']:
                continue
            ma = b.get('MEASUREDAREA')
            bld_polys.append({
                'rings': geom['rings'], 'n_outer': geom['n_outer'], 'n_holes': geom['n_holes'],
                'attrs': {
                    'BUILDINGID': bid,
                    'LANDID': b.get('LANDID') if b.get('LANDID') is not None else 0,
                    'BUILDNO': b.get('BUILDNO') if b.get('BUILDNO') is not None else 0,
                    'MEAS_AREA': ma if (ma is not None and not math.isnan(ma)) else 0.0,
                    'AREA_CALC': geom['area'],
                    'FILENAME': filename,
                }})

    return {'land_polys': land_polys, 'bld_polys': bld_polys, 'n_lands': len(land_map),
            'n_raw_pts': n_raw, 'n_bld_pts': n_bld_pts, 'n_skipped': n_skipped,
            'n_dropped_pts': n_dropped}


# ════════════════════════════════════════════════════════════
#  Geometrie
# ════════════════════════════════════════════════════════════
def same_pt(a, b):
    return abs(a[0] - b[0]) < COORD_EPS and abs(a[1] - b[1]) < COORD_EPS


def signed_area(ring):
    """Arie cu semn (shoelace): pozitivă = CCW, negativă = CW."""
    a = 0.0
    m = len(ring)
    j = m - 1
    for i in range(m):
        a += (ring[j][0] + ring[i][0]) * (ring[j][1] - ring[i][1])
        j = i
    return -a / 2


def point_in_ring(pt, ring):
    inside = False
    x, y = pt
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def ring_inside(inner, outer):
    n = len(inner)
    if n > 1 and same_pt(inner[0], inner[n - 1]):
        n -= 1
    votes = total = 0
    for i in range(n):
        if any(same_pt(inner[i], o) for o in outer):
            continue
        total += 1
        if point_in_ring(inner[i], outer):
            votes += 1
    return total > 0 and votes * 2 > total


def split_into_rings(coords, do_close):
    c = []
    for p in coords:
        if not c or not same_pt(c[-1], p):
            c.append(p)
    rings = []
    start = 0
    i = start + 1
    while i < len(c):
        if i - start >= 3 and same_pt(c[i], c[start]):
            ring = [list(p) for p in c[start:i + 1]]
            ring[-1] = [ring[0][0], ring[0][1]]
            rings.append(ring)
            start = i + 1
            i = start
        i += 1
    rem = [list(p) for p in c[start:]]
    n_dropped = 0
    if len(rem) >= 3:
        if do_close and not same_pt(rem[0], rem[-1]):
            rem.append([rem[0][0], rem[0][1]])
        rings.append(rem)
    else:
        n_dropped += len(rem)
    return rings, n_dropped


def build_polygon_rings(coords, do_close):
    """Inele orientate ESRI: exterior CW, enclave CCW; inelele disjuncte = părți multiple."""
    rings, n_dropped = split_into_rings(coords, do_close)
    if not rings:
        return {'rings': [], 'n_outer': 0, 'n_holes': 0, 'area': 0.0, 'n_dropped': n_dropped}
    rings.sort(key=lambda r: -abs(signed_area(r)))
    out = []
    n_outer = n_holes = 0
    area = 0.0
    for i, r in enumerate(rings):
        depth = sum(1 for j in range(i) if ring_inside(r, rings[j]))
        is_hole = depth % 2 == 1
        sa = signed_area(r)
        if (sa < 0) if is_hole else (sa > 0):
            r = r[::-1]
        if is_hole:
            n_holes += 1
            area -= abs(sa)
        else:
            n_outer += 1
            area += abs(sa)
        out.append(r)
    return {'rings': out, 'n_outer': n_outer, 'n_holes': n_holes, 'area': area, 'n_dropped': n_dropped}


# ════════════════════════════════════════════════════════════
#  Shapefile (SHP + SHX), tip 5 = Polygon
# ════════════════════════════════════════════════════════════
def build_shp(polygons):
    sizes = []
    for p in polygons:
        npts = sum(len(r) for r in p['rings'])
        sizes.append(4 + 32 + 4 + 4 + 4 * len(p['rings']) + npts * 16)
    shp_len = 100 + sum(8 + s for s in sizes)
    shx_len = 100 + len(polygons) * 8

    xs = [c[0] for p in polygons for r in p['rings'] for c in r]
    ys = [c[1] for p in polygons for r in p['rings'] for c in r]
    if xs:
        bbox = (min(xs), min(ys), max(xs), max(ys))
    else:
        bbox = (0.0, 0.0, 0.0, 0.0)

    def header(flen):
        return (struct.pack('>7i', 9994, 0, 0, 0, 0, 0, flen // 2) +
                struct.pack('<2i', 1000, 5) +
                struct.pack('<8d', bbox[0], bbox[1], bbox[2], bbox[3], 0, 0, 0, 0))

    shp = io.BytesIO()
    shx = io.BytesIO()
    shp.write(header(shp_len))
    shx.write(header(shx_len))
    off = 100
    for i, p in enumerate(polygons):
        rings = p['rings']
        words = sizes[i] // 2
        shx.write(struct.pack('>2i', off // 2, words))
        shp.write(struct.pack('>2i', i + 1, words))
        px = [c[0] for r in rings for c in r]
        py = [c[1] for r in rings for c in r]
        npts = len(px)
        shp.write(struct.pack('<i4d2i', 5, min(px), min(py), max(px), max(py), len(rings), npts))
        part = 0
        for r in rings:
            shp.write(struct.pack('<i', part))
            part += len(r)
        for r in rings:
            for c in r:
                shp.write(struct.pack('<2d', c[0], c[1]))
        off += 8 + sizes[i]
    return shp.getvalue(), shx.getvalue()


# ════════════════════════════════════════════════════════════
#  DBF (dBASE III+), text UTF-8 — lungimi în BYTES
# ════════════════════════════════════════════════════════════
def dbf_fields(rich, kind):
    if kind == 'building':
        return [('ID', 'N', 10, 0), ('BUILDINGID', 'N', 10, 0), ('LANDID', 'N', 10, 0),
                ('BUILDNO', 'N', 6, 0), ('MEAS_AREA', 'N', 16, 3), ('AREA_CALC', 'N', 16, 3),
                ('FILENAME', 'C', 100, 0)]
    if rich:
        return [('ID', 'N', 10, 0), ('LANDID', 'N', 10, 0), ('MEAS_AREA', 'N', 16, 3),
                ('AREA_CALC', 'N', 16, 3), ('AREA_DIFF', 'N', 10, 2), ('PAPERCADNO', 'C', 50, 0),
                ('E2IDENTIF', 'C', 50, 0), ('CADSECTOR', 'C', 50, 0), ('TOPONO', 'C', 50, 0),
                ('CATFOLOS', 'C', 50, 0), ('ACTE', 'C', 254, 0), ('PROPRIETAR', 'C', 254, 0),
                ('FILENAME', 'C', 100, 0), ('OPERTYPE', 'C', 50, 0), ('EXPORTDATE', 'C', 10, 0)]
    return [('ID', 'N', 10, 0), ('LANDID', 'N', 10, 0), ('PAPERCADNO', 'C', 50, 0),
            ('CATFOLOS', 'C', 50, 0), ('ACTE', 'C', 254, 0), ('PROPRIETAR', 'C', 254, 0),
            ('FILENAME', 'C', 100, 0)]


def _fmt_num(num, length, dec):
    if num is None or isinstance(num, str):
        num = js_float(num) if isinstance(num, str) else None
    if num is None or not math.isfinite(num):
        num = 0.0
    if dec > 0:
        if num == 0:
            num = 0.0
        s = '%.*f' % (dec, num)
    else:
        r = math.floor(num + 0.5)          # Math.round din JavaScript
        s = str(int(r)) if r != 0 else '0'
    if len(s) > length:
        return '*' * length, True
    return s.rjust(length), False


def encode_utf8_fixed(s, length, pad=0x20):
    enc = s.encode('utf-8')
    n = min(len(enc), length)
    if n < len(enc):
        while n > 0 and (enc[n] & 0xC0) == 0x80:
            n -= 1
    out = enc[:n] + bytes([pad]) * (length - n)
    return out, n < len(enc)


def build_dbf(polygons, rich, kind, warn=None, today=None):
    fields = dbf_fields(rich, kind)
    for f in fields:
        if len(f[0]) > 10:
            raise ValueError('Nume câmp DBF > 10 caractere: ' + f[0])
    rec_len = 1 + sum(f[2] for f in fields)
    hdr_size = 32 + 32 * len(fields) + 1
    d = today or datetime.date.today()

    b = bytearray()
    b += struct.pack('<4BIHH', 3, d.year - 1900, d.month, d.day, len(polygons), hdr_size, rec_len)
    b += b'\x00' * 20
    for name, typ, length, dec in fields:
        fd = bytearray(32)
        fd[0:len(name)] = name.encode('ascii')
        fd[11] = ord(typ)
        fd[16] = length
        fd[17] = dec
        b += fd
    b += b'\x0d'

    n_overflow = 0
    trunc = {}
    for p in polygons:
        b += b' '
        for name, typ, length, dec in fields:
            raw = p['attrs'].get(name)
            if raw is None:
                raw = ''
            if typ == 'N':
                if isinstance(raw, str):
                    raw = js_float(raw)
                s, over = _fmt_num(raw, length, dec)
                if over:
                    n_overflow += 1
                b += s.encode('ascii')
            else:
                enc, was_trunc = encode_utf8_fixed(str(raw), length)
                if was_trunc:
                    trunc[name] = trunc.get(name, 0) + 1
                b += enc
    b += b'\x1a'

    if warn:
        lbl = 'constructii.dbf' if kind == 'building' else 'teren.dbf'
        if n_overflow:
            warn('%s: %d valori numerice prea lungi (scrise ca ***)' % (lbl, n_overflow))
        lens = dict((f[0], f[2]) for f in fields)
        for name in trunc:
            warn('%s: câmpul %s — %d valori trunchiate la %d bytes' % (lbl, name, trunc[name], lens[name]))
    return bytes(b)


# ════════════════════════════════════════════════════════════
#  Colectarea intrărilor
# ════════════════════════════════════════════════════════════
def is_cgxml_name(rel_path):
    p = rel_path.replace('\\', '/')
    base = p.split('/')[-1]
    if re.search(r'(^|/)__MACOSX/', p, re.I):
        return False
    if base.startswith('._'):
        return False
    return base.lower().endswith('.cgxml')


def collect_sources(paths):
    """Primește o listă de căi (ZIP-uri, foldere, fișiere .cgxml).
    Returnează o listă de (nume_afișat, funcție_care_citește_bytes)."""
    sources = []
    for path in paths:
        if os.path.isdir(path):
            for dirpath, dirnames, filenames in os.walk(path):
                dirnames.sort()
                for fn in sorted(filenames):
                    full = os.path.join(dirpath, fn)
                    rel = os.path.relpath(full, path)
                    if is_cgxml_name(rel):
                        sources.append((rel.replace('\\', '/'), _file_reader(full)))
                    elif fn.lower().endswith('.zip'):
                        sources.extend(_zip_sources(full, prefix=rel.replace('\\', '/') + ':'))
        elif path.lower().endswith('.zip'):
            sources.extend(_zip_sources(path))
        elif is_cgxml_name(os.path.basename(path)):
            sources.append((os.path.basename(path), _file_reader(path)))
    return sources


def _file_reader(path):
    def read():
        with open(path, 'rb') as f:
            return f.read()
    return read


def _zip_sources(path, prefix=''):
    try:
        zf = zipfile.ZipFile(path)
    except zipfile.BadZipFile as e:
        raise ConversionError('Arhivă ZIP invalidă: %s (%s)' % (os.path.basename(path), e))
    out = []
    for info in zf.infolist():
        if info.is_dir():
            continue
        name = _zip_name(info)
        if is_cgxml_name(name):
            out.append((prefix + name, (lambda i=info, z=zf: z.read(i))))
    return out


def _zip_name(info):
    # Arhivele create cu Windows Explorer pot avea nume în CP437/CP852 fără flagul UTF-8.
    name = info.filename
    if not (info.flag_bits & 0x800):
        try:
            raw = name.encode('cp437')
            try:
                name = raw.decode('utf-8')
            except UnicodeDecodeError:
                name = raw.decode('cp852')
        except UnicodeEncodeError:
            pass
    return name


# ════════════════════════════════════════════════════════════
#  Conversia completă
# ════════════════════════════════════════════════════════════
class Result(object):
    def __init__(self):
        self.files = 0
        self.lands = 0
        self.polys = 0
        self.enclaves = 0
        self.multipart = 0
        self.points = 0
        self.buildings = 0
        self.errors = 0
        self.output = None
        self.outputs = []


def convert(inputs, output, opts, log=None, progress=None, cancel=None, output_is_dir=None):
    """Convertește intrările într-un shapefile.

    inputs  : listă de căi (ZIP, folder, .cgxml)
    output  : cale .zip (arhivă) sau folder (fișiere separate)
    log     : funcție log(mesaj, nivel) cu nivel în {'info','ok','warn','error','head','dim'}
    progress: funcție progress(curent, total)
    cancel  : funcție fără argumente care întoarce True pentru oprire
    """
    log = log or (lambda m, lvl='info': None)
    progress = progress or (lambda a, b: None)
    res = Result()

    log('Colectare fișiere CGXML ...', 'head')
    sources = collect_sources(inputs)
    if not sources:
        raise ConversionError('Nu există fișiere .cgxml în intrările selectate!')
    log('Găsite %d fișier(e) CGXML' % len(sources), 'ok')

    all_land, all_bld = [], []
    for idx, (name, reader) in enumerate(sources):
        if cancel and cancel():
            raise ConversionError('Procesare oprită de utilizator.')
        progress(idx, len(sources))
        fname = name.split('/')[-1].split(':')[-1]
        log('[%d/%d]  %s' % (idx + 1, len(sources), name), 'head')
        try:
            r = parse_cgxml(reader(), fname, opts)
        except Exception as e:  # un fișier defect nu oprește lotul
            res.errors += 1
            log('  -> Eroare: %s' % e, 'error')
            continue

        res.lands += r['n_lands']
        msg = '  Land-uri: %d  |  Puncte brute: %d' % (r['n_lands'], r['n_raw_pts'])
        if r['n_bld_pts']:
            msg += '  |  Puncte construcții (excluse din teren): %d' % r['n_bld_pts']
        log(msg, 'dim')
        if r['n_skipped']:
            log('  Ignorate (< 3 puncte distincte): %d' % r['n_skipped'], 'warn')
        if r['n_dropped_pts']:
            log('  Puncte rămase în afara unui inel valid (ignorate): %d' % r['n_dropped_pts'], 'warn')

        for p in r['land_polys']:
            p['attrs']['ID'] = len(all_land) + 1
            npts = sum(len(x) for x in p['rings'])
            res.points += npts
            if p['n_holes']:
                res.enclaves += 1
            if p['n_outer'] > 1:
                res.multipart += 1
            tag = ''
            if p['n_holes']:
                tag += '  [ENCLAVE: %d]' % p['n_holes']
            if p['n_outer'] > 1:
                tag += '  [MULTIPART: %d]' % p['n_outer']
            a = p['attrs']
            diff_txt = ('  dif=%.2f%%' % a['AREA_DIFF']) if a['MEAS_AREA'] > 0 else ''
            log('  OK LANDID=%s  inele=%d  pct=%d  S_calc=%.2f%s  PAPERCADNO="%s"%s' % (
                a['LANDID'], len(p['rings']), npts, a['AREA_CALC'], diff_txt,
                a['PAPERCADNO'] or '-', tag), 'warn' if (tag or a['AREA_DIFF'] > 1) else 'ok')
            all_land.append(p)

        if opts.buildings:
            for p in r['bld_polys']:
                p['attrs']['ID'] = len(all_bld) + 1
                all_bld.append(p)
            if r['bld_polys']:
                log('  Construcții: %d' % len(r['bld_polys']), 'info')
    progress(len(sources), len(sources))
    res.files = len(sources)

    if not all_land:
        raise ConversionError('Niciun poligon Land valid!')

    res.polys = len(all_land)
    res.buildings = len(all_bld)
    log('--- TOTAL: %d poligoane, %d cu enclave, %d multipart, %d puncte' % (
        res.polys, res.enclaves, res.multipart, res.points), 'head')
    log('Generare fișiere shapefile ...', 'info')

    warn = lambda m: log('  ' + m, 'warn')
    files = {}
    shp, shx = build_shp(all_land)
    files['teren.shp'] = shp
    files['teren.shx'] = shx
    files['teren.dbf'] = build_dbf(all_land, opts.rich_dbf, 'land', warn)
    files['teren.prj'] = PRJ.encode('ascii')
    files['teren.cpg'] = b'UTF-8'
    if opts.buildings and all_bld:
        shp, shx = build_shp(all_bld)
        files['constructii.shp'] = shp
        files['constructii.shx'] = shx
        files['constructii.dbf'] = build_dbf(all_bld, opts.rich_dbf, 'building', warn)
        files['constructii.prj'] = PRJ.encode('ascii')
        files['constructii.cpg'] = b'UTF-8'
        log('Strat constructii.shp: %d poligoane' % len(all_bld), 'ok')
    elif opts.buildings:
        log('Nu s-au găsit construcții cu contur valid.', 'warn')

    if output_is_dir is None:
        output_is_dir = not output.lower().endswith('.zip')
    if output_is_dir:
        os.makedirs(output, exist_ok=True)
        for n, data in files.items():
            pth = os.path.join(output, n)
            with open(pth, 'wb') as f:
                f.write(data)
            res.outputs.append(pth)
        log('Fișiere scrise în: %s' % output, 'ok')
    else:
        parent = os.path.dirname(os.path.abspath(output))
        os.makedirs(parent, exist_ok=True)
        tmp = output + '.tmp'
        with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zf:
            for n, data in files.items():
                zf.writestr(n, data)
        os.replace(tmp, output)
        res.outputs.append(output)
        log('ZIP generat: %s (%.1f KB)' % (output, os.path.getsize(output) / 1024.0), 'ok')
    res.output = output
    return res
