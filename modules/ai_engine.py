"""
AI Engine Module - Communicates with Ollama to run a local LLM.

Uses the Ollama REST API (http://localhost:11434) to send prompts
and stream responses. Supports a system prompt and persistent
conversation history.
"""

from __future__ import annotations

import json
import sys
from typing import Any, Optional

try:
    import requests
except ImportError:
    print("[Error] 'requests' package is required. Run: pip install requests")
    sys.exit(1)


OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"
DEFAULT_MODEL = "llama3"

JARVIS_SYSTEM_PROMPT = (
    "You are J.A.R.V.I.S. (Just A Rather Very Intelligent System), "
    "a helpful, witty, and highly capable AI desktop assistant. "
    "You assist with tasks, answer questions clearly, and engage in friendly "
    "conversation. Keep responses concise and practical. "
    "You run 100% locally on the user's machine — no cloud, no API keys."
)


class AIEngine:
    """Handles all communication with the Ollama local LLM."""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        system_prompt: Optional[str] = None,
    ) -> None:
        self.model: str = model
        self._system_prompt: str = system_prompt or JARVIS_SYSTEM_PROMPT
        self.conversation_history: list[dict[str, str]] = []

    # ── Status ───────────────────────────────────────────────────────────────

    def is_ollama_running(self) -> bool:
        try:
            response = requests.get(OLLAMA_TAGS_URL, timeout=5)
            return response.status_code == 200
        except (requests.ConnectionError, requests.Timeout):
            return False

    def list_models(self) -> list[str]:
        try:
            response = requests.get(OLLAMA_TAGS_URL, timeout=5)
            if response.status_code == 200:
                data: dict[str, Any] = response.json()
                return [str(m["name"]) for m in data.get("models", [])]
        except (requests.ConnectionError, requests.Timeout):
            pass
        return []

    # ── Chat ─────────────────────────────────────────────────────────────────

    def chat(self, prompt: str, image_base64: Optional[str] = None) -> str:
        """
        Chat-style interaction using /api/chat with conversation memory.
        The system prompt is always prepended as the first message.
        """
        user_msg: dict[str, Any] = {"role": "user", "content": prompt}
        if image_base64:
            user_msg["images"] = [image_base64]
            
        self.conversation_history.append(user_msg)

        messages: list[dict[str, str]] = [
            {"role": "system", "content": self._system_prompt},
            *self.conversation_history,
        ]

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }

        parts: list[str] = []
        try:
            with requests.post(
                OLLAMA_CHAT_URL, json=payload, stream=True, timeout=120
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if line:
                        chunk: dict[str, Any] = json.loads(line)
                        token: str = chunk.get("message", {}).get("content", "")
                        print(token, end="", flush=True)
                        parts.append(token)
                        if chunk.get("done", False):
                            break
            print()
        except requests.ConnectionError:
            parts.append(
                "Error: Cannot connect to Ollama. "
                "Make sure Ollama is running (ollama serve)."
            )
        except Exception as e:
            parts.append(f"Error: {e}")

        full_response = "".join(parts)
        self.conversation_history.append(
            {"role": "assistant", "content": full_response}
        )
        return full_response

    def vision_chat(self, prompt: str, image_base64: str, vision_model: str = "llava") -> str:
        """
        Temporarily overrides the active model to process an image query,
        then switches back. Warns if the vision model is missing.
        """
        original_model = self.model
        
        # Check if the vision model is available
        available = self.list_models()
        # Some users might have llava:latest or llava:7b, check by prefix
        model_name = next((m for m in available if m.startswith(vision_model)), None)
        
        if not model_name:
            return (
                f"[System]: Vision model '{vision_model}' is not installed.\n"
                f"Please run `ollama pull {vision_model}` in your terminal first."
            )
            
        self.model = model_name
        try:
            return self.chat(prompt, image_base64=image_base64)
        finally:
            self.model = original_model

    # ── History management ───────────────────────────────────────────────────

    def clear_history(self) -> None:
        """Reset conversation history."""
        self.conversation_history.clear()

    def load_history(self, history: list[dict[str, str]]) -> None:
        """Restore a previously saved conversation history."""
        self.conversation_history = list(history)

    def set_system_prompt(self, prompt: str) -> None:
        self._system_prompt = prompt
