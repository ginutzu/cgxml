# -*- coding: utf-8 -*-
"""Interfața grafică (Tkinter) pentru CGXML2SHP."""

import json
import os
import queue
import subprocess
import sys
import threading
import traceback

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import core

APP_NAME = 'CGXML2SHP'
APP_TITLE = 'CGXML2SHP %s' % core.__version__
CONTACT = 'ginu.popescu@gmail.com'

# Culorile aplicației web
BG = '#0b0e14'
PANEL = '#111520'
ACCENT = '#00d4ff'
ACCENT2 = '#00ff9d'
WARN = '#ff9d00'
TEXT = '#c8d6e5'
MUTED = '#6b8299'
LOG_BG = '#080b10'

LOG_COLORS = {'info': TEXT, 'ok': ACCENT2, 'warn': WARN, 'error': '#ff5555', 'head': ACCENT, 'dim': MUTED}

OPTIONS = [
    ('close_ring', 'Închide inelul poligon', 'Repetă primul punct la final dacă lipsește', True),
    ('rich_dbf', 'Atribute extinse DBF', 'MEAS_AREA · AREA_CALC · AREA_DIFF · E2IDENTIF · CADSECTOR …', True),
    ('buildings', 'Include construcții', 'Strat separat constructii.shp din Points.BUILDINGID', False),
    ('swap_xy', 'Forțează inversare X↔Y', 'Când poligoanele apar rotite/oglindite (X=Nord, Y=Est)', False),
    ('id_code', 'Include CNP/CUI în PROPRIETAR', 'Date cu caracter personal (GDPR)', False),
]


def app_root():
    """Folderul aplicației (cel care conține CGXML2SHP.exe)."""
    here = os.path.dirname(os.path.abspath(__file__))       # .../app/cgxml2shp
    return os.path.dirname(os.path.dirname(here))           # .../


def settings_path():
    root = app_root()
    if os.path.exists(os.path.join(root, 'portable.txt')):
        return os.path.join(root, 'settings.json')           # modul portabil: setări lângă aplicație
    base = os.environ.get('APPDATA') or os.path.expanduser('~')
    return os.path.join(base, APP_NAME, 'settings.json')


def load_settings():
    try:
        with open(settings_path(), 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_settings(data):
    try:
        p = settings_path()
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def open_in_explorer(path):
    try:
        if sys.platform.startswith('win'):
            if os.path.isfile(path):
                subprocess.Popen(['explorer', '/select,', os.path.normpath(path)])
            else:
                os.startfile(path)  # noqa
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', path if os.path.isdir(path) else os.path.dirname(path)])
        else:
            subprocess.Popen(['xdg-open', path if os.path.isdir(path) else os.path.dirname(path)])
    except Exception as e:
        messagebox.showerror(APP_TITLE, 'Nu s-a putut deschide folderul:\n%s' % e)


def enable_dpi_awareness():
    if sys.platform.startswith('win'):
        try:
            import ctypes
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


class App(object):
    def __init__(self, root, initial_paths=None):
        self.root = root
        self.settings = load_settings()
        self.inputs = []
        self.queue = queue.Queue()
        self.worker = None
        self.cancel_flag = threading.Event()
        self.last_output = None
        self.output_touched = False

        root.title(APP_TITLE)
        root.configure(bg=BG)
        root.minsize(760, 640)
        self._set_icon()
        self._style()
        self._build()

        for p in initial_paths or []:
            self._add_paths([p])
        self._refresh_inputs()
        root.protocol('WM_DELETE_WINDOW', self._on_close)
        root.after(100, self._poll)

    # ── aspect ───────────────────────────────────────────────
    def _set_icon(self):
        ico = os.path.join(app_root(), 'app', 'app.ico')
        if not os.path.exists(ico):
            ico = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app.ico')
        try:
            if sys.platform.startswith('win') and os.path.exists(ico):
                self.root.iconbitmap(default=ico)
        except Exception:
            pass

    def _style(self):
        st = ttk.Style(self.root)
        try:
            st.theme_use('clam')
        except tk.TclError:
            pass
        base = ('Segoe UI', 10)
        st.configure('.', background=BG, foreground=TEXT, font=base)
        st.configure('Panel.TFrame', background=PANEL)
        st.configure('Panel.TLabel', background=PANEL, foreground=TEXT)
        st.configure('Head.TLabel', background=PANEL, foreground=ACCENT, font=('Segoe UI Semibold', 10))
        st.configure('Muted.TLabel', background=PANEL, foreground=MUTED, font=('Segoe UI', 9))
        st.configure('Title.TLabel', background=BG, foreground=ACCENT, font=('Segoe UI Semibold', 20))
        st.configure('Sub.TLabel', background=BG, foreground=MUTED, font=('Segoe UI', 9))
        st.configure('StatV.TLabel', background=PANEL, foreground=ACCENT, font=('Consolas', 16))
        st.configure('StatL.TLabel', background=PANEL, foreground=MUTED, font=('Segoe UI', 8))
        st.configure('TButton', background='#1a2333', foreground=TEXT, bordercolor='#1e2d45',
                     focuscolor=ACCENT, padding=(10, 5))
        st.map('TButton', background=[('active', '#22324a'), ('disabled', PANEL)],
               foreground=[('disabled', MUTED)])
        st.configure('Run.TButton', background=ACCENT, foreground='#000000',
                     font=('Segoe UI Semibold', 11), padding=(10, 8))
        st.map('Run.TButton', background=[('active', '#5fe6ff'), ('disabled', '#1e2d45')],
               foreground=[('disabled', MUTED)])
        st.configure('TCheckbutton', background=PANEL, foreground=TEXT, indicatorbackground=LOG_BG,
                     indicatorforeground=ACCENT)
        st.map('TCheckbutton', background=[('active', PANEL)],
               indicatorbackground=[('selected', ACCENT), ('active', '#1a2333')],
               indicatorforeground=[('selected', '#000000')])
        st.configure('TRadiobutton', background=PANEL, foreground=TEXT, indicatorbackground=LOG_BG)
        st.map('TRadiobutton', background=[('active', PANEL)],
               indicatorbackground=[('selected', ACCENT)])
        st.configure('TEntry', fieldbackground=LOG_BG, foreground=TEXT, insertcolor=TEXT,
                     bordercolor='#1e2d45')
        st.configure('Horizontal.TProgressbar', background=ACCENT, troughcolor='#1e2d45',
                     bordercolor='#1e2d45', lightcolor=ACCENT, darkcolor=ACCENT)

    def _panel(self, parent, title):
        outer = tk.Frame(parent, bg=ACCENT, padx=0, pady=0)
        inner = ttk.Frame(outer, style='Panel.TFrame', padding=(12, 8, 12, 10))
        inner.pack(fill='both', expand=True, pady=(2, 0))
        ttk.Label(inner, text=title.upper(), style='Head.TLabel').pack(anchor='w', pady=(0, 6))
        return outer, inner

    # ── interfață ────────────────────────────────────────────
    def _build(self):
        main = tk.Frame(self.root, bg=BG, padx=14, pady=10)
        main.pack(fill='both', expand=True)

        hdr = tk.Frame(main, bg=BG)
        hdr.pack(fill='x')
        ttk.Label(hdr, text=APP_TITLE, style='Title.TLabel').pack(side='left')
        ttk.Label(hdr, text='CGXML → Shapefile · EPSG:3844 Stereo70 · ' + CONTACT,
                  style='Sub.TLabel').pack(side='left', padx=12, pady=(8, 0))

        # Intrare
        o, p = self._panel(main, 'Intrare — arhive ZIP, foldere sau fișiere .cgxml')
        o.pack(fill='x', pady=(10, 6))
        row = ttk.Frame(p, style='Panel.TFrame')
        row.pack(fill='x')
        self.lst = tk.Listbox(row, height=4, bg=LOG_BG, fg=TEXT, selectbackground='#1e2d45',
                              highlightthickness=1, highlightbackground='#1e2d45', borderwidth=0,
                              activestyle='none', font=('Consolas', 9), selectmode='extended')
        self.lst.pack(side='left', fill='both', expand=True)
        btns = ttk.Frame(row, style='Panel.TFrame')
        btns.pack(side='left', padx=(8, 0), fill='y')
        self.btn_zip = ttk.Button(btns, text='Adaugă ZIP…', command=self._add_zip)
        self.btn_dir = ttk.Button(btns, text='Adaugă folder…', command=self._add_dir)
        self.btn_files = ttk.Button(btns, text='Adaugă .cgxml…', command=self._add_files)
        self.btn_rm = ttk.Button(btns, text='Elimină', command=self._remove_selected)
        for b in (self.btn_zip, self.btn_dir, self.btn_files, self.btn_rm):
            b.pack(fill='x', pady=1)
        self.lbl_count = ttk.Label(p, text='', style='Muted.TLabel')
        self.lbl_count.pack(anchor='w', pady=(4, 0))

        # Ieșire
        o, p = self._panel(main, 'Ieșire')
        o.pack(fill='x', pady=6)
        r1 = ttk.Frame(p, style='Panel.TFrame')
        r1.pack(fill='x')
        self.out_mode = tk.StringVar(value=self.settings.get('out_mode', 'zip'))
        ttk.Radiobutton(r1, text='Arhivă ZIP', value='zip', variable=self.out_mode,
                        command=self._mode_changed).pack(side='left')
        ttk.Radiobutton(r1, text='Folder cu fișiere SHP', value='dir', variable=self.out_mode,
                        command=self._mode_changed).pack(side='left', padx=(14, 0))
        r2 = ttk.Frame(p, style='Panel.TFrame')
        r2.pack(fill='x', pady=(6, 0))
        self.out_var = tk.StringVar()
        self.ent_out = ttk.Entry(r2, textvariable=self.out_var, font=('Consolas', 9))
        self.ent_out.pack(side='left', fill='x', expand=True)
        self.ent_out.bind('<Key>', lambda e: setattr(self, 'output_touched', True))
        self.btn_out = ttk.Button(r2, text='Alege…', command=self._choose_output)
        self.btn_out.pack(side='left', padx=(8, 0))

        # Opțiuni
        o, p = self._panel(main, 'Opțiuni de procesare')
        o.pack(fill='x', pady=6)
        grid = ttk.Frame(p, style='Panel.TFrame')
        grid.pack(fill='x')
        saved = self.settings.get('options', {})
        self.opt_vars = {}
        for i, (key, label, sub, default) in enumerate(OPTIONS):
            v = tk.BooleanVar(value=bool(saved.get(key, default)))
            self.opt_vars[key] = v
            cell = ttk.Frame(grid, style='Panel.TFrame')
            cell.grid(row=i // 2, column=i % 2, sticky='w', padx=(0, 18), pady=2)
            ttk.Checkbutton(cell, text=label, variable=v).pack(anchor='w')
            ttk.Label(cell, text=sub, style='Muted.TLabel').pack(anchor='w', padx=(22, 0))
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        # Rulare
        run = tk.Frame(main, bg=BG)
        run.pack(fill='x', pady=(8, 4))
        self.btn_run = ttk.Button(run, text='▶  Procesează fișierele CGXML', style='Run.TButton',
                                  command=self._start)
        self.btn_run.pack(side='left', fill='x', expand=True)
        self.btn_stop = ttk.Button(run, text='Oprește', command=self._stop, state='disabled')
        self.btn_stop.pack(side='left', padx=(8, 0))
        self.prog = ttk.Progressbar(main, mode='determinate', style='Horizontal.TProgressbar')
        self.prog.pack(fill='x', pady=(4, 6))

        # Statistici
        stats = tk.Frame(main, bg='#1e2d45')
        stats.pack(fill='x')
        self.stat_vars = {}
        for i, (k, lbl) in enumerate([('files', 'Fișiere CGXML'), ('lands', 'Terenuri Land'),
                                      ('polys', 'Poligoane SHP'), ('enclaves', 'Cu enclave'),
                                      ('buildings', 'Construcții'), ('points', 'Puncte totale')]):
            c = ttk.Frame(stats, style='Panel.TFrame', padding=(6, 6))
            c.grid(row=0, column=i, sticky='nsew', padx=(0 if i == 0 else 1, 0))
            stats.columnconfigure(i, weight=1)
            v = tk.StringVar(value='–')
            self.stat_vars[k] = v
            ttk.Label(c, textvariable=v, style='StatV.TLabel').pack()
            ttk.Label(c, text=lbl.upper(), style='StatL.TLabel').pack()

        # Bara de jos (ancorată jos, rămâne vizibilă și în ferestre mici)
        self._foot = tk.Frame(main, bg=BG)
        self._foot.pack(side='bottom', fill='x', pady=(8, 0))

        # Jurnal
        logf = tk.Frame(main, bg=BG)
        logf.pack(fill='both', expand=True, pady=(8, 0))
        self.txt = tk.Text(logf, bg=LOG_BG, fg=TEXT, insertbackground=TEXT, height=8, wrap='none',
                           font=('Consolas', 9), borderwidth=0, highlightthickness=1,
                           highlightbackground='#1e2d45', state='disabled')
        sb = ttk.Scrollbar(logf, orient='vertical', command=self.txt.yview)
        self.txt.configure(yscrollcommand=sb.set)
        self.txt.pack(side='left', fill='both', expand=True)
        sb.pack(side='left', fill='y')
        for lvl, col in LOG_COLORS.items():
            self.txt.tag_configure(lvl, foreground=col)

        foot = self._foot
        self.btn_open = ttk.Button(foot, text='Deschide rezultatul', command=self._open_result,
                                   state='disabled')
        self.btn_open.pack(side='left')
        ttk.Button(foot, text='Salvează jurnalul…', command=self._save_log).pack(side='left', padx=6)
        ttk.Button(foot, text='Manual (PDF)', command=self._open_manual).pack(side='left')
        ttk.Label(foot, text='Proiecție EPSG:3844 · Pulkovo 1942 (Adj 1958) · CGXMLSchema_new_v3.xsd',
                  style='Sub.TLabel').pack(side='right')

    # ── intrări ──────────────────────────────────────────────
    def _initial_dir(self):
        d = self.settings.get('last_dir')
        return d if d and os.path.isdir(d) else os.path.expanduser('~')

    def _add_zip(self):
        ps = filedialog.askopenfilenames(parent=self.root, title='Alege arhive ZIP',
                                         initialdir=self._initial_dir(),
                                         filetypes=[('Arhive ZIP', '*.zip'), ('Toate fișierele', '*.*')])
        self._add_paths(ps)

    def _add_dir(self):
        p = filedialog.askdirectory(parent=self.root, title='Alege folderul cu fișiere CGXML',
                                    initialdir=self._initial_dir())
        if p:
            self._add_paths([p])

    def _add_files(self):
        ps = filedialog.askopenfilenames(parent=self.root, title='Alege fișiere CGXML',
                                         initialdir=self._initial_dir(),
                                         filetypes=[('Fișiere CGXML', '*.cgxml'), ('Toate fișierele', '*.*')])
        self._add_paths(ps)

    def _add_paths(self, paths):
        added = False
        for p in paths or []:
            p = os.path.normpath(p)
            if os.path.exists(p) and p not in self.inputs:
                self.inputs.append(p)
                added = True
                self.settings['last_dir'] = p if os.path.isdir(p) else os.path.dirname(p)
        if added:
            self._refresh_inputs()

    def _remove_selected(self):
        for i in reversed(self.lst.curselection()):
            del self.inputs[i]
        self._refresh_inputs()

    def _refresh_inputs(self):
        self.lst.delete(0, 'end')
        for p in self.inputs:
            kind = 'folder' if os.path.isdir(p) else ('ZIP' if p.lower().endswith('.zip') else 'CGXML')
            self.lst.insert('end', '[%s]  %s' % (kind, p))
        n = len(self.inputs)
        self.lbl_count.configure(text=('1 intrare selectată' if n == 1 else '%d intrări selectate' % n) if n else
                                 'Nicio intrare. Puteți și trage o arhivă ZIP peste pictograma CGXML2SHP.exe.')
        if not self.output_touched:
            self._suggest_output()

    def _suggest_output(self):
        if not self.inputs:
            return
        from .cli import default_output
        self.out_var.set(default_output(self.inputs, self.out_mode.get() == 'dir'))

    def _mode_changed(self):
        cur = self.out_var.get().strip()
        if self.out_mode.get() == 'zip' and cur and not cur.lower().endswith('.zip'):
            self.out_var.set(cur.rstrip('\\/') + '.zip')
        elif self.out_mode.get() == 'dir' and cur.lower().endswith('.zip'):
            self.out_var.set(cur[:-4])
        elif not cur:
            self._suggest_output()

    def _choose_output(self):
        cur = self.out_var.get().strip()
        start = os.path.dirname(cur) if cur else self._initial_dir()
        if self.out_mode.get() == 'zip':
            p = filedialog.asksaveasfilename(parent=self.root, title='Salvează arhiva ZIP',
                                             initialdir=start if os.path.isdir(start) else None,
                                             initialfile=os.path.basename(cur) or 'cgxml_to_shp.zip',
                                             defaultextension='.zip', filetypes=[('Arhivă ZIP', '*.zip')])
        else:
            p = filedialog.askdirectory(parent=self.root, title='Alege folderul de ieșire',
                                        initialdir=start if os.path.isdir(start) else None)
        if p:
            self.out_var.set(os.path.normpath(p))
            self.output_touched = True

    # ── procesare ────────────────────────────────────────────
    def _options(self):
        return core.Options(**dict((k, v.get()) for k, v in self.opt_vars.items()))

    def _set_running(self, running):
        st = 'disabled' if running else 'normal'
        for b in (self.btn_run, self.btn_zip, self.btn_dir, self.btn_files, self.btn_rm, self.btn_out):
            b.configure(state=st)
        self.btn_stop.configure(state='normal' if running else 'disabled')

    def _start(self):
        if not self.inputs:
            messagebox.showwarning(APP_TITLE, 'Adăugați cel puțin o arhivă ZIP, un folder sau un fișier .cgxml.')
            return
        out = self.out_var.get().strip()
        if not out:
            messagebox.showwarning(APP_TITLE, 'Alegeți unde se salvează rezultatul.')
            return
        as_dir = self.out_mode.get() == 'dir'
        if not as_dir and not out.lower().endswith('.zip'):
            out += '.zip'
            self.out_var.set(out)
        if not as_dir and os.path.exists(out):
            if not messagebox.askyesno(APP_TITLE, 'Fișierul există deja:\n%s\n\nÎl înlocuiți?' % out):
                return
        if as_dir and os.path.isdir(out) and any(
                os.path.exists(os.path.join(out, n)) for n in ('teren.shp', 'constructii.shp')):
            if not messagebox.askyesno(APP_TITLE, 'Folderul conține deja un shapefile teren/constructii.\n'
                                                  'Fișierele vor fi înlocuite. Continuați?'):
                return
        if self.opt_vars['id_code'].get():
            if not messagebox.askyesno(APP_TITLE, 'Ați ales să includeți CNP/CUI în atributul PROPRIETAR.\n\n'
                                                  'Acestea sunt date cu caracter personal. Continuați?'):
                return

        self._clear_log()
        for v in self.stat_vars.values():
            v.set('–')
        self.prog.configure(value=0, maximum=1)
        self.btn_open.configure(state='disabled')
        self.cancel_flag.clear()
        self._set_running(True)
        opts = self._options()
        inputs = list(self.inputs)
        self._persist()

        def work():
            try:
                res = core.convert(inputs, out, opts,
                                   log=lambda m, lvl='info': self.queue.put(('log', m, lvl)),
                                   progress=lambda a, b: self.queue.put(('prog', a, b)),
                                   cancel=self.cancel_flag.is_set, output_is_dir=as_dir)
                self.queue.put(('done', res, None))
            except core.ConversionError as e:
                self.queue.put(('fail', str(e), None))
            except Exception as e:
                self.queue.put(('fail', '%s\n%s' % (e, traceback.format_exc()), None))

        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()

    def _stop(self):
        self.cancel_flag.set()
        self.btn_stop.configure(state='disabled')

    def _poll(self):
        try:
            for _ in range(500):
                kind, a, b = self.queue.get_nowait()
                if kind == 'log':
                    self._log(a, b)
                elif kind == 'prog':
                    self.prog.configure(maximum=max(b, 1), value=a)
                elif kind == 'done':
                    self._finished(a)
                elif kind == 'fail':
                    self._log('EROARE: ' + a, 'error')
                    self._set_running(False)
                    messagebox.showerror(APP_TITLE, a.split('\n')[0])
        except queue.Empty:
            pass
        self.root.after(80, self._poll)

    def _finished(self, res):
        self._set_running(False)
        self.last_output = res.output
        for k in self.stat_vars:
            self.stat_vars[k].set(str(getattr(res, k)))
        self.btn_open.configure(state='normal')
        msg = 'Conversie finalizată: %d poligoane' % res.polys
        if res.errors:
            msg += ' (%d fișiere cu erori — vezi jurnalul)' % res.errors
        self._log(msg, 'ok' if not res.errors else 'warn')

    # ── jurnal & diverse ─────────────────────────────────────
    def _log(self, msg, lvl='info'):
        self.txt.configure(state='normal')
        self.txt.insert('end', '▶ ' + msg + '\n', lvl)
        self.txt.see('end')
        self.txt.configure(state='disabled')

    def _clear_log(self):
        self.txt.configure(state='normal')
        self.txt.delete('1.0', 'end')
        self.txt.configure(state='disabled')

    def _save_log(self):
        p = filedialog.asksaveasfilename(parent=self.root, title='Salvează jurnalul',
                                         defaultextension='.txt', initialfile='cgxml2shp_jurnal.txt',
                                         filetypes=[('Text', '*.txt')])
        if p:
            with open(p, 'w', encoding='utf-8') as f:
                f.write(self.txt.get('1.0', 'end'))

    def _open_result(self):
        if self.last_output and os.path.exists(self.last_output):
            open_in_explorer(self.last_output)

    def _open_manual(self):
        docs = os.path.join(app_root(), 'docs')
        pdfs = [f for f in os.listdir(docs) if f.lower().endswith('.pdf')] if os.path.isdir(docs) else []
        if not pdfs:
            messagebox.showinfo(APP_TITLE, 'Manualul PDF nu a fost găsit în folderul docs.')
            return
        p = os.path.join(docs, sorted(pdfs)[0])
        try:
            if sys.platform.startswith('win'):
                os.startfile(p)  # noqa
            else:
                subprocess.Popen(['xdg-open', p])
        except Exception as e:
            messagebox.showerror(APP_TITLE, str(e))

    def _persist(self):
        self.settings['options'] = dict((k, v.get()) for k, v in self.opt_vars.items())
        self.settings['out_mode'] = self.out_mode.get()
        save_settings(self.settings)

    def _on_close(self):
        if self.worker and self.worker.is_alive():
            if not messagebox.askyesno(APP_TITLE, 'Procesarea rulează. Închideți oricum?'):
                return
            self.cancel_flag.set()
        self._persist()
        self.root.destroy()


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    enable_dpi_awareness()
    root = tk.Tk()
    try:
        scale = root.winfo_fpixels('1i') / 72.0
        if scale > 1.0:
            root.tk.call('tk', 'scaling', scale)
    except Exception:
        pass
    App(root, initial_paths=[a for a in argv if os.path.exists(a)])
    h = min(900, max(640, root.winfo_screenheight() - 90))
    root.geometry('920x%d' % h)
    root.mainloop()


if __name__ == '__main__':
    main()
