"""Resolve bundled asset paths whether running from source or a PyInstaller
onefile exe (which unpacks data files to a temp dir at `sys._MEIPASS`)."""
import os
import sys


def asset_path(filename: str) -> str:
    base = getattr(sys, "_MEIPASS", None)
    if base is None:
        base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
    else:
        base = os.path.join(base, "assets")
    return os.path.join(base, filename)
