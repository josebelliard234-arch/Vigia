import streamlit as st
import streamlit.components.v1 as components

from styles.theme import get_theme_tokens, get_mode, BLUE, GREEN, RED, YELLOW, GRAY


def _build_css(T: dict, mode: str) -> str:
    """Build the full CSS string from theme tokens T.

    Outputs TWO sets of CSS custom properties:
      1. Semantic tokens  (--main-bg, --card-bg, --text-primary, ...)
      2. Legacy aliases   (--bg-app, --t0, --bdm, ...)  so existing inline HTML
         in tabs that already uses the old names keeps working without changes.
    """
    is_light = mode == "light"

    # ── Light-mode overrides injected directly (no iframe dependency) ──────
    # These are non-empty only when is_light=True, placed at the END of the
    # <style> block so they win any specificity tie with Streamlit's own CSS.
    _native = f"""
/* ════ LIGHT MODE — Streamlit native element overrides ════ */

/* Override Streamlit's own theming CSS variables.
   Streamlit uses these internally (e.g. --secondary-background-color for
   the sidebar), so overriding them here is the most reliable sidebar fix. */
:root {{
    --secondary-background-color: {T["SIDEBAR_BG"]} !important;
    --background-color:           {T["MAIN_BG"]}    !important;
    --text-color:                 {T["TEXT_PRIMARY"]} !important;
}}

.stApp {{
    background: linear-gradient(180deg, {T["MAIN_BG"]} 0%, {T["SIDEBAR_BG_2"]} 100%) !important;
    color: {T["TEXT_PRIMARY"]} !important;
}}
[data-testid="stHeader"] {{
    background: {T["HDR_BG"]} !important;
    border-bottom: 1px solid {T["BORDER_SOFT"]} !important;
}}

/* ── SIDEBAR — all known selectors for Streamlit 1.x ─────────
   Outer shell gets the gradient; every inner wrapper → transparent.
   section[data-testid] has tag+attr specificity (0,1,1) which beats
   Streamlit's plain attribute-only selectors. */
section[data-testid="stSidebar"],
[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, {T["SIDEBAR_BG"]} 0%, {T["SIDEBAR_BG_2"]} 100%) !important;
    background-color: {T["SIDEBAR_BG"]} !important;
    border-right: 1px solid {T["BORDER_SOFT"]} !important;
    color: {T["TEXT_PRIMARY"]} !important;
}}

/* All inner wrappers → transparent so the gradient from the shell shows */
[data-testid="stSidebar"] > div,
[data-testid="stSidebar"] > div:first-child,
[data-testid="stSidebar"] > div > div,
[data-testid="stSidebar"] section,
[data-testid="stSidebar"] [data-testid="stSidebarContent"],
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"],
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{
    background: transparent !important;
    background-color: transparent !important;
}}

/* ── SIDEBAR BUTTONS ─────────────────────────────────────────
   Primary (type="primary") → solid blue (logout, import, confirm).
   Secondary / default       → glass pill (theme toggle, small actions). */
[data-testid="stSidebar"] button[kind="primary"] {{
    background: {T["PRIMARY"]} !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    width: 100% !important;
    box-shadow: 0 4px 14px {T["PRIMARY"]}44 !important;
}}
[data-testid="stSidebar"] button[kind="primary"]:hover {{
    background: {T["PRIMARY_HOVER"]} !important;
    box-shadow: 0 6px 18px {T["PRIMARY"]}55 !important;
}}
[data-testid="stSidebar"] button:not([kind="primary"]) {{
    background: rgba(255,255,255,0.72) !important;
    border: 1px solid {T["BORDER"]} !important;
    color: {T["TEXT_PRIMARY"]} !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    box-shadow: 0 2px 8px {T["SHADOW"]} !important;
}}
[data-testid="stSidebar"] button:not([kind="primary"]):hover {{
    background: rgba(255,255,255,0.90) !important;
    border-color: {T["PRIMARY"]} !important;
    color: {T["PRIMARY"]} !important;
}}

/* Select + MultiSelect */
[data-baseweb="select"] > div {{
    background-color: {T["INPUT_BG"]} !important;
    border-color: {T["INPUT_BORDER"]} !important;
}}
[data-baseweb="select"] > div > div,
[data-baseweb="select"] > div > div > div {{
    background-color: {T["INPUT_BG"]} !important;
    color: {T["TEXT_PRIMARY"]} !important;
}}
[data-baseweb="select"] div[class],
[data-baseweb="select"] span {{
    color: {T["TEXT_PRIMARY"]} !important;
}}

/* Text / number inputs */
[data-baseweb="base-input"] {{
    background-color: {T["INPUT_BG"]} !important;
}}
[data-baseweb="base-input"] input,
[data-baseweb="input"] input,
input:not([type="checkbox"]):not([type="radio"]):not([type="range"]) {{
    background-color: {T["INPUT_BG"]} !important;
    color: {T["TEXT_PRIMARY"]} !important;
}}
textarea {{
    background-color: {T["INPUT_BG"]} !important;
    color: {T["TEXT_PRIMARY"]} !important;
}}

/* Dropdown popover */
div[role="listbox"],
ul[data-baseweb="menu"] {{
    background-color: {T["INPUT_BG"]} !important;
    border-color: {T["BORDER"]} !important;
}}
li[role="option"] {{
    color: {T["TEXT_PRIMARY"]} !important;
    background-color: {T["INPUT_BG"]} !important;
}}
li[role="option"]:hover {{ background-color: {T["TABLE_ROW_ALT_BG"]} !important; }}
li[aria-selected="true"] {{ background-color: {T["PRIMARY_SOFT"]} !important; color: {T["PRIMARY"]} !important; }}

/* Multiselect tags */
[data-baseweb="tag"] {{
    background-color: {T["PRIMARY_SOFT"]} !important;
    border-color: {T["PRIMARY"]}44 !important;
}}
[data-baseweb="tag"] span {{ color: {T["PRIMARY"]} !important; }}

/* Labels + body text */
label {{
    color: {T["TEXT_PRIMARY"]} !important;
    font-weight: 600 !important;
}}
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] span:not([style]) {{
    color: {T["TEXT_PRIMARY"]} !important;
    font-weight: 500 !important;
}}
[data-testid="stText"] {{ color: {T["TEXT_PRIMARY"]} !important; }}
.stCaption, [data-testid="stCaptionContainer"] p {{ color: {T["TEXT_MUTED"]} !important; }}
h1, h2, h3, h4, h5, h6,
[data-testid="stSubheader"],
[data-testid="stHeadingContainer"] {{ color: {T["TEXT_PRIMARY"]} !important; }}
hr, [data-testid="stDivider"] {{ border-color: {T["BORDER_SOFT"]} !important; }}

/* Expander */
[data-testid="stExpander"] {{
    background: {T["GLASS_BG"]} !important;
    border-color: {T["BORDER_SOFT"]} !important;
}}
[data-testid="stExpander"] summary p,
[data-testid="stExpander"] summary span {{
    color: {T["TEXT_PRIMARY"]} !important;
    font-weight: 600 !important;
}}

/* Sidebar text */
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span:not([style]),
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {{ color: {T["TEXT_SECONDARY"]} !important; }}
[data-testid="stSidebar"] small,
[data-testid="stSidebar"] .stCaption {{ color: {T["TEXT_MUTED"]} !important; }}

/* File uploader */
[data-testid="stFileUploadDropzone"] {{
    background-color: {T["TABLE_ROW_ALT_BG"]} !important;
    border-color: {T["INPUT_BORDER"]} !important;
}}
[data-testid="stNumberInput"] [data-baseweb="input"] {{
    background-color: {T["INPUT_BG"]} !important;
}}
[data-testid="stRadio"] label,
[data-testid="stCheckbox"] label {{ color: {T["TEXT_SECONDARY"]} !important; }}
""" if is_light else ""

    return f'''
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* ════════════════════════════════════════════════════════════
   SEMANTIC TOKENS  (--main-bg, --card-bg, --text-primary …)
   ════════════════════════════════════════════════════════════ */
:root {{
    /* Backgrounds */
    --main-bg:          {T["MAIN_BG"]};
    --sidebar-bg:       {T["SIDEBAR_BG"]};
    --sidebar-bg-2:     {T["SIDEBAR_BG_2"]};
    --card-bg:          {T["CARD_BG"]};
    --card-bg-solid:    {T["CARD_BG_SOLID"]};
    --glass-bg:         {T["GLASS_BG"]};

    /* Typography */
    --text-primary:     {T["TEXT_PRIMARY"]};
    --text-secondary:   {T["TEXT_SECONDARY"]};
    --text-muted:       {T["TEXT_MUTED"]};
    --text-faint:       {T["TEXT_FAINT"]};

    /* Borders */
    --border:           {T["BORDER"]};
    --border-soft:      {T["BORDER_SOFT"]};
    --border-strong:    {T["BORDER_STRONG"]};

    /* Inputs */
    --input-bg:         {T["INPUT_BG"]};
    --input-border:     {T["INPUT_BORDER"]};
    --input-focus:      {T["INPUT_FOCUS"]};

    /* Actions */
    --primary:          {T["PRIMARY"]};
    --primary-soft:     {T["PRIMARY_SOFT"]};
    --success:          {T["SUCCESS"]};
    --danger:           {T["DANGER"]};
    --warning:          {T["WARNING"]};

    /* Tables */
    --table-bg:         {T["TABLE_BG"]};
    --table-header-bg:  {T["TABLE_HEADER_BG"]};
    --table-row-bg:     {T["TABLE_ROW_BG"]};
    --table-row-alt-bg: {T["TABLE_ROW_ALT_BG"]};
    --table-border:     {T["TABLE_BORDER"]};

    /* Misc */
    --shadow:           {T["SHADOW"]};

    /* Accent (same in both modes) */
    --blue:   {BLUE};
    --green:  {GREEN};
    --red:    {RED};
    --yellow: {YELLOW};
    --gray:   {GRAY};
}}

/* ════════════════════════════════════════════════════════════
   LEGACY ALIASES  — existing inline HTML in tabs uses these
   ════════════════════════════════════════════════════════════ */
:root {{
    --bg-app:    var(--main-bg);
    --bg-sec:    {T["SIDEBAR_BG_2"]};
    --bg-card:   var(--card-bg);
    --bg-subtle: var(--glass-bg);
    --bg-solid:  var(--card-bg-solid);
    --t0:        var(--text-primary);
    --t1:        var(--text-secondary);
    --t2:        var(--text-muted);
    --t3:        var(--text-faint);
    --bd:        var(--border-soft);
    --bdm:       var(--border);
    --bds:       var(--border-strong);
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
    font-weight: {T["FW_BODY"]};
}}

/* ── App background ───────────────────────────────────────── */
.stApp {{
    background: linear-gradient(180deg, var(--main-bg) 0%, var(--sidebar-bg-2) 100%);
    color: var(--text-primary);
}}

/* ── Header ───────────────────────────────────────────────── */
[data-testid="stHeader"] {{
    background: {T["HDR_BG"]};
    backdrop-filter: blur(14px);
    border-bottom: 1px solid var(--border-soft);
}}

/* ── Sidebar ──────────────────────────────────────────────── */
[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, {T["SIDEBAR_BG"]}, {T["SIDEBAR_BG_2"]}) !important;
    background-color: {T["SIDEBAR_BG"]} !important;
    border-right: 1px solid var(--border);
}}
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] h3 {{ color: var(--text-primary) !important; }}
[data-testid="stSidebar"] small,
[data-testid="stSidebar"] .stCaption {{ color: var(--text-muted) !important; }}

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
    border: 1px solid var(--border);
    border-radius: 24px;
    background: linear-gradient(135deg, var(--card-bg), var(--glass-bg));
    box-shadow: 0 18px 55px var(--shadow);
    backdrop-filter: blur(18px);
    animation: fadeIn 520ms ease-out;
}}
.header-title {{
    font-size: 1.55rem;
    font-weight: 800;
    letter-spacing: -0.035em;
    color: var(--text-primary);
    margin: 0;
}}
.header-subtitle {{
    font-size: 0.90rem;
    color: var(--text-muted);
    margin-top: 0.25rem;
}}

/* ── KPI cards ────────────────────────────────────────────── */
.kpi-card {{
    padding: 1rem;
    min-height: 112px;
    border-radius: 20px;
    background: linear-gradient(145deg, var(--card-bg), var(--glass-bg));
    border: 1px solid var(--border-soft);
    box-shadow: 0 12px 28px var(--shadow);
    animation: floatIn 500ms ease-out;
}}
.kpi-label {{ font-size: 0.78rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: .08em; font-weight: 700; }}
.kpi-value {{ font-size: 1.45rem; color: var(--text-primary); font-weight: 800; margin-top: .35rem; }}
.kpi-note  {{ font-size: 0.82rem; color: var(--text-secondary); margin-top: .25rem; }}
.kpi-blue   {{ border-left: 4px solid {BLUE}; }}
.kpi-green  {{ border-left: 4px solid {GREEN}; }}
.kpi-red    {{ border-left: 4px solid {RED}; }}
.kpi-yellow {{ border-left: 4px solid {YELLOW}; }}

/* ── st.metric ────────────────────────────────────────────── */
.stMetric {{
    background: linear-gradient(145deg, var(--card-bg), var(--glass-bg));
    border: 1px solid var(--border-soft);
    border-radius: 18px;
    padding: 0.95rem;
    box-shadow: 0 10px 26px var(--shadow);
}}
[data-testid="stMetricLabel"] p {{ color: var(--text-muted) !important; font-weight: 600; }}
[data-testid="stMetricValue"]   {{ color: var(--text-primary) !important; font-weight: 800; }}
[data-testid="stMetricDelta"]   {{ font-weight: 700; }}

/* ── DataFrame ────────────────────────────────────────────── */
.stDataFrame {{
    border-radius: 18px;
    overflow: hidden;
    border: 1px solid var(--border-soft);
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
    border: 1px solid var(--border-soft);
    border-radius: 18px;
    background: var(--glass-bg);
}}

/* ── Scrollbar ────────────────────────────────────────────── */
::-webkit-scrollbar {{ width: 10px; height: 10px; }}
::-webkit-scrollbar-track {{ background: {T["SCROLL_TRACK"]}; }}
::-webkit-scrollbar-thumb {{ background: {T["SCROLL_THUMB"]}; border-radius: 999px; }}
::-webkit-scrollbar-thumb:hover {{ background: var(--text-muted); }}

/* ── Animations ───────────────────────────────────────────── */
@keyframes fadeIn  {{ from {{ opacity: 0; transform: translateY(8px);            }} to {{ opacity: 1; transform: translateY(0);        }} }}
@keyframes floatIn {{ from {{ opacity: 0; transform: translateY(10px) scale(.99); }} to {{ opacity: 1; transform: translateY(0) scale(1); }} }}

{_native}
</style>
'''


def apply_css() -> None:
    """Inject theme-aware CSS. Source of truth: get_theme_tokens() in styles/theme.py."""
    mode = get_mode()
    T = get_theme_tokens(mode)
    st.markdown(_build_css(T, mode), unsafe_allow_html=True)


def inject_theme_script() -> None:
    """Set data-theme attribute on <html> for any CSS that uses html[data-theme] selectors."""
    mode = get_mode()
    components.html(
        f'<script>(function(){{'
        f'var d=window.parent.document.documentElement;'
        f'if(d.dataset.theme!=="{mode}")d.dataset.theme="{mode}";'
        f'}})();</script>',
        height=0,
        scrolling=False,
    )
