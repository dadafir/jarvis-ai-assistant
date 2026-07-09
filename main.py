#!/usr/bin/env python3
"""
main.py — Entry point for the Jarvis AI Desktop Assistant.

Usage:
    python main.py                  # default (llama3, voice enabled)
    python main.py --model phi3     # use a different Ollama model
    python main.py --no-voice       # disable voice features
    python main.py --resume         # resume last saved session
"""

import argparse
import sys

from jarvis_gui import run_gui


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Jarvis — Your Local AI Desktop Assistant"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="llama3",
        help="Ollama model to use (default: llama3)",
    )
    parser.add_argument(
        "--no-voice",
        action="store_true",
        help="Disable voice (TTS/STT) features",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume the last saved conversation session",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        run_gui(
            model=args.model,
            voice_enabled=not args.no_voice,
            resume=args.resume,
        )
    except Exception as e:
        print(f"\n[!] Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
