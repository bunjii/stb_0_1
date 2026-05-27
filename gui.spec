# -*- mode: python ; coding: utf-8 -*-
import os

import sys
sys.setrecursionlimit(sys.getrecursionlimit() * 5)

from vedo import installdir as vedo_installdir
vedo_fontsdir = os.path.join(vedo_installdir, 'fonts')

block_cipher = None

added_files = [
    (os.path.join(vedo_fontsdir,'*'), os.path.join('vedo','fonts')),
]

a = Analysis(
    ['gui.py'],
    pathex=[],
    binaries=[],
    hiddenimports=[
        'vtkmodules',
        'vtkmodules.all',
        'vtkmodules.util',
        'vtkmodules.util.numpy_support',
        'vtkmodules.wx.wxVTKRenderWindowInteractor',
    ],
    datas = added_files,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None
    )
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='gui',
)
