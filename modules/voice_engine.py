"""
Voice Engine Module - Optional speech input/output.

Text-to-Speech (TTS) via pyttsx3 (offline, no API key).
Speech-to-Text (STT) via SpeechRecognition + PyAudio (uses Google STT by default).

Both dependencies are optional - the module gracefully degrades if missing.
"""

from __future__ import annotations

import re
import threading
from typing import Any, Optional, Callable


class VoiceEngine:
    """Provides text-to-speech and speech-to-text capabilities."""

    def __init__(self) -> None:
        self._tts_available: bool = False
        self._stt_available: bool = False
        self._pyttsx3_module: Any = None
        self._sr_module: Any = None
        self._recognizer: Any = None
        self._tts_rate: int = 175  # words per minute
        self._init_tts()
        self._init_stt()

    # -- Initialisation -------------------------------------------------------

    def _init_tts(self) -> None:
        """Try to initialise the pyttsx3 TTS engine."""
        try:
            import pyttsx3  # type: ignore[import-untyped]

            self._pyttsx3_module = pyttsx3
            # Quick test to make sure it can init
            engine = pyttsx3.init()
            engine.stop()
            self._tts_available = True
        except Exception:
            self._tts_available = False

    def _init_stt(self) -> None:
        """Try to initialise the SpeechRecognition recognizer."""
        try:
            import speech_recognition as sr  # type: ignore[import-untyped]

            self._sr_module = sr
            self._recognizer = sr.Recognizer()
            self._stt_available = True
        except ImportError:
            self._stt_available = False

    # -- Public API -----------------------------------------------------------

    @property
    def tts_available(self) -> bool:
        """Whether text-to-speech is available."""
        return self._tts_available

    @property
    def stt_available(self) -> bool:
        """Whether speech-to-text is available."""
        return self._stt_available

    def speak(self, text: str, on_complete: Optional[Callable] = None) -> None:
        """
        Speak the given text aloud using pyttsx3.
        Creates a fresh engine each call to avoid threading freeze issues.
        Runs in a background thread so it doesn't block the main loop.
        """
        if not self._tts_available or self._pyttsx3_module is None:
            return

        clean: str = self._strip_markup(text)
        pyttsx3_mod = self._pyttsx3_module

        def _run() -> None:
            try:
                engine = pyttsx3_mod.init()
                engine.setProperty("rate", self._tts_rate)
                voices = engine.getProperty("voices")
                if voices and len(voices) > 1:
                    engine.setProperty("voice", voices[1].id)
                engine.say(clean)
                engine.runAndWait()
                engine.stop()
            except Exception as e:
                print(f"[TTS Error] {e}")
            finally:
                if on_complete:
                    on_complete()

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

    def set_rate(self, rate: int) -> None:
        """Update the TTS speech rate (words per minute). Default is 175."""
        self._tts_rate = max(80, min(400, rate))


    def listen(self, timeout: int = 5, phrase_limit: int = 10) -> Optional[str]:
        """
        Listen to the microphone and return recognised text.

        Returns None if nothing was understood or STT is unavailable.
        """
        if not self._stt_available or self._sr_module is None or self._recognizer is None:
            return None

        sr = self._sr_module
        recognizer = self._recognizer

        try:
            with sr.Microphone() as source:
                print("[Mic] Listening...", flush=True)
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.listen(
                    source, timeout=timeout, phrase_time_limit=phrase_limit
                )

            print("[...] Recognising...", flush=True)
            text: str = recognizer.recognize_google(audio)
            return text

        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            print(f"[Error] Speech recognition service error: {e}")
            return None
        except sr.WaitTimeoutError:
            return None
        except Exception as e:
            print(f"[Error] Microphone error: {e}")
            return None

    # -- Helpers --------------------------------------------------------------

    @staticmethod
    def _strip_markup(text: str) -> str:
        """Remove Rich-style markup tags like [bold red]...[/bold red]."""
        return re.sub(r"\[/?[a-z ]+\]", "", text, flags=re.IGNORECASE)