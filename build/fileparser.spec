# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for FileParser Windows build."""

import sys
from pathlib import Path

block_cipher = None
root = Path(SPECPATH).parent.parent

added_files = [
    (str(root / "config" / "templates"), "config/templates"),
    (str(root / "config" / "settings.example.yaml"), "config"),
]

a = Analysis(
    [str(root / "src" / "fileparser" / "main.py")],
    pathex=[str(root / "src")],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
    ],
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
    name="FileParser",
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
    name="FileParser",
)
