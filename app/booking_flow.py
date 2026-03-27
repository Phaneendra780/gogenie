"""
app/booking_flow.py — GoGenie Booking Flow
Multi-turn slot-filling state machine.
States: transport → route → date → time → options → details → confirm → done
Uses Gemini entity extraction for natural language inputs.
Uses tools.py for persistence, email, and travel search.
"""

from typing import Dict, List, Tuple, Optional
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app.chat_logic import extract_entity
from app.tools      import web_search_tool, booking_persistence_tool, email_tool

# ── Ordered step list ─────────────────────────────────────────────────────────
STEPS = ["transport", "route", "date", "time", "options", "details", "confirm", "done"]

STEP_LABELS = {
    "transport": "🚀 Transport",
    "route":     "📍 Route",
    "date":      "📅 Date",
    "time":      "⏰ Time",
    "options":   "🔍 Options",
    "details":   "👤 Details",
    "confirm":   "✅ Confirm",
    "done":      "🎉 Done",
}


# ═══════════════════════════════════════════════════════════════════════════════
# Signal constants returned as bot_response
# (main.py checks for these to render special widgets)
# ═══════════════════════════════════════════════════════════════════════════════
SIGNAL_CONFIRM_CARD = "__SHOW_CONFIRM_CARD__"
SIGNAL_SUCCESS      = "__BOOKING_SUCCESS__"   # suffixed with ":booking_id:email_msg"


# ═══════════════════════════════════════════════════════════════════════════════
# Main Processor
# ═══════════════════════════════════════════════════════════════════════════════
def process_booking_input(
    user_input:   str,
    booking_state: str,
    booking_data:  Dict,
) -> Tuple[Dict, str, str, List[str], bool]:
    """
    Processes one turn of the booking flow.

    Returns:
        updated_booking_data  – dict with collected fields
        new_state             – next state string
        bot_response          – message to show (may be a SIGNAL constant)
        options               – list of travel option strings (for option selection UI)
        pending_option_select – bool, True when option buttons should be shown
    """
    bdata          = booking_data.copy()
    new_state      = booking_state
    options        = []
    pending_select = False
    bot_response   = ""

    lower = user_input.strip().lower()

    # ── route: "from" city ────────────────────────────────────────────────────
    if booking_state == "route" and "from" not in bdata:
        city        = extract_entity(user_input, "city")
        bdata["from"] = city.title()
        bot_response  = (
            f"Got it — travelling from **{bdata['from']}** 📍\n\n"
            "Where are you **travelling to**?"
        )

    # ── route: "to" city ──────────────────────────────────────────────────────
    elif booking_state == "route" and "to" not in bdata:
        city       = extract_entity(user_input, "city")
        bdata["to"] = city.title()
        new_state   = "date"
        bot_response = (
            f"**{bdata['from']} → {bdata['to']}** 🗺️\n\n"
            "What **date** would you like to travel?\n"
            "*e.g. 2025-07-15 or July 15 or next Monday*"
        )

    # ── date ──────────────────────────────────────────────────────────────────
    elif booking_state == "date":
        date_val    = extract_entity(user_input, "date")
        bdata["date"] = date_val
        new_state   = "time"
        bot_response = (
            f"📅 **{bdata['date']}** noted!\n\n"
            "What's your **preferred departure time**?\n"
            "*e.g. Morning, 9 AM, Evening, Any time*"
        )

    # ── time → fetch travel options ───────────────────────────────────────────
    elif booking_state == "time":
        time_val      = extract_entity(user_input, "time")
        bdata["time"] = time_val
        new_state     = "options"

        result  = web_search_tool(
            transport  = bdata.get("transport", "Flight"),
            from_city  = bdata.get("from", ""),
            to_city    = bdata.get("to", ""),
            date       = bdata.get("date", ""),
            time_pref  = time_val
        )
        options        = result.get("options", [])
        pending_select = True
        source_tag     = "🌐 live results" if result.get("source") == "tavily" else "📋 curated options"

        bot_response = (
            f"⏰ **{time_val}** preference noted! Fetching {source_tag}...\n\n"
            f"Here are available **{bdata.get('transport','trips')}s** "
            f"from **{bdata.get('from','—')} → {bdata.get('to','—')}** on **{bdata.get('date','—')}**:"
        )

    # ── details: name ─────────────────────────────────────────────────────────
    elif booking_state == "details" and "name" not in bdata:
        bdata["name"] = user_input.strip().title()
        bot_response  = (
            f"Nice to meet you, **{bdata['name']}**! 👋\n\n"
            "What's your **email address**?"
        )

    # ── details: email ────────────────────────────────────────────────────────
    elif booking_state == "details" and "email" not in bdata:
        email = user_input.strip().lower()
        if "@" not in email or "." not in email.split("@")[-1]:
            bot_response = (
                "⚠️ That doesn't look like a valid email address.\n"
                "Please enter a valid email *(e.g. raj@gmail.com)*"
            )
        else:
            bdata["email"] = email
            bot_response   = (
                f"📧 **{bdata['email']}** saved!\n\n"
                "Lastly, what's your **phone number**?"
            )

    # ── details: phone → confirmation card ───────────────────────────────────
    elif booking_state == "details" and "phone" not in bdata:
        clean = user_input.strip().replace("+","").replace(" ","").replace("-","")
        if not clean.isdigit() or len(clean) < 10:
            bot_response = (
                "⚠️ Please enter a valid phone number *(at least 10 digits)*."
            )
        else:
            bdata["phone"] = user_input.strip()
            new_state      = "confirm"
            bot_response   = SIGNAL_CONFIRM_CARD   # main.py will render card

    # ── confirm / cancel ──────────────────────────────────────────────────────
    elif booking_state == "confirm":

        yes_words = ["yes","confirm","correct","ok","sure","yep","yeah","proceed","looks good","go ahead","book it"]
        no_words  = ["no","cancel","wrong","incorrect","nope","stop","abort","back"]

        if any(w in lower for w in yes_words):
            # Save to DB
            persist = booking_persistence_tool(bdata)

            if persist["success"]:
                booking_id = persist["booking_id"]
                # Send email
                email_res = email_tool(
                    to_email     = bdata.get("email", ""),
                    subject      = f"GoGenie — Booking Confirmed #{booking_id}",
                    booking_data = bdata,
                    booking_id   = booking_id
                )
                email_msg = (
                    email_res["message"]
                    if email_res["success"]
                    else f"⚠️ Note: {email_res.get('error','Email not sent, but booking is saved.')}"
                )
                new_state    = "done"
                bot_response = f"{SIGNAL_SUCCESS}:{booking_id}:{email_msg}"
            else:
                bot_response = (
                    f"⚠️ Database error: {persist.get('error')}.\n"
                    "Please try again or contact support."
                )

        elif any(w in lower for w in no_words):
            new_state    = "cancelled"
            bot_response = (
                "No problem! Booking cancelled. 🚫\n\n"
                "Would you like to start a new booking or is there anything else I can help with?"
            )

        else:
            bot_response = (
                "Please reply **Yes** to confirm your booking or **No** to cancel."
            )

    return bdata, new_state, bot_response, options, pending_select


# ═══════════════════════════════════════════════════════════════════════════════
# Option Selection Helper
# ═══════════════════════════════════════════════════════════════════════════════
def handle_option_selection(selected: str, bdata: Dict) -> Tuple[Dict, str, str]:
    """
    Called when user clicks an option button.
    Returns (updated_bdata, new_state, bot_response).
    """
    bdata["selected_option"] = selected
    bot_response = (
        f"Great choice! ✅ **{selected}** selected.\n\n"
        "Now I need a few details to complete your booking.\n\n"
        "**What's your full name?**"
    )
    return bdata, "details", bot_response
