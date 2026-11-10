# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

block_cipher = None

site_packages = Path(".venv/Lib/site-packages").resolve()
if not site_packages.exists():
    import site
    site_packages = Path(site.getsitepackages()[-1])

flet_desktop_dir = site_packages / "flet_desktop"

datas = [
    ('app', 'app'),
]
if flet_desktop_dir.exists():
    datas.append((str(flet_desktop_dir), 'flet_desktop'))

binaries = []
hiddenimports = [
    'flet',
    'flet_desktop',
    'sqlalchemy',
    'sqlalchemy.sql.default_comparator',
    'pydantic',
    'reportlab',
    'openpyxl',
    'sqlite3',
]

for pkg in ['flet', 'flet_desktop']:
    pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(pkg)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hiddenimports

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FiadoManager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='FiadoManager',
)
