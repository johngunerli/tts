# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Text-to-Speech App
Builds:
  macOS  → dist/Text-to-Speech.app
  Windows → dist/Text-to-Speech.exe
  Linux  → dist/Text-to-Speech (binary)

Run with:
  pyinstaller tts_app.spec
"""

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=[
        # Bundle the Piper voice models alongside the app
        ("audio-model", "audio-model"),
    ],
    hiddenimports=[
        "piper",
        "piper.voice",
        "onnxruntime",
        "urllib",
        "urllib.request",
        "urllib.parse",
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
    exclude_binaries=True,       # onedir mode: binaries go into COLLECT
    name="Text-to-Speech",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
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
    name="Text-to-Speech",
)

# ── macOS .app bundle ──────────────────────────────────────────────────────
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Text-to-Speech.app",
        icon=None,           # swap in a .icns file path if you have one
        bundle_identifier="com.yourname.tts",
        info_plist={
            "NSHighResolutionCapable": True,
            "CFBundleShortVersionString": "1.0.0",
            "LSUIElement": False,
        },
    )
