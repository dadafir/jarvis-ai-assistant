"""
Tray Manager — Jarvis lives in the system tray.

Uses pystray to create a persistent tray icon so Jarvis can run
silently in the background. The window can be shown/hidden from the
tray menu, and wake-word detection keeps running even when hidden.
"""

from __future__ import annotations

from typing import Callable, Optional

try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False


def _make_icon() -> "Image.Image":
    """
    Draw a J.A.R.V.I.S tray icon programmatically using Pillow.
    No external icon file needed.
    """
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Outer glow ring
    draw.ellipse([0, 0, size - 1, size - 1], fill=(0, 120, 215, 60))
    # Main dark circle background
    draw.ellipse([3, 3, size - 4, size - 4], fill=(10, 15, 35))
    # Bright blue border
    draw.ellipse([3, 3, size - 4, size - 4], outline=(0, 180, 255), width=3)

    # Draw the letter "J" using rectangles / arc
    # Top horizontal bar
    draw.rectangle([18, 13, 46, 20], fill=(0, 210, 255))
    # Vertical stem (right side of J)
    draw.rectangle([37, 13, 45, 43], fill=(0, 210, 255))
    # Bottom curve
    draw.arc([13, 34, 45, 54], start=90, end=270, fill=(0, 210, 255), width=8)

    return img


class TrayManager:
    """Manages the system tray icon lifecycle."""

    def __init__(
        self,
        on_show: Callable,
        on_hide: Callable,
        on_quit: Callable,
    ) -> None:
        self._on_show = on_show
        self._on_hide = on_hide
        self._on_quit = on_quit
        self._icon: Optional["pystray.Icon"] = None
        self.available: bool = TRAY_AVAILABLE

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Create and start the tray icon (non-blocking — runs detached)."""
        if not self.available:
            print("[Tray] pystray not installed — tray disabled.")
            return

        menu = pystray.Menu(
            pystray.MenuItem("Show Jarvis",  self._cb_show, default=True),
            pystray.MenuItem("Hide Jarvis",  self._cb_hide),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit",         self._cb_quit),
        )

        self._icon = pystray.Icon(
            name="jarvis",
            icon=_make_icon(),
            title="J.A.R.V.I.S  —  Running",
            menu=menu,
        )
        # run_detached() launches the icon loop in its own OS thread
        self._icon.run_detached()
        print("[Tray] System tray icon started.")

    def set_tooltip(self, text: str) -> None:
        """Update the tray tooltip (visible on hover)."""
        if self._icon:
            try:
                self._icon.title = text
            except Exception:
                pass

    def stop(self) -> None:
        """Remove the tray icon."""
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass

    # ── Private callbacks ─────────────────────────────────────────────────────

    def _cb_show(self, icon: "pystray.Icon", item: "pystray.MenuItem") -> None:
        self._on_show()

    def _cb_hide(self, icon: "pystray.Icon", item: "pystray.MenuItem") -> None:
        self._on_hide()

    def _cb_quit(self, icon: "pystray.Icon", item: "pystray.MenuItem") -> None:
        self._on_quit()
