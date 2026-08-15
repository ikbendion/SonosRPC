"""Convenience wrapper: `python build/build.py` builds the onefile exe.

Equivalent to running `pyinstaller build/build.spec` from the repo root,
which is what actually does the work -- this just resolves paths so it
can be invoked from anywhere and cleans previous build output first.
"""
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC_FILE = Path(__file__).resolve().parent / "build.spec"
WORK_DIR = REPO_ROOT / "build" / "_pyinstaller"
DIST_DIR = REPO_ROOT / "dist"


def main() -> int:
    shutil.rmtree(DIST_DIR, ignore_errors=True)
    shutil.rmtree(WORK_DIR, ignore_errors=True)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean", "--noconfirm",
        "--workpath", str(WORK_DIR),
        "--distpath", str(DIST_DIR),
        str(SPEC_FILE),
    ]
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    if result.returncode == 0:
        print(f"\nBuilt: {REPO_ROOT / 'dist' / 'SonosDiscordPresence.exe'}")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
