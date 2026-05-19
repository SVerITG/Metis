# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec — Metis Tray Launcher
#
# Produces: MetisTray.exe  (no console window, no Python install required)
#
# Build from system/install/ on Windows with the Metis venv active:
#   pip install pyinstaller pystray Pillow
#   pyinstaller tray-launcher.spec
#
# Output: system/install/dist/MetisTray.exe
# The .exe is referenced in metis-setup.iss [Files] section.
#
# PyInstaller collects pystray and Pillow automatically.
# No external .ico asset is required — the icon is drawn at runtime with Pillow.

block_cipher = None

a = Analysis(
    ['tray_launcher.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'pystray',
        'pystray._win32',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'PIL.ImageFont',
        'pkg_resources.py2_warn',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy', 'pandas'],
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
    [],
    name='MetisTray',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,           # windowStyle = no terminal
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='windows/metis.ico',
    version_file=None,
)
