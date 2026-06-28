# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the Kebbet Zamen receipt app.
#
# Build (on a Windows PC with Python installed):
#     pip install -r requirements.txt pyinstaller
#     pyinstaller KebbetZamen.spec
#
# The finished app is written to:  dist\KebbetZamen.exe
#
# IMPORTANT: ui.html is bundled into the .exe (the app loads it from the
# PyInstaller bundle). Whenever ui.html or extract.py changes, the .exe MUST
# be rebuilt for the change to take effect — replacing the source files alone
# does nothing to an already-built .exe.

a = Analysis(
    ['receipt_server.py'],
    pathex=[],
    binaries=[],
    datas=[('ui.html', '.')],   # bundle the UI next to the app at runtime
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='KebbetZamen',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,   # show a small window confirming the app is running
)
