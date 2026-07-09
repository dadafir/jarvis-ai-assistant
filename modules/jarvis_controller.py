"""
Jarvis Controller — The brain that ties all modules together.

Routes user input to CommandExecutor (system commands), AIEngine
(LLM conversations), NotesManager (notes), or SystemInfo (stats).
"""

from __future__ import annotations

import os
import re
import sys

# Force UTF-8 output on Windows
if sys.platform == "win32":
    os.system("chcp 65001 > nul 2>&1")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from modules.ai_engine import AIEngine
from modules.alarm_manager import AlarmManager
from modules.command_executor import CommandExecutor
from modules.memory_store import MemoryStore
from modules.notes_manager import NotesManager
from modules.system_info import SystemInfo
from modules.voice_engine import VoiceEngine
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console(force_terminal=True)


class Jarvis:
    """Main controller orchestrating AI, commands, voice, memory, and notes."""

    def __init__(
        self,
        model: str = "llama3",
        voice_enabled: bool = True,
        resume: bool = False,
    ) -> None:
        self.memory = MemoryStore()
        self.ai = AIEngine(model=model)
        self.cmd = CommandExecutor()
        self.notes = NotesManager(self.memory)
        self.sysinfo = SystemInfo()
        self.voice = VoiceEngine() if voice_enabled else None
        self.running = True
        # AlarmManager starts its background thread immediately
        self.alarms = AlarmManager(speak_cb=self._say)

        if resume:
            history = self.memory.load_last_session()
            if history:
                self.ai.load_history(history)
                console.print(
                    f"[dim]>> Resumed last session "
                    f"({len(history) // 2} exchanges loaded)[/dim]"
                )

    # ── Startup ──────────────────────────────────────────────────────────────

    def greet(self) -> None:
        banner = Text()
        banner.append("╔══════════════════════════════════════════╗\n", style="cyan")
        banner.append("║          ", style="cyan")
        banner.append("J.A.R.V.I.S  v2.0", style="bold bright_white")
        banner.append("             ║\n", style="cyan")
        banner.append("║    ", style="cyan")
        banner.append("Your Local AI Desktop Assistant", style="italic bright_cyan")
        banner.append("     ║\n", style="cyan")
        banner.append("╚══════════════════════════════════════════╝", style="cyan")
        console.print(Panel(banner, border_style="bright_blue", padding=(1, 2)))

        # Status row
        ollama_ok = self.ai.is_ollama_running()
        ok = lambda b: "[green]✓[/green]" if b else "[red]✗[/red]"
        models = self.ai.list_models() if ollama_ok else []

        console.print(
            f"  {ok(ollama_ok)}  Ollama  "
            + (
                f"[green]Running[/green]  Model: [bold]{self.ai.model}[/bold]"
                f"  Available: {', '.join(models[:5]) or 'none'}"
                if ollama_ok
                else "[red]Not running[/red]  —  start with [bold]ollama serve[/bold]"
            )
        )

        tts_ok = bool(self.voice and self.voice.tts_available)
        stt_ok = bool(self.voice and self.voice.stt_available)
        mem_ok = self.memory.session_count() > 0
        sys_ok = self.sysinfo.available

        console.print(
            f"  {ok(tts_ok)}  TTS      "
            + ("[green]Ready[/green]" if tts_ok else "[yellow]Unavailable[/yellow]")
        )
        console.print(
            f"  {ok(stt_ok)}  STT      "
            + ("[green]Ready[/green]" if stt_ok else "[yellow]Unavailable[/yellow]")
        )
        console.print(
            f"  {ok(sys_ok)}  psutil   "
            + (
                "[green]Ready[/green]  (system stats available)"
                if sys_ok
                else "[yellow]Not installed[/yellow]  (run: pip install psutil)"
            )
        )
        console.print(
            f"  [cyan]✦[/cyan]  Memory   "
            + f"[dim]{self.memory.session_count()} saved session(s) | "
            f"{len(self.memory.get_notes())} note(s)[/dim]"
        )
        console.print()
        console.print(
            "  [dim]Type your command or question. "
            "[bold]help[/bold] for commands, [bold]quit[/bold] to exit.[/dim]\n"
        )

    # ── Main loop ────────────────────────────────────────────────────────────

    def run(self) -> None:
        self.greet()
        while self.running:
            try:
                user_input = console.input(
                    "[bold bright_green]Jarvis ❯ [/bold bright_green]"
                ).strip()
                if not user_input:
                    continue
                self._handle(user_input)
                console.print()
            except KeyboardInterrupt:
                console.print(
                    "\n[dim]Interrupted. Type [bold]quit[/bold] to exit.[/dim]"
                )
            except EOFError:
                self.running = False

        self._on_exit()

    # ── Input routing ────────────────────────────────────────────────────────

    def _handle(self, text: str) -> None:
        lower = text.lower().strip()

        # ── Exit ─────────────────────────────────────────────────────────
        if lower in ("quit", "exit", "bye", "goodbye"):
            self._say("Goodbye sir!")
            self.running = False
            return

        # ── Help ─────────────────────────────────────────────────────────
        if lower == "help":
            self._show_help()
            return

        # ── Clear screen ─────────────────────────────────────────────────
        if lower == "clear":
            os.system("cls" if os.name == "nt" else "clear")
            return

        # ── Conversation controls ─────────────────────────────────────────
        if lower in ("clear history", "reset", "new chat"):
            self.ai.clear_history()
            console.print("[dim]>> Conversation history cleared.[/dim]")
            return

        if lower in ("save", "save session", "save chat"):
            self.memory.save_session(self.ai.conversation_history)
            console.print("[dim]>> Session saved.[/dim]")
            return

        if lower in ("load", "load last", "resume last"):
            hist = self.memory.load_last_session()
            if hist:
                self.ai.load_history(hist)
                console.print(
                    f"[dim]>> Loaded last session "
                    f"({len(hist) // 2} exchanges).[/dim]"
                )
            else:
                console.print("[yellow]No saved session found.[/yellow]")
            return

        # ── Voice input ───────────────────────────────────────────────────
        if lower in ("listen", "voice"):
            self._voice_input()
            return

        # ── Model management ──────────────────────────────────────────────
        if lower == "models":
            self._list_models()
            return

        if lower.startswith("use model ") or lower.startswith("model "):
            name = text.split(" ", 2)[-1].strip()
            self.ai.model = name
            console.print(f"[green]Switched to model: [bold]{name}[/bold][/green]")
            return

        # ── System stats ──────────────────────────────────────────────────
        if lower in ("stats", "system", "system info", "sysinfo", "status"):
            console.print(
                Panel(
                    self.sysinfo.summary(),
                    title="System Stats",
                    border_style="bright_blue",
                )
            )
            return

        if lower in ("top", "processes", "top processes"):
            console.print(self.sysinfo.top_processes())
            return

        if lower in ("cpu",):
            console.print(self.sysinfo.cpu())
            return

        if lower in ("ram", "memory usage"):
            console.print(self.sysinfo.ram())
            return

        if lower in ("disk", "disk usage", "storage"):
            console.print(self.sysinfo.disk())
            return

        if lower in ("battery", "batt"):
            console.print(self.sysinfo.battery())
            return

        # ── Notes ─────────────────────────────────────────────────────────
        if lower.startswith("note: ") or lower.startswith("note "):
            note_text = text[text.index(":") + 1:].strip() if ":" in text else text[5:].strip()
            console.print(self.notes.add(note_text))
            return

        if lower in ("notes", "my notes", "show notes", "list notes"):
            self.notes.show()
            return

        if lower.startswith("delete note "):
            try:
                idx = int(lower.split("delete note ", 1)[1].strip())
                console.print(self.notes.delete(idx))
            except ValueError:
                console.print("[yellow]Usage: delete note <number>[/yellow]")
            return

        if lower in ("clear notes", "delete all notes"):
            console.print(self.notes.clear())
            return

        # ── Alarms ───────────────────────────────────────────────────────
        # "set alarm for 7:30 am" / "set alarm in 10 minutes"
        if lower.startswith(("set alarm", "alarm ")):
            rest = re.sub(r"^(set alarm|alarm)\s*(for|in)?\s*", "", lower).strip()
            if rest.startswith("in ") or re.search(r"\d+\s*(min|hour|sec)", rest):
                console.print(self.alarms.set_alarm_in(rest))
            else:
                console.print(self.alarms.set_alarm(rest))
            return

        # "remind me in 10 minutes to take medicine"
        # "remind me at 3pm to call mom"
        if lower.startswith(("remind me", "reminder", "set reminder")):
            rest = re.sub(r"^(remind me|reminder|set reminder)\s*", "", lower).strip()
            console.print(self.alarms.set_reminder(rest))
            return

        if lower in ("alarms", "reminders", "show alarms", "list alarms",
                     "show reminders", "list reminders"):
            self.alarms.list_all()
            return

        if lower.startswith("cancel alarm ") or lower.startswith("cancel reminder "):
            try:
                idx = int(lower.split()[-1])
                console.print(self.alarms.cancel(idx))
            except ValueError:
                console.print("[yellow]Usage: cancel alarm <number>[/yellow]")
            return

        if lower in ("cancel all alarms", "cancel all reminders", "clear alarms"):
            console.print(self.alarms.cancel_all())
            return

        # ── System command vs AI ──────────────────────────────────────────
        if self.cmd.is_system_command(lower):
            result = self.cmd.execute(text)
            console.print(result)
            self._say(result)
        else:
            console.print("[bold bright_cyan]Jarvis:[/bold bright_cyan] ", end="")
            response = self.ai.chat(text)
            self._say(response[:200])

    # ── Voice helpers ─────────────────────────────────────────────────────────

    def _say(self, text: str) -> None:
        if self.voice and self.voice.tts_available:
            self.voice.speak(text)

    def _voice_input(self) -> None:
        if not self.voice or not self.voice.stt_available:
            console.print(
                "[yellow]Voice input unavailable. "
                "Install SpeechRecognition + PyAudio.[/yellow]"
            )
            return
        heard = self.voice.listen()
        if heard:
            console.print(f'[dim][Mic] You said: "{heard}"[/dim]')
            self._handle(heard)
        else:
            console.print("[yellow]Didn't catch that. Try again.[/yellow]")

    # ── Exit handler ──────────────────────────────────────────────────────────

    def _on_exit(self) -> None:
        self.alarms.shutdown()
        if self.ai.conversation_history:
            self.memory.save_session(self.ai.conversation_history)
            console.print("[dim]>> Session auto-saved.[/dim]")
        console.print("[cyan]Goodbye![/cyan]")

    # ── Model listing ─────────────────────────────────────────────────────────

    def _list_models(self) -> None:
        models = self.ai.list_models()
        if not models:
            console.print("[yellow]No models found. Is Ollama running?[/yellow]")
            return
        table = Table(title="Available Models", border_style="bright_blue")
        table.add_column("Model", style="white")
        table.add_column("Active", style="green", justify="center")
        for m in models:
            table.add_row(m, "✓" if m == self.ai.model else "")
        console.print(table)

    # ── Help ──────────────────────────────────────────────────────────────────

    def _show_help(self) -> None:
        help_text = """\
[bold bright_cyan]━━━ System Commands ━━━[/bold bright_cyan]
  open <app/site>          Open app or website (chrome, youtube, discord…)
  close <app>              Close a running application
  search for <query>       Google search
  weather [in <city>]      Live weather info
  screenshot               Save screenshot to Desktop
  time / date              Current time or date
  ip / network             Network info
  ping <host>              Ping a host
  volume up/down/mute      Adjust system volume
  lock / sleep / shutdown  Power controls

[bold bright_cyan]━━━ System Stats ━━━[/bold bright_cyan]
  stats / system           CPU, RAM, Disk & Battery overview
  cpu / ram / disk         Individual stat
  battery                  Battery status
  top / processes          Top CPU-consuming processes

[bold bright_cyan]━━━ Notes ━━━[/bold bright_cyan]
  note: <text>             Save a note
  notes                    List all notes
  delete note <n>          Delete note by number
  clear notes              Delete all notes

[bold bright_cyan]━━━ Alarms & Reminders ━━━[/bold bright_cyan]
  set alarm for 7:30 am    Set alarm at a specific time
  set alarm in 10 minutes  Set alarm after a duration
  remind me in 20 min to <task>     Reminder in relative time
  remind me at 3:00 pm to <task>    Reminder at exact time
  alarms / reminders       List all active alarms & reminders
  cancel alarm <n>         Cancel by ID
  cancel all alarms        Cancel everything

[bold bright_cyan]━━━ Jarvis Controls ━━━[/bold bright_cyan]
  listen / voice           Switch to voice input
  models                   List Ollama models
  use model <name>         Switch LLM model
  save                     Save conversation to memory
  load last                Reload last saved session
  clear history            Reset conversation context
  clear                    Clear terminal
  help                     Show this help
  quit / exit              Exit Jarvis

[dim]Anything else → sent to the AI.[/dim]"""
        console.print(Panel(help_text, border_style="bright_blue", title="Help"))
