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
    "hdr_bg":    "rgba(15,23,42,0.78)",
    "side_bg1":  "rgba(17,24,39,0.98)",
    "side_bg2":  "rgba(15,23,42,0.98)",
    "scroll_tr": "#111827",
    "scroll_th": "#4B5563",
}

_LIGHT = {
    "bg_app":    "#F8FAFC",
    "bg_sec":    "#F1F5F9",
    "bg_card":   "rgba(255,255,255,0.93)",
    "bg_subtle": "rgba(241,245,249,0.80)",
    "bg_solid":  "#FFFFFF",
    "t0":        "#0F172A",
    "t1":        "#1E293B",
    "t2":        "#64748B",
    "t3":        "#94A3B8",
    "bd":        "rgba(15,23,42,0.10)",
    "bdm":       "rgba(15,23,42,0.16)",
    "bds":       "rgba(15,23,42,0.22)",
    "shadow":    "rgba(15,23,42,0.09)",
    "hdr_bg":    "rgba(248,250,252,0.93)",
    "side_bg1":  "rgba(241,245,249,0.99)",
    "side_bg2":  "rgba(248,250,252,0.99)",
    "scroll_tr": "#F1F5F9",
    "scroll_th": "#CBD5E1",
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
/* Keep button hover snappy - re-add opacity/shadow transitions */
.stButton > button {{
    transition: background-color 0.30s ease, color 0.22s ease,
                border-color 0.25s ease,
                opacity 0.15s ease, box-shadow 0.15s ease !important;
}}

html, body, [class*="css"] {{
    font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}}

/* ── App background ───────────────────────────────────────── */
.stApp {{
    background: linear-gradient(180deg, var(--bg-app) 0%, var(--bg-sec) 100%);
    color: var(--t0);
}}

/* ── Header ───────────────────────────────────────────────── */
[data-testid="stHeader"] {{
    background: {C["hdr_bg"]};
    backdrop-filter: blur(14px);
    border-bottom: 1px solid var(--bdm);
}}

/* ── Sidebar ──────────────────────────────────────────────── */
[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, {C["side_bg1"]}, {C["side_bg2"]});
    border-right: 1px solid var(--bdm);
}}
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] h3 {{
    color: var(--t0) !important;
}}
[data-testid="stSidebar"] .stCaption,
[data-testid="stSidebar"] small {{
    color: var(--t2) !important;
}}

.block-container {{
    padding-top: 1.5rem;
    padding-bottom: 3rem;
    max-width: 1500px;
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
.kpi-label {{ font-size: 0.78rem; color: var(--t2); text-transform: uppercase; letter-spacing: .08em; }}
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
[data-testid="stMetricLabel"] p {{ color: var(--t2); font-weight: 600; }}
[data-testid="stMetricValue"]   {{ color: var(--t0); font-weight: 800; }}
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
    border: 1px solid rgba(37,99,235,0.40) !important;
    background: {BLUE} !important;
    color: white !important;
    font-weight: 600 !important;
}}
.stButton > button:hover {{
    opacity: 0.88;
    box-shadow: 0 6px 18px rgba(37,99,235,0.22);
}}

/* ── Expander ─────────────────────────────────────────────── */
[data-testid="stExpander"] {{
    border: 1px solid var(--bd);
    border-radius: 18px;
    background: var(--bg-subtle);
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
    """Set data-theme attribute on the HTML element via iframe script (enables CSS var override)."""
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
