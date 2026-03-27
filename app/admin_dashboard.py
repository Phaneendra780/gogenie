"""
app/admin_dashboard.py — GoGenie Admin Dashboard
MANDATORY requirement per assignment spec.
Features: view all bookings, search/filter, stats, export CSV, status management.
"""

import streamlit as st
import pandas as pd
from datetime import datetime

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from db.database import get_all_bookings, search_bookings, update_booking_status, delete_booking


def render_admin_dashboard():
    """Main entry point — renders the complete admin dashboard page."""

    # ── Page styles ───────────────────────────────────────────────────────────
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=DM+Sans:wght@300;400;500&display=swap');

    [data-testid="stAppViewContainer"] { background: #04071a; }
    [data-testid="stSidebar"] {
        background: #080d2e !important;
        border-right: 1px solid rgba(255,255,255,0.06);
    }
    * { font-family: 'DM Sans', sans-serif; }
    h1, h2, h3 { font-family: 'Syne', sans-serif !important; color: #fff !important; }

    [data-testid="stTextInput"] input {
        background: rgba(255,255,255,0.05) !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        border-radius: 10px !important; color: #fff !important;
    }
    [data-testid="stSelectbox"] > div {
        background: rgba(255,255,255,0.05) !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        border-radius: 10px !important; color: #fff !important;
    }
    [data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }
    .stDownloadButton button {
        background: rgba(245,197,66,0.1) !important;
        border: 1px solid rgba(245,197,66,0.3) !important;
        color: #f5c542 !important; border-radius: 10px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown("""
    <div style='background: linear-gradient(135deg, rgba(8,13,46,0.95), rgba(4,7,26,0.98));
         border: 1px solid rgba(245,197,66,0.18); border-radius: 20px;
         padding: 28px 36px; margin-bottom: 28px;'>
        <div style='display:flex; align-items:center; gap:14px;'>
            <div style='width:52px;height:52px;border-radius:14px;
                 background:rgba(245,197,66,0.12);border:1px solid rgba(245,197,66,0.3);
                 display:flex;align-items:center;justify-content:center;font-size:1.5rem;'>
                🛡️
            </div>
            <div>
                <div style='font-family:Syne,sans-serif;font-size:1.5rem;
                     font-weight:800;color:#fff;'>GoGenie Admin Dashboard</div>
                <div style='color:rgba(200,216,240,0.45);font-size:0.82rem;margin-top:3px;'>
                    Booking management · SQLite · Real-time
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Search + Refresh ──────────────────────────────────────────────────────
    col_s, col_r = st.columns([4, 1])
    with col_s:
        search_q = st.text_input(
            "🔍 Search",
            placeholder="Name, email, date (YYYY-MM-DD), booking ID (GG-…), city…",
            label_visibility="collapsed"
        )
    with col_r:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    # ── Load bookings ─────────────────────────────────────────────────────────
    bookings = search_bookings(search_q) if search_q.strip() else get_all_bookings()

    # ── Stats row ─────────────────────────────────────────────────────────────
    total      = len(bookings)
    confirmed  = sum(1 for b in bookings if b.get("status") == "confirmed")
    cancelled  = sum(1 for b in bookings if b.get("status") == "cancelled")
    today_str  = datetime.now().strftime("%Y-%m-%d")
    today_bk   = sum(1 for b in bookings if (b.get("created_at") or "").startswith(today_str))
    completion = f"{int(confirmed/total*100)}%" if total else "N/A"

    def _stat(icon, label, val, color):
        return f"""
        <div style='background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.07);
             border-radius:14px;padding:18px 22px;'>
            <div style='font-size:1.5rem;margin-bottom:4px;'>{icon}</div>
            <div style='font-size:1.8rem;font-weight:700;color:{color};
                 font-family:Syne,sans-serif;'>{val}</div>
            <div style='font-size:0.75rem;color:rgba(200,216,240,0.4);
                 letter-spacing:0.5px;margin-top:2px;'>{label}</div>
        </div>"""

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.markdown(_stat("🎫", "Total Bookings",   total,      "#f5c542"), unsafe_allow_html=True)
    c2.markdown(_stat("✅", "Confirmed",         confirmed,  "#86efac"), unsafe_allow_html=True)
    c3.markdown(_stat("❌", "Cancelled",         cancelled,  "#fca5a5"), unsafe_allow_html=True)
    c4.markdown(_stat("📅", "Today",             today_bk,   "#93c5fd"), unsafe_allow_html=True)
    c5.markdown(_stat("📊", "Completion Rate",  completion, "#c4b5fd"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── No bookings ───────────────────────────────────────────────────────────
    if not bookings:
        st.markdown("""
        <div style='text-align:center;padding:60px 20px;
             color:rgba(200,216,240,0.35);'>
            <div style='font-size:3rem;margin-bottom:12px;'>📭</div>
            <div style='font-size:1.1rem;'>No bookings found</div>
            <div style='font-size:0.85rem;margin-top:8px;'>
                Bookings will appear here once confirmed by users.
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    # ── Data table ────────────────────────────────────────────────────────────
    st.markdown("""
    <div style='font-size:0.78rem;font-weight:600;color:rgba(200,216,240,0.45);
         letter-spacing:1.2px;text-transform:uppercase;margin-bottom:10px;'>
        All Bookings
    </div>
    """, unsafe_allow_html=True)

    df = pd.DataFrame(bookings)

    # Columns to display + rename
    col_map = {
        "id":              "Booking ID",
        "name":            "Passenger",
        "email":           "Email",
        "phone":           "Phone",
        "booking_type":    "Transport",
        "from_city":       "From",
        "to_city":         "To",
        "date":            "Date",
        "time":            "Time",
        "selected_option": "Option",
        "status":          "Status",
        "created_at":      "Booked At",
    }
    available = [c for c in col_map if c in df.columns]
    df_disp   = df[available].rename(columns=col_map)

    # Colour status column
    def _style_status(val):
        if val == "confirmed":
            return "background-color: rgba(34,197,94,0.12); color: #86efac;"
        if val == "cancelled":
            return "background-color: rgba(239,68,68,0.12); color: #fca5a5;"
        return ""

    st.dataframe(
        df_disp.style.applymap(_style_status, subset=["Status"]) if "Status" in df_disp.columns else df_disp,
        use_container_width=True,
        height=420
    )

    # ── Actions row ───────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    col_exp, col_mgmt = st.columns([1, 1])

    with col_exp:
        st.markdown("""
        <div style='font-size:0.78rem;color:rgba(200,216,240,0.45);
             letter-spacing:1px;text-transform:uppercase;margin-bottom:8px;'>
            Export
        </div>""", unsafe_allow_html=True)
        csv_data = df_disp.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️  Download CSV",
            data=csv_data,
            file_name=f"gogenie_bookings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )

    with col_mgmt:
        st.markdown("""
        <div style='font-size:0.78rem;color:rgba(200,216,240,0.45);
             letter-spacing:1px;text-transform:uppercase;margin-bottom:8px;'>
            Manage Booking
        </div>""", unsafe_allow_html=True)
        booking_ids  = [b["id"] for b in bookings]
        selected_id  = st.selectbox("Select booking:", booking_ids, label_visibility="collapsed")

    # ── Booking detail card ───────────────────────────────────────────────────
    if selected_id:
        sb = next((b for b in bookings if b["id"] == selected_id), None)
        if sb:
            status_color = "#86efac" if sb.get("status") == "confirmed" else "#fca5a5"

            st.markdown(f"""
            <div style='background:rgba(255,255,255,0.03);border:1px solid rgba(245,197,66,0.18);
                 border-radius:16px;padding:24px 28px;margin-top:16px;'>
                <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;'>
                    <div style='font-family:Syne,sans-serif;font-size:1.05rem;
                         font-weight:700;color:#f5c542;'>
                        {selected_id}
                    </div>
                    <div style='background:rgba(0,0,0,0.3);border-radius:100px;
                         padding:4px 14px;font-size:0.78rem;color:{status_color};
                         border:1px solid {status_color}33;'>
                        {sb.get("status","—").upper()}
                    </div>
                </div>
                <div style='display:grid;grid-template-columns:1fr 1fr;gap:12px;
                     font-size:0.88rem;'>
                    <div>
                        <span style='color:rgba(200,216,240,0.4);'>Passenger</span><br>
                        <span style='color:#fff;font-weight:500;'>{sb.get("name","—")}</span>
                    </div>
                    <div>
                        <span style='color:rgba(200,216,240,0.4);'>Email</span><br>
                        <span style='color:#fff;font-weight:500;'>{sb.get("email","—")}</span>
                    </div>
                    <div>
                        <span style='color:rgba(200,216,240,0.4);'>Route</span><br>
                        <span style='color:#fff;font-weight:500;'>
                            {sb.get("from_city","—")} → {sb.get("to_city","—")}
                        </span>
                    </div>
                    <div>
                        <span style='color:rgba(200,216,240,0.4);'>Date & Time</span><br>
                        <span style='color:#fff;font-weight:500;'>
                            {sb.get("date","—")} at {sb.get("time","—")}
                        </span>
                    </div>
                    <div>
                        <span style='color:rgba(200,216,240,0.4);'>Transport</span><br>
                        <span style='color:#fff;font-weight:500;'>{sb.get("booking_type","—")}</span>
                    </div>
                    <div>
                        <span style='color:rgba(200,216,240,0.4);'>Option</span><br>
                        <span style='color:#c8d8f0;font-size:0.82rem;'>
                            {sb.get("selected_option","—")[:60]}
                        </span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Action buttons
            st.markdown("<br>", unsafe_allow_html=True)
            bc1, bc2, bc3 = st.columns(3)
            with bc1:
                if st.button("✅ Confirm", use_container_width=True):
                    update_booking_status(selected_id, "confirmed")
                    st.success("Status → confirmed")
                    st.rerun()
            with bc2:
                if st.button("❌ Cancel", use_container_width=True):
                    update_booking_status(selected_id, "cancelled")
                    st.warning("Status → cancelled")
                    st.rerun()
            with bc3:
                if st.button("🗑️ Delete", use_container_width=True):
                    delete_booking(selected_id)
                    st.error("Booking deleted")
                    st.rerun()
