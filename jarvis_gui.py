"""
Jarvis GUI Controller — A modern desktop UI using CustomTkinter.
Replaces the terminal-based controller.
"""

from __future__ import annotations

import threading
import time
import re
import base64
import io
from typing import Optional, Callable

import customtkinter as ctk

from modules.ai_engine import AIEngine
from modules.alarm_manager import AlarmManager
from modules.command_executor import CommandExecutor
from modules.config_manager import ConfigManager
from modules.memory_store import MemoryStore
from modules.notes_manager import NotesManager
from modules.system_info import SystemInfo
from modules.settings_window import SettingsWindow
from modules.tray_manager import TrayManager
from modules.voice_engine import VoiceEngine


class JarvisGUI(ctk.CTk):
    def __init__(
        self,
        model: str = "llama3",
        voice_enabled: bool = True,
        resume: bool = False,
    ):
        super().__init__()

        # --- Window Setup ---
        self.title("J.A.R.V.I.S")
        self.geometry("500x700")
        self.minsize(400, 600)
        self.attributes("-topmost", True)  # Floating window
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # --- Config (load first so modules use saved prefs) ---
        self.config_mgr = ConfigManager()

        # Override model from config if no explicit arg passed
        if model == "llama3" and self.config_mgr.get("model") != "llama3":
            model = self.config_mgr.get("model", "llama3")

        # --- Module Initialization ---
        self.memory = MemoryStore()
        self.ai = AIEngine(model=model)
        self.cmd = CommandExecutor()
        self.notes = NotesManager(self.memory)
        self.sysinfo = SystemInfo()
        self.voice = VoiceEngine() if voice_enabled else None
        self.alarms = AlarmManager(speak_cb=self._speak_text)
        
        self.is_listening = False
        self.is_running = True

        # System tray — minimize here instead of closing
        self.tray = TrayManager(
            on_show=self._show_window,
            on_hide=self._hide_window,
            on_quit=self._real_quit,
        )
        self.tray.start()

        if resume:
            history = self.memory.load_last_session()
            if history:
                self.ai.load_history(history)

        # --- UI Components ---
        self._build_ui()
        
        # Load history into UI
        if self.ai.conversation_history:
            for msg in self.ai.conversation_history:
                role = "User" if msg["role"] == "user" else "Jarvis"
                self._append_to_chat(f"[{role}]: {msg['content']}")
        else:
            self._append_to_chat("[Jarvis]: Hello, I am Jarvis. How can I help you today?")
            self._speak_text("Hello, I am Jarvis. How can I help you today?")

        # Start wake word listener thread
        if self.voice and self.voice.stt_available:
            self.wake_thread = threading.Thread(target=self._continuous_listen, daemon=True)
            self.wake_thread.start()

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _build_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Top bar: title + settings gear
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.grid(row=0, column=0, padx=20, pady=(15, 0), sticky="ew")
        top_bar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            top_bar,
            text="J.A.R.V.I.S",
            font=("Helvetica", 20, "bold"),
            text_color="#00BFFF",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            top_bar,
            text="Settings",
            width=80,
            font=("Helvetica", 12),
            fg_color="#1a1a2e",
            hover_color="#0066CC",
            command=self._open_settings,
        ).grid(row=0, column=1, sticky="e")

        # Chat History
        self.chat_box = ctk.CTkTextbox(
            self,
            wrap="word",
            state="disabled",
            font=("Consolas", 14)
        )
        self.chat_box.grid(row=1, column=0, padx=20, pady=(10, 10), sticky="nsew")
        self.grid_rowconfigure(1, weight=1)

        # Status Label
        self.status_label = ctk.CTkLabel(
            self,
            text="[Idle] Idle",
            font=("Helvetica", 16, "bold"),
            text_color="#00FF00"
        )
        self.status_label.grid(row=2, column=0, padx=20, pady=(0, 10))

        # Bottom Frame (Input + Mic)
        self.bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.bottom_frame.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.bottom_frame.grid_columnconfigure(0, weight=1)

        self.input_entry = ctk.CTkEntry(
            self.bottom_frame,
            placeholder_text="Type a command...",
            font=("Helvetica", 14)
        )
        self.input_entry.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        self.input_entry.bind("<Return>", lambda e: self._handle_text_input())

        self.mic_btn = ctk.CTkButton(
            self.bottom_frame,
            text="Mic",
            width=60,
            font=("Helvetica", 13, "bold"),
            fg_color="#003366",
            hover_color="#0066CC",
            command=self._manual_listen_trigger
        )
        self.mic_btn.grid(row=0, column=1)

    # --- UI Updaters ---
    def _update_status(self, state: str):
        """Thread-safe status update — also syncs tray tooltip."""
        colors = {
            "Idle": "#00FF00",
            "Listening": "#00BFFF",
            "Thinking": "#FFD700",
            "Thinking (Vision)": "#FFD700",
            "Speaking": "#DA70D6"
        }
        icons = {
            "Idle": "Green",
            "Listening": "Blue",
            "Thinking": "Gold",
            "Thinking (Vision)": "Gold",
            "Speaking": "Purple"
        }
        label_icons = {
            "Idle": "[Idle]",
            "Listening": "[Listening]",
            "Thinking": "[Thinking]",
            "Thinking (Vision)": "[Vision]",
            "Speaking": "[Speaking]"
        }
        color = colors.get(state, "white")
        label_icon = label_icons.get(state, "[ ]")

        def _set():
            self.status_label.configure(
                text=f"{label_icon} {state}",
                text_color=color
            )
        self.after(0, _set)
        self.tray.set_tooltip(f"J.A.R.V.I.S  —  {state}")

    def _append_to_chat(self, text: str):
        """Thread-safe chat append."""
        def _append():
            self.chat_box.configure(state="normal")
            self.chat_box.insert("end", text + "\n\n")
            self.chat_box.configure(state="disabled")
            self.chat_box.see("end")
        self.after(0, _append)

    # --- Core Logic ---
    def _handle_text_input(self):
        text = self.input_entry.get().strip()
        if not text:
            return
        self.input_entry.delete(0, "end")
        self._append_to_chat(f"[User]: {text}")
        
        # Process in background to avoid freezing UI
        threading.Thread(target=self._process_command, args=(text,), daemon=True).start()

    def _manual_listen_trigger(self):
        if not self.voice or not self.voice.stt_available:
            self._append_to_chat("[System]: Voice recognition is unavailable.")
            return
        
        self.is_listening = True
        self._update_status("Listening")
        
        def _listen():
            heard = self.voice.listen(timeout=5, phrase_limit=10)
            self.is_listening = False
            
            if heard:
                self._append_to_chat(f"[User (Voice)]: {heard}")
                self._process_command(heard)
            else:
                self._update_status("Idle")
                
        threading.Thread(target=_listen, daemon=True).start()

    def _continuous_listen(self):
        """Background loop for wake-word detection."""
        while self.is_running:
            if not self.is_listening:
                try:
                    # Short timeout so it doesn't block forever and can be interrupted
                    heard = self.voice.listen(timeout=1, phrase_limit=10)
                    if heard:
                        lower_heard = heard.lower()
                        # Check for wake words
                        if "hey jarvis" in lower_heard or "jarvis" in lower_heard:
                            # Extract command after wake word if present
                            command = re.sub(r".*(hey jarvis|jarvis)\b", "", lower_heard, flags=re.IGNORECASE).strip()
                            
                            if command:
                                self.after(0, lambda h=heard: self._append_to_chat(f"[User (Voice)]: {h}"))
                                self._process_command(command)
                            else:
                                # Just said "Jarvis", acknowledge and listen again
                                self._update_status("Listening")
                                self._speak_text("Yes sir?")
                                
                                self.is_listening = True
                                followup = self.voice.listen(timeout=5, phrase_limit=10)
                                self.is_listening = False
                                
                                if followup:
                                    self.after(0, lambda f=followup: self._append_to_chat(f"[User (Voice)]: {f}"))
                                    self._process_command(followup)
                                else:
                                    self._update_status("Idle")
                except Exception:
                    pass
            time.sleep(0.1)

    def _process_command(self, text: str):
        lower = text.lower().strip()
        
        # --- Meta commands ---
        if lower in ("quit", "exit", "bye", "goodbye"):
            self._speak_text("Goodbye sir!", on_complete=self.destroy)
            return
            
        if lower in ("clear history", "reset", "new chat"):
            self.ai.clear_history()
            self._append_to_chat("[System]: Conversation history cleared.")
            return

        self._update_status("Thinking")

        # --- System Command vs AI ---
        if self.cmd.is_system_command(lower):
            result = self.cmd.execute(text)
            self._append_to_chat(f"[Jarvis]: {result}")
            self._speak_text(result)
            return
            
        # Alarms
        if lower.startswith(("set alarm", "alarm ")):
            rest = re.sub(r"^(set alarm|alarm)\s*(for|in)?\s*", "", lower).strip()
            if rest.startswith("in ") or re.search(r"\d+\s*(min|hour|sec)", rest):
                res = self.alarms.set_alarm_in(rest)
            else:
                res = self.alarms.set_alarm(rest)
            self._append_to_chat(f"[Jarvis]: {res}")
            self._speak_text(res)
            return

        if lower.startswith(("remind me", "reminder", "set reminder")):
            rest = re.sub(r"^(remind me|reminder|set reminder)\s*", "", lower).strip()
            res = self.alarms.set_reminder(rest)
            self._append_to_chat(f"[Jarvis]: {res}")
            self._speak_text(res)
            return

        if lower in ("alarms", "reminders", "show alarms"):
            # Console output not ideal for GUI, but skipping full list impl for brevity
            self._append_to_chat("[Jarvis]: Check console for alarm list.")
            self.alarms.list_all()
            self._update_status("Idle")
            return

        # --- Screen Vision ---
        vision_triggers = ("look at my screen", "what's on my screen", "what is on my screen", "what do you see", "vision:")
        if any(lower.startswith(trigger) for trigger in vision_triggers):
            self._update_status("Thinking (Vision)")
            
            b64_image = self._capture_screen_b64()
            if not b64_image:
                res = "[System]: Could not capture screen. Is Pillow installed?"
                self._append_to_chat(res)
                self._speak_text(res)
                return
                
            response = self.ai.vision_chat(text, image_base64=b64_image)
            self._append_to_chat(f"[Jarvis]: {response}")
            self._speak_text(response[:200])
            return

        # --- AI Inference ---
        # Note: self.ai.chat streams to stdout. For GUI, we capture the return value.
        # It might take a few seconds, which is why this is in a thread.
        response = self.ai.chat(text)
        self._append_to_chat(f"[Jarvis]: {response}")
        
        # Speak response (first 200 chars to avoid rambling)
        self._speak_text(response[:200])

    def _speak_text(self, text: str, on_complete: Optional[Callable] = None):
        """Wrapper to update status around speech."""
        if not self.voice or not self.voice.tts_available:
            self._update_status("Idle")
            if on_complete:
                on_complete()
            return

        self._update_status("Speaking")
        
        def _done():
            self._update_status("Idle")
            if on_complete:
                self.after(0, on_complete)
                
        self.voice.speak(text, on_complete=_done)

    def _on_closing(self):
        """Pressing X hides the window to tray instead of quitting."""
        self._hide_window()

    def _show_window(self):
        """Restore Jarvis window from tray."""
        self.after(0, self.deiconify)
        self.after(0, self.lift)
        self.after(0, self.focus_force)

    def _hide_window(self):
        """Send Jarvis to the system tray."""
        self.after(0, self.withdraw)

    def _real_quit(self):
        """Fully quit Jarvis from the tray menu."""
        self.is_running = False
        self.alarms.shutdown()
        self.tray.stop()
        if self.ai.conversation_history:
            self.memory.save_session(self.ai.conversation_history)
        self.after(0, self.destroy)

    # ── Settings ──────────────────────────────────────────────────────────────

    def _open_settings(self) -> None:
        """Open the settings dialog."""
        models = self.ai.list_models() or [self.ai.model]
        SettingsWindow(
            parent=self,
            config=self.config_mgr,
            available_models=models,
            on_apply=self._on_apply_settings,
        )

    def _on_apply_settings(self, new_values: dict) -> None:
        """Apply settings changes to live modules immediately."""
        if "model" in new_values:
            self.ai.model = new_values["model"]

        if "system_prompt" in new_values:
            self.ai.set_system_prompt(new_values["system_prompt"])

        if "voice_speed" in new_values and self.voice:
            self.voice.set_rate(new_values["voice_speed"])

        if "wake_words" in new_values:
            # The continuous_listen loop reads this list each iteration
            self._wake_words = new_values["wake_words"]

        self._append_to_chat("[System]: Settings saved and applied.")

    def _capture_screen_b64(self) -> Optional[str]:
        """Takes a screenshot and returns it as a base64 encoded JPEG string."""
        try:
            from PIL import ImageGrab
            screenshot = ImageGrab.grab()
            
            # Resize image slightly to speed up inference and save token space
            max_size = (1280, 720)
            screenshot.thumbnail(max_size)
            
            buffer = io.BytesIO()
            screenshot.save(buffer, format="JPEG", quality=70)
            return base64.b64encode(buffer.getvalue()).decode("utf-8")
        except Exception as e:
            print(f"[Vision Error] {e}")
            return None

def run_gui(model="llama3", voice_enabled=True, resume=False):
    app = JarvisGUI(model=model, voice_enabled=voice_enabled, resume=resume)
    app.mainloop()
