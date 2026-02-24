from dotenv import load_dotenv
load_dotenv()

import streamlit as st
from database import init_db, get_connection, get_setting, set_setting
from memory import get_history, clear_memory
from agent import stream_agent

st.set_page_config(
    page_title="Sage AI",
    page_icon="🌿",
    layout="centered",
)

# ── Themes ────────────────────────────────────────────────────────────────────
THEMES = {
    "dark": {
        "bg":         "#0d0f14",
        "sidebar_bg": "#13151e",
        "card_bg":    "#1a1d2b",
        "text":       "#e2e8f0",
        "muted":      "#64748b",
        "border":     "#252840",
        "accent":     "#818cf8",
        "accent_dim": "#818cf820",
        "toggle_icon": "☀️",
        "shadow":     "none",
    },
    "light": {
        "bg":         "#f9fafb",
        "sidebar_bg": "#ffffff",
        "card_bg":    "#ffffff",
        "text":       "#111827",
        "muted":      "#6b7280",
        "border":     "#e5e7eb",
        "accent":     "#4f46e5",
        "accent_dim": "#4f46e510",
        "toggle_icon": "🌙",
        "shadow":     "0 1px 3px rgba(0,0,0,0.08)",
    },
}

if "mode" not in st.session_state:
    st.session_state.mode = "dark"

t = THEMES[st.session_state.mode]
mode = st.session_state.mode


def inject_theme(t: dict, mode: str) -> None:
    light_extra = ""
    if mode == "light":
        light_extra = f"""
        body, .stApp, [data-testid="stAppViewContainer"],
        .main, .block-container {{
            background-color: {t['bg']} !important;
            color: {t['text']} !important;
        }}
        [data-testid="stMarkdownContainer"],
        [data-testid="stMarkdownContainer"] p,
        [data-testid="stMarkdownContainer"] li,
        [data-testid="stMarkdownContainer"] h1,
        [data-testid="stMarkdownContainer"] h2,
        [data-testid="stMarkdownContainer"] h3,
        [data-testid="stMarkdownContainer"] strong,
        [data-testid="stCaptionContainer"] p,
        .stChatMessage p, .stChatMessage li,
        label, [data-testid="stWidgetLabel"] p {{
            color: {t['text']} !important;
        }}
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] li,
        [data-testid="stSidebar"] label {{
            color: {t['text']} !important;
        }}
        /* Fix ALL buttons in light mode */
        .stButton > button {{
            background: transparent !important;
            border: 1px solid {t['border']} !important;
            color: {t['text']} !important;
        }}
        .stButton > button:hover {{
            border-color: {t['accent']} !important;
            color: {t['accent']} !important;
            background: {t['accent_dim']} !important;
        }}
        [data-testid="stChatMessage"] {{
            background-color: {t['card_bg']} !important;
            border: 1px solid {t['border']} !important;
            box-shadow: {t['shadow']} !important;
        }}
        /* Chat input — make visible on white bg */
        [data-testid="stBottom"],
        [data-testid="stBottom"] > div,
        .stChatInputContainer,
        .stChatInputContainer > div {{
            background-color: {t['bg']} !important;
            border-top: 2px solid {t['border']} !important;
        }}
        [data-testid="stChatInput"] > div,
        .stChatInput > div {{
            background-color: #ffffff !important;
            border: 1.5px solid #d1d5db !important;
            border-radius: 12px !important;
            box-shadow: 0 1px 4px rgba(0,0,0,0.08) !important;
        }}
        [data-testid="stChatInput"] textarea {{
            background-color: #ffffff !important;
            color: {t['text']} !important;
            border: none !important;
        }}
        /* Submit button */
        [data-testid="stChatInputSubmitButton"] {{
            background-color: {t['accent']} !important;
            border-radius: 8px !important;
        }}
        [data-testid="stChatInputSubmitButton"] svg {{
            fill: #ffffff !important;
        }}
        """

    st.markdown(f"""
    <style>
        #MainMenu {{visibility: hidden;}}
        footer     {{visibility: hidden;}}
        header     {{visibility: hidden;}}

        .stApp {{
            background-color: {t['bg']} !important;
        }}

        [data-testid="stSidebar"] {{
            background-color: {t['sidebar_bg']} !important;
            border-right: 1px solid {t['border']} !important;
        }}

        /* All buttons — transparent base, no dark box ever */
        .stButton > button {{
            background: transparent !important;
            border: 1px solid {t['border']} !important;
            color: {t['text']} !important;
            font-size: 0.83rem;
            border-radius: 6px;
            transition: all 0.15s;
        }}
        .stButton > button:hover {{
            border-color: {t['accent']} !important;
            color: {t['accent']} !important;
            background: {t['accent_dim']} !important;
        }}

        /* Chat input area */
        [data-testid="stBottom"],
        [data-testid="stBottom"] > div,
        .stChatInputContainer,
        .stChatInputContainer > div {{
            background-color: {t['bg']} !important;
            border-top: 1px solid {t['border']} !important;
        }}
        [data-testid="stChatInput"] textarea {{
            background-color: {t['sidebar_bg']} !important;
            color: {t['text']} !important;
            border-color: {t['border']} !important;
        }}

        hr {{ border-color: {t['border']} !important; }}

        .stMarkdown p, .stMarkdown li {{ color: {t['text']}; }}

        /* ── App header ── */
        .app-header {{
            text-align: center;
            padding: 1.5rem 0 0.5rem 0;
        }}
        .app-header h1 {{
            font-size: 1.8rem;
            font-weight: 700;
            margin: 0;
            color: {t['text']};
            letter-spacing: -0.02em;
        }}
        .app-header p {{
            color: {t['muted']};
            font-size: 0.88rem;
            margin-top: 0.3rem;
        }}

        /* ── Sidebar info card ── */
        .info-card {{
            background: {t['card_bg']};
            border: 1px solid {t['border']};
            border-radius: 10px;
            padding: 0.9rem 1rem;
            margin: 0.5rem 0;
            box-shadow: {t['shadow']};
        }}
        .info-card .card-title {{
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: {t['muted']};
            margin-bottom: 0.3rem;
        }}
        .info-card .card-value {{
            font-size: 1.5rem;
            font-weight: 700;
            color: {t['text']};
            line-height: 1.2;
        }}
        .info-card .how-item {{
            display: flex;
            align-items: flex-start;
            gap: 0.5rem;
            padding: 0.3rem 0;
            font-size: 0.83rem;
            color: {t['text']};
            border-bottom: 1px solid {t['border']};
        }}
        .info-card .how-item:last-child {{ border-bottom: none; }}
        .info-card .how-icon {{
            color: {t['accent']};
            font-size: 0.9rem;
            flex-shrink: 0;
            padding-top: 1px;
        }}

        /* ── Empty state ── */
        .empty-state {{
            text-align: center;
            padding: 3rem 1rem 1rem 1rem;
        }}
        .empty-state h3 {{
            color: {t['text']};
            opacity: 0.45;
            font-weight: 500;
            margin-bottom: 0.3rem;
        }}
        .empty-state p {{ color: {t['muted']}; font-size: 0.88rem; }}

        /* Sidebar vertical gap */
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div {{
            gap: 0.2rem !important;
        }}

        /* Sidebar header */
        .sidebar-header {{
            padding: 0.5rem 0 0.2rem 0;
        }}
        .sidebar-header .app-name {{
            font-size: 1.25rem;
            font-weight: 700;
            color: {t['text']};
            letter-spacing: -0.01em;
            margin: 0;
        }}
        .sidebar-header .user-line {{
            font-size: 0.92rem;
            color: {t['muted']};
            margin-top: 0.15rem;
        }}
        .sidebar-header .user-line strong {{
            color: {t['text']};
            font-weight: 600;
        }}

        /* Card title / value sizes */
        .info-card .card-title {{
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: {t['muted']};
            margin-bottom: 0.25rem;
        }}
        .info-card .card-value {{
            font-size: 1.8rem;
            font-weight: 700;
            color: {t['text']};
        }}
        .info-card .how-item {{
            font-size: 0.88rem;
            color: {t['text']};
        }}

        {light_extra}
    </style>
    """, unsafe_allow_html=True)


inject_theme(t, mode)
init_db()

user_name = get_setting("user_name")


def get_conv_count() -> int:
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]


# ── Onboarding ────────────────────────────────────────────────────────────────
if not user_name:
    st.markdown(f"""
    <style>
        .onboard-wrap {{
            max-width: 400px;
            margin: 7rem auto 0 auto;
            text-align: center;
        }}
        .onboard-wrap .icon {{ font-size: 2.8rem; margin-bottom: 0.5rem; }}
        .onboard-wrap h2 {{
            color: {t['text']};
            font-size: 1.5rem;
            font-weight: 700;
            margin: 0 0 0.3rem 0;
            letter-spacing: -0.02em;
        }}
        .onboard-wrap p {{
            color: {t['muted']};
            font-size: 0.9rem;
            margin-bottom: 1.5rem;
        }}
    </style>
    <div class="onboard-wrap">
        <div class="icon">🌿</div>
        <h2>I'm Sage AI</h2>
        <p>Your personal AI companion.<br>What should I call you?</p>
    </div>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 2, 1])
    with col:
        name_input = st.text_input("name", placeholder="Your name...", label_visibility="collapsed")
        if st.button("Continue →", use_container_width=True, type="primary"):
            name = name_input.strip()
            if name:
                set_setting("user_name", name)
                st.rerun()
            else:
                st.error("Please enter your name.")
    st.stop()


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    col_title, col_toggle = st.columns([5, 1])
    with col_title:
        st.markdown(f"""
        <div class="sidebar-header">
            <p class="app-name">🌿 Sage AI</p>
            <p class="user-line">with <strong>{user_name}</strong></p>
        </div>
        """, unsafe_allow_html=True)
    with col_toggle:
        if st.button(t["toggle_icon"], key="theme_toggle", help="Toggle theme"):
            st.session_state.mode = "light" if mode == "dark" else "dark"
            st.rerun()

    st.divider()

    # Stats card
    total = get_conv_count()
    st.markdown(f"""
    <div class="info-card">
        <div class="card-title">Total Exchanges</div>
        <div class="card-value">{total}</div>
    </div>
    """, unsafe_allow_html=True)

    # How it works card
    st.markdown(f"""
    <div class="info-card" style="margin-top:0.6rem">
        <div class="card-title">How it works</div>
        <div class="how-item">
            <span class="how-icon">→</span>
            <span>Share your priorities &amp; goals</span>
        </div>
        <div class="how-item">
            <span class="how-icon">→</span>
            <span>Sage remembers them across sessions</span>
        </div>
        <div class="how-item">
            <span class="how-icon">→</span>
            <span>Ask what to focus on, spot blockers</span>
        </div>
        <div class="how-item">
            <span class="how-icon">→</span>
            <span>Get patterns from past conversations</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("")

    if st.button("🗑️ Clear History", use_container_width=True, type="secondary"):
        clear_memory()
        st.session_state.messages = []
        st.success("Cleared!")
        st.rerun()

    if st.button("✏️ Change Name", use_container_width=True, type="secondary"):
        set_setting("user_name", "")
        st.session_state.messages = []
        st.rerun()


# ── Session state ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
    for turn in get_history(limit=20):
        st.session_state.messages.append({"role": "user",      "content": turn["user_msg"]})
        st.session_state.messages.append({"role": "assistant", "content": turn["agent_msg"]})


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="app-header">
    <h1>🌿 Sage AI</h1>
    <p>Hey <strong>{user_name}</strong> — what are we tackling today?</p>
</div>
""", unsafe_allow_html=True)


# ── Quick-action buttons ──────────────────────────────────────────────────────
QUICK_PROMPTS = [
    ("🎯 Focus",      "What should I focus on right now?"),
    ("🚧 Blockers",   "What's currently blocking me?"),
    ("📋 Priorities", "Summarize my current priorities"),
    ("💡 Patterns",   "What patterns do you notice in my work?"),
]

triggered_prompt: str | None = None
cols = st.columns(len(QUICK_PROMPTS))
for i, (label, full_prompt) in enumerate(QUICK_PROMPTS):
    if cols[i].button(label, use_container_width=True):
        triggered_prompt = full_prompt

st.divider()


# ── Empty state ───────────────────────────────────────────────────────────────
if not st.session_state.messages:
    st.markdown(f"""
    <div class="empty-state">
        <h3>Good to see you, {user_name} 👋</h3>
        <p>Tell me what you're working on — or tap a button above.</p>
    </div>
    """, unsafe_allow_html=True)


# ── Chat history ──────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# ── Handle prompt ─────────────────────────────────────────────────────────────
def handle_prompt(user_input: str) -> None:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
    with st.chat_message("assistant"):
        try:
            reply = st.write_stream(stream_agent(user_input))
        except Exception as e:
            reply = f"⚠️ Error: {e}"
            st.markdown(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})


if triggered_prompt:
    handle_prompt(triggered_prompt)

if chat_input := st.chat_input("Ask Sage anything..."):
    handle_prompt(chat_input)
