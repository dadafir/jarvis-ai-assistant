import sys
sys.path.insert(0, ".")

results = {}
ok = "OK"
fail = "FAIL"

modules = [
    "modules.ai_engine",
    "modules.alarm_manager",
    "modules.command_executor",
    "modules.memory_store",
    "modules.notes_manager",
    "modules.system_info",
    "modules.voice_engine",
]

for m in modules:
    try:
        __import__(m)
        results[m] = ok
    except Exception as e:
        results[m] = "FAIL: " + str(e)

try:
    import jarvis_gui
    results["jarvis_gui"] = ok
except Exception as e:
    results["jarvis_gui"] = "FAIL: " + str(e)

try:
    import main as main_mod
    results["main"] = ok
except Exception as e:
    results["main"] = "FAIL: " + str(e)

print()
print("=== MODULE AUDIT ===")
for k, v in results.items():
    icon = "[OK]  " if v == ok else "[FAIL]"
    print("  " + icon + " " + k + ": " + v)

print()
print("=== FEATURE CHECKS ===")

from modules.ai_engine import AIEngine
ai = AIEngine()
check = lambda b: "[OK]  " if b else "[FAIL]"
print("  " + check(hasattr(ai, "vision_chat")) + " ai_engine: vision_chat method")
print("  " + check("image_base64" in ai.chat.__code__.co_varnames) + " ai_engine: image_base64 param in chat()")

from modules.voice_engine import VoiceEngine
import inspect
sig = inspect.signature(VoiceEngine.speak)
print("  " + check("on_complete" in sig.parameters) + " voice_engine: on_complete callback (non-blocking TTS)")

from modules.memory_store import MemoryStore
ms = MemoryStore()
print("  " + check(hasattr(ms, "add_note")) + " memory_store: notes support")
print("  " + check(hasattr(ms, "save_session")) + " memory_store: session save/load")

from modules.system_info import SystemInfo
si = SystemInfo()
print("  " + check(si.available) + " system_info: psutil = " + str(si.available))

from modules.alarm_manager import AlarmManager
am = AlarmManager()
print("  " + check(hasattr(am, "set_alarm") and hasattr(am, "set_reminder")) + " alarm_manager: alarms + reminders")
am.shutdown()

import jarvis_gui as jg
print("  " + check(hasattr(jg.JarvisGUI, "_capture_screen_b64")) + " jarvis_gui: screen vision")
print("  " + check(hasattr(jg.JarvisGUI, "_continuous_listen")) + " jarvis_gui: wake-word listener")
print("  " + check(hasattr(jg.JarvisGUI, "_manual_listen_trigger")) + " jarvis_gui: mic button")
print("  " + check(hasattr(jg.JarvisGUI, "_update_status")) + " jarvis_gui: animated status (Idle/Listening/Thinking/Speaking)")
print("  " + check(hasattr(jg.JarvisGUI, "_append_to_chat")) + " jarvis_gui: conversation history display")

print()
all_ok = all(v == ok for v in results.values())
print("=== OVERALL: " + ("ALL SYSTEMS GO ✓" if all_ok else "ISSUES FOUND - see above") + " ===")
