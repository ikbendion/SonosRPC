"""Entry point. Packaged with PyInstaller as a windowed (no console) exe.

A windowed/no-console build has no stderr for the interpreter to print an
uncaught exception to -- if something blows up before the app's own
RotatingFileHandler is installed (import errors, a bad config file, a
missing DLL), it would otherwise fail completely silently. So this sets
up a bare-bones crash log using only stdlib, before importing anything
from the app package, and installs it as sys.excepthook too so nothing
can slip past it.
"""
import logging
import logging.handlers
import os
import sys

# config.py only touches stdlib (json/os) at import time -- safe to import
# this early, before the heavier pypresence/pystray/soco/PIL imports that
# live behind `sonos_discord_presence.app`.
from sonos_discord_presence.config import get_config_dir, get_log_path


def _install_early_logging() -> None:
    os.makedirs(get_config_dir(), exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        get_log_path(), maxBytes=1_000_000, backupCount=2, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)

    def excepthook(exc_type, exc_value, exc_tb):
        logging.getLogger("crash").critical(
            "Unhandled exception", exc_info=(exc_type, exc_value, exc_tb)
        )

    sys.excepthook = excepthook


def main() -> int:
    _install_early_logging()
    log = logging.getLogger(__name__)
    log.info("Launching Sonos Discord Presence")

    try:
        from sonos_discord_presence.app import App
        App().run()
    except Exception:
        log.exception("Fatal error")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
