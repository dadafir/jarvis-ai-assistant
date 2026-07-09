"""
Settings Window — A CTkToplevel dialog for configuring Jarvis.

Changes take effect immediately AND are saved to config.json.
"""

from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk


class SettingsWindow(ctk.CTkToplevel):
    """
    Modal settings window.  Accepts callbacks so the parent GUI can
    react immediately when a setting is changed.
    """

    def __init__(
        self,
        parent: ctk.CTk,
        config: "ConfigManager",           # type: ignore[name-defined]
        available_models: list[str],
        on_apply: Callable[[dict], None],  # called with {key: new_value, ...}
    ) -> None:
        super().__init__(parent)
        self.title("Jarvis Settings")
        self.geometry("520x640")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.grab_set()   # Modal — blocks interaction with parent

        self._config       = config
        self._models       = available_models if available_models else ["llama3"]
        self._on_apply     = on_apply

        # Widget vars (populated in _build)
        self._var_model:        ctk.StringVar
        self._var_vision_model: ctk.StringVar
        self._var_voice:        ctk.BooleanVar
        self._var_speed:        ctk.IntVar
        self._txt_prompt:       ctk.CTkTextbox
        self._txt_wake:         ctk.CTkEntry

        self._build()
        self._load_current()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)

        row = 0

        # ── Header ────────────────────────────────────────────────────────────
        ctk.CTkLabel(
            self, text="J.A.R.V.I.S — Settings",
            font=("Helvetica", 18, "bold"),
            text_color="#00BFFF",
        ).grid(row=row, column=0, padx=20, pady=(20, 5), sticky="w")
        row += 1

        ctk.CTkLabel(
            self, text="Changes take effect immediately and are saved to config.json.",
            font=("Helvetica", 11), text_color="gray",
        ).grid(row=row, column=0, padx=20, pady=(0, 15), sticky="w")
        row += 1

        # ── AI Model ──────────────────────────────────────────────────────────
        row = self._section(row, "AI Model")

        ctk.CTkLabel(self, text="Primary model (text chat):").grid(
            row=row, column=0, padx=20, pady=(4, 0), sticky="w")
        row += 1
        self._var_model = ctk.StringVar()
        ctk.CTkOptionMenu(
            self, variable=self._var_model,
            values=self._models,
            width=300,
        ).grid(row=row, column=0, padx=20, pady=(2, 8), sticky="w")
        row += 1

        ctk.CTkLabel(self, text="Vision model (screen analysis):").grid(
            row=row, column=0, padx=20, pady=(4, 0), sticky="w")
        row += 1
        self._var_vision_model = ctk.StringVar()
        vision_models = [m for m in self._models if "llava" in m.lower()] or ["llava"]
        ctk.CTkOptionMenu(
            self, variable=self._var_vision_model,
            values=["llava", "llava:7b", "llava:13b", *vision_models],
            width=300,
        ).grid(row=row, column=0, padx=20, pady=(2, 8), sticky="w")
        row += 1

        # ── Voice ─────────────────────────────────────────────────────────────
        row = self._section(row, "Voice")

        voice_row = ctk.CTkFrame(self, fg_color="transparent")
        voice_row.grid(row=row, column=0, padx=20, pady=(4, 8), sticky="w")
        self._var_voice = ctk.BooleanVar()
        ctk.CTkSwitch(
            voice_row, text="Enable voice (TTS + STT)",
            variable=self._var_voice,
        ).pack(side="left")
        row += 1

        ctk.CTkLabel(self, text="Speech speed (words per minute):").grid(
            row=row, column=0, padx=20, pady=(4, 0), sticky="w")
        row += 1
        self._var_speed = ctk.IntVar()
        speed_frame = ctk.CTkFrame(self, fg_color="transparent")
        speed_frame.grid(row=row, column=0, padx=20, pady=(2, 8), sticky="w")
        speed_slider = ctk.CTkSlider(
            speed_frame, from_=100, to=300,
            variable=self._var_speed, width=260,
            number_of_steps=20,
        )
        speed_slider.pack(side="left")
        self._speed_label = ctk.CTkLabel(speed_frame, text="175 wpm", width=70)
        self._speed_label.pack(side="left", padx=(10, 0))
        self._var_speed.trace_add("write", self._on_speed_change)
        row += 1

        # ── Personality ───────────────────────────────────────────────────────
        row = self._section(row, "AI Personality (System Prompt)")

        self._txt_prompt = ctk.CTkTextbox(self, height=100, wrap="word",
                                          font=("Consolas", 12))
        self._txt_prompt.grid(row=row, column=0, padx=20, pady=(4, 8), sticky="ew")
        row += 1

        # ── Wake Words ────────────────────────────────────────────────────────
        row = self._section(row, "Wake Words (comma-separated)")

        self._txt_wake = ctk.CTkEntry(self, placeholder_text="hey jarvis, jarvis",
                                      width=400)
        self._txt_wake.grid(row=row, column=0, padx=20, pady=(4, 12), sticky="w")
        row += 1

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=row, column=0, padx=20, pady=(0, 20), sticky="ew")
        btn_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            btn_frame, text="Save & Apply",
            fg_color="#0066CC", hover_color="#0055AA",
            command=self._save,
        ).grid(row=0, column=0, padx=(0, 8), sticky="ew")

        ctk.CTkButton(
            btn_frame, text="Cancel",
            fg_color="#333333", hover_color="#444444",
            command=self.destroy,
        ).grid(row=0, column=1, padx=(8, 0), sticky="ew")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _section(self, row: int, title: str) -> int:
        """Render a section header and return next row number."""
        ctk.CTkLabel(
            self, text=title,
            font=("Helvetica", 13, "bold"),
            text_color="#00BFFF",
        ).grid(row=row, column=0, padx=20, pady=(10, 2), sticky="w")
        return row + 1

    def _on_speed_change(self, *_) -> None:
        self._speed_label.configure(text=f"{self._var_speed.get()} wpm")

    def _load_current(self) -> None:
        """Populate widgets with values from the current config."""
        cfg = self._config

        model = cfg.get("model", "llama3")
        if model not in self._models:
            self._models.insert(0, model)
        self._var_model.set(model)

        self._var_vision_model.set(cfg.get("vision_model", "llava"))
        self._var_voice.set(cfg.get("voice_enabled", True))
        self._var_speed.set(cfg.get("voice_speed", 175))

        self._txt_prompt.delete("0.0", "end")
        self._txt_prompt.insert("0.0", cfg.get("system_prompt", ""))

        wake = ", ".join(cfg.get("wake_words", ["hey jarvis", "jarvis"]))
        self._txt_wake.delete(0, "end")
        self._txt_wake.insert(0, wake)

    def _save(self) -> None:
        """Persist and apply all settings."""
        wake_raw = self._txt_wake.get().strip()
        wake_list = [w.strip().lower() for w in wake_raw.split(",") if w.strip()]

        new_values = {
            "model":         self._var_model.get(),
            "vision_model":  self._var_vision_model.get(),
            "voice_enabled": self._var_voice.get(),
            "voice_speed":   self._var_speed.get(),
            "system_prompt": self._txt_prompt.get("0.0", "end").strip(),
            "wake_words":    wake_list,
        }

        for k, v in new_values.items():
            self._config.set(k, v)
        self._config.save()

        self._on_apply(new_values)
        self.destroy()
