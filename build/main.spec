# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for BodyLocaliser.
#
# Build from the project root with:
#   pyinstaller build/main.spec
#
# The resulting executable will be in dist/BodyLocaliser/

import os
PROJ_ROOT = os.path.abspath(os.path.join(SPECPATH, '..'))

a = Analysis(
    [os.path.join(PROJ_ROOT, 'src', 'main.py')],
    pathex=[os.path.join(PROJ_ROOT, 'src')],
    binaries=[],
    datas=[
        (os.path.join(PROJ_ROOT, 'assets', 'images'), os.path.join('assets', 'images')),
        (os.path.join(PROJ_ROOT, 'src', 'parameters.py'), 'src'),
    ],
    hiddenimports=[
        'psychopy',
        'psychopy.visual',
        'psychopy.core',
        'psychopy.event',
        'psychopy.gui',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BodyLocaliser',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='BodyLocaliser',
)
