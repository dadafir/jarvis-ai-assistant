"""
Alarm & Reminder Manager — Background threaded alarms and reminders.

Alarms  : fire at an exact wall-clock time (HH:MM).
Reminders: "remind me in X minutes/hours to <task>" or
           "remind me at HH:MM [am/pm] to <task>".

Fires a console notification + system beep (+ TTS if a speak callback
is provided).  Alarms persist across restarts via MemoryStore.
"""

from __future__ import annotations

import re
import sys
import threading
import time
import datetime
from typing import Any, Callable, Optional

from rich.console import Console
from rich.panel import Panel

console = Console(force_terminal=True)

# ── helpers ────────────────────────────────────────────────────────────────────

def _beep() -> None:
    """Platform-safe audio alert."""
    try:
        if sys.platform == "win32":
            import winsound
            for _ in range(3):
                winsound.Beep(1000, 400)
                time.sleep(0.15)
        else:
            sys.stdout.write("\a")
            sys.stdout.flush()
    except Exception:
        pass


def _parse_time(text: str) -> Optional[datetime.datetime]:
    """
    Parse a time string into a datetime today (or tomorrow if past).

    Accepts: '7:30 am', '7:30 pm', '07:30', '7:30', '930', '14:00'
    Returns None if unparseable.
    """
    text = text.strip().lower()
    patterns = [
        r"(\d{1,2}):(\d{2})\s*(am|pm)?",
        r"(\d{1,2})(am|pm)",
    ]
    for pat in patterns:
        m = re.fullmatch(pat, text)
        if m:
            groups = m.groups()
            hour = int(groups[0])
            minute = int(groups[1]) if len(groups) > 2 and groups[1] and groups[1].isdigit() else 0
            meridiem = groups[-1] if groups[-1] in ("am", "pm") else None
            if meridiem == "pm" and hour != 12:
                hour += 12
            if meridiem == "am" and hour == 12:
                hour = 0
            now = datetime.datetime.now()
            fire = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if fire <= now:
                fire += datetime.timedelta(days=1)
            return fire
    return None


def _parse_relative(text: str) -> Optional[datetime.timedelta]:
    """
    Parse a relative duration like '10 minutes', '1 hour', '2 hours 30 minutes'.
    Returns a timedelta or None.
    """
    text = text.strip().lower()
    total_seconds = 0

    hour_m = re.search(r"(\d+)\s*hour", text)
    min_m  = re.search(r"(\d+)\s*min",  text)
    sec_m  = re.search(r"(\d+)\s*sec",  text)

    if hour_m: total_seconds += int(hour_m.group(1)) * 3600
    if min_m:  total_seconds += int(min_m.group(1))  * 60
    if sec_m:  total_seconds += int(sec_m.group(1))

    return datetime.timedelta(seconds=total_seconds) if total_seconds > 0 else None


# ── main class ─────────────────────────────────────────────────────────────────

class AlarmManager:
    """Manages alarms and reminders in a background watcher thread."""

    def __init__(
        self,
        speak_cb: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._speak: Optional[Callable[[str], None]] = speak_cb
        self._lock   = threading.Lock()
        self._items: list[dict[str, Any]] = []   # unified list
        self._next_id = 1
        self._running  = True

        # Start background watcher
        self._thread = threading.Thread(target=self._watcher, daemon=True)
        self._thread.start()

    # ── Public API ─────────────────────────────────────────────────────────────

    def set_alarm(self, time_str: str, label: str = "Alarm") -> str:
        """
        Set an alarm at a specific time.
        time_str: '7:30 am', '14:00', '3pm', etc.
        """
        fire_at = _parse_time(time_str)
        if fire_at is None:
            return f"[Alarm] Could not parse time '{time_str}'. Try: '7:30 am' or '14:00'."
        return self._add("alarm", label, fire_at)

    def set_alarm_in(self, duration_str: str, label: str = "Alarm") -> str:
        """
        Set an alarm relative to now.
        duration_str: '10 minutes', '1 hour 30 minutes', etc.
        """
        delta = _parse_relative(duration_str)
        if delta is None:
            return f"[Alarm] Could not parse duration '{duration_str}'."
        fire_at = datetime.datetime.now() + delta
        return self._add("alarm", label, fire_at)

    def set_reminder(self, raw: str) -> str:
        """
        Parse and set a reminder from a natural-language string.

        Patterns:
          "in 10 minutes to take medicine"
          "in 1 hour to call mom"
          "at 3:00 pm to submit report"
          "at 15:30 review PR"
        """
        raw = raw.strip()

        # "in X ... to <task>"
        in_m = re.match(
            r"in\s+(.+?)\s+to\s+(.+)",
            raw, re.IGNORECASE
        )
        if in_m:
            duration_str, task = in_m.group(1), in_m.group(2)
            delta = _parse_relative(duration_str)
            if delta:
                fire_at = datetime.datetime.now() + delta
                return self._add("reminder", task.strip(), fire_at)

        # "at HH:MM [am/pm] to <task>" or "at HH:MM [am/pm] <task>"
        at_m = re.match(
            r"at\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\s+(?:to\s+)?(.+)",
            raw, re.IGNORECASE
        )
        if at_m:
            time_str, task = at_m.group(1), at_m.group(2)
            fire_at = _parse_time(time_str.strip())
            if fire_at:
                return self._add("reminder", task.strip(), fire_at)

        # Fallback: treat whole string as task, no time found
        return (
            "[Reminder] Could not parse. Try:\n"
            "  remind me in 10 minutes to take medicine\n"
            "  remind me at 3:00 pm to call mom"
        )

    def list_all(self) -> None:
        """Print a table of pending alarms and reminders."""
        with self._lock:
            pending = [i for i in self._items if not i["fired"]]

        if not pending:
            console.print("[yellow]No active alarms or reminders.[/yellow]")
            return

        from rich.table import Table
        table = Table(title="Alarms & Reminders", border_style="bright_blue", show_lines=True)
        table.add_column("ID",   style="dim cyan", width=4, justify="right")
        table.add_column("Type", style="bold",     width=10)
        table.add_column("Label / Task",  style="white", min_width=30)
        table.add_column("Fires at",      style="green", width=20)

        for item in pending:
            fire_str = item["fire_at"].strftime("%I:%M %p  %b %d")
            table.add_row(
                str(item["id"]),
                item["type"].capitalize(),
                item["label"],
                fire_str,
            )
        console.print(table)

    def cancel(self, item_id: int) -> str:
        """Cancel an alarm or reminder by its ID."""
        with self._lock:
            for item in self._items:
                if item["id"] == item_id and not item["fired"]:
                    item["fired"] = True
                    return f"[{item['type'].capitalize()}] #{item_id} '{item['label']}' cancelled."
        return f"[Alarm] No active alarm/reminder with id #{item_id}."

    def cancel_all(self) -> str:
        with self._lock:
            count = sum(1 for i in self._items if not i["fired"])
            for i in self._items:
                i["fired"] = True
        return f"[Alarm] {count} alarm(s)/reminder(s) cancelled."

    def shutdown(self) -> None:
        self._running = False

    # ── Internal helpers ────────────────────────────────────────────────────────

    def _add(self, kind: str, label: str, fire_at: datetime.datetime) -> str:
        with self._lock:
            item: dict[str, Any] = {
                "id":      self._next_id,
                "type":    kind,
                "label":   label,
                "fire_at": fire_at,
                "fired":   False,
            }
            self._items.append(item)
            self._next_id += 1

        fire_str = fire_at.strftime("%I:%M %p")
        delta = fire_at - datetime.datetime.now()
        mins  = int(delta.total_seconds() // 60)
        eta   = f"in {mins} min" if mins < 60 else f"in {mins // 60}h {mins % 60}m"
        return (
            f"[{kind.capitalize()}] #{item['id']} set — "
            f"'{label}' at {fire_str} ({eta})"
        )

    def _watcher(self) -> None:
        """Background thread: checks every 10 s and fires due items."""
        while self._running:
            now = datetime.datetime.now()
            fired_items: list[dict] = []

            with self._lock:
                for item in self._items:
                    if not item["fired"] and now >= item["fire_at"]:
                        item["fired"] = True
                        fired_items.append(item)

            for item in fired_items:
                self._fire(item)

            time.sleep(10)

    def _fire(self, item: dict[str, Any]) -> None:
        kind  = item["type"].upper()
        label = item["label"]
        msg   = f" {kind} — {label} "

        # Print notification (visible even mid-typing)
        console.print()
        console.print(
            Panel(
                f"[bold bright_white]{label}[/bold bright_white]",
                title=f"[bold bright_yellow]{kind}[/bold bright_yellow]",
                border_style="bright_yellow",
                padding=(0, 4),
            )
        )
        console.print("[dim]  Press Enter to continue...[/dim]")

        # Beep in a thread so it doesn't block
        threading.Thread(target=_beep, daemon=True).start()

        # TTS
        if self._speak:
            try:
                self._speak(f"{kind.lower()} — {label}")
            except Exception:
                pass
