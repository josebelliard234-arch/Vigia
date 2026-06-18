import streamlit as st
from styles.theme import (
    BG_MAIN, BG_SECONDARY, CARD_BG, CARD_ELEVATED,
    TEXT_MAIN, TEXT_SECONDARY, TEXT_MUTED,
    BLUE, GREEN, RED, YELLOW, GRAY,
)

_CSS = f'''
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {{
    --bg-main: {BG_MAIN};
    --bg-secondary: {BG_SECONDARY};
    --card-bg: {CARD_BG};
    --card-elevated: {CARD_ELEVATED};
    --text-main: {TEXT_MAIN};
    --text-secondary: {TEXT_SECONDARY};
    --text-muted: {TEXT_MUTED};
    --blue: {BLUE};
    --green: {GREEN};
    --red: {RED};
    --yellow: {YELLOW};
    --gray: {GRAY};
}}

html, body, [class*="css"] {{
    font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}}

.stApp {{
    background: linear-gradient(180deg, {BG_MAIN} 0%, {BG_SECONDARY} 100%);
    color: {TEXT_MAIN};
}}

[data-testid="stHeader"] {{
    background: rgba(15, 23, 42, 0.78);
    backdrop-filter: blur(14px);
    border-bottom: 1px solid rgba(148, 163, 184, 0.12);
}}

[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, rgba(17,24,39,0.98), rgba(15,23,42,0.98));
    border-right: 1px solid rgba(148, 163, 184, 0.12);
}}

.block-container {{
    padding-top: 1.5rem;
    padding-bottom: 3rem;
    max-width: 1500px;
}}

.premium-header {{
    position: sticky;
    top: 0.65rem;
    z-index: 20;
    padding: 1.25rem 1.35rem;
    margin-bottom: 1.25rem;
    border: 1px solid rgba(148, 163, 184, 0.16);
    border-radius: 24px;
    background: linear-gradient(135deg, rgba(30,41,59,0.94), rgba(39,52,73,0.86));
    box-shadow: 0 18px 55px rgba(0,0,0,0.25);
    backdrop-filter: blur(18px);
    animation: fadeIn 520ms ease-out;
}}

.header-title {{
    font-size: 1.55rem;
    font-weight: 800;
    letter-spacing: -0.035em;
    color: {TEXT_MAIN};
    margin: 0;
}}

.header-subtitle {{
    font-size: 0.90rem;
    color: {TEXT_MUTED};
    margin-top: 0.25rem;
}}

.kpi-card {{
    padding: 1rem;
    min-height: 112px;
    border-radius: 20px;
    background: linear-gradient(145deg, rgba(39,52,73,0.96), rgba(30,41,59,0.96));
    border: 1px solid rgba(148,163,184,0.14);
    box-shadow: 0 12px 28px rgba(0,0,0,0.18);
    animation: floatIn 500ms ease-out;
}}
.kpi-label {{ font-size: 0.78rem; color: {TEXT_MUTED}; text-transform: uppercase; letter-spacing: .08em; }}
.kpi-value {{ font-size: 1.45rem; color: {TEXT_MAIN}; font-weight: 800; margin-top: .35rem; }}
.kpi-note {{ font-size: 0.82rem; color: {TEXT_SECONDARY}; margin-top: .25rem; }}
.kpi-blue {{ border-left: 4px solid {BLUE}; }}
.kpi-green {{ border-left: 4px solid {GREEN}; }}
.kpi-red {{ border-left: 4px solid {RED}; }}
.kpi-yellow {{ border-left: 4px solid {YELLOW}; }}

.stMetric {{
    background: linear-gradient(145deg, rgba(39,52,73,0.96), rgba(30,41,59,0.96));
    border: 1px solid rgba(148,163,184,0.14);
    border-radius: 18px;
    padding: 0.95rem;
    box-shadow: 0 10px 26px rgba(0,0,0,0.16);
}}
[data-testid="stMetricLabel"] p {{ color: {TEXT_MUTED}; font-weight: 600; }}
[data-testid="stMetricValue"] {{ color: {TEXT_MAIN}; font-weight: 800; }}
[data-testid="stMetricDelta"] {{ font-weight: 700; }}

.stDataFrame {{
    border-radius: 18px;
    overflow: hidden;
    border: 1px solid rgba(148,163,184,0.14);
}}

.stButton > button {{
    border-radius: 10px !important;
    border: 1px solid rgba(37,99,235,0.40) !important;
    background: {BLUE} !important;
    color: white !important;
    font-weight: 600 !important;
    transition: opacity 150ms ease, box-shadow 150ms ease !important;
}}
.stButton > button:hover {{
    opacity: 0.88;
    box-shadow: 0 6px 18px rgba(37,99,235,0.22);
}}

[data-testid="stExpander"] {{
    border: 1px solid rgba(148,163,184,0.14);
    border-radius: 18px;
    background: rgba(30,41,59,0.72);
}}

::-webkit-scrollbar {{ width: 10px; height: 10px; }}
::-webkit-scrollbar-track {{ background: {BG_SECONDARY}; }}
::-webkit-scrollbar-thumb {{ background: {GRAY}; border-radius: 999px; }}
::-webkit-scrollbar-thumb:hover {{ background: {TEXT_MUTED}; }}

@keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(8px); }} to {{ opacity: 1; transform: translateY(0); }} }}
@keyframes floatIn {{ from {{ opacity: 0; transform: translateY(10px) scale(.99); }} to {{ opacity: 1; transform: translateY(0) scale(1); }} }}
</style>
'''


def apply_css():
    """Inyecta el bloque CSS premium en la pagina."""
    st.markdown(_CSS, unsafe_allow_html=True)
