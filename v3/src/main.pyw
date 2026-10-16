# -*- coding: utf-8 -*-
"""Pornește interfața grafică CGXML2SHP."""
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# pythonw.exe nu are consolă: evită erorile la scriere pe stdout/stderr
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')

try:
    from cgxml2shp.gui import main
    main()
except Exception:
    err = traceback.format_exc()
    log = os.path.join(os.environ.get('TEMP', HERE), 'cgxml2shp_eroare.txt')
    try:
        with open(log, 'w', encoding='utf-8') as f:
            f.write(err)
    except Exception:
        pass
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, 'CGXML2SHP nu a putut porni.\n\n%s\n\nDetalii: %s'
                                         % (err.strip().splitlines()[-1], log), 'CGXML2SHP', 0x10)
    except Exception:
        sys.__stderr__ and sys.__stderr__.write(err)
    sys.exit(1)
