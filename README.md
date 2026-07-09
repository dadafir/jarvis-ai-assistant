# 🤖 J.A.R.V.I.S — Local AI Desktop Assistant v2.0

A fully local, privacy-first AI desktop assistant powered by **Ollama** and **Llama3**.
No cloud. No API keys. Everything runs on your machine.

---

## ✨ Features

| Feature | Details |
|---|---|
| 💬 **AI Chat** | Multi-turn conversations with a local LLM (llama3, phi3, mistral…) |
| ⚡ **System Commands** | Open/close apps, screenshots, search, power controls |
| 🌤️ **Live Weather** | Real-time weather via wttr.in (no API key needed) |
| 📊 **System Stats** | CPU, RAM, Disk, Battery, top processes via psutil |
| ⏰ **Alarms** | Set alarms at exact times or relative durations |
| 🔔 **Reminders** | Natural-language reminders ("in 30 min to call mom") |
| 📝 **Notes** | Persistent quick-notes saved across sessions |
| 🧠 **Memory** | Conversation history saved and resumable across restarts |
| 🎙️ **Voice I/O** | Optional TTS + STT (pyttsx3 + SpeechRecognition) |
| 🖥️ **Rich Terminal UI** | Beautiful styled console with panels and tables |

---

## 📁 Project Structure

```
jarvis-ai/
├── main.py                     # Entry point
├── start_jarvis.bat            # Double-click launcher (Windows)
├── requirements.txt
├── README.md
└── modules/
    ├── ai_engine.py            # Ollama LLM integration + system prompt
    ├── alarm_manager.py        # Alarms & reminders (background thread)
    ├── command_executor.py     # 40+ system commands
    ├── jarvis_controller.py    # Main orchestrator
    ├── memory_store.py         # Persistent JSON storage (~/.jarvis/)
    ├── notes_manager.py        # Quick note-taking
    ├── system_info.py          # psutil system metrics
    └── voice_engine.py         # TTS & STT (optional)
```

---

## 🚀 Quick Start

### Prerequisites
1. **Python 3.10+**
2. **Ollama** — Install from [ollama.com](https://ollama.com)
3. Pull a model:
   ```bash
   ollama pull llama3
   ```

### Install & Run

```bash
# Install dependencies
pip install -r requirements.txt

# Option A: Double-click (auto-starts Ollama)
start_jarvis.bat

# Option B: Terminal
ollama serve          # in a separate terminal
python main.py --no-voice
```

### CLI Flags

```bash
python main.py                  # Default (llama3, voice enabled)
python main.py --no-voice       # Disable TTS/STT
python main.py --model phi3     # Use a different Ollama model
python main.py --resume         # Resume last conversation
```

---

## 💬 Commands Reference

### System
| Command | Action |
|---|---|
| `open chrome` / `open youtube` | Launch app or website |
| `close spotify` | Kill a running process |
| `search for python tutorials` | Google search |
| `weather in london` | Live weather |
| `screenshot` | Save screenshot to Desktop |
| `time` / `date` | Current time / date |
| `ip` / `network` | Network info |
| `ping google.com` | Ping a host |
| `volume up` / `volume down` / `mute` | System volume |
| `lock` / `sleep` / `shutdown` / `restart` | Power controls |

### System Stats
| Command | Action |
|---|---|
| `stats` / `system` | Full overview (CPU, RAM, Disk, Battery) |
| `cpu` / `ram` / `disk` / `battery` | Individual stat |
| `top` / `processes` | Top CPU-consuming processes |

### Alarms & Reminders
| Command | Action |
|---|---|
| `set alarm for 7:30 am` | Alarm at exact time |
| `set alarm in 10 minutes` | Alarm after duration |
| `remind me in 30 min to take medicine` | Relative reminder |
| `remind me at 3:00 pm to call mom` | Exact-time reminder |
| `alarms` / `reminders` | List all active |
| `cancel alarm 2` | Cancel by ID |
| `cancel all alarms` | Cancel everything |

### Notes & Memory
| Command | Action |
|---|---|
| `note: buy groceries` | Save a note |
| `notes` | View all notes |
| `delete note 2` | Delete note by number |
| `save` | Manually save conversation |
| `load last` | Reload last session |
| `clear history` | Reset conversation context |

### Jarvis Controls
| Command | Action |
|---|---|
| `listen` / `voice` | Switch to voice input |
| `models` | List available Ollama models |
| `use model phi3` | Switch AI model |
| `clear` | Clear terminal |
| `help` | Show all commands |
| `quit` / `exit` | Exit (auto-saves session) |

### Supported Apps (open / close)
`chrome`, `firefox`, `edge`, `brave`, `vscode`, `notepad`, `calculator`,
`spotify`, `discord`, `slack`, `teams`, `zoom`, `vlc`, `obs`, `paint`,
`word`, `excel`, `powerpoint`, `task manager`, `settings`, `explorer`…

### Supported Websites (open)
`youtube`, `google`, `github`, `chatgpt`, `claude`, `netflix`, `reddit`,
`linkedin`, `gmail`, `maps`, `translate`, `drive`, `docs`, `sheets`…

---

## 🧠 Memory & Persistence

All data is stored in `~/.jarvis/memory.json`:
- **Conversation sessions** — last 10 sessions saved automatically on exit
- **Notes** — persist indefinitely until deleted

---

## 🎙️ Voice Setup (Optional)

```bash
pip install pyttsx3 SpeechRecognition PyAudio
python main.py   # voice enabled by default
```

Use `listen` command or just run without `--no-voice` to enable mic input.

---

## License

MIT
