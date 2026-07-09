"""
System Info Module — Live system metrics using psutil.
Gracefully degrades if psutil is not installed.
"""

from __future__ import annotations

from typing import Any


class SystemInfo:
    """Retrieves CPU, RAM, disk, battery, and process statistics."""

    def __init__(self) -> None:
        self._available: bool = False
        self._psutil: Any = None
        try:
            import psutil  # type: ignore[import-untyped]
            self._psutil = psutil
            self._available = True
        except ImportError:
            pass

    @property
    def available(self) -> bool:
        return self._available

    def cpu(self) -> str:
        if not self._available:
            return "psutil not installed. Run: pip install psutil"
        p = self._psutil
        pct = p.cpu_percent(interval=0.5)
        cores = p.cpu_count(logical=True)
        freq = p.cpu_freq()
        freq_str = f"{freq.current / 1000:.2f} GHz" if freq else "N/A"
        return f"CPU  : {pct:.1f}% load  |  {cores} logical cores  |  {freq_str}"

    def ram(self) -> str:
        if not self._available:
            return "psutil not installed."
        mem = self._psutil.virtual_memory()
        used = mem.used / 1024**3
        total = mem.total / 1024**3
        return f"RAM  : {used:.1f} GB / {total:.1f} GB used  ({mem.percent:.1f}%)"

    def disk(self) -> str:
        if not self._available:
            return "psutil not installed."
        import sys
        root = "C:\\" if sys.platform == "win32" else "/"
        try:
            d = self._psutil.disk_usage(root)
        except Exception:
            return "Disk: Could not read disk usage."
        used = d.used / 1024**3
        total = d.total / 1024**3
        free = d.free / 1024**3
        return f"Disk : {used:.1f} GB / {total:.1f} GB used  ({free:.1f} GB free)"

    def battery(self) -> str:
        if not self._available:
            return "psutil not installed."
        bat = self._psutil.sensors_battery()
        if bat is None:
            return "Batt : No battery detected."
        plug = "Charging" if bat.power_plugged else "On battery"
        return f"Batt : {bat.percent:.0f}%  ({plug})"

    def summary(self) -> str:
        return "\n".join([self.cpu(), self.ram(), self.disk(), self.battery()])

    def top_processes(self, n: int = 5) -> str:
        if not self._available:
            return "psutil not installed."
        procs: list[dict] = []
        for proc in self._psutil.process_iter(
            ["pid", "name", "cpu_percent", "memory_percent"]
        ):
            try:
                procs.append(proc.info)
            except Exception:
                pass
        procs.sort(key=lambda x: x.get("cpu_percent") or 0.0, reverse=True)
        lines = [f"Top {n} processes by CPU:"]
        for p in procs[:n]:
            name = (p.get("name") or "?")[:28]
            cpu = p.get("cpu_percent") or 0.0
            mem = p.get("memory_percent") or 0.0
            lines.append(f"  {name:<28}  CPU {cpu:5.1f}%  RAM {mem:4.1f}%")
        return "\n".join(lines)
