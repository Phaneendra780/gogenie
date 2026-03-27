"""
config.py — GoGenie Centralized Configuration
All API keys, model names, and app settings live here.
Reads from Streamlit secrets (production) or environment variables (local).
"""

import os

try:
    import streamlit as st
    def _get(key, default=""):
        return st.secrets.get(key, os.getenv(key, default))
except Exception:
    def _get(key, default=""):
        return os.getenv(key, default)

# ── API Keys ──────────────────────────────────────────────────────────────────
GEMINI_API_KEY   = _get("GEMINI_API_KEY")
TAVILY_API_KEY   = _get("TAVILY_API_KEY")
SMTP_EMAIL       = _get("SMTP_EMAIL")
SMTP_PASSWORD    = _get("SMTP_PASSWORD")      # Gmail App Password
SUPABASE_URL     = _get("SUPABASE_URL")
SUPABASE_KEY     = _get("SUPABASE_KEY")

# ── Model Config ─────────────────────────────────────────────────────────────
GEMINI_MODEL       = "gemini-2.0-flash"       # Main chat model
GEMINI_EMBED_MODEL = "models/text-embedding-004"  # For RAG embeddings

# ── DB Config ─────────────────────────────────────────────────────────────────
USE_SUPABASE = bool(SUPABASE_URL and SUPABASE_KEY)
SQLITE_PATH  = "gogenie_bookings.db"

# ── Memory ────────────────────────────────────────────────────────────────────
MAX_MEMORY_MESSAGES = 25   # Last N messages to keep in context

# ── RAG Pipeline ──────────────────────────────────────────────────────────────
CHUNK_SIZE    = 600    # Characters per chunk
CHUNK_OVERLAP = 80     # Overlap between chunks
TOP_K_CHUNKS  = 4      # Number of chunks to retrieve

# ── Feature flags ─────────────────────────────────────────────────────────────
GEMINI_ENABLED = bool(GEMINI_API_KEY)
TAVILY_ENABLED = bool(TAVILY_API_KEY)
EMAIL_ENABLED  = bool(SMTP_EMAIL and SMTP_PASSWORD)
