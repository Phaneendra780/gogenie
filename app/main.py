"""
app/main.py — GoGenie Streamlit Entry Point
Pages: landing | chat | bookings | faq | admin
Wires: Gemini 2.0 Flash · Tavily · SQLite · SMTP · RAG pipeline
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import streamlit.components.v1 as components

# ── App init ──────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title = "GoGenie – AI Travel Assistant",
    page_icon  = "🧞",
    layout     = "wide",
    initial_sidebar_state = "collapsed"
)

# ── DB init (runs once per process) ──────────────────────────────────────────
from db.database import init_db
init_db()

# ── Global CSS reset ──────────────────────────────────────────────────────────
st.markdown("""
<style>
  #MainMenu, footer, header { visibility: hidden; }
  .block-container { padding: 0 !important; max-width: 100% !important; }
  [data-testid="stAppViewContainer"] { background: #04071a; }
</style>
""", unsafe_allow_html=True)

# ── Session state defaults ────────────────────────────────────────────────────
def _init_session():
    defaults = {
        "page":                 "landing",
        "messages":             [],
        "booking_state":        None,
        "booking_data":         {},
        "uploaded_pdfs":        [],
        "pdf_chunks":           [],
        "pdf_embeddings":       [],
        "pdf_ingested":         False,
        "show_options":         [],
        "pending_option_select": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_session()

# ── Query-param routing ───────────────────────────────────────────────────────
qp = st.query_params
if "page" in qp:
    st.session_state.page = qp["page"]


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def nav_to(page: str):
    st.session_state.page = page
    st.rerun()

def add_msg(role: str, content: str, **kwargs):
    msg = {"role": role, "content": content}
    msg.update(kwargs)
    st.session_state.messages.append(msg)
    # Enforce 25-message memory cap
    if len(st.session_state.messages) > 50:
        st.session_state.messages = st.session_state.messages[-25:]

def reset_booking():
    st.session_state.booking_state        = None
    st.session_state.booking_data         = {}
    st.session_state.show_options         = []
    st.session_state.pending_option_select = False


# ═══════════════════════════════════════════════════════════════════════════════
# LANDING PAGE
# ═══════════════════════════════════════════════════════════════════════════════
if st.session_state.page == "landing":

    landing_html = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet"/>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --night: #04071a; --deep: #080d2e; --gold: #f5c542; --gold2: #ffab00;
    --sky: #4fa3e0; --mist: #c8d8f0;
    --glow: rgba(245,197,66,0.18);
    --card-bg: rgba(255,255,255,0.035);
    --card-border: rgba(255,255,255,0.08);
  }
  html, body { min-height: 100vh; background: var(--night); color: var(--mist);
    font-family: 'DM Sans', sans-serif; overflow-x: hidden; }
  #stars-canvas { position: fixed; inset: 0; z-index: 0; pointer-events: none; }
  .orb { position: fixed; border-radius: 50%; filter: blur(80px); pointer-events: none; z-index: 0; }
  .orb1 { width:500px;height:500px;background:rgba(79,163,224,0.12);top:-100px;left:-120px; }
  .orb2 { width:400px;height:400px;background:rgba(245,197,66,0.10);bottom:50px;right:-80px; }
  .orb3 { width:300px;height:300px;background:rgba(120,80,200,0.10);top:40%;left:40%; }
  nav { position:fixed;top:0;left:0;right:0;z-index:100;display:flex;align-items:center;
    justify-content:space-between;padding:20px 60px;
    background:linear-gradient(180deg,rgba(4,7,26,0.95) 0%,transparent 100%);backdrop-filter:blur(2px); }
  .logo { font-family:'Syne',sans-serif;font-weight:800;font-size:1.5rem;color:#fff;
    letter-spacing:-0.5px;display:flex;align-items:center;gap:8px; }
  .logo span { color:var(--gold); }
  .nav-links { display:flex;gap:32px;align-items:center; }
  .nav-links a { color:rgba(200,216,240,0.65);text-decoration:none;font-size:0.875rem;
    font-weight:400;letter-spacing:0.3px;transition:color 0.2s; }
  .nav-links a:hover { color:#fff; }
  .nav-btn { background:var(--gold);color:#1a1000;border:none;padding:9px 22px;
    border-radius:100px;font-family:'DM Sans',sans-serif;font-weight:500;font-size:0.875rem;
    cursor:pointer;transition:all 0.2s; }
  .nav-btn:hover { background:#fff;transform:translateY(-1px); }
  .hero { position:relative;z-index:1;min-height:100vh;display:flex;flex-direction:column;
    align-items:center;justify-content:center;text-align:center;padding:120px 24px 60px; }
  .hero-badge { display:inline-flex;align-items:center;gap:6px;
    background:rgba(245,197,66,0.1);border:1px solid rgba(245,197,66,0.25);
    border-radius:100px;padding:6px 16px;font-size:0.78rem;font-weight:500;color:var(--gold);
    letter-spacing:0.8px;text-transform:uppercase;margin-bottom:28px;
    animation:fadeSlideUp 0.7s ease both; }
  .badge-dot { width:6px;height:6px;border-radius:50%;background:var(--gold);animation:pulse 2s ease infinite; }
  @keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.5;transform:scale(1.4)} }
  .hero h1 { font-family:'Syne',sans-serif;font-weight:800;
    font-size:clamp(2.8rem,7vw,5.5rem);line-height:1.05;letter-spacing:-2px;
    color:#fff;margin-bottom:20px;animation:fadeSlideUp 0.7s 0.1s ease both; }
  .hero h1 .accent { color:var(--gold); }
  .hero h1 .sky-text { color:var(--sky); }
  .hero p { max-width:540px;font-size:1.1rem;line-height:1.7;
    color:rgba(200,216,240,0.65);margin-bottom:40px;animation:fadeSlideUp 0.7s 0.2s ease both; }
  .hero-cta { display:flex;gap:14px;flex-wrap:wrap;justify-content:center;animation:fadeSlideUp 0.7s 0.3s ease both; }
  .btn-primary { background:var(--gold);color:#1a1000;border:none;padding:14px 32px;
    border-radius:100px;font-family:'DM Sans',sans-serif;font-weight:500;font-size:1rem;
    cursor:pointer;transition:all 0.25s;display:flex;align-items:center;gap:8px;
    box-shadow:0 0 30px rgba(245,197,66,0.3); }
  .btn-primary:hover { background:#fff;transform:translateY(-2px);box-shadow:0 0 50px rgba(245,197,66,0.4); }
  .btn-secondary { background:transparent;color:var(--mist);
    border:1px solid rgba(255,255,255,0.15);padding:14px 32px;border-radius:100px;
    font-family:'DM Sans',sans-serif;font-weight:400;font-size:1rem;
    cursor:pointer;transition:all 0.25s; }
  .btn-secondary:hover { border-color:rgba(255,255,255,0.4);color:#fff;transform:translateY(-2px); }
  .floating-plane { font-size:3.5rem;margin-bottom:12px;display:block;animation:floatPlane 4s ease-in-out infinite; }
  @keyframes floatPlane { 0%,100%{transform:translateY(0) rotate(-5deg)} 50%{transform:translateY(-14px) rotate(5deg)} }
  section { position:relative;z-index:1;padding:100px 60px;max-width:1200px;margin:0 auto; }
  .section-label { font-size:0.75rem;font-weight:500;color:var(--gold);letter-spacing:2px;text-transform:uppercase;margin-bottom:12px; }
  .section-title { font-family:'Syne',sans-serif;font-weight:700;font-size:clamp(1.8rem,3.5vw,2.8rem);
    line-height:1.15;letter-spacing:-0.8px;color:#fff;margin-bottom:16px; }
  .section-sub { color:rgba(200,216,240,0.55);font-size:1rem;line-height:1.7;max-width:460px;margin-bottom:56px; }
  .cards-grid { display:grid;grid-template-columns:repeat(4,1fr);gap:18px; }
  .card { position:relative;overflow:hidden;background:var(--card-bg);border:1px solid var(--card-border);
    border-radius:20px;padding:32px 26px;cursor:pointer;transition:all 0.35s cubic-bezier(0.23,1,0.32,1); }
  .card::before { content:'';position:absolute;inset:0;border-radius:20px;
    background:linear-gradient(135deg,rgba(245,197,66,0.06) 0%,transparent 60%);opacity:0;transition:opacity 0.35s; }
  .card:hover { transform:translateY(-6px);border-color:rgba(245,197,66,0.3);
    box-shadow:0 24px 60px rgba(0,0,0,0.4),0 0 0 1px rgba(245,197,66,0.1); }
  .card:hover::before { opacity:1; }
  .card-icon { width:48px;height:48px;border-radius:12px;display:flex;align-items:center;
    justify-content:center;font-size:1.3rem;margin-bottom:18px;
    background:rgba(245,197,66,0.1);border:1px solid rgba(245,197,66,0.2);transition:transform 0.3s; }
  .card:hover .card-icon { transform:scale(1.1) rotate(-4deg); }
  .card-icon.blue { background:rgba(79,163,224,0.1);border-color:rgba(79,163,224,0.2); }
  .card-icon.purple { background:rgba(140,80,220,0.1);border-color:rgba(140,80,220,0.2); }
  .card-icon.green { background:rgba(34,197,94,0.1);border-color:rgba(34,197,94,0.2); }
  .card h3 { font-family:'Syne',sans-serif;font-weight:700;font-size:1.1rem;color:#fff;margin-bottom:8px; }
  .card p { color:rgba(200,216,240,0.5);font-size:0.88rem;line-height:1.6; }
  .card-arrow { position:absolute;top:26px;right:26px;color:rgba(255,255,255,0.2);font-size:1.1rem;transition:all 0.3s; }
  .card:hover .card-arrow { color:var(--gold);transform:translate(3px,-3px); }
  .steps { display:grid;grid-template-columns:repeat(4,1fr);gap:0;position:relative; }
  .steps::before { content:'';position:absolute;top:28px;left:12%;right:12%;height:1px;
    background:linear-gradient(90deg,transparent,rgba(245,197,66,0.3),transparent);z-index:0; }
  .step { text-align:center;padding:0 16px;position:relative;z-index:1; }
  .step-num { width:56px;height:56px;border-radius:50%;background:var(--deep);
    border:1px solid rgba(245,197,66,0.3);display:flex;align-items:center;justify-content:center;
    font-family:'Syne',sans-serif;font-weight:700;font-size:1.1rem;color:var(--gold);margin:0 auto 20px; }
  .step:hover .step-num { background:var(--gold);color:#1a1000;transform:scale(1.1); }
  .step h4 { font-family:'Syne',sans-serif;font-weight:700;font-size:1rem;color:#fff;margin-bottom:8px; }
  .step p { font-size:0.85rem;color:rgba(200,216,240,0.5);line-height:1.6; }
  .transport-strip { display:flex;gap:12px;flex-wrap:wrap;margin-top:40px; }
  .chip { display:flex;align-items:center;gap:8px;background:rgba(255,255,255,0.04);
    border:1px solid rgba(255,255,255,0.1);border-radius:100px;padding:10px 20px;
    font-size:0.9rem;color:var(--mist);transition:all 0.25s;cursor:default; }
  .chip:hover { background:rgba(245,197,66,0.1);border-color:var(--gold);color:#fff; }
  footer { position:relative;z-index:1;border-top:1px solid rgba(255,255,255,0.06);
    padding:40px 60px;display:flex;align-items:center;justify-content:space-between;
    color:rgba(200,216,240,0.35);font-size:0.82rem; }
  footer strong { color:var(--gold); }
  @keyframes fadeSlideUp { from{opacity:0;transform:translateY(24px)} to{opacity:1;transform:translateY(0)} }
  #cursor-glow { position:fixed;pointer-events:none;z-index:9999;width:300px;height:300px;
    border-radius:50%;background:radial-gradient(circle,rgba(245,197,66,0.06) 0%,transparent 70%);
    transform:translate(-50%,-50%);transition:opacity 0.3s; }
</style>
</head>
<body>
<canvas id="stars-canvas"></canvas>
<div class="orb orb1"></div><div class="orb orb2"></div><div class="orb orb3"></div>
<div id="cursor-glow"></div>
<nav>
  <div class="logo">🧞 Go<span>Genie</span></div>
  <div class="nav-links">
    <a href="#features">Features</a>
    <a href="#how">How it works</a>
    <a href="#transports">Routes</a>
    <button class="nav-btn">Start booking →</button>
  </div>
</nav>
<div class="hero">
  <span class="floating-plane">✈️</span>
  <div class="hero-badge"><span class="badge-dot"></span> AI-powered travel booking</div>
  <h1>Your <span class="accent">Genie</span> for<br>every <span class="sky-text">journey</span></h1>
  <p>Tell the Genie where you want to go. It handles flights, trains & buses — all through a simple conversation powered by Gemini AI.</p>
  <div class="hero-cta">
    <button class="btn-primary">🧞 Chat with Genie</button>
    <button class="btn-secondary">My Bookings</button>
  </div>
</div>
<section id="features">
  <div class="section-label">What GoGenie does</div>
  <div class="section-title">Four tools,<br>one assistant</div>
  <div class="section-sub">Everything you need for a trip — booked in one conversation.</div>
  <div class="cards-grid">
    <div class="card"><div class="card-arrow">↗</div><div class="card-icon">🧞</div>
      <h3>Chat & Book</h3><p>Gemini AI understands natural language and guides you through booking any transport.</p></div>
    <div class="card"><div class="card-arrow">↗</div><div class="card-icon blue">📄</div>
      <h3>PDF Travel Guide</h3><p>Upload luggage rules, visa guides or timetables — Genie reads them and answers instantly via RAG.</p></div>
    <div class="card"><div class="card-arrow">↗</div><div class="card-icon purple">🎫</div>
      <h3>My Bookings</h3><p>All your trips in one place. Loaded from SQLite/Supabase in real time.</p></div>
    <div class="card"><div class="card-arrow">↗</div><div class="card-icon green">🛡️</div>
      <h3>Admin Dashboard</h3><p>Full booking management: search, filter, confirm, cancel, export CSV.</p></div>
  </div>
</section>
<section id="how" style="padding-top:0;">
  <div class="section-label">How it works</div>
  <div class="section-title">Four steps to<br>your next trip</div>
  <div class="section-sub" style="margin-bottom:64px;">No forms, no tabs, no hassle.</div>
  <div class="steps">
    <div class="step"><div class="step-num">01</div><h4>Pick transport</h4><p>Flight, train or bus</p></div>
    <div class="step"><div class="step-num">02</div><h4>Set your route</h4><p>Source, destination, date</p></div>
    <div class="step"><div class="step-num">03</div><h4>Choose option</h4><p>Live options via Tavily</p></div>
    <div class="step"><div class="step-num">04</div><h4>Confirm & go</h4><p>Saved to DB, email sent</p></div>
  </div>
</section>
<section id="transports" style="padding-top:0;">
  <div class="section-label">Supported routes</div>
  <div class="section-title">Wherever you're<br>headed, we've got it</div>
  <div class="transport-strip">
    <div class="chip">✈️ Flights</div><div class="chip">🚂 Trains</div><div class="chip">🚌 Buses</div>
    <div class="chip">🏙️ City to city</div><div class="chip">🌍 International</div><div class="chip">🔁 Round trips</div>
  </div>
</section>
<footer>
  <div>Built with 🧞 by GoGenie · <strong>AI-powered travel</strong></div>
  <div>Streamlit · Gemini 2.0 Flash · Tavily · SQLite/Supabase</div>
</footer>
<script>
const canvas = document.getElementById('stars-canvas');
const ctx    = canvas.getContext('2d');
let stars    = [];
function resize() { canvas.width = window.innerWidth; canvas.height = window.innerHeight; }
resize(); window.addEventListener('resize', resize);
for (let i=0;i<180;i++) stars.push({x:Math.random(),y:Math.random(),r:Math.random()*1.2+0.2,a:Math.random(),speed:Math.random()*0.002+0.0005,tw:Math.random()*Math.PI*2});
function drawStars(ts){
  ctx.clearRect(0,0,canvas.width,canvas.height);
  stars.forEach(s=>{
    s.a = 0.3+0.7*Math.abs(Math.sin(ts*s.speed*3+s.tw));
    ctx.beginPath(); ctx.arc(s.x*canvas.width,s.y*canvas.height,s.r,0,Math.PI*2);
    ctx.fillStyle=`rgba(255,255,255,${s.a*0.8})`; ctx.fill();
  }); requestAnimationFrame(drawStars);
} requestAnimationFrame(drawStars);
const glow = document.getElementById('cursor-glow');
document.addEventListener('mousemove',e=>{glow.style.left=e.clientX+'px';glow.style.top=e.clientY+'px';});
</script>
</body>
</html>
"""
    components.html(landing_html, height=900, scrolling=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            if st.button("🧞 Chat", use_container_width=True, type="primary"):
                nav_to("chat")
        with c2:
            if st.button("🎫 Bookings", use_container_width=True):
                nav_to("bookings")
        with c3:
            if st.button("📄 PDF Guide", use_container_width=True):
                nav_to("faq")
        with c4:
            if st.button("🛡️ Admin", use_container_width=True):
                nav_to("admin")


# ═══════════════════════════════════════════════════════════════════════════════
# CHAT PAGE
# ═══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "chat":

    # ── Chat page styles ──────────────────────────────────────────────────────
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@600;700&family=DM+Sans:wght@300;400;500&display=swap');
    [data-testid="stAppViewContainer"] { background: #04071a; }
    [data-testid="stSidebar"] { background: #080d2e !important; border-right: 1px solid rgba(255,255,255,0.07); }
    [data-testid="stSidebar"] * { color: #c8d8f0 !important; }
    .block-container { padding: 0 !important; max-width: 100% !important; }
    [data-testid="stChatMessage"] { background: transparent !important; padding: 6px 0 !important; }
    [data-testid="stChatInput"] textarea {
        background: rgba(255,255,255,0.05) !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        border-radius: 16px !important; color: #fff !important;
        font-family: 'DM Sans', sans-serif !important;
    }
    [data-testid="stChatInput"] textarea:focus {
        border-color: rgba(245,197,66,0.4) !important;
        box-shadow: 0 0 0 2px rgba(245,197,66,0.1) !important;
    }
    [data-testid="stFileUploader"] {
        background: rgba(255,255,255,0.03) !important;
        border: 1px dashed rgba(245,197,66,0.3) !important;
        border-radius: 12px !important; padding: 12px !important;
    }
    div[data-testid="column"] .stButton button {
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        border-radius: 12px !important; color: #c8d8f0 !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 0.88rem !important; padding: 10px 14px !important;
        transition: all 0.2s !important; width: 100% !important;
        white-space: normal !important; text-align: left !important;
    }
    div[data-testid="column"] .stButton button:hover {
        background: rgba(245,197,66,0.1) !important;
        border-color: rgba(245,197,66,0.4) !important;
        color: #f5c542 !important; transform: translateY(-2px) !important;
    }
    .status-info { background:rgba(79,163,224,0.1);border:1px solid rgba(79,163,224,0.3);
        border-radius:12px;padding:12px 16px;color:#93c5fd;font-size:0.88rem;margin:6px 0; }
    .confirm-card { background:rgba(255,255,255,0.04);border:1px solid rgba(245,197,66,0.25);
        border-radius:16px;padding:20px 24px;margin:10px 0; }
    .confirm-card h4 { font-family:'Syne',sans-serif;font-size:0.95rem;color:#f5c542;margin-bottom:12px; }
    .confirm-row { display:flex;justify-content:space-between;padding:6px 0;
        border-bottom:1px solid rgba(255,255,255,0.05);font-size:0.86rem; }
    .confirm-row:last-child { border-bottom:none; }
    .confirm-label { color:rgba(200,216,240,0.45); }
    .confirm-value { color:#fff;font-weight:500; }
    .booking-success { background:linear-gradient(135deg,rgba(34,197,94,0.12),rgba(245,197,66,0.08));
        border:1px solid rgba(34,197,94,0.3);border-radius:20px;padding:28px 32px;
        text-align:center;margin:12px 0; }
    .booking-success .tick { font-size:2.5rem;display:block;margin-bottom:10px; }
    .booking-success h3 { font-family:'Syne',sans-serif;font-size:1.25rem;color:#86efac;margin-bottom:8px; }
    .booking-success p { color:rgba(200,216,240,0.65);font-size:0.88rem; }
    .booking-id { display:inline-block;margin-top:12px;background:rgba(245,197,66,0.15);
        border:1px solid rgba(245,197,66,0.3);border-radius:8px;padding:6px 16px;
        color:#f5c542;font-size:0.85rem;font-family:monospace;letter-spacing:1px; }
    </style>
    """, unsafe_allow_html=True)

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("""
        <div style='padding:8px 0 20px;'>
            <div style='font-family:Syne,sans-serif;font-size:1.2rem;font-weight:700;color:#fff;'>🧞 GoGenie</div>
            <div style='font-size:0.75rem;color:rgba(200,216,240,0.45);margin-top:3px;'>AI Travel Assistant</div>
        </div>""", unsafe_allow_html=True)

        if st.button("← Home", use_container_width=True):
            nav_to("landing")
        if st.button("🛡️ Admin", use_container_width=True):
            nav_to("admin")

        st.markdown("---")

        # ── PDF Upload ────────────────────────────────────────────────────────
        st.markdown("""
        <div style='font-size:0.78rem;font-weight:500;color:rgba(200,216,240,0.55);
             letter-spacing:1px;text-transform:uppercase;margin-bottom:8px;'>
            📄 Travel PDF Upload
        </div>
        <div style='font-size:0.76rem;color:rgba(200,216,240,0.35);margin-bottom:10px;line-height:1.5;'>
            Upload luggage rules, visa guides or timetables — Genie answers from them.
        </div>""", unsafe_allow_html=True)

        uploaded_files = st.file_uploader(
            "Upload PDF(s)", type=["pdf"], accept_multiple_files=True,
            label_visibility="collapsed"
        )

        if uploaded_files:
            # Ingest PDFs if new files were uploaded
            names = [f.name for f in uploaded_files]
            prev  = [f.name for f in st.session_state.uploaded_pdfs] if st.session_state.uploaded_pdfs else []

            if names != prev or not st.session_state.pdf_ingested:
                import config as cfg
                if cfg.GEMINI_ENABLED:
                    with st.spinner("📖 Processing PDFs..."):
                        from app.rag_pipeline import ingest_pdfs
                        chunks, embeddings = ingest_pdfs(uploaded_files)
                        st.session_state.pdf_chunks     = chunks
                        st.session_state.pdf_embeddings = embeddings
                        st.session_state.pdf_ingested   = True
                    st.markdown(f"""<div class='status-info'>
                        ✅ {len(uploaded_files)} PDF(s) processed · {len(chunks)} chunks indexed
                    </div>""", unsafe_allow_html=True)
                else:
                    st.session_state.pdf_ingested = True
                    st.markdown("""<div class='status-info'>
                        ⚠️ PDF uploaded (add GEMINI_API_KEY to enable RAG search)
                    </div>""", unsafe_allow_html=True)
                st.session_state.uploaded_pdfs = uploaded_files

        st.markdown("---")

        # ── Booking progress tracker ──────────────────────────────────────────
        bstate = st.session_state.booking_state
        bdata  = st.session_state.booking_data

        if bstate and bstate not in ("done", "cancelled"):
            steps   = ["transport","route","date","time","options","details","confirm"]
            cur_idx = steps.index(bstate) if bstate in steps else -1

            st.markdown("""<div style='font-size:0.78rem;font-weight:500;color:rgba(200,216,240,0.55);
                 letter-spacing:1px;text-transform:uppercase;margin-bottom:12px;'>
                🎫 Booking Progress</div>""", unsafe_allow_html=True)

            icons = {"transport":"🚀","route":"📍","date":"📅","time":"⏰","options":"🔍","details":"👤","confirm":"✅"}
            for i, s in enumerate(steps):
                color = "#86efac" if i < cur_idx else ("#f5c542" if i == cur_idx else "rgba(200,216,240,0.2)")
                sym   = "✓" if i < cur_idx else ("●" if i == cur_idx else "○")
                st.markdown(f"""<div style='display:flex;align-items:center;gap:8px;padding:3px 0;
                     font-size:0.8rem;color:{color};'>
                    <span>{sym}</span><span>{icons.get(s,'')} {s.title()}</span>
                </div>""", unsafe_allow_html=True)

            if bdata:
                st.markdown("---")
                st.markdown("""<div style='font-size:0.72rem;color:rgba(200,216,240,0.35);
                     letter-spacing:0.8px;text-transform:uppercase;margin-bottom:6px;'>
                    Collected so far</div>""", unsafe_allow_html=True)
                field_icons = {"transport":"🚀","from":"📍","to":"📍","date":"📅",
                               "time":"⏰","selected_option":"🎫","name":"👤","email":"📧","phone":"📱"}
                for k, v in bdata.items():
                    if v:
                        ico = field_icons.get(k, "•")
                        label = "option" if k == "selected_option" else k
                        val   = str(v)[:30] + "…" if len(str(v)) > 30 else str(v)
                        st.markdown(f"""<div style='font-size:0.76rem;color:rgba(200,216,240,0.55);
                             padding:2px 0;display:flex;gap:6px;'>
                            <span>{ico}</span>
                            <span style='color:rgba(200,216,240,0.3);'>{label}:</span>
                            <span style='color:#e0e8ff;'>{val}</span>
                        </div>""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("✕ Cancel booking", use_container_width=True):
                reset_booking()
                add_msg("assistant", "Booking cancelled. How else can I help you? 🧞")
                st.rerun()
        else:
            st.markdown("""<div style='font-size:0.76rem;color:rgba(200,216,240,0.3);line-height:1.7;'>
                💡 <strong style='color:rgba(200,216,240,0.5);'>Tips:</strong><br>
                • Say <em>"Book a flight"</em> to start<br>
                • Ask about your uploaded PDFs<br>
                • Say <em>"My bookings"</em> to view trips<br>
                • Visit Admin to manage bookings
            </div>""", unsafe_allow_html=True)

    # ── Chat header ───────────────────────────────────────────────────────────
    import config as cfg
    ai_status = "🟢 Online · Gemini 2.0 Flash" if cfg.GEMINI_ENABLED else "🟡 Online · Keyword mode (add GEMINI_API_KEY)"
    tavily_tag = " · Tavily Search" if cfg.TAVILY_ENABLED else ""
    db_tag     = " · SQLite"

    st.markdown(f"""
    <div style='background:linear-gradient(180deg,#04071a 0%,rgba(4,7,26,0.95) 100%);
         border-bottom:1px solid rgba(255,255,255,0.06);padding:16px 28px;
         display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:10;'>
        <div style='display:flex;align-items:center;gap:12px;'>
            <div style='width:40px;height:40px;border-radius:50%;
                 background:rgba(245,197,66,0.15);border:1px solid rgba(245,197,66,0.3);
                 display:flex;align-items:center;justify-content:center;font-size:1.2rem;'>🧞</div>
            <div>
                <div style='font-family:Syne,sans-serif;font-size:1rem;font-weight:700;color:#fff;'>Genie</div>
                <div style='font-size:0.7rem;color:rgba(34,197,94,0.8);'>{ai_status}{tavily_tag}{db_tag}</div>
            </div>
        </div>
        <div style='font-size:0.76rem;color:rgba(200,216,240,0.3);'>GoGenie AI Travel Booking</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Welcome message ───────────────────────────────────────────────────────
    if not st.session_state.messages:
        add_msg("assistant",
            "✨ **Hey there! I'm Genie, your AI travel assistant.**\n\n"
            "I can help you:\n"
            "- 🎫 **Book** flights, trains or buses\n"
            "- 📄 **Answer questions** from your uploaded travel PDFs\n"
            "- 🗂️ **View** your past bookings\n\n"
            "Just say **\"Book a flight\"** or ask me anything! 🧞"
        )

    # ── Render message history ────────────────────────────────────────────────
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar="🧞" if msg["role"] == "assistant" else "👤"):
            mtype = msg.get("type", "")

            if mtype == "success":
                st.markdown(f"""
                <div class='booking-success'>
                    <span class='tick'>🎉</span>
                    <h3>Booking Confirmed!</h3>
                    <p>{msg['content']}</p>
                    <div class='booking-id'>#{msg.get('booking_id','GG-??????')}</div>
                </div>""", unsafe_allow_html=True)

            elif mtype == "confirm_card":
                d = msg.get("data", {})
                st.markdown(f"""
                <div class='confirm-card'>
                    <h4>📋 Booking Summary</h4>
                    <div class='confirm-row'><span class='confirm-label'>Transport</span><span class='confirm-value'>{d.get('transport','—')}</span></div>
                    <div class='confirm-row'><span class='confirm-label'>Route</span><span class='confirm-value'>{d.get('from','—')} → {d.get('to','—')}</span></div>
                    <div class='confirm-row'><span class='confirm-label'>Date</span><span class='confirm-value'>{d.get('date','—')}</span></div>
                    <div class='confirm-row'><span class='confirm-label'>Time</span><span class='confirm-value'>{d.get('time','—')}</span></div>
                    <div class='confirm-row'><span class='confirm-label'>Option</span><span class='confirm-value'>{d.get('selected_option','—')}</span></div>
                    <div class='confirm-row'><span class='confirm-label'>Passenger</span><span class='confirm-value'>{d.get('name','—')}</span></div>
                    <div class='confirm-row'><span class='confirm-label'>Email</span><span class='confirm-value'>{d.get('email','—')}</span></div>
                    <div class='confirm-row'><span class='confirm-label'>Phone</span><span class='confirm-value'>{d.get('phone','—')}</span></div>
                </div>
                <div style='color:rgba(200,216,240,0.55);font-size:0.88rem;margin-top:8px;'>
                    Everything look right? Reply <strong style='color:#86efac;'>Yes</strong> to confirm
                    or <strong style='color:#fca5a5;'>No</strong> to cancel.
                </div>""", unsafe_allow_html=True)

            else:
                st.markdown(msg["content"])

    # ── Option selection buttons ───────────────────────────────────────────────
    if st.session_state.pending_option_select and st.session_state.show_options:
        options = st.session_state.show_options
        st.markdown("""<div style='padding:6px 0 4px;font-size:0.8rem;
             color:rgba(200,216,240,0.4);letter-spacing:0.5px;'>
            Tap to select your preferred option:
        </div>""", unsafe_allow_html=True)
        cols = st.columns(min(len(options), 2))
        for i, opt in enumerate(options):
            with cols[i % 2]:
                if st.button(opt, key=f"opt_{i}", use_container_width=True):
                    from app.booking_flow import handle_option_selection
                    bdata, new_state, resp = handle_option_selection(opt, st.session_state.booking_data)
                    st.session_state.booking_data         = bdata
                    st.session_state.booking_state        = new_state
                    st.session_state.pending_option_select = False
                    st.session_state.show_options         = []
                    add_msg("user",      f"I'll take: {opt}")
                    add_msg("assistant", resp)
                    st.rerun()

    # ── Transport type buttons (at start of booking) ──────────────────────────
    if st.session_state.booking_state == "transport":
        st.markdown("""<div style='padding:6px 0 4px;font-size:0.8rem;
             color:rgba(200,216,240,0.4);'>Choose your mode of transport:</div>""", unsafe_allow_html=True)
        t_cols = st.columns(3)
        transports = [("✈️ Flight", "Flight"), ("🚂 Train", "Train"), ("🚌 Bus", "Bus")]
        for i, (label, val) in enumerate(transports):
            with t_cols[i]:
                if st.button(label, key=f"transport_{val}", use_container_width=True):
                    st.session_state.booking_data["transport"] = val
                    st.session_state.booking_state = "route"
                    add_msg("user", label)
                    add_msg("assistant", f"**{label}** it is! 🎯\n\nWhere are you **travelling from**?")
                    st.rerun()

    # ── Chat input ─────────────────────────────────────────────────────────────
    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

    if prompt := st.chat_input("Message Genie… (e.g. 'Book a flight' or ask anything)"):
        add_msg("user", prompt)
        bstate = st.session_state.booking_state
        bdata  = st.session_state.booking_data

        # ── Active booking flow ───────────────────────────────────────────────
        if bstate and bstate not in ("done", "cancelled"):
            from app.booking_flow import (
                process_booking_input, SIGNAL_CONFIRM_CARD, SIGNAL_SUCCESS
            )
            new_bdata, new_state, bot_resp, options, pending = process_booking_input(
                user_input    = prompt,
                booking_state = bstate,
                booking_data  = bdata
            )
            st.session_state.booking_data  = new_bdata
            st.session_state.booking_state = new_state

            if bot_resp == SIGNAL_CONFIRM_CARD:
                add_msg("assistant", "Almost there! Let me summarise your booking:",
                        type="confirm_card", data=dict(new_bdata))

            elif bot_resp.startswith(SIGNAL_SUCCESS):
                _, booking_id, email_msg = bot_resp.split(":", 2)
                add_msg("assistant",
                        f"Saved to database ✅  |  {email_msg}",
                        type="success", booking_id=booking_id)
                reset_booking()

            elif new_state == "cancelled":
                add_msg("assistant", bot_resp)
                reset_booking()

            else:
                add_msg("assistant", bot_resp)

            if options:
                st.session_state.show_options         = options
                st.session_state.pending_option_select = True

        # ── Intent routing (no active booking) ───────────────────────────────
        else:
            from app.chat_logic import detect_intent, general_chat
            from app.tools      import rag_tool

            intent = detect_intent(prompt, st.session_state.messages)

            if intent == "view_bookings":
                nav_to("bookings")

            elif intent == "booking":
                st.session_state.booking_state = "transport"
                st.session_state.booking_data  = {}
                add_msg("assistant",
                    "🧞 Great! Let's get your trip sorted.\n\n**Which mode of transport would you like?**")

            elif intent == "pdf_query":
                if st.session_state.pdf_chunks and st.session_state.pdf_embeddings:
                    with st.spinner("🔍 Searching your documents..."):
                        result = rag_tool(prompt, st.session_state.pdf_chunks, st.session_state.pdf_embeddings)
                    add_msg("assistant",
                        result["answer"] if result["success"]
                        else f"⚠️ RAG error: {result['answer']}")
                elif st.session_state.uploaded_pdfs:
                    add_msg("assistant",
                        "⚠️ PDFs uploaded but not yet indexed (add GEMINI_API_KEY to enable RAG).")
                else:
                    add_msg("assistant",
                        "📄 I don't see any uploaded PDFs yet! Upload one via the sidebar and I'll answer questions from it.")

            elif intent == "confirm" and bstate == "confirm":
                # Forward into booking flow
                from app.booking_flow import process_booking_input, SIGNAL_SUCCESS
                new_bdata, new_state, bot_resp, _, _ = process_booking_input(prompt, "confirm", bdata)
                st.session_state.booking_data  = new_bdata
                st.session_state.booking_state = new_state
                if bot_resp.startswith(SIGNAL_SUCCESS):
                    _, booking_id, email_msg = bot_resp.split(":", 2)
                    add_msg("assistant", f"Saved ✅  |  {email_msg}", type="success", booking_id=booking_id)
                    reset_booking()
                else:
                    add_msg("assistant", bot_resp)

            else:  # general
                with st.spinner("🧞 Thinking..."):
                    reply = general_chat(prompt, st.session_state.messages)
                add_msg("assistant", reply)

        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# BOOKINGS PAGE
# ═══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "bookings":
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background: #04071a; }
    [data-testid="stTextInput"] input {
        background: rgba(255,255,255,0.05) !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        border-radius: 10px !important; color: #fff !important;
    }
    </style>""", unsafe_allow_html=True)

    col_b, col_t = st.columns([1, 5])
    with col_b:
        if st.button("← Home"):
            nav_to("landing")

    st.markdown("""
    <div style='padding:28px 0 4px;'>
        <div style='font-family:Syne,sans-serif;font-size:1.8rem;font-weight:800;color:#fff;'>🎫 My Bookings</div>
        <div style='color:rgba(200,216,240,0.45);font-size:0.85rem;margin-top:4px;'>Your travel history</div>
    </div>""", unsafe_allow_html=True)

    email_filter = st.text_input("🔍 Search by email to find your bookings:", placeholder="your@email.com")

    from db.database import get_all_bookings, get_bookings_by_email
    import pandas as pd

    bookings = get_bookings_by_email(email_filter.strip()) if email_filter.strip() else get_all_bookings()

    if not bookings:
        st.markdown("""
        <div style='text-align:center;padding:60px;color:rgba(200,216,240,0.35);'>
            <div style='font-size:3rem;margin-bottom:12px;'>✈️</div>
            <div>No bookings found. <a href='#' style='color:#f5c542;'>Book your first trip!</a></div>
        </div>""", unsafe_allow_html=True)
    else:
        for b in bookings:
            status_color = "#86efac" if b.get("status") == "confirmed" else "#fca5a5"
            transport_emoji = {"Flight": "✈️", "Train": "🚂", "Bus": "🚌"}.get(b.get("booking_type",""), "🎫")
            st.markdown(f"""
            <div style='background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);
                 border-radius:16px;padding:20px 24px;margin:10px 0;
                 display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px;'>
                <div>
                    <div style='display:flex;align-items:center;gap:10px;margin-bottom:8px;'>
                        <span style='font-size:1.4rem;'>{transport_emoji}</span>
                        <div>
                            <div style='font-family:Syne,sans-serif;font-size:1rem;font-weight:700;color:#fff;'>
                                {b.get("from_city","—")} → {b.get("to_city","—")}
                            </div>
                            <div style='font-size:0.78rem;color:rgba(200,216,240,0.4);'>
                                {b.get("date","—")} · {b.get("time","—")} · {b.get("booking_type","—")}
                            </div>
                        </div>
                    </div>
                    <div style='font-size:0.82rem;color:rgba(200,216,240,0.5);'>
                        {b.get("selected_option","—")[:70]}
                    </div>
                </div>
                <div style='text-align:right;'>
                    <div style='font-family:monospace;font-size:0.82rem;color:#f5c542;
                         background:rgba(245,197,66,0.1);border:1px solid rgba(245,197,66,0.2);
                         border-radius:6px;padding:4px 10px;margin-bottom:6px;'>
                        {b.get("id","—")}
                    </div>
                    <div style='font-size:0.78rem;color:{status_color};font-weight:600;'>
                        ● {(b.get("status","—") or "—").upper()}
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🧞 Book another trip", use_container_width=False):
        nav_to("chat")


# ═══════════════════════════════════════════════════════════════════════════════
# FAQ / TRAVEL GUIDE PAGE
# ═══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "faq":
    st.markdown("""
    <style>[data-testid="stAppViewContainer"] { background: #04071a; }</style>""", unsafe_allow_html=True)

    if st.button("← Home"):
        nav_to("landing")

    st.markdown("""
    <div style='padding:20px 0 4px;'>
        <div style='font-family:Syne,sans-serif;font-size:1.8rem;font-weight:800;color:#fff;'>📄 Travel Guide RAG</div>
        <div style='color:rgba(200,216,240,0.45);font-size:0.85rem;margin-top:4px;'>
            Upload a PDF — Genie will answer your questions from it
        </div>
    </div>""", unsafe_allow_html=True)

    uploaded = st.file_uploader("Upload travel PDF", type=["pdf"], accept_multiple_files=True)
    question = st.text_input("Ask a question about your document:", placeholder="e.g. What is the baggage allowance?")

    if st.button("🔍 Ask Genie", type="primary") and uploaded and question:
        import config as cfg
        if not cfg.GEMINI_ENABLED:
            st.error("Add GEMINI_API_KEY to secrets to enable RAG.")
        else:
            with st.spinner("📖 Reading documents and finding the answer..."):
                from app.rag_pipeline import ingest_pdfs, answer_from_pdf
                chunks, embeddings = ingest_pdfs(uploaded)
                answer = answer_from_pdf(question, chunks, embeddings)
            st.markdown(f"""
            <div style='background:rgba(79,163,224,0.08);border:1px solid rgba(79,163,224,0.25);
                 border-radius:14px;padding:20px 24px;margin-top:16px;color:#c8d8f0;'>
                <div style='font-size:0.75rem;color:rgba(79,163,224,0.7);font-weight:600;
                     letter-spacing:1px;text-transform:uppercase;margin-bottom:10px;'>
                    🧞 Genie's Answer
                </div>
                {answer}
            </div>""", unsafe_allow_html=True)

    elif st.button("🔍 Ask Genie", type="primary", key="faq_btn2"):
        st.warning("Please upload a PDF and enter a question.")

    st.markdown("<br>")
    if st.button("🧞 Go to full chat"):
        nav_to("chat")


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN DASHBOARD PAGE
# ═══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "admin":
    col_b, _ = st.columns([1, 5])
    with col_b:
        if st.button("← Home"):
            nav_to("landing")

    from app.admin_dashboard import render_admin_dashboard
    render_admin_dashboard()
