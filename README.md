# 🧞 GoGenie — AI Travel Booking Assistant

> AI-driven booking chatbot · Gemini 2.0 Flash · Tavily Search · RAG · SQLite/Supabase · Streamlit

---

## Overview

GoGenie is a fully conversational AI booking assistant that lets users book flights, trains, and buses through natural language chat. It uses:

| Component | Technology |
|---|---|
| LLM (chat + intent) | Gemini 2.0 Flash via `google-generativeai` |
| RAG embeddings | Gemini `text-embedding-004` |
| Travel search | Tavily API (with mock fallback) |
| PDF parsing | PyMuPDF (fitz) |
| Database | SQLite (local) or Supabase (cloud) |
| Email | SMTP via Gmail App Password |
| Frontend | Streamlit |

---

## Project Structure

```
gogenie/
├── app/
│   ├── main.py              # Streamlit entry point — all pages
│   ├── chat_logic.py        # Gemini intent detection + entity extraction + general chat
│   ├── booking_flow.py      # Multi-turn booking state machine
│   ├── rag_pipeline.py      # PDF ingest → chunk → embed → retrieve → answer
│   ├── tools.py             # 4 tools: RAG, BookingPersistence, Email, WebSearch
│   └── admin_dashboard.py   # Admin UI — view/search/export/manage bookings
│
├── db/
│   ├── database.py          # SQLite CRUD: customers + bookings tables
│   └── models.py            # Customer + Booking dataclasses
│
├── .streamlit/
│   └── secrets.toml         # API keys (never commit real keys)
│
├── config.py                # Centralised config (reads secrets + env vars)
├── requirements.txt
└── README.md
```

---

## Setup (Local)

### 1. Clone and install

```bash
git clone https://github.com/your-username/gogenie.git
cd gogenie
pip install -r requirements.txt
```

### 2. Configure API keys

Copy `.streamlit/secrets.toml` and fill in your keys:

```toml
GEMINI_API_KEY = "your-gemini-api-key"
TAVILY_API_KEY = "your-tavily-api-key"       # optional
SMTP_EMAIL     = "your-gmail@gmail.com"       # optional
SMTP_PASSWORD  = "your-app-password"          # optional
```

Get keys from:
- **Gemini**: https://aistudio.google.com/app/apikey
- **Tavily**: https://app.tavily.com
- **Gmail App Password**: Google Account → Security → App Passwords

### 3. Run

```bash
streamlit run app/main.py
```

---

## Deploy to Streamlit Cloud

1. Push to GitHub
2. Go to https://share.streamlit.io → New app
3. Set **Main file path**: `app/main.py`
4. Add API keys in **Secrets** section (paste from `secrets.toml`)
5. Deploy ✅

---

## Features

### ✅ Core Requirements Met

| Requirement | Implementation |
|---|---|
| Chat-based UI | Streamlit `st.chat_message` / `st.chat_input` |
| RAG from uploaded PDFs | PyMuPDF → chunk → Gemini embeddings → cosine retrieval → Gemini answer |
| Intent detection | Gemini few-shot prompt (falls back to keyword matching) |
| Multi-turn booking flow | State machine: transport → route → date → time → options → details → confirm |
| Confirmation before saving | Confirm card shown, data stored only on "Yes" |
| SQLite storage | `customers` + `bookings` tables with FK relationship |
| Email confirmation | HTML email via Gmail SMTP |
| Admin Dashboard | View all, search/filter, stats, export CSV, confirm/cancel/delete |
| Deployed on Streamlit Cloud | `app/main.py` as entry point |
| Short-term memory | Rolling 25-message window in `st.session_state` |
| Error handling | Validation for email, phone; graceful fallbacks for all tools |

### 🔧 Tool Implementations

1. **RAG Tool** — `tools.rag_tool(query, chunks, embeddings)` → retrieved answer
2. **Booking Persistence Tool** — `tools.booking_persistence_tool(payload)` → `booking_id`
3. **Email Tool** — `tools.email_tool(to, subject, data, id)` → success/failure
4. **Web Search Tool** — `tools.web_search_tool(transport, from, to, date)` → options list (Tavily + mock fallback)

### 🎁 Bonus Features

- Beautiful animated landing page with stars + cursor glow
- Booking progress tracker in sidebar
- "Collected so far" live preview in sidebar
- Admin: per-booking detail card with action buttons (confirm / cancel / delete)
- Admin: CSV export with timestamp
- My Bookings page with card-style layout
- Standalone Travel Guide FAQ page

---

## Booking Flow

```
User: "Book a flight"
  → Intent detected: booking
  → State: transport  → user clicks [✈️ Flight]
  → State: route      → "From?" → "To?"
  → State: date       → "Travel date?"
  → State: time       → "Preferred time?"
  → Tavily search (or mock) → options shown as buttons
  → State: details    → Name → Email → Phone
  → State: confirm    → Summary card shown
  → User: "Yes"
  → booking_persistence_tool() → SQLite → booking_id
  → email_tool() → confirmation email sent
  → State: done       → 🎉 success card
```

---

## Error Handling

- Invalid email → re-prompted with friendly message
- Invalid phone → re-prompted with friendly message  
- DB error → shown to user, booking not lost
- Email failure → booking saved, user notified email couldn't send
- Tavily failure → graceful fallback to mock options
- RAG with no chunks → "Please upload a PDF first"
- No Gemini key → keyword-based intent detection fallback

---

## Schema

```sql
-- customers
customer_id TEXT PRIMARY KEY,
name        TEXT NOT NULL,
email       TEXT NOT NULL UNIQUE,
phone       TEXT NOT NULL,
created_at  TEXT

-- bookings
id              TEXT PRIMARY KEY,       -- GG-XXXXXX
customer_id     TEXT (FK → customers),
booking_type    TEXT,                   -- Flight / Train / Bus
from_city       TEXT,
to_city         TEXT,
date            TEXT,
time            TEXT,
selected_option TEXT,
status          TEXT DEFAULT 'confirmed',
created_at      TEXT
```
