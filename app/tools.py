"""
app/tools.py — GoGenie Tool Layer
Implements the 4 required tools from the assignment spec:
  1. RAG Tool              — query → retrieved answer from uploaded PDFs
  2. Booking Persistence   — booking payload → save to DB → booking_id
  3. Email Tool            — send HTML confirmation email via SMTP
  4. Web Search Tool       — Tavily search for real travel options (with mock fallback)
"""

import smtplib
from email.mime.text       import MIMEText
from email.mime.multipart  import MIMEMultipart
from typing import Dict, Any, List, Optional

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import config
from db.database import upsert_customer, insert_booking
from db.models   import Customer, Booking


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL 1 — RAG Tool
# ═══════════════════════════════════════════════════════════════════════════════
def rag_tool(
    query:      str,
    chunks:     List[str],
    embeddings: List[List[float]]
) -> Dict[str, Any]:
    """
    Input:  user query, pre-embedded chunks from uploaded PDFs
    Output: {"success": bool, "answer": str}
    """
    from app.rag_pipeline import answer_from_pdf
    try:
        answer = answer_from_pdf(query, chunks, embeddings)
        return {"success": True, "answer": answer, "source": "rag"}
    except Exception as e:
        return {"success": False, "answer": f"RAG retrieval error: {e}", "source": "rag"}


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL 2 — Booking Persistence Tool
# ═══════════════════════════════════════════════════════════════════════════════
def booking_persistence_tool(booking_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Input:  structured booking payload dict
    Output: {"success": bool, "booking_id": str, "customer_id": str, "error": str}
    """
    try:
        # Upsert customer
        customer = Customer(
            name  = booking_data.get("name", ""),
            email = booking_data.get("email", ""),
            phone = booking_data.get("phone", "")
        )
        customer_id = upsert_customer(customer)

        # Insert booking
        booking = Booking(
            customer_id     = customer_id,
            booking_type    = booking_data.get("transport", ""),
            from_city       = booking_data.get("from", ""),
            to_city         = booking_data.get("to", ""),
            date            = booking_data.get("date", ""),
            time            = booking_data.get("time", ""),
            selected_option = booking_data.get("selected_option", "")
        )
        booking_id = insert_booking(booking)

        return {
            "success":     True,
            "booking_id":  booking_id,
            "customer_id": customer_id,
            "error":       None
        }
    except Exception as e:
        return {
            "success":     False,
            "booking_id":  None,
            "customer_id": None,
            "error":       str(e)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL 3 — Email Tool
# ═══════════════════════════════════════════════════════════════════════════════
def email_tool(
    to_email:     str,
    subject:      str,
    booking_data: Dict[str, Any],
    booking_id:   str
) -> Dict[str, Any]:
    """
    Input:  to_email, subject, booking_data dict, booking_id
    Output: {"success": bool, "message": str, "error": str}
    Sends rich HTML confirmation email via SMTP (Gmail). 
    Falls back gracefully if SMTP not configured.
    """
    # Build HTML email body
    html_body = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8"/>
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f0f2f8; margin: 0; padding: 20px; }}
  .wrapper {{ max-width: 600px; margin: 0 auto; }}
  .header {{ background: linear-gradient(135deg, #04071a 0%, #0d1640 100%);
             border-radius: 16px 16px 0 0; padding: 32px; text-align: center; }}
  .logo {{ font-size: 2rem; font-weight: 900; color: #f5c542; letter-spacing: -1px; }}
  .tagline {{ color: rgba(200,216,240,0.6); font-size: 0.85rem; margin-top: 6px; }}
  .body {{ background: #fff; padding: 32px; }}
  .greeting {{ font-size: 1.1rem; color: #1a1a2e; margin-bottom: 16px; }}
  .confirm-badge {{ display: inline-block; background: #ecfdf5; border: 1px solid #a7f3d0;
                    border-radius: 100px; padding: 6px 16px; font-size: 0.85rem;
                    color: #065f46; font-weight: 600; margin-bottom: 24px; }}
  .card {{ background: #f8f9ff; border: 1px solid #e0e7ff; border-radius: 12px;
           padding: 24px; margin: 16px 0; }}
  .card-title {{ font-size: 0.85rem; font-weight: 700; color: #6366f1;
                 letter-spacing: 1px; text-transform: uppercase; margin-bottom: 16px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  td {{ padding: 9px 0; border-bottom: 1px solid #f0f0f8; font-size: 0.9rem; }}
  td:first-child {{ color: #888; width: 42%; }}
  td:last-child {{ color: #1a1a2e; font-weight: 600; }}
  .booking-id {{ font-family: monospace; font-size: 1.2rem; color: #f5c542;
                 background: #1a1a2e; border-radius: 8px; padding: 4px 12px;
                 display: inline-block; margin-top: 4px; }}
  .note {{ color: #888; font-size: 0.82rem; line-height: 1.6; margin-top: 20px; }}
  .footer {{ background: #f0f2f8; border-radius: 0 0 16px 16px; padding: 16px 32px;
             text-align: center; color: #aaa; font-size: 0.78rem; }}
  .footer strong {{ color: #f5c542; }}
</style>
</head>
<body>
<div class="wrapper">
  <div class="header">
    <div class="logo">🧞 GoGenie</div>
    <div class="tagline">Your AI Travel Assistant</div>
  </div>
  <div class="body">
    <div class="greeting">Hello <strong>{booking_data.get('name', 'Traveller')}</strong>! 👋</div>
    <div class="confirm-badge">✅ Booking Confirmed</div>
    <p style="color:#555; font-size:0.95rem;">
      Your trip has been successfully booked. Here are your booking details:
    </p>

    <div class="card">
      <div class="card-title">📋 Booking Summary</div>
      <table>
        <tr><td>Booking ID</td><td><span class="booking-id">#{booking_id}</span></td></tr>
        <tr><td>Transport</td><td>{booking_data.get('transport','—')}</td></tr>
        <tr><td>Route</td><td>{booking_data.get('from','—')} → {booking_data.get('to','—')}</td></tr>
        <tr><td>Date</td><td>{booking_data.get('date','—')}</td></tr>
        <tr><td>Departure</td><td>{booking_data.get('time','—')}</td></tr>
        <tr><td>Option</td><td>{booking_data.get('selected_option','—')}</td></tr>
      </table>
    </div>

    <div class="card">
      <div class="card-title">👤 Passenger Details</div>
      <table>
        <tr><td>Name</td><td>{booking_data.get('name','—')}</td></tr>
        <tr><td>Email</td><td>{booking_data.get('email','—')}</td></tr>
        <tr><td>Phone</td><td>{booking_data.get('phone','—')}</td></tr>
      </table>
    </div>

    <p class="note">
      Please keep this email for your records. If you have any questions,
      contact GoGenie support. Have a wonderful journey! 🌏
    </p>
  </div>
  <div class="footer">
    Powered by <strong>GoGenie</strong> · AI Travel Booking · Gemini 2.0 Flash · Supabase
  </div>
</div>
</body>
</html>
"""

    # Check SMTP config
    if not config.EMAIL_ENABLED:
        return {
            "success": False,
            "message": None,
            "error": "Email not configured — booking saved to DB but email skipped. Add SMTP_EMAIL and SMTP_PASSWORD to secrets."
        }

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = config.SMTP_EMAIL
        msg["To"]      = to_email
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
            server.login(config.SMTP_EMAIL, config.SMTP_PASSWORD)
            server.sendmail(config.SMTP_EMAIL, to_email, msg.as_string())

        return {"success": True, "message": f"Confirmation email sent to {to_email} ✉️", "error": None}

    except smtplib.SMTPAuthenticationError:
        return {"success": False, "message": None,
                "error": "SMTP auth failed — check Gmail App Password in secrets."}
    except smtplib.SMTPException as e:
        return {"success": False, "message": None, "error": f"SMTP error: {e}"}
    except Exception as e:
        return {"success": False, "message": None, "error": f"Email error: {e}"}


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL 4 — Web Search Tool (Tavily)
# ═══════════════════════════════════════════════════════════════════════════════
def web_search_tool(
    transport:  str,
    from_city:  str,
    to_city:    str,
    date:       str,
    time_pref:  str = ""
) -> Dict[str, Any]:
    """
    Input:  transport type, route, date
    Output: {"success": bool, "options": list[str], "source": str, "error": str}
    Uses Tavily for real-time search; falls back to curated mock data.
    """
    if config.TAVILY_ENABLED:
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=config.TAVILY_API_KEY)

            query_map = {
                "Flight": f"cheapest flights {from_city} to {to_city} {date} India prices schedule",
                "Train":  f"trains {from_city} to {to_city} {date} IRCTC schedule fare",
                "Bus":    f"buses {from_city} to {to_city} {date} redbus booking fare"
            }
            query   = query_map.get(transport, f"{transport} {from_city} to {to_city} {date}")
            results = client.search(query=query, max_results=6, search_depth="basic")

            options = []
            for r in results.get("results", [])[:5]:
                title   = (r.get("title", "") or "")[:60]
                snippet = (r.get("content", "") or "")[:100]
                url     = r.get("url", "")
                if title:
                    options.append(f"🔍 {title} — {snippet.strip()}{'...' if snippet else ''}")

            if options:
                return {"success": True, "options": options[:4], "source": "tavily", "error": None}

        except Exception as e:
            pass  # fall through to mock

    # ── Curated mock options (when Tavily unavailable or returns nothing) ──
    options = _mock_options(transport, from_city, to_city, date, time_pref)
    return {"success": True, "options": options, "source": "mock", "error": None}


def _mock_options(transport: str, frm: str, to: str, date: str, time_pref: str = "") -> List[str]:
    """Realistic mock travel options as fallback."""
    t = time_pref.lower()

    if transport == "Flight":
        return [
            f"✈️  IndiGo 6E-201     │ {frm} → {to} │ 06:00 AM │ ₹4,200  │ 2h 15m",
            f"✈️  Air India AI-505  │ {frm} → {to} │ 10:30 AM │ ₹5,800  │ 2h 30m",
            f"✈️  SpiceJet SG-112   │ {frm} → {to} │ 02:15 PM │ ₹3,900  │ 2h 10m",
            f"✈️  Vistara UK-820    │ {frm} → {to} │ 07:45 PM │ ₹6,500  │ 2h 20m",
        ]
    elif transport == "Train":
        return [
            f"🚂  Shatabdi 12001    │ {frm} → {to} │ 06:00 AM │ ₹850   │ 5h 45m",
            f"🚂  Rajdhani 12951    │ {frm} → {to} │ 04:55 PM │ ₹1,200 │ 7h 00m",
            f"🚂  Duronto 12213     │ {frm} → {to} │ 11:00 PM │ ₹980   │ 6h 30m",
        ]
    else:  # Bus
        return [
            f"🚌  RedBus Volvo AC   │ {frm} → {to} │ 08:00 PM │ ₹650   │ 8h 00m",
            f"🚌  KSRTC AC Sleeper  │ {frm} → {to} │ 10:30 PM │ ₹480   │ 9h 00m",
            f"🚌  Orange Travels    │ {frm} → {to} │ 11:45 PM │ ₹720   │ 8h 30m",
        ]
