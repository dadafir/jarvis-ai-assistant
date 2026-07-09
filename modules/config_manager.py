"""
Config Manager — Persistent settings for Jarvis.

Saves/loads user preferences from config.json in the project root.
All modules should read their defaults from here.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONFIG_FILE = Path(__file__).parent.parent / "config.json"

DEFAULTS: dict[str, Any] = {
    "model":            "llama3",
    "vision_model":     "llava",
    "voice_enabled":    True,
    "voice_speed":      175,
    "system_prompt": (
        "You are J.A.R.V.I.S. (Just A Rather Very Intelligent System), "
        "a helpful, witty, and highly capable AI desktop assistant. "
        "You assist with tasks, answer questions clearly, and engage in friendly "
        "conversation. Keep responses concise and practical. "
        "You run 100% locally on the user's machine — no cloud, no API keys."
    ),
    "wake_words":       ["hey jarvis", "jarvis"],
    "startup_message":  "Hello, I am Jarvis. How can I help you today?",
}


class ConfigManager:
    """Load, access, and persist Jarvis settings."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = dict(DEFAULTS)
        self._load()

    # ── IO ────────────────────────────────────────────────────────────────────

    def _load(self) -> None:
        """Merge saved config on top of defaults (missing keys use defaults)."""
        if CONFIG_FILE.exists():
            try:
                saved = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                self._data.update(saved)
            except Exception as e:
                print(f"[Config] Could not load config.json: {e}")

    def save(self) -> None:
        """Write current settings to config.json."""
        try:
            CONFIG_FILE.write_text(
                json.dumps(self._data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            print(f"[Config] Could not save config.json: {e}")

    # ── Access ────────────────────────────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def all(self) -> dict[str, Any]:
        return dict(self._data)
