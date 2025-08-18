# vertex_desktop.spec
# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['vertex_desktop.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['google.auth', 'google.auth.transport.requests'],
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
    a.binaries,
    a.datas,
    [],
    name='Vertex AI Client',
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
    codesign_identity=None, # See recommendation below
    entitlements_file=None,
    icon='icon.icns',
)

app = BUNDLE(
    exe,
    name='Vertex AI Client.app',
    icon='icon.icns',
    bundle_identifier='com.vertex.desktop',
    info_plist={
        # --- ADDED/REQUIRED KEYS ---
        'CFBundleName': 'Vertex AI Client',
        'CFBundleDisplayName': 'Vertex AI Client',
        'CFBundleExecutable': 'Vertex AI Client', # <-- Must match the 'name' in EXE
        'CFBundlePackageType': 'APPL',            # <-- Essential key
        'LSMinimumSystemVersion': '10.13.0',      # <-- Good practice

        # --- Original Keys ---
        'NSPrincipalClass': 'NSApplication',
        'NSAppleScriptEnabled': False,
        'CFBundleDocumentTypes': [],
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'NSHumanReadableCopyright': 'Copyright © 2024',
        'NSRequiresAquaSystemAppearance': False,
        'NSHighResolutionCapable': True,
    },
)

