"""
Memory Store — Persistent conversation history and notes.

Data is saved in ~/.jarvis/memory.json so Jarvis remembers
across sessions.
"""

from __future__ import annotations

import json
import datetime
from pathlib import Path
from typing import Any

JARVIS_DIR = Path.home() / ".jarvis"
MEMORY_FILE = JARVIS_DIR / "memory.json"


def _ensure_dir() -> None:
    JARVIS_DIR.mkdir(parents=True, exist_ok=True)


class MemoryStore:
    """Manages persistent storage for conversation history and notes."""

    def __init__(self) -> None:
        _ensure_dir()
        self._data: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        if MEMORY_FILE.exists():
            try:
                return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"sessions": [], "notes": []}

    def _save(self) -> None:
        tmp = MEMORY_FILE.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(MEMORY_FILE)

    # ── Conversation sessions ────────────────────────────────────────────────

    def save_session(self, history: list[dict[str, str]]) -> None:
        """Append the current conversation to saved sessions (keeps last 10)."""
        if not history:
            return
        sessions: list = self._data.setdefault("sessions", [])
        sessions.append(
            {
                "timestamp": datetime.datetime.now().isoformat(),
                "messages": history,
            }
        )
        self._data["sessions"] = sessions[-10:]
        self._save()

    def load_last_session(self) -> list[dict[str, str]]:
        """Return messages from the most recent saved session."""
        sessions: list = self._data.get("sessions", [])
        if sessions:
            return list(sessions[-1].get("messages", []))
        return []

    def session_count(self) -> int:
        return len(self._data.get("sessions", []))

    # ── Notes ────────────────────────────────────────────────────────────────

    def add_note(self, text: str) -> int:
        """Save a note. Returns 1-based index of the new note."""
        notes: list = self._data.setdefault("notes", [])
        notes.append(
            {
                "id": len(notes) + 1,
                "text": text.strip(),
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            }
        )
        self._save()
        return len(notes)

    def get_notes(self) -> list[dict[str, Any]]:
        return list(self._data.get("notes", []))

    def delete_note(self, index: int) -> bool:
        """Delete note by 1-based index. Returns True if successful."""
        notes: list = self._data.get("notes", [])
        if 1 <= index <= len(notes):
            notes.pop(index - 1)
            for i, n in enumerate(notes, 1):
                n["id"] = i
            self._data["notes"] = notes
            self._save()
            return True
        return False

    def clear_notes(self) -> None:
        self._data["notes"] = []
        self._save()
