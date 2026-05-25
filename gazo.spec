# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

block_cipher = None
ROOT = Path('.').resolve()
ICON_PATH = ROOT / 'static_dist' / 'logo' / 'logo.ico'


a = Analysis(
    ['app.py'],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        ('static_dist', 'static_dist'),
        ('naming.py', '.'),
        ('download_runtime.py', '.'),
    ],
    hiddenimports=[
        'flask',
        'requests',
        'dotenv',
        'danbooru_crawler',
        'yande_crawler',
        'naming',
        'download_runtime',
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
    a.binaries,
    a.datas,
    [],
    name='Gazo',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON_PATH) if ICON_PATH.exists() else None,
)
