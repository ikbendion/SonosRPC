# PyInstaller spec for Sonos Discord Presence.
# Build from the repo root with:  pyinstaller build/build.spec
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(SPEC)))

a = Analysis(
    [os.path.join(REPO_ROOT, "main.py")],
    pathex=[REPO_ROOT],
    binaries=[],
    datas=[
        (os.path.join(REPO_ROOT, "assets", "icon.png"), "assets"),
        (os.path.join(REPO_ROOT, "assets", "icon_error.png"), "assets"),
        (os.path.join(REPO_ROOT, "assets", "logo.png"), "assets"),
    ],
    hiddenimports=["pystray._win32", "PIL._tkinter_finder"],
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
    name="SonosDiscordPresence",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    windowed=True,
    icon=os.path.join(REPO_ROOT, "assets", "icon.ico"),
)
