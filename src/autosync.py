"""Auto-sync whitelist management for skill-upload."""
import json
import os
from pathlib import Path
from typing import List, Dict, Optional


WHITELIST_FILE = Path.home() / ".skill-upload" / "auto-sync.json"


def get_whitelist() -> Dict:
    """Load whitelist configuration."""
    if not WHITELIST_FILE.exists():
        return {"enabled": []}

    try:
        with open(WHITELIST_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"enabled": []}


def save_whitelist(config: Dict):
    """Save whitelist configuration."""
    WHITELIST_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(WHITELIST_FILE, 'w') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def normalize_path(path: str) -> str:
    """Normalize path for comparison."""
    # Expand ~ and resolve to absolute path
    expanded = Path(path).expanduser().resolve()
    return str(expanded)


def add_to_whitelist(path: str) -> bool:
    """
    Add a path to whitelist.

    Args:
        path: Local directory path or GitHub URL

    Returns:
        True if added, False if already exists
    """
    config = get_whitelist()
    normalized = normalize_path(path)

    # Check if already exists
    for item in config["enabled"]:
        if normalize_path(item) == normalized:
            return False

    config["enabled"].append(path)
    save_whitelist(config)
    return True


def remove_from_whitelist(path: str) -> bool:
    """
    Remove a path from whitelist.

    Args:
        path: Local directory path or GitHub URL (can be partial match)

    Returns:
        True if removed, False if not found
    """
    config = get_whitelist()

    # Try exact match first
    for item in config["enabled"]:
        if item == path or normalize_path(item) == normalize_path(path):
            config["enabled"].remove(item)
            save_whitelist(config)
            return True

    # Try partial match (by name)
    for item in config["enabled"]:
        if path in item:
            config["enabled"].remove(item)
            save_whitelist(config)
            return True

    return False


def list_whitelist() -> List[str]:
    """Return list of whitelisted paths."""
    config = get_whitelist()
    return config.get("enabled", [])


def is_in_whitelist(path: str) -> bool:
    """Check if a path is in whitelist."""
    config = get_whitelist()
    normalized = normalize_path(path)

    for item in config["enabled"]:
        if normalize_path(item) == normalized:
            return True

    return False


def init_whitelist_with_defaults():
    """Initialize whitelist with default entries."""
    if WHITELIST_FILE.exists():
        return

    defaults = {
        "enabled": [
            "~/.agents/skills/mp-editor"
        ]
    }

    save_whitelist(defaults)
    return defaults
