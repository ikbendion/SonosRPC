"""Toggle "Start with Windows" via the per-user Run registry key.

HKCU (not HKLM) on purpose: the app installs to %LOCALAPPDATA% without
admin rights, so the startup entry must not require them either.
"""
import logging
import sys

log = logging.getLogger(__name__)

RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE_NAME = "SonosDiscordPresence"

try:
    import winreg
except ImportError:  # non-Windows dev environment
    winreg = None


def _exe_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    return f'"{sys.executable}" "{sys.argv[0]}"'


def is_enabled() -> bool:
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH) as key:
            winreg.QueryValueEx(key, RUN_VALUE_NAME)
            return True
    except FileNotFoundError:
        return False
    except OSError:
        log.exception("Failed to read startup registry key")
        return False


def set_enabled(enabled: bool) -> bool:
    if winreg is None:
        log.warning("winreg unavailable; cannot change startup setting on this platform")
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, RUN_VALUE_NAME, 0, winreg.REG_SZ, _exe_command())
            else:
                try:
                    winreg.DeleteValue(key, RUN_VALUE_NAME)
                except FileNotFoundError:
                    pass
        return True
    except OSError:
        log.exception("Failed to update startup registry key")
        return False
