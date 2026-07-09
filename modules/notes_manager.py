"""
Notes Manager — Quick note-taking integrated with MemoryStore.
"""

from __future__ import annotations

from modules.memory_store import MemoryStore
from rich.console import Console
from rich.table import Table

console = Console(force_terminal=True)


class NotesManager:
    """Add, view, and delete quick notes stored persistently."""

    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    def add(self, text: str) -> str:
        idx = self._store.add_note(text)
        return f"[Notes] ✓ Note #{idx} saved."

    def show(self) -> None:
        notes = self._store.get_notes()
        if not notes:
            console.print(
                "[yellow]No notes yet. Use 'note: <text>' to add one.[/yellow]"
            )
            return
        table = Table(
            title="📝 Notes",
            border_style="bright_blue",
            show_lines=True,
        )
        table.add_column("#", style="dim cyan", width=4, justify="right")
        table.add_column("Content", style="white", min_width=40)
        table.add_column("Saved", style="dim", width=18)
        for n in notes:
            table.add_row(str(n["id"]), n["text"], n["timestamp"])
        console.print(table)

    def delete(self, index: int) -> str:
        if self._store.delete_note(index):
            return f"[Notes] Note #{index} deleted."
        return f"[Notes] No note found with id #{index}."

    def clear(self) -> str:
        self._store.clear_notes()
        return "[Notes] All notes cleared."
