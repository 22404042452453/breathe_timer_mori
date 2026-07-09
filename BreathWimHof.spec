# -*- mode: python ; coding: utf-8 -*-
# Сборка Kivy-приложения main.py в один .exe:
#   python -m PyInstaller BreathWimHof.spec --noconfirm --clean
from kivy_deps import sdl2, glew, angle

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    # pyttsx3 подгружает драйвер sapi5 динамически — PyInstaller его не видит.
    hiddenimports=[
        'pyttsx3.drivers',
        'pyttsx3.drivers.sapi5',
        'pyttsx3.drivers.dummy',
        'comtypes',
        'comtypes.client',
        'win32com',
        'win32com.client',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter'],   # main.py на Kivy, tkinter не нужен
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    *[Tree(p) for p in (sdl2.dep_bins + glew.dep_bins + angle.dep_bins)],
    name='BreathWimHof',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,           # без консольного окна
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
