"""
BuildMate AI — Streamlit Frontend
Fully wired to the FastAPI backend at http://localhost:8000
"""

import streamlit as st
import requests
import json
import pandas as pd
import uuid
import os
import base64
from datetime import datetime, timedelta

# Forward Streamlit secrets to environment variables (for Cloud deployment)
try:
    if hasattr(st, "secrets"):
        for k, v in st.secrets.items():
            if isinstance(v, str) and k not in os.environ:
                os.environ[k] = v
except Exception:
    pass

def get_base64_image(image_path: str) -> str:
    if os.path.exists(image_path):
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    return ""

_ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
_PC_IMG_B64 = get_base64_image(os.path.join(_ASSETS_DIR, "pc_rig.png"))

# ── Page configuration ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="BuildMate AI — PC Builder",
    page_icon="🖥️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', 'Inter', sans-serif !important;
        background-color: #F8FAFC !important;
        color: #1E293B !important;
    }

    /* Main Container Padding */
    .block-container {
        padding-top: 1.8rem !important;
        padding-bottom: 5rem !important;
        max-width: 1050px !important;
    }

    /* Modern Hero Header Banner */
    .header-container {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 20px;
        padding: 2rem 2.5rem;
        margin-bottom: 1.8rem;
        box-shadow: 0 4px 20px -2px rgba(99, 102, 241, 0.08), 0 2px 6px -1px rgba(0, 0, 0, 0.04);
        position: relative;
        overflow: hidden;
    }
    .header-container::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, #6366F1, #8B5CF6, #EC4899);
    }
    .header-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #312E81, #4F46E5, #7C3AED);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .header-subtitle {
        font-size: 1rem;
        color: #64748B;
        margin-top: 0.5rem;
        line-height: 1.5;
    }
    .header-pills {
        display: flex;
        flex-wrap: wrap;
        gap: 0.6rem;
        margin-top: 1.2rem;
    }
    .header-pill {
        background: #F1F5F9;
        border: 1px solid #E2E8F0;
        color: #475569;
        padding: 0.35rem 0.85rem;
        border-radius: 20px;
        font-size: 0.82rem;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
    }

    /* Streamlit Chat Messages Styling */
    [data-testid="stChatMessage"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 16px !important;
        padding: 1.2rem 1.4rem !important;
        margin-bottom: 1rem !important;
        box-shadow: 0 2px 8px -1px rgba(0, 0, 0, 0.04) !important;
    }

    /* Metric Cards */
    .metric-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 16px;
        padding: 1.2rem 1.5rem;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
    }
    .metric-label {
        font-size: 0.78rem;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 0.35rem;
        font-weight: 600;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 800;
        color: #4F46E5;
    }

    /* Compatibility Badges */
    .badge-ok {
        background: #ECFDF5;
        color: #059669;
        border: 1px solid #A7F3D0;
        padding: 0.35rem 0.95rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
    }
    .badge-err {
        background: #FEF2F2;
        color: #DC2626;
        border: 1px solid #FECACA;
        padding: 0.35rem 0.95rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E2E8F0 !important;
    }
    section[data-testid="stSidebar"] h2 {
        color: #1E293B !important;
        font-weight: 800 !important;
    }

    /* Sidebar primary button (New Build Chat) */
    button[kind="primary"] {
        background: linear-gradient(135deg, #6366F1, #8B5CF6) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35) !important;
        padding: 0.6rem 1rem !important;
        transition: all 0.2s ease !important;
    }
    button[kind="primary"]:hover {
        opacity: 0.95 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 18px rgba(99, 102, 241, 0.45) !important;
    }

    /* Secondary buttons in sidebar & main */
    button[kind="secondary"] {
        background: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 10px !important;
        color: #334155 !important;
        font-weight: 500 !important;
        transition: all 0.15s ease !important;
    }
    button[kind="secondary"]:hover {
        background: #F8FAFC !important;
        border-color: #CBD5E1 !important;
        color: #4F46E5 !important;
    }

    /* Floating Chat Input Bar */
    .stChatInputContainer {
        border-top: none !important;
        background: transparent !important;
    }
    div[data-testid="stChatInput"] {
        background: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 18px !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06) !important;
        transition: all 0.2s ease !important;
    }
    div[data-testid="stChatInput"]:focus-within {
        border-color: #6366F1 !important;
        box-shadow: 0 4px 20px rgba(99, 102, 241, 0.18) !important;
    }

    /* Ensure all text is crisp, dark, and readable */
    .stMarkdown, .stMarkdown p, .stMarkdown span, .stMarkdown li, .stMarkdown div,
    [data-testid="stChatMessage"] p, [data-testid="stChatMessage"] span, [data-testid="stChatMessage"] li,
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] li {
        color: #1E293B !important;
    }

    /* User Chat Message bubble: Soft lavender/purple */
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
        background-color: #F5F3FF !important;
        border: 1px solid #DDD6FE !important;
    }
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) p {
        color: #1E1B4B !important;
        font-weight: 500 !important;
    }

    /* Assistant Chat Message card: Crisp white */
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
    }

    /* Fix bottom sticky chat bar background */
    [data-testid="stBottom"], .stBottomBlockContainer, [data-testid="stChatInputContainer"], [data-testid="stChatInputBottom"], footer {
        background-color: #F8FAFC !important;
        background: #F8FAFC !important;
    }

    /* Code blocks and inline tags */
    code {
        color: #4F46E5 !important;
        background: #EEF2FF !important;
        padding: 0.15rem 0.4rem !important;
        border-radius: 6px !important;
        font-size: 0.9em !important;
    }

    /* Streamlit DataFrame */
    [data-testid="stDataFrame"] {
        border-radius: 14px !important;
        overflow: hidden !important;
        border: 1px solid #E2E8F0 !important;
        background: #FFFFFF !important;
    }

    /* Sidebar subheadings */
    [data-testid="stSidebar"] h4 {
        color: #0F172A !important;
        font-weight: 700 !important;
        margin-top: 1rem !important;
    }

    /* Hide Streamlit branding/deploy */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none !important;}
    header[data-testid="stHeader"] {background: transparent !important;}
    [data-testid="collapsedControl"] {
        visibility: visible !important;
        display: flex !important;
        color: #4F46E5 !important;
    }
</style>
""", unsafe_allow_html=True)

# ── Backend URL ─────────────────────────────────────────────────────────────────
BACKEND_URL = "http://localhost:8000"


# ── Session persistence ──────────────────────────────────────────────────────────
HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat_history.json")
MAX_SESSIONS  = 5


def load_sessions() -> dict:
    """Load all sessions from the JSON file on disk."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_sessions(sessions: dict):
    """Persist all sessions to disk."""
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(sessions, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[save_sessions] Failed: {e}")


def new_session_id() -> str:
    return str(uuid.uuid4())


def make_session(session_id: str, title: str = "New Build Chat") -> dict:
    return {
        "id":         session_id,
        "title":      title,
        "created_at": datetime.now().isoformat(),
        "messages":   [],
        "last_build": None,
        "last_intent": {},
    }


def curr_session() -> dict:
    """Return the currently active session dict."""
    return st.session_state.sessions[st.session_state.current_session_id]


def _init_state():
    if "sessions" not in st.session_state:
        st.session_state.sessions = load_sessions()

    # Trim to MAX_SESSIONS (keep most recent)
    if len(st.session_state.sessions) > MAX_SESSIONS:
        sorted_ids = sorted(
            st.session_state.sessions,
            key=lambda sid: st.session_state.sessions[sid].get("created_at", ""),
            reverse=True,
        )
        for old_id in sorted_ids[MAX_SESSIONS:]:
            del st.session_state.sessions[old_id]
        save_sessions(st.session_state.sessions)

    if "current_session_id" not in st.session_state:
        # Start with an existing session or create a fresh one
        if st.session_state.sessions:
            most_recent = max(
                st.session_state.sessions,
                key=lambda sid: st.session_state.sessions[sid].get("created_at", ""),
            )
            st.session_state.current_session_id = most_recent
        else:
            sid = new_session_id()
            st.session_state.sessions[sid] = make_session(sid)
            st.session_state.current_session_id = sid
            save_sessions(st.session_state.sessions)

    if "backend_ok" not in st.session_state:
        st.session_state.backend_ok = None


_init_state()


# ── Helpers ─────────────────────────────────────────────────────────────────────
def check_backend() -> bool:
    """Ping /health to see if the FastAPI server is up. Auto-start if not running."""
    try:
        r = requests.get(f"{BACKEND_URL}/health", timeout=2)
        if r.status_code == 200:
            return True
    except Exception:
        pass

    # Auto-launch FastAPI backend in background (useful for Streamlit Cloud & local runs)
    try:
        import subprocess, sys, time
        subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        for _ in range(6):
            time.sleep(1)
            try:
                r = requests.get(f"{BACKEND_URL}/health", timeout=1)
                if r.status_code == 200:
                    return True
            except Exception:
                pass
    except Exception:
        pass
    return False


def call_build_api(user_text: str) -> dict:
    """
    POST /build with the full conversation history and previously extracted intent.
    Returns the parsed JSON response or raises a RuntimeError with a user-friendly message.
    """
    session = curr_session()
    conv = [{"role": m["role"], "content": m["content"]} for m in session["messages"]]

    payload = {
        "conversation":  conv,
        "user_message":  user_text,
        "budget":        session["last_intent"].get("budget"),
        "use_case":      session["last_intent"].get("use_case"),
        "preferences":   session["last_intent"].get("preferences", {}),
        "current_build": session["last_build"],
    }

    try:
        resp = requests.post(f"{BACKEND_URL}/build", json=payload, timeout=60)
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "⚠️ Cannot reach the backend server. "
            "Make sure FastAPI is running:\n\n"
            "```\nuvicorn api.main:app --reload\n```"
        )
    except requests.exceptions.Timeout:
        raise RuntimeError(
            "⏱️ The request timed out (60 s). The LLM might be slow — please try again."
        )

    if resp.status_code == 400:
        detail = resp.json().get("detail", "Bad request")
        raise RuntimeError(f"💬 {detail}")
    elif resp.status_code == 422:
        detail = resp.json().get("detail", "Validation error")
        raise RuntimeError(f"🤔 {detail}")
    elif resp.status_code != 200:
        raise RuntimeError(
            f"🚨 Server error {resp.status_code}: {resp.text[:300]}"
        )

    return resp.json()


def fmt_inr(amount: float) -> str:
    """Format a number as Indian Rupees."""
    return f"₹{amount:,.0f}"


def render_build_card(data: dict):
    """Render the parts list, metrics, and explanation inside the chat."""
    build    = data.get("build", {})
    selected = build.get("selected_components", {})
    total    = build.get("total_cost", 0)
    remain   = build.get("remaining_budget", 0)
    explain  = data.get("explanation", "")
    warnings = data.get("warnings") or []
    compat   = data.get("compatibility_passed", True)
    notes    = build.get("notes", [])
    intent   = data.get("input_analysis", {})

    # ── Intent summary ──────────────────────────────────────────────────────────
    use_case_emoji = {"gaming": "🎮", "editing": "🎬", "general": "💼"}.get(
        intent.get("use_case", "general"), "💻"
    )
    prefs = intent.get("preferences", {})
    pref_str = ", ".join(f"{k}: {v}" for k, v in prefs.items()) if prefs else "none"

    st.markdown(
        f"**Detected:** {use_case_emoji} **{intent.get('use_case','general').title()}** build · "
        f"Budget: **{fmt_inr(intent.get('budget', 0))}** · Preferences: *{pref_str}*"
    )

    # ── Compatibility badge ─────────────────────────────────────────────────────
    if compat:
        st.markdown('<span class="badge-ok">✅ All compatibility checks passed</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="badge-err">⚠️ Compatibility warnings below</span>', unsafe_allow_html=True)

    st.markdown("")   # spacer

    # ── Parts table ─────────────────────────────────────────────────────────────
    component_defs = [
        ("cpu",         "🖥️",  "CPU"),
        ("gpu",         "🎮",  "GPU"),
        ("motherboard", "🔧",  "Motherboard"),
        ("ram",         "💾",  "RAM"),
        ("storage",     "💿",  "Storage"),
        ("psu",         "⚡",  "PSU"),
        ("case",        "📦",  "Case"),
    ]

    rows = []
    for key, icon, label in component_defs:
        comp = selected.get(key)
        if isinstance(comp, dict) and comp:
            name  = comp.get("name", "Unknown")
            price = float(comp.get("price", 0))

            # Build a detail string based on component type
            if key == "cpu":
                detail = f"{comp.get('core_count', '?')} cores · {comp.get('socket', '?')} · {comp.get('tdp', '?')}W"
            elif key == "gpu":
                detail = f"{comp.get('performance_tier','?')} · {comp.get('tdp','?')}W · {comp.get('length_mm','?')}mm"
            elif key == "motherboard":
                detail = f"{comp.get('socket','?')} · {comp.get('ram_type','?')} · {comp.get('form_factor','?')}"
            elif key == "ram":
                detail = f"{comp.get('capacity','?')}GB {comp.get('type','?')} @ {comp.get('speed','?')}MHz"
            elif key == "storage":
                detail = f"{comp.get('capacity','?')}GB {comp.get('type','?')}"
            elif key == "psu":
                detail = f"{comp.get('wattage','?')}W · {comp.get('efficiency_rating','?')}"
            elif key == "case":
                feats = []
                if comp.get("tempered_glass"): feats.append("Tempered Glass")
                if comp.get("rgb"):            feats.append("RGB")
                if comp.get("airflow") == "high": feats.append("High Airflow")
                detail = " · ".join(feats) if feats else comp.get("form_factor", "")
            else:
                detail = ""
        else:
            name   = "Not selected"
            price  = 0.0
            detail = ""

        rows.append({
            "Component": f"{icon} {label}",
            "Name":      name,
            "Specs":     detail,
            "Price":     fmt_inr(price),
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # ── Cost summary ────────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Cost</div>
            <div class="metric-value">{fmt_inr(total)}</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Remaining Budget</div>
            <div class="metric-value">{fmt_inr(remain)}</div>
        </div>""", unsafe_allow_html=True)

    # ── Compatibility warnings ──────────────────────────────────────────────────
    if warnings:
        st.markdown("")
        for w in warnings:
            st.warning(f"⚠️ {w}")

    # ── Power & Electricity Cost ────────────────────────────────────────────────
    power_data = data.get("power_analysis")
    with st.expander("⚡ Power & Electricity Cost", expanded=False):
        if power_data:
            p_col1, p_col2, p_col3 = st.columns(3)
            with p_col1:
                st.metric("Est. Peak Power", f"{power_data.get('peak_power_watts', 0)} W")
            with p_col2:
                st.metric("PSU Load", f"{power_data.get('psu_load_percentage', 0)}%", power_data.get('load_status', ''))
            with p_col3:
                st.metric("Est. Monthly Electricity", f"₹{power_data.get('monthly_cost_inr', 0):,}")

            st.markdown("---")
            st.markdown(f"""
- **CPU Power Draw**: {power_data.get('cpu_tdp', 0)}W TDP
- **GPU Power Draw**: {power_data.get('gpu_tdp', 0)}W TDP
- **Base System Overhead (Motherboard, RAM, SSD, Fans)**: ~{power_data.get('base_overhead', 50)}W
- **Recommended Minimum PSU**: {power_data.get('recommended_psu_watts', 0)}W *(with 30% safety headroom)*
- **Selected PSU**: {power_data.get('selected_psu_watts', 0)}W ({power_data.get('psu_efficiency', '80+')})
- **Estimated Annual Running Cost**: ₹{power_data.get('yearly_cost_inr', 0):,} *(based on ~4h active load + 4h idle/day @ ₹8/kWh)*
            """)
        else:
            st.info("Power analysis data unavailable.")

    # ── Bottleneck Analysis ─────────────────────────────────────────────────────
    bottleneck_data = data.get("bottleneck_analysis")
    with st.expander("🔍 Bottleneck Analysis", expanded=False):
        if bottleneck_data:
            b_label = bottleneck_data.get("status_label", "")
            b_expl = bottleneck_data.get("explanation", "")
            st.markdown(f"**System Balance Rating:** `{b_label}`")
            st.markdown(b_expl)

            st.markdown("##### 🎮 Resolution Performance Breakdown")
            res_dict = bottleneck_data.get("resolutions", {})
            r_col1, r_col2, r_col3 = st.columns(3)
            with r_col1:
                fhd = res_dict.get("1080p_fhd", {})
                st.markdown(f"**🖥️ {fhd.get('label', '1080p')}**")
                st.caption(f"{fhd.get('assessment', '')}\n\nRating: **{fhd.get('rating', '')}**")
            with r_col2:
                qhd = res_dict.get("1440p_qhd", {})
                st.markdown(f"**🖥️ {qhd.get('label', '1440p')}**")
                st.caption(f"{qhd.get('assessment', '')}\n\nRating: **{qhd.get('rating', '')}**")
            with r_col3:
                uhd = res_dict.get("4k_uhd", {})
                st.markdown(f"**🖥️ {uhd.get('label', '4K UHD')}**")
                st.caption(f"{uhd.get('assessment', '')}\n\nRating: **{uhd.get('rating', '')}**")
        else:
            st.info("Bottleneck analysis data unavailable.")

    # ── Cost-Saving Alternatives ────────────────────────────────────────────────
    alts_data = data.get("alternatives") or []
    with st.expander("💸 Cost-Saving Alternatives", expanded=False):
        if alts_data:
            st.markdown("Compatible component swaps that can save money with minimal impact on performance:")
            for alt in alts_data:
                st.markdown(f"""
- **{alt.get('category')}**: Swap **{alt.get('original')}** (₹{alt.get('original_price', 0):,}) → **{alt.get('alternative')}** (₹{alt.get('alternative_price', 0):,})
  - 💰 **Potential Savings:** `₹{alt.get('savings', 0):,}`
  - ℹ️ *Trade-off:* {alt.get('trade_off')}
                """)
        else:
            st.success("This build is already highly cost-optimized! No significant cheaper alternatives found for the current configuration.")

    # ── Check Prices on PC Part Picker ──────────────────────────────────────────
    retailer_data = data.get("retailer_links") or []
    with st.expander("🛒 Check Prices on PC Part Picker", expanded=False):
        if retailer_data:
            st.markdown("Compare live market prices and availability:")
            ret_markdown = "| Component | Part Name | PCPartPicker | Amazon India |\n|---|---|:---:|:---:|\n"
            for item in retailer_data:
                ret_markdown += f"| {item.get('category')} | **{item.get('component_name')}** | [🔗 View]({item.get('pcpartpicker')}) | [🛒 Amazon]({item.get('amazon_in')}) |\n"
            st.markdown(ret_markdown, unsafe_allow_html=True)
        else:
            st.info("Retailer links unavailable.")

    # ── Build notes (from engine) ───────────────────────────────────────────────
    if notes:
        with st.expander("📝 Build notes from the engine"):
            for note in notes:
                st.info(note)

    # ── Explanation ─────────────────────────────────────────────────────────────
    if explain:
        st.markdown("---")
        st.markdown("**💡 Why these components?**")
        st.markdown(explain)


def render_chat_history():
    """Render all chat messages with proper alignment."""
    for msg in curr_session()["messages"]:
        if msg["role"] == "user":
            with st.chat_message("user", avatar="🧑‍💻"):
                st.markdown(msg["content"])
        else:
            with st.chat_message("assistant", avatar="🤖"):
                if msg.get("type") == "build":
                    render_build_card(msg["data"])
                else:
                    st.markdown(msg["content"])


# ── Sidebar ─────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🖥️ BuildMate AI")
    st.markdown("*Your personal PC building assistant*")

    # ── New Build Chat button (like GPT's compose/pencil) ───────────────────────
    if st.button("✏️  New Build Chat", type="primary", use_container_width=True):
        # Only create a new session if the current one isn't empty
        if curr_session()["messages"]:
            # Enforce 5-session limit — drop oldest if needed
            if len(st.session_state.sessions) >= MAX_SESSIONS:
                oldest_id = min(
                    st.session_state.sessions,
                    key=lambda sid: st.session_state.sessions[sid].get("created_at", ""),
                )
                del st.session_state.sessions[oldest_id]
            sid = new_session_id()
            st.session_state.sessions[sid] = make_session(sid)
            st.session_state.current_session_id = sid
            save_sessions(st.session_state.sessions)
        st.rerun()

    st.markdown("---")

    # ── Chat History ─────────────────────────────────────────────────────────────
    st.markdown("#### 🕘 Chat History")

    # Sort sessions newest-first
    sorted_sessions = sorted(
        st.session_state.sessions.values(),
        key=lambda s: s.get("created_at", ""),
        reverse=True,
    )

    now = datetime.now()

    def _date_group(iso: str) -> str:
        try:
            dt = datetime.fromisoformat(iso)
        except Exception:
            return "Older"
        delta = (now - dt).days
        if delta == 0:   return "Today"
        if delta == 1:   return "Yesterday"
        if delta <= 7:   return "Last 7 Days"
        return "Older"

    shown_groups = []
    delete_target = None

    for session in sorted_sessions:
        group = _date_group(session.get("created_at", ""))
        if group not in shown_groups:
            st.markdown(f"<p style='color:#64748B;font-size:0.75rem;margin:0.8rem 0 0.3rem;text-transform:uppercase;letter-spacing:1px;font-weight:700'>{group}</p>", unsafe_allow_html=True)
            shown_groups.append(group)

        sid      = session["id"]
        title    = session["title"]
        is_active = sid == st.session_state.current_session_id

        col_btn, col_del = st.columns([5, 1])
        with col_btn:
            label = f"**{title}**" if is_active else title
            if st.button(label, key=f"sess_{sid}", use_container_width=True):
                st.session_state.current_session_id = sid
                st.rerun()
        with col_del:
            if st.button("🗑", key=f"del_{sid}", help="Delete this chat"):
                delete_target = sid

    # Handle delete outside the loop to avoid rerun mid-loop
    if delete_target:
        del st.session_state.sessions[delete_target]
        # If we just deleted the active session, switch to another or create fresh
        if st.session_state.current_session_id == delete_target:
            if st.session_state.sessions:
                st.session_state.current_session_id = max(
                    st.session_state.sessions,
                    key=lambda sid: st.session_state.sessions[sid].get("created_at", ""),
                )
            else:
                sid = new_session_id()
                st.session_state.sessions[sid] = make_session(sid)
                st.session_state.current_session_id = sid
        save_sessions(st.session_state.sessions)
        st.rerun()

    st.markdown("---")

    # ── Example prompts ──────────────────────────────────────────────────────────
    st.markdown("#### 💡 Try an example")
    example_prompts = [
        "Gaming PC under ₹80,000",
        "Video editing PC ₹1.5 lakh, AMD",
        "General use PC for ₹50,000",
        "Best gaming rig ₹2 lakh, NVIDIA",
        "Budget college PC ₹48,000",
    ]
    for ex in example_prompts:
        if st.button(ex, key=f"ex_{ex}", use_container_width=True):
            # If current session already has messages, start a new one for the example
            if curr_session()["messages"]:
                if len(st.session_state.sessions) >= MAX_SESSIONS:
                    oldest_id = min(
                        st.session_state.sessions,
                        key=lambda sid: st.session_state.sessions[sid].get("created_at", ""),
                    )
                    del st.session_state.sessions[oldest_id]
                sid = new_session_id()
                st.session_state.sessions[sid] = make_session(sid, title=ex)
                st.session_state.current_session_id = sid
                save_sessions(st.session_state.sessions)
            st.session_state["_inject_prompt"] = ex
            st.rerun()

    st.markdown("---")

    # ── Backend status ───────────────────────────────────────────────────────────
    if st.button("🔄 Check backend status"):
        st.session_state.backend_ok = check_backend()

    if st.session_state.backend_ok is None:
        st.info("Click above to check if the backend is online.")
    elif st.session_state.backend_ok:
        st.success("✅ Backend is online")
    else:
        st.error("❌ Backend is offline — start it with:\n\n`uvicorn api.main:app --reload`")

    st.markdown("---")
    st.caption(f"Prices in ₹ · v2.0 · Max {MAX_SESSIONS} sessions")


# ── Main area ───────────────────────────────────────────────────────────────────
pc_img_html = f'<div style="flex-shrink: 0; display: flex; align-items: center; justify-content: center;"><img src="data:image/png;base64,{_PC_IMG_B64}" style="max-height: 175px; border-radius: 14px; filter: drop-shadow(0 12px 24px rgba(99, 102, 241, 0.16));" alt="Custom Gaming PC" /></div>' if _PC_IMG_B64 else ""

st.markdown(f"""
<div class="header-container">
    <div style="display: flex; align-items: center; justify-content: space-between; gap: 1.5rem; flex-wrap: wrap;">
        <div style="flex: 1; min-width: 280px;">
            <div class="header-title">✨ BuildMate AI</div>
            <div class="header-subtitle">
                Tell me your budget and what you'll use the PC for — I'll design a fully compatible build just for you.
            </div>
            <div class="header-pills">
                <span class="header-pill">🛡️ Fully Compatible</span>
                <span class="header-pill">📈 Best Performance</span>
                <span class="header-pill">💸 Great Value</span>
            </div>
        </div>
        {pc_img_html}
    </div>
</div>
""", unsafe_allow_html=True)

# Auto-run an example prompt if sidebar button was clicked
injected = st.session_state.pop("_inject_prompt", None)

# Render existing messages
render_chat_history()

# If no messages in this session, show a welcome card
if not curr_session()["messages"]:
    with st.chat_message("assistant", avatar="🤖"):
        st.markdown(
            "👋 Hi! I'm **BuildMate AI** — your personal PC building assistant.\n\n"
            "Just tell me:\n"
            "- 💰 Your **budget** (e.g., ₹80,000)\n"
            "- 🎯 What you'll **use it for** (gaming / video editing / general use)\n"
            "- 🔧 Any **preferences** (AMD / Intel / NVIDIA / specific RAM type)\n\n"
            "I'll give you a fully compatible, optimized parts list with detailed analytics! "
            "After that, feel free to ask questions (like *'Why Intel?'*) or request changes anytime."
        )

# ── Dynamic Chat input ──────────────────────────────────────────────────────────
if curr_session()["last_build"]:
    chat_placeholder = "Ask anything about this build (e.g. 'Why Intel?' or 'Change processor to AMD')..."
else:
    chat_placeholder = "Describe your PC build requirements (e.g. 'gaming PC under ₹80,000 with AMD')..."

user_input = st.chat_input(chat_placeholder)

# Use injected prompt if sidebar example was clicked
if injected:
    user_input = injected

if user_input:
    # Check backend first (lazy check on first real request)
    if st.session_state.backend_ok is None:
        st.session_state.backend_ok = check_backend()

    if not st.session_state.backend_ok:
        st.error(
            "❌ The backend server is not running. Please start it first:\n\n"
            "Open a terminal and run:\n```\nuvicorn api.main:app --reload\n```\n\n"
            "Then refresh this page."
        )
    else:
        session = curr_session()

        # Auto-title: set from first user message
        if session["title"] == "New Build Chat" and not session["messages"]:
            raw_title = user_input.strip()
            session["title"] = (raw_title[:42] + "…") if len(raw_title) > 42 else raw_title

        # Show user message
        with st.chat_message("user", avatar="🧑‍💻"):
            st.markdown(user_input)
        session["messages"].append({"role": "user", "content": user_input})
        save_sessions(st.session_state.sessions)

        # Call backend with loading spinner
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("🤖 Thinking..."):
                try:
                    data = call_build_api(user_input)

                    if data.get("response_type") == "chat":
                        reply_text = data.get("content", "")
                        st.markdown(reply_text)
                        session["messages"].append({
                            "role":    "assistant",
                            "type":    "chat",
                            "content": reply_text,
                        })
                    else:
                        session["last_intent"] = data.get("input_analysis", {})
                        session["last_build"]  = data

                        render_build_card(data)

                        session["messages"].append({
                            "role":    "assistant",
                            "type":    "build",
                            "data":    data,
                            "content": "[build result]",
                        })

                    save_sessions(st.session_state.sessions)

                except RuntimeError as e:
                    err_msg = str(e)
                    st.error(err_msg)
                    session["messages"].append({
                        "role":    "assistant",
                        "content": f"❌ {err_msg}",
                    })
                    save_sessions(st.session_state.sessions)
                except Exception as e:
                    err_msg = f"An unexpected error occurred: {str(e)}"
                    st.error(err_msg)
                    session["messages"].append({
                        "role":    "assistant",
                        "content": f"❌ {err_msg}",
                    })
                    save_sessions(st.session_state.sessions)