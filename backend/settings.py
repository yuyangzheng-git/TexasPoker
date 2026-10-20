"""Load configuration before importing LLM clients."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / "config" / ".env")

POKER_AGENT_MODE = os.getenv("POKER_AGENT_MODE", "strategy").lower()
if POKER_AGENT_MODE not in {"strategy", "llm"}:
    raise RuntimeError("POKER_AGENT_MODE must be strategy or llm")
