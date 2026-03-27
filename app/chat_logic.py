"""
app/chat_logic.py — GoGenie Chat Logic
Gemini 2.0 Flash powers:
  - Intent detection (booking / pdf_query / view_bookings / confirm / cancel / general)
  - Entity extraction (city, date, time from free-form messages)
  - General conversational chat with rolling 25-message memory
"""

from typing import List, Dict, Optional
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import config


# ── Gemini client ─────────────────────────────────────────────────────────────
def _get_model():
    import google.generativeai as genai
    genai.configure(api_key=config.GEMINI_API_KEY)
    return genai.GenerativeModel(config.GEMINI_MODEL)


# ═══════════════════════════════════════════════════════════════════════════════
# Intent Detection
# ═══════════════════════════════════════════════════════════════════════════════
def detect_intent(message: str, history: List[Dict]) -> str:
    """
    Returns one of: booking | pdf_query | view_bookings | confirm | cancel | general
    Uses Gemini when available; falls back to keyword matching.
    """
    if not config.GEMINI_ENABLED:
        return _keyword_intent(message)

    recent = "\n".join(
        f"{m['role'].upper()}: {str(m.get('content',''))[:120]}"
        for m in history[-6:]
    )

    prompt = f"""Classify the user's message into exactly ONE intent. Reply with only the intent word.

Recent conversation:
{recent}

User's latest message: "{message}"

Intents:
- booking      → wants to book a flight / train / bus / ticket / travel
- pdf_query    → asking about an uploaded PDF / document / travel guide / rules / luggage / visa
- view_bookings → wants to see their past bookings / trips / reservation history
- confirm      → confirming / approving the booking summary (yes / ok / confirm / correct / sure)
- cancel       → cancelling / rejecting / stopping the booking (no / cancel / wrong / stop)
- general      → anything else (greeting, travel tips, general question)

Reply with ONE word only:"""

    try:
        model    = _get_model()
        response = model.generate_content(prompt)
        intent   = response.text.strip().lower().split()[0]
        VALID    = {"booking", "pdf_query", "view_bookings", "confirm", "cancel", "general"}
        return intent if intent in VALID else "general"
    except Exception:
        return _keyword_intent(message)


def _keyword_intent(message: str) -> str:
    """Fallback keyword-based intent detection (no Gemini)."""
    lower = message.lower()
    if any(w in lower for w in ["yes","confirm","correct","ok","sure","yep","yeah","proceed"]):
        return "confirm"
    if any(w in lower for w in ["no","cancel","wrong","incorrect","nope","stop","abort"]):
        return "cancel"
    if any(w in lower for w in ["my booking","my trip","my ticket","view booking","past booking","show booking"]):
        return "view_bookings"
    if any(w in lower for w in ["book","ticket","reserve","travel","flight","train","bus","journey","trip to"]):
        return "booking"
    if any(w in lower for w in ["pdf","document","upload","guide","rules","policy","luggage","visa","what does it say"]):
        return "pdf_query"
    return "general"


# ═══════════════════════════════════════════════════════════════════════════════
# General Conversational Chat
# ═══════════════════════════════════════════════════════════════════════════════
def general_chat(message: str, history: List[Dict]) -> str:
    """
    Handle non-booking messages with full Gemini conversation.
    Maintains a rolling window of the last MAX_MEMORY_MESSAGES.
    """
    if not config.GEMINI_ENABLED:
        return (
            "I'm Genie, your AI travel assistant! 🧞\n\n"
            "I can help you **book flights, trains, and buses**, answer questions from uploaded travel PDFs, "
            "or view your past bookings.\n\n"
            "Try: *\"Book a flight to Mumbai\"* or *\"Show my bookings\"*"
        )

    system = """You are Genie — a warm, witty, and knowledgeable AI travel assistant for GoGenie.
You specialise in Indian travel (flights, trains, buses) but know about global travel too.
Keep replies concise (2-4 sentences max), friendly, and occasionally use a relevant emoji.
If someone wants to book, encourage them with: "Just say 'Book a flight/train/bus' to get started!"
Do NOT make up flight/train prices or schedules — real data comes from the booking tool."""

    # Build Gemini chat history (last MAX_MEMORY_MESSAGES - 1)
    recent      = history[-config.MAX_MEMORY_MESSAGES:]
    chat_history = []
    for msg in recent[:-1]:     # skip the current user message
        role = "user" if msg["role"] == "user" else "model"
        content = str(msg.get("content", ""))
        if content.strip():
            chat_history.append({"role": role, "parts": [content]})

    try:
        import google.generativeai as genai
        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel(
            config.GEMINI_MODEL,
            system_instruction=system
        )
        chat     = model.start_chat(history=chat_history)
        response = chat.send_message(message)
        return response.text.strip()
    except Exception as e:
        return f"I ran into a small issue ({e}). Please try again!"


# ═══════════════════════════════════════════════════════════════════════════════
# Entity Extraction
# ═══════════════════════════════════════════════════════════════════════════════
def extract_entity(message: str, field: str) -> str:
    """
    Extract a specific entity from a free-form user message using Gemini.
    Falls back to returning the raw message if Gemini unavailable.
    """
    if not config.GEMINI_ENABLED:
        return message.strip()

    prompts = {
        "city": (
            f'Extract ONLY the city or location name from this message: "{message}"\n'
            "Return just the city name, properly capitalised. Nothing else."
        ),
        "date": (
            f'Extract ONLY the travel date from: "{message}"\n'
            "Return in YYYY-MM-DD format if a specific date, otherwise return the phrase as-is. Nothing else."
        ),
        "time": (
            f'Extract ONLY the time preference from: "{message}"\n'
            'Return a short phrase like "Morning", "09:00 AM", "Evening", "Any". Nothing else.'
        ),
    }

    prompt = prompts.get(field, f'Extract the {field} from: "{message}". Return only the value.')

    try:
        model    = _get_model()
        response = model.generate_content(prompt)
        return response.text.strip().strip('"\'')
    except Exception:
        return message.strip()
