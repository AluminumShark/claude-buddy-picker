"""Read / write ~/.claude.json for buddy overrides."""

import json
from pathlib import Path

CLAUDE_JSON = Path.home() / ".claude.json"
BACKUP_KEY = "_buddy_picker_original_userID"


def read_config() -> dict:
    if CLAUDE_JSON.exists():
        return json.loads(CLAUDE_JSON.read_text(encoding="utf-8"))
    return {}


def write_config(cfg: dict) -> None:
    CLAUDE_JSON.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


def get_current_uid() -> str:
    return read_config().get("userID", "")


def apply_uid(uid: str) -> None:
    """Write *uid* as the new userID and remove the companion block."""
    cfg = read_config()
    if BACKUP_KEY not in cfg and "userID" in cfg:
        cfg[BACKUP_KEY] = cfg["userID"]
    cfg["userID"] = uid
    cfg.pop("companion", None)
    write_config(cfg)


def restore_uid() -> None:
    """Restore the original userID from backup."""
    cfg = read_config()
    original = cfg.pop(BACKUP_KEY, None)
    if original:
        cfg["userID"] = original
        cfg.pop("companion", None)
        write_config(cfg)
        print(f"  Restored original userID: {original[:16]}...")
        print("  Companion cleared. Restart Claude Code and run /buddy.")
    else:
        print("  No backup found. Nothing to restore.")
