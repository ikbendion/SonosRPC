"""Entry point. Packaged with PyInstaller as a windowed (no console) exe."""
import logging
import sys

from sonos_discord_presence.app import App


def main() -> int:
    app = App()
    try:
        app.run()
    except Exception:
        logging.getLogger(__name__).exception("Fatal error")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
