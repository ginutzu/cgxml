# -*- coding: utf-8 -*-
"""Interfața în linie de comandă pentru CGXML2SHP."""

import argparse
import os
import sys

from . import core

_COLORS = {'ok': '', 'warn': '! ', 'error': '!! ', 'head': '', 'dim': '', 'info': ''}


def default_output(inputs, as_folder):
    if len(inputs) == 1:
        p = os.path.abspath(inputs[0].rstrip('\\/'))
        stem = os.path.splitext(os.path.basename(p))[0] if os.path.isfile(p) else os.path.basename(p)
        base = os.path.join(os.path.dirname(p), (stem or 'cgxml') + '_SHP')
    else:
        base = os.path.join(os.getcwd(), 'cgxml_to_shp')
    return base if as_folder else base + '.zip'


def build_parser():
    ap = argparse.ArgumentParser(
        prog='cgxml2shp-cli',
        description='CGXML2SHP %s — conversie fișiere cadastrale CGXML în shapefile EPSG:3844.' % core.__version__,
        epilog='Exemple:\n'
               '  cgxml2shp-cli date.zip\n'
               '  cgxml2shp-cli D:\\cgxml\\ -o D:\\rezultat\\teren.zip --constructii\n'
               '  cgxml2shp-cli a.cgxml b.cgxml --folder -o D:\\rezultat',
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('intrari', nargs='+', metavar='INTRARE',
                    help='arhivă ZIP, folder sau fișier .cgxml (se pot da mai multe)')
    ap.add_argument('-o', '--iesire', metavar='CALE',
                    help='fișierul .zip sau folderul de ieșire (implicit: lângă intrare, <nume>_SHP.zip)')
    ap.add_argument('--folder', action='store_true',
                    help='scrie fișierele shapefile într-un folder în loc de arhivă ZIP')
    ap.add_argument('--constructii', action='store_true', help='generează și stratul constructii.shp')
    ap.add_argument('--inversare-xy', action='store_true', help='inversează axele (X=Nord, Y=Est în CGXML)')
    ap.add_argument('--dbf-simplu', action='store_true', help='doar atributele de bază în DBF')
    ap.add_argument('--fara-inchidere', action='store_true', help='nu închide automat inelele poligoanelor')
    ap.add_argument('--cnp', action='store_true',
                    help='include IDCODE (CNP/CUI) în PROPRIETAR — date cu caracter personal')
    ap.add_argument('-q', '--silentios', action='store_true', help='afișează doar erorile și rezumatul')
    ap.add_argument('--version', action='version', version='CGXML2SHP ' + core.__version__)
    return ap


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            if stream.isatty():
                stream.reconfigure(errors='replace')
            else:  # ieșire redirecționată în fișier: UTF-8, ca diacriticele să nu se piardă
                stream.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

    args = build_parser().parse_args(argv)
    for p in args.intrari:
        if not os.path.exists(p):
            print('EROARE: nu există: %s' % p, file=sys.stderr)
            return 2

    as_folder = args.folder or (args.iesire is not None and not args.iesire.lower().endswith('.zip'))
    out = args.iesire or default_output(args.intrari, as_folder)
    opts = core.Options(close_ring=not args.fara_inchidere, rich_dbf=not args.dbf_simplu,
                        buildings=args.constructii, swap_xy=args.inversare_xy, id_code=args.cnp)

    def log(msg, lvl='info'):
        if args.silentios and lvl not in ('error',):
            return
        stream = sys.stderr if lvl == 'error' else sys.stdout
        print(_COLORS.get(lvl, '') + msg, file=stream)

    try:
        r = core.convert(args.intrari, out, opts, log=log, output_is_dir=as_folder)
    except core.ConversionError as e:
        print('EROARE: %s' % e, file=sys.stderr)
        return 1
    print('Gata: %d fișiere, %d poligoane (%d cu enclave), %d construcții -> %s' % (
        r.files, r.polys, r.enclaves, r.buildings, r.output))
    return 1 if r.errors else 0


if __name__ == '__main__':
    sys.exit(main())
