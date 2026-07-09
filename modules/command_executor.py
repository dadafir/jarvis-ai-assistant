"""
Command Executor Module - Handles system-level commands.

Recognizes keywords in user input and executes the corresponding
system actions. Now supports weather, volume control, close app,
and many more apps/websites.
"""

from __future__ import annotations

import ctypes
import datetime
import os
import socket
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Optional

try:
    import requests as _requests
except ImportError:
    _requests = None  # type: ignore[assignment]

# ── App mappings ──────────────────────────────────────────────────────────────
APP_COMMANDS: dict[str, str] = {
    "chrome": "start chrome",
    "google chrome": "start chrome",
    "brave": "start brave",
    "firefox": "start firefox",
    "edge": "start msedge",
    "notepad": "notepad",
    "notepad++": "start notepad++",
    "calculator": "calc",
    "calc": "calc",
    "cmd": "start cmd",
    "terminal": "start cmd",
    "powershell": "start powershell",
    "explorer": "explorer",
    "file explorer": "explorer",
    "vscode": "code",
    "visual studio code": "code",
    "vs code": "code",
    "task manager": "taskmgr",
    "paint": "mspaint",
    "word": "start winword",
    "excel": "start excel",
    "powerpoint": "start powerpnt",
    "spotify": "start spotify",
    "discord": "start discord",
    "slack": "start slack",
    "teams": "start teams",
    "zoom": "start zoom",
    "obs": "start obs64",
    "vlc": "start vlc",
    "snipping tool": "snippingtool",
    "settings": "start ms-settings:",
    "control panel": "control",
    "device manager": "devmgmt.msc",
    "registry": "regedit",
    "services": "services.msc",
}

# ── Website shortcuts ─────────────────────────────────────────────────────────
WEBSITE_SHORTCUTS: dict[str, str] = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "github": "https://github.com",
    "stackoverflow": "https://stackoverflow.com",
    "stack overflow": "https://stackoverflow.com",
    "chatgpt": "https://chat.openai.com",
    "gmail": "https://mail.google.com",
    "twitter": "https://twitter.com",
    "x": "https://twitter.com",
    "reddit": "https://www.reddit.com",
    "linkedin": "https://www.linkedin.com",
    "netflix": "https://www.netflix.com",
    "amazon": "https://www.amazon.com",
    "wikipedia": "https://www.wikipedia.org",
    "maps": "https://maps.google.com",
    "google maps": "https://maps.google.com",
    "translate": "https://translate.google.com",
    "drive": "https://drive.google.com",
    "google drive": "https://drive.google.com",
    "docs": "https://docs.google.com",
    "sheets": "https://sheets.google.com",
    "claude": "https://claude.ai",
    "ollama": "https://ollama.com",
}

# ── Process names for close command ──────────────────────────────────────────
CLOSE_PROCESS: dict[str, str] = {
    "chrome": "chrome.exe",
    "firefox": "firefox.exe",
    "edge": "msedge.exe",
    "brave": "brave.exe",
    "notepad": "notepad.exe",
    "calculator": "calculator.exe",
    "spotify": "Spotify.exe",
    "discord": "Discord.exe",
    "teams": "Teams.exe",
    "zoom": "Zoom.exe",
    "vlc": "vlc.exe",
    "obs": "obs64.exe",
    "vscode": "Code.exe",
    "vs code": "Code.exe",
    "code": "Code.exe",
    "slack": "slack.exe",
    "word": "WINWORD.EXE",
    "excel": "EXCEL.EXE",
    "powerpoint": "POWERPNT.EXE",
}

# ── Windows virtual key codes for media/volume ────────────────────────────────
_VK_VOLUME_MUTE = 0xAD
_VK_VOLUME_DOWN = 0xAE
_VK_VOLUME_UP = 0xAF


class CommandExecutor:
    """Parses user input and executes recognized system commands."""

    SYSTEM_KEYWORDS: list[str] = [
        "open",
        "launch",
        "start",
        "close",
        "kill",
        "screenshot",
        "take screenshot",
        "shutdown",
        "restart",
        "lock",
        "sleep",
        "hibernate",
        "volume",
        "mute",
        "unmute",
        "time",
        "date",
        "ip address",
        "ip",
        "search for",
        "search ",
        "weather",
        "wifi",
        "network",
        "ping",
    ]

    def is_system_command(self, text: str) -> bool:
        lower = text.lower().strip()
        return any(lower.startswith(kw) for kw in self.SYSTEM_KEYWORDS)

    def execute(self, command: str) -> str:
        cmd = command.lower().strip()

        # ── Open / Launch apps ────────────────────────────────────────────────
        if cmd.startswith(("open ", "launch ", "start ")):
            target = cmd.split(" ", 1)[1].strip()
            return self._open_target(target)

        # ── Close / Kill apps ─────────────────────────────────────────────────
        if cmd.startswith(("close ", "kill ")):
            target = cmd.split(" ", 1)[1].strip()
            return self._close_app(target)

        # ── Screenshot ────────────────────────────────────────────────────────
        if "screenshot" in cmd:
            return self._take_screenshot()

        # ── Date / Time ───────────────────────────────────────────────────────
        if cmd in ("time", "what time is it", "current time"):
            now = datetime.datetime.now().strftime("%I:%M %p")
            return f"[Time] The current time is {now}."

        if cmd in ("date", "today's date", "what is the date", "current date", "today"):
            today = datetime.datetime.now().strftime("%A, %B %d, %Y")
            return f"[Date] Today is {today}."

        # ── Power ─────────────────────────────────────────────────────────────
        if cmd in ("shutdown", "shut down"):
            return self._power_cmd("shutdown /s /t 5", "Shutting down")

        if cmd in ("restart", "reboot"):
            return self._power_cmd("shutdown /r /t 5", "Restarting")

        if cmd in ("lock", "lock screen", "lock pc"):
            ctypes.windll.user32.LockWorkStation()
            return "[Lock] PC locked."

        if cmd in ("sleep", "sleep mode"):
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            return "[Sleep] System entering sleep mode."

        if cmd == "hibernate":
            os.system("shutdown /h")
            return "[Hibernate] System hibernating."

        # ── Network ───────────────────────────────────────────────────────────
        if "ip address" in cmd or cmd in ("ip", "my ip"):
            return self._get_ip()

        if cmd.startswith("ping "):
            host = cmd[5:].strip()
            return self._ping(host)

        if cmd in ("wifi", "network", "network info"):
            return self._network_info()

        # ── Volume ────────────────────────────────────────────────────────────
        if cmd.startswith("volume"):
            return self._handle_volume(cmd)

        if cmd in ("mute", "mute audio"):
            return self._press_key(_VK_VOLUME_MUTE, "Audio muted/unmuted.")

        if cmd in ("unmute",):
            return self._press_key(_VK_VOLUME_MUTE, "Audio unmuted.")

        # ── Weather ───────────────────────────────────────────────────────────
        if cmd.startswith("weather"):
            city: Optional[str] = None
            if " in " in cmd:
                city = cmd.split(" in ", 1)[1].strip()
            elif cmd != "weather":
                city = cmd.replace("weather", "").strip()
            return self._get_weather(city)

        # ── Web search ────────────────────────────────────────────────────────
        if cmd.startswith("search for ") or cmd.startswith("search "):
            query = cmd.replace("search for ", "").replace("search ", "").strip()
            webbrowser.open(f"https://www.google.com/search?q={query}")
            return f"[Search] Searching Google for '{query}'."

        return f"[?] Command not recognized: '{command}'"

    # ── Private helpers ───────────────────────────────────────────────────────

    def _open_target(self, target: str) -> str:
        if target in WEBSITE_SHORTCUTS:
            webbrowser.open(WEBSITE_SHORTCUTS[target])
            return f"[Web] Opening {target}."
        if target in APP_COMMANDS:
            os.system(APP_COMMANDS[target])
            return f"[Launch] Opening {target}."
        if target.startswith("http") or (
            "." in target and " " not in target
        ):
            url = target if target.startswith("http") else "https://" + target
            webbrowser.open(url)
            return f"[Web] Opening {url}."
        try:
            subprocess.Popen(target, shell=True)
            return f"[Launch] Attempting to open '{target}'."
        except Exception as e:
            return f"[Error] Failed to open '{target}': {e}"

    def _close_app(self, target: str) -> str:
        if sys.platform != "win32":
            return "[Error] Close command is only supported on Windows."
        proc = CLOSE_PROCESS.get(target, target + ".exe")
        result = subprocess.run(
            ["taskkill", "/f", "/im", proc],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return f"[Close] {target} has been closed."
        return f"[Error] Could not close '{target}' (process: {proc})."

    def _take_screenshot(self) -> str:
        try:
            from PIL import ImageGrab  # type: ignore[import-untyped]
            screenshot = ImageGrab.grab()
            desktop = Path.home() / "Desktop"
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = desktop / f"screenshot_{ts}.png"
            screenshot.save(str(filepath))
            return f"[Screenshot] Saved to {filepath}."
        except ImportError:
            return "[Error] Pillow not installed. Run: pip install Pillow"
        except Exception as e:
            return f"[Error] Screenshot failed: {e}"

    def _power_cmd(self, cmd: str, action: str) -> str:
        os.system(cmd)
        return f"[Power] {action} in 5 seconds..."

    def _get_ip(self) -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return f"[Network] Local IP: {ip}"
        except Exception:
            return "[Error] Could not determine IP address."

    def _ping(self, host: str) -> str:
        flag = "-n" if sys.platform == "win32" else "-c"
        result = subprocess.run(
            ["ping", flag, "3", host],
            capture_output=True,
            text=True,
            timeout=15,
        )
        lines = [l for l in result.stdout.splitlines() if l.strip()]
        summary = lines[-1] if lines else "No response."
        return f"[Ping] {host} → {summary}"

    def _network_info(self) -> str:
        ip = self._get_ip()
        try:
            hostname = socket.gethostname()
            return f"{ip}  |  Hostname: {hostname}"
        except Exception:
            return ip

    def _handle_volume(self, cmd: str) -> str:
        if "up" in cmd:
            for _ in range(5):
                self._press_key(_VK_VOLUME_UP)
            return "[Volume] Turned up."
        if "down" in cmd:
            for _ in range(5):
                self._press_key(_VK_VOLUME_DOWN)
            return "[Volume] Turned down."
        if "mute" in cmd:
            return self._press_key(_VK_VOLUME_MUTE, "[Volume] Toggled mute.")
        # volume <0-100>
        parts = cmd.split()
        if len(parts) == 2 and parts[1].isdigit():
            level = max(0, min(100, int(parts[1])))
            try:
                subprocess.run(
                    [
                        "powershell",
                        "-command",
                        f"[Audio.Volume]::SetVolume({level})",
                    ],
                    capture_output=True,
                )
            except Exception:
                pass
            return f"[Volume] Set to {level}%."
        return "[Volume] Usage: volume up / down / mute / <0-100>"

    def _press_key(self, vk: int, msg: str = "") -> str:
        if sys.platform == "win32":
            ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
            ctypes.windll.user32.keybd_event(vk, 0, 2, 0)
        return msg

    def _get_weather(self, city: Optional[str]) -> str:
        if _requests is None:
            return "[Error] 'requests' not installed."
        location = city if city else ""
        url = f"https://wttr.in/{location}?format=4"
        try:
            resp = _requests.get(url, timeout=8)
            if resp.status_code == 200:
                return f"[Weather] {resp.text.strip()}"
            return f"[Weather] Could not fetch weather (HTTP {resp.status_code})."
        except Exception as e:
            return f"[Weather] Error: {e}"
