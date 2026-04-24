# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for AXIOM Browser.

Build command (from project root, inside .venv):
    pyinstaller axiom.spec --noconfirm

Output: dist/Axiom/Axiom.exe  (one-directory build)
"""

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

block_cipher = None

# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=[
        # App assets
        ("assets/axiom.png",       "assets"),
        ("assets/axiom.ico",       "assets"),
        # Adblock domain list
        ("core/blocklist.txt",     "core"),
    ],
    hiddenimports=[
        # PyQt6 WebEngine requires explicit listing in some hook versions
        "PyQt6.QtWebEngineWidgets",
        "PyQt6.QtWebEngineCore",
        "PyQt6.QtWebChannel",
        "PyQt6.QtNetwork",
        "PyQt6.QtPrintSupport",
        "PyQt6.sip",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Trim unused heavy stdlib modules
        "tkinter",
        "unittest",
        "xmlrpc",
        "pydoc",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# ---------------------------------------------------------------------------
# PYZ archive
# ---------------------------------------------------------------------------

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ---------------------------------------------------------------------------
# EXE
# ---------------------------------------------------------------------------

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,          # one-directory mode (required for WebEngine)
    name="Axiom",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                      # UPX breaks some Qt DLLs — keep off
    console=False,                  # no terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets\\axiom.ico",
    version_file=None,
)

# ---------------------------------------------------------------------------
# COLLECT — assembles the one-directory bundle
# ---------------------------------------------------------------------------

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Axiom",
)
