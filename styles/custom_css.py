import streamlit as st
import streamlit.components.v1 as components

from styles.theme import BLUE, GREEN, RED, YELLOW, GRAY

# ── Theme color palettes ───────────────────────────────────────
_DARK = {
    "bg_app":    "#0F172A",
    "bg_sec":    "#111827",
    "bg_card":   "rgba(15,23,42,0.75)",
    "bg_subtle": "rgba(30,41,59,0.55)",
    "bg_solid":  "#1E293B",
    "t0":        "#F1F5F9",
    "t1":        "#CBD5E1",
    "t2":        "#94A3B8",
    "t3":        "#64748B",
    "bd":        "rgba(148,163,184,0.13)",
    "bdm":       "rgba(148,163,184,0.20)",
    "bds":       "rgba(148,163,184,0.28)",
    "shadow":    "rgba(0,0,0,0.25)",
    "hdr_bg":    "rgba(15,23,42,0.88)",
    "side_bg1":  "rgba(17,24,39,0.98)",
    "side_bg2":  "rgba(15,23,42,0.98)",
    "scroll_tr": "#111827",
    "scroll_th": "#4B5563",
    "fw_body":   "400",
}

_LIGHT = {
    "bg_app":    "#F8FAFC",
    "bg_sec":    "#F1F5F9",
    "bg_card":   "rgba(255,255,255,0.96)",
    "bg_subtle": "rgba(241,245,249,0.85)",
    "bg_solid":  "#FFFFFF",
    "t0":        "#0F172A",      # near-black — max contrast
    "t1":        "#1E293B",      # dark secondary
    "t2":        "#475569",      # muted — 5.9:1 on white (WCAG AA)
    "t3":        "#64748B",      # captions — 4.6:1 on white (WCAG AA)
    "bd":        "rgba(15,23,42,0.12)",
    "bdm":       "rgba(15,23,42,0.18)",
    "bds":       "rgba(15,23,42,0.26)",
    "shadow":    "rgba(15,23,42,0.08)",
    "hdr_bg":    "rgba(248,250,252,0.95)",
    "side_bg1":  "#F1F5F9",
    "side_bg2":  "#E2E8F0",
    "scroll_tr": "#F1F5F9",
    "scroll_th": "#CBD5E1",
    "fw_body":   "500",          # slightly medium weight for legibility
}


def _build_css(C: dict) -> str:
    return f'''
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {{
    --bg-app:    {C["bg_app"]};
    --bg-sec:    {C["bg_sec"]};
    --bg-card:   {C["bg_card"]};
    --bg-subtle: {C["bg_subtle"]};
    --bg-solid:  {C["bg_solid"]};
    --t0: {C["t0"]};
    --t1: {C["t1"]};
    --t2: {C["t2"]};
    --t3: {C["t3"]};
    --bd:  {C["bd"]};
    --bdm: {C["bdm"]};
    --bds: {C["bds"]};
    --shadow: {C["shadow"]};
    --blue:   {BLUE};
    --green:  {GREEN};
    --red:    {RED};
    --yellow: {YELLOW};
    --gray:   {GRAY};
}}

/* ── Smooth theme transitions ─────────────────────────────── */
*, *::before, *::after {{
    transition: background-color 0.30s ease, color 0.22s ease,
                border-color 0.25s ease !important;
}}
.stButton > button {{
    transition: background-color 0.30s ease, color 0.22s ease,
                border-color 0.25s ease,
                opacity 0.15s ease, box-shadow 0.15s ease !important;
}}

/* ── Base typography ──────────────────────────────────────── */
html, body, [class*="css"] {{
    font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-weight: {C["fw_body"]};
}}
p, label, span, div {{
    color: var(--t0);
}}

/* ── App background ───────────────────────────────────────── */
.stApp {{
    background: linear-gradient(180deg, var(--bg-app) 0%, var(--bg-sec) 100%) !important;
    color: var(--t0);
}}

/* ── Header ───────────────────────────────────────────────── */
[data-testid="stHeader"] {{
    background: {C["hdr_bg"]} !important;
    backdrop-filter: blur(14px);
    border-bottom: 1px solid var(--bdm);
}}

/* ── Sidebar — force background with high specificity ─────── */
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] > div:first-child {{
    background: linear-gradient(180deg, {C["side_bg1"]}, {C["side_bg2"]}) !important;
    background-color: {C["side_bg1"]} !important;
    border-right: 1px solid var(--bdm) !important;
}}
section[data-testid="stSidebar"] * {{
    color: var(--t0);
}}
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] h3 {{
    color: var(--t0) !important;
    font-weight: 600 !important;
}}
section[data-testid="stSidebar"] small,
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{
    color: var(--t2) !important;
    font-weight: {C["fw_body"]} !important;
}}
section[data-testid="stSidebar"] .stDivider {{
    border-color: var(--bdm) !important;
}}

.block-container {{
    padding-top: 1.5rem;
    padding-bottom: 3rem;
    max-width: 1500px;
}}

/* ── Streamlit native form elements — use CSS vars ────────── */
/* Select boxes */
[data-baseweb="select"] > div:first-child {{
    background-color: var(--bg-solid) !important;
    border-color: var(--bdm) !important;
    color: var(--t0) !important;
}}
[data-baseweb="select"] > div:first-child > div {{
    color: var(--t0) !important;
}}
/* Text inputs */
[data-baseweb="base-input"],
[data-baseweb="input"] {{
    background-color: var(--bg-solid) !important;
    color: var(--t0) !important;
}}
input, textarea {{
    color: var(--t0) !important;
    background-color: var(--bg-solid) !important;
    font-weight: {C["fw_body"]} !important;
}}
/* Placeholder */
::placeholder {{
    color: var(--t3) !important;
    opacity: 1 !important;
}}
/* Multiselect tags */
[data-baseweb="tag"] {{
    background-color: {BLUE}22 !important;
    color: {BLUE} !important;
}}
[data-baseweb="tag"] span {{
    color: {BLUE} !important;
}}
/* Dropdown popover */
div[role="listbox"],
ul[data-baseweb="menu"] {{
    background-color: var(--bg-solid) !important;
    border-color: var(--bdm) !important;
}}
li[role="option"] {{
    color: var(--t0) !important;
    background-color: transparent !important;
    font-weight: {C["fw_body"]} !important;
}}
li[role="option"]:hover,
li[aria-selected="true"] {{
    background-color: var(--bg-subtle) !important;
}}
/* Select box wrapper highlight */
[data-testid="stSelectbox"] > div > div,
[data-testid="stMultiSelect"] > div > div {{
    border-color: var(--bdm) !important;
}}

/* ── General text elements ────────────────────────────────── */
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
.stMarkdown p {{
    color: var(--t0) !important;
    font-weight: {C["fw_body"]} !important;
}}
[data-testid="stText"] {{
    color: var(--t0) !important;
}}
.stCaption, [data-testid="stCaptionContainer"] {{
    color: var(--t2) !important;
}}
h1, h2, h3, h4, h5, h6 {{
    color: var(--t0) !important;
}}
[data-testid="stSubheader"] {{
    color: var(--t0) !important;
}}

/* ── Sticky header card ───────────────────────────────────── */
.premium-header {{
    position: sticky;
    top: 0.65rem;
    z-index: 20;
    padding: 1.25rem 1.35rem;
    margin-bottom: 1.25rem;
    border: 1px solid var(--bdm);
    border-radius: 24px;
    background: linear-gradient(135deg, var(--bg-card), var(--bg-subtle));
    box-shadow: 0 18px 55px var(--shadow);
    backdrop-filter: blur(18px);
    animation: fadeIn 520ms ease-out;
}}
.header-title {{
    font-size: 1.55rem;
    font-weight: 800;
    letter-spacing: -0.035em;
    color: var(--t0);
    margin: 0;
}}
.header-subtitle {{
    font-size: 0.90rem;
    color: var(--t2);
    margin-top: 0.25rem;
}}

/* ── KPI cards ────────────────────────────────────────────── */
.kpi-card {{
    padding: 1rem;
    min-height: 112px;
    border-radius: 20px;
    background: linear-gradient(145deg, var(--bg-card), var(--bg-subtle));
    border: 1px solid var(--bd);
    box-shadow: 0 12px 28px var(--shadow);
    animation: floatIn 500ms ease-out;
}}
.kpi-label {{ font-size: 0.78rem; color: var(--t2); text-transform: uppercase; letter-spacing: .08em; font-weight: 700; }}
.kpi-value {{ font-size: 1.45rem; color: var(--t0); font-weight: 800; margin-top: .35rem; }}
.kpi-note  {{ font-size: 0.82rem; color: var(--t1); margin-top: .25rem; }}
.kpi-blue   {{ border-left: 4px solid {BLUE}; }}
.kpi-green  {{ border-left: 4px solid {GREEN}; }}
.kpi-red    {{ border-left: 4px solid {RED}; }}
.kpi-yellow {{ border-left: 4px solid {YELLOW}; }}

/* ── st.metric ────────────────────────────────────────────── */
.stMetric {{
    background: linear-gradient(145deg, var(--bg-card), var(--bg-subtle));
    border: 1px solid var(--bd);
    border-radius: 18px;
    padding: 0.95rem;
    box-shadow: 0 10px 26px var(--shadow);
}}
[data-testid="stMetricLabel"] p {{ color: var(--t2) !important; font-weight: 600; }}
[data-testid="stMetricValue"]   {{ color: var(--t0) !important; font-weight: 800; }}
[data-testid="stMetricDelta"]   {{ font-weight: 700; }}

/* ── DataFrame ────────────────────────────────────────────── */
.stDataFrame {{
    border-radius: 18px;
    overflow: hidden;
    border: 1px solid var(--bd);
}}

/* ── Buttons ──────────────────────────────────────────────── */
.stButton > button {{
    border-radius: 10px !important;
    border: 1px solid {BLUE}66 !important;
    background: {BLUE} !important;
    color: white !important;
    font-weight: 600 !important;
}}
.stButton > button:hover {{
    opacity: 0.88;
    box-shadow: 0 6px 18px {BLUE}38;
}}

/* ── Expander ─────────────────────────────────────────────── */
[data-testid="stExpander"] {{
    border: 1px solid var(--bd);
    border-radius: 18px;
    background: var(--bg-subtle);
}}
[data-testid="stExpander"] summary {{
    color: var(--t0) !important;
    font-weight: 600;
}}

/* ── Divider ──────────────────────────────────────────────── */
hr, [data-testid="stDivider"] {{
    border-color: var(--bdm) !important;
}}

/* ── Scrollbar ────────────────────────────────────────────── */
::-webkit-scrollbar {{ width: 10px; height: 10px; }}
::-webkit-scrollbar-track {{ background: {C["scroll_tr"]}; }}
::-webkit-scrollbar-thumb {{ background: {C["scroll_th"]}; border-radius: 999px; }}
::-webkit-scrollbar-thumb:hover {{ background: var(--t2); }}

/* ── Animations ───────────────────────────────────────────── */
@keyframes fadeIn  {{ from {{ opacity: 0; transform: translateY(8px);          }} to {{ opacity: 1; transform: translateY(0);       }} }}
@keyframes floatIn {{ from {{ opacity: 0; transform: translateY(10px) scale(.99); }} to {{ opacity: 1; transform: translateY(0) scale(1); }} }}
</style>
'''


def apply_css():
    """Inject theme-aware CSS into the page."""
    try:
        mode = st.session_state.get("theme_mode", "dark")
    except Exception:
        mode = "dark"
    C = _LIGHT if mode == "light" else _DARK
    st.markdown(_build_css(C), unsafe_allow_html=True)


def inject_theme_script():
    """Set data-theme attribute on the HTML element via iframe script."""
    try:
        mode = st.session_state.get("theme_mode", "dark")
    except Exception:
        mode = "dark"
    components.html(
        f'<script>'
        f'(function(){{'
        f'  var d=window.parent.document.documentElement;'
        f'  if(d.dataset.theme!=="{mode}")d.dataset.theme="{mode}";'
        f'}})();'
        f'</script>',
        height=0,
        scrolling=False,
    )
