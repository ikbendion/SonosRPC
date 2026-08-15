"""Local JSON configuration storage.

Config lives at %APPDATA%\\SonosDiscordPresence\\config.json so it survives
app updates/reinstalls and needs no admin rights to write.
"""
import json
import logging
import os

from . import APP_NAME

log = logging.getLogger(__name__)

DEFAULTS = {
    "discord_client_id": "",
    "speaker_uid": "",
    "speaker_name": "",
    "speaker_ip": "",
    "poll_interval": 5,
    "idle_grace_seconds": 12,
    "start_with_windows": False,
}


def get_config_dir() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, APP_NAME)


def get_config_path() -> str:
    return os.path.join(get_config_dir(), "config.json")


def get_log_path() -> str:
    return os.path.join(get_config_dir(), "app.log")


def load_config() -> dict:
    path = get_config_path()
    cfg = dict(DEFAULTS)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                cfg.update(json.load(fh))
        except (OSError, ValueError) as exc:
            log.warning("Failed to read config at %s (%s); using defaults", path, exc)
    return cfg


def save_config(cfg: dict) -> None:
    os.makedirs(get_config_dir(), exist_ok=True)
    path = get_config_path()
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2)
    os.replace(tmp_path, path)


def is_configured(cfg: dict) -> bool:
    return bool(cfg.get("discord_client_id")) and bool(cfg.get("speaker_uid"))
