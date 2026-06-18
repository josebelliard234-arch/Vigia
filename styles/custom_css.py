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
    background:
        radial-gradient(circle at top left,  rgba(37,99,235,0.08),  transparent 30%),
        radial-gradient(circle at top right, rgba(22,163,74,0.06),  transparent 28%),
        #F6F8FC !important;
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

/* ══════════════════════════════════════════════════════════════
   FORM CONTROLS — light mode
   BaseWeb renders the dropdown popover at <body> level (not inside
   the widget), so selectors here MUST be global, not scoped.
   All values are hardcoded (no CSS vars) to avoid resolution issues.
   ══════════════════════════════════════════════════════════════ */

/* ── SELECT / MULTISELECT — closed state ─────────────────── */
[data-baseweb="select"] {{
    border-radius: 12px !important;
}}
/* Control container (border + background visible when closed) */
[data-baseweb="select"] > div {{
    background-color: #FFFFFF !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: 12px !important;
    color: #0F172A !important;
    min-height: 42px !important;
}}
[data-baseweb="select"] > div:focus-within {{
    border-color: #2563EB !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.14) !important;
}}
/* All inner divs of the closed control */
[data-baseweb="select"] > div > div {{
    background-color: #FFFFFF !important;
    color: #0F172A !important;
}}
[data-baseweb="select"] > div > div > div {{
    background-color: #FFFFFF !important;
    color: #0F172A !important;
    font-weight: 600 !important;
}}
/* Catch-all: any span or div[class] inside select */
[data-baseweb="select"] span,
[data-baseweb="select"] div[class] {{
    color: #0F172A !important;
}}
/* Search input inside select (for searchable selects) */
[data-baseweb="select"] input {{
    background-color: transparent !important;
    color: #0F172A !important;
    caret-color: #2563EB !important;
}}
[data-baseweb="select"] input::placeholder {{
    color: #94A3B8 !important;
    font-weight: 500 !important;
}}

/* ── DROPDOWN POPOVER (rendered at body level) ───────────── */
/* Outer popover shell */
[data-baseweb="popover"] > div,
[data-baseweb="popover"] {{
    background-color: #FFFFFF !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: 12px !important;
    box-shadow: 0 16px 36px rgba(15,23,42,0.14) !important;
    overflow: hidden !important;
}}
/* Menu / listbox inside popover */
[data-baseweb="popover"] [data-baseweb="menu"],
[data-baseweb="popover"] ul,
[data-baseweb="menu"],
div[role="listbox"],
ul[data-baseweb="menu"] {{
    background-color: #FFFFFF !important;
    border: none !important;
    border-radius: 0 !important;
}}
/* Every option row */
[data-baseweb="popover"] li[role="option"],
li[role="option"] {{
    background-color: #FFFFFF !important;
    color: #0F172A !important;
    font-weight: 500 !important;
}}
[data-baseweb="popover"] li[role="option"] span,
li[role="option"] span {{
    color: #0F172A !important;
}}
/* Hover */
[data-baseweb="popover"] li[role="option"]:hover,
li[role="option"]:hover {{
    background-color: #EFF6FF !important;
    color: #0F172A !important;
}}
/* Selected option */
[data-baseweb="popover"] li[aria-selected="true"],
li[aria-selected="true"] {{
    background-color: #DBEAFE !important;
    color: #1D4ED8 !important;
    font-weight: 700 !important;
}}
[data-baseweb="popover"] li[aria-selected="true"] span,
li[aria-selected="true"] span {{
    color: #1D4ED8 !important;
}}

/* ── MULTISELECT TAGS ────────────────────────────────────── */
[data-baseweb="tag"] {{
    background-color: #DBEAFE !important;
    border: 1px solid #BFDBFE !important;
    border-radius: 8px !important;
    color: #1D4ED8 !important;
}}
[data-baseweb="tag"] span {{
    color: #1D4ED8 !important;
    font-weight: 700 !important;
}}
/* Close (×) button on tag */
[data-baseweb="tag"] [role="button"],
[data-baseweb="tag"] button {{
    color: #1D4ED8 !important;
    opacity: 0.8;
}}
[data-baseweb="tag"] [role="button"]:hover,
[data-baseweb="tag"] button:hover {{
    opacity: 1;
}}

/* ── TEXT INPUT ──────────────────────────────────────────── */
[data-baseweb="base-input"] {{
    background-color: #FFFFFF !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: 12px !important;
    overflow: visible !important;
}}
[data-baseweb="base-input"]:focus-within {{
    border-color: #2563EB !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.14) !important;
}}
[data-baseweb="base-input"] > div {{
    background-color: #FFFFFF !important;
}}
[data-baseweb="base-input"] input,
[data-baseweb="input"] input {{
    background-color: #FFFFFF !important;
    color: #0F172A !important;
    font-weight: 600 !important;
    caret-color: #2563EB !important;
}}
[data-baseweb="base-input"] input::placeholder,
[data-baseweb="input"] input::placeholder {{
    color: #94A3B8 !important;
    font-weight: 500 !important;
}}
/* Catch-all for native inputs not wrapped by baseweb */
input:not([type="checkbox"]):not([type="radio"]):not([type="range"]):not([type="color"]) {{
    background-color: #FFFFFF !important;
    color: #0F172A !important;
}}
input:not([type="checkbox"]):not([type="radio"])::placeholder {{
    color: #94A3B8 !important;
}}

/* ── TEXTAREA ────────────────────────────────────────────── */
[data-baseweb="textarea"],
[data-baseweb="textarea"] > div {{
    background-color: #FFFFFF !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: 12px !important;
}}
[data-baseweb="textarea"]:focus-within {{
    border-color: #2563EB !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.14) !important;
}}
textarea {{
    background-color: #FFFFFF !important;
    color: #0F172A !important;
    font-weight: 500 !important;
}}
textarea::placeholder {{
    color: #94A3B8 !important;
    font-weight: 400 !important;
}}

/* ── NUMBER INPUT ────────────────────────────────────────── */
[data-testid="stNumberInput"] [data-baseweb="input"],
[data-testid="stNumberInput"] [data-baseweb="base-input"] {{
    background-color: #FFFFFF !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: 12px !important;
}}

/* ══════════════════════════════════════════════════════════════
   DATAFRAME + HTML TABLES — light mode
   GDG renders cells on canvas; per-cell colors come from the pandas
   Styler (applied via light_df() helper in styles/theme.py).
   These CSS rules cover: container chrome, HTML table fallback,
   and any <table> injected via st.markdown.
   ══════════════════════════════════════════════════════════════ */

/* ══════════════════════════════════════════════════════════════
   AG GRID — ag-theme-alpine (light mode only)
   ag-theme-alpine-dark is used in dark mode (set in Python).
   CSS vars are the standard AG Grid v27+ custom-property API.
   ══════════════════════════════════════════════════════════════ */
.ag-theme-alpine {{
    --ag-background-color:                  #FFFFFF;
    --ag-foreground-color:                  #1E293B;
    --ag-border-color:                      #D8E0EA;
    --ag-secondary-border-color:            #E2E8F0;
    --ag-header-background-color:           #EAF1FB;
    --ag-header-foreground-color:           #0F172A;
    --ag-row-hover-color:                   #EFF6FF;
    --ag-selected-row-background-color:     #DBEAFE;
    --ag-odd-row-background-color:          #F8FAFC;
    --ag-control-panel-background-color:    #F8FAFC;
    --ag-subheader-background-color:        #EAF1FB;
    --ag-panel-background-color:            #FFFFFF;
    --ag-menu-background-color:             #FFFFFF;
    --ag-tooltip-background-color:          #F8FAFC;
    --ag-header-column-separator-color:     #CBD5E1;
    --ag-range-selection-border-color:      #2563EB;
    --ag-range-selection-background-color:  rgba(37,99,235,0.10);
    --ag-input-focus-border-color:          #2563EB;
    --ag-input-focus-box-shadow:            0 0 0 3px rgba(37,99,235,0.14);
    --ag-checkbox-checked-color:            #2563EB;
    --ag-checkbox-background-color:         #FFFFFF;
    --ag-checkbox-border-radius:            4px;
    --ag-card-shadow:                       0 8px 24px rgba(15,23,42,0.08);
    --ag-popup-shadow:                      0 8px 24px rgba(15,23,42,0.12);
    --ag-font-size:                         13px;
    --ag-font-family:                       Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    --ag-cell-horizontal-padding:           12px;
    --ag-row-height:                        38px;
    --ag-header-height:                     44px;
    border-radius: 14px !important;
    overflow: hidden !important;
    border: 1px solid #D8E0EA !important;
}}

/* Header: font weight, bottom border */
.ag-theme-alpine .ag-header {{
    border-bottom: 2px solid #CBD5E1 !important;
}}
.ag-theme-alpine .ag-header-cell-text {{
    color: #0F172A !important;
    font-weight: 800 !important;
}}
.ag-theme-alpine .ag-header-cell,
.ag-theme-alpine .ag-header-group-cell {{
    background-color: #EAF1FB !important;
    color: #0F172A !important;
}}

/* Rows */
.ag-theme-alpine .ag-row-even {{
    background-color: #FFFFFF !important;
}}
.ag-theme-alpine .ag-row-odd {{
    background-color: #F8FAFC !important;
}}
.ag-theme-alpine .ag-row:hover {{
    background-color: #EFF6FF !important;
}}
.ag-theme-alpine .ag-row-selected,
.ag-theme-alpine .ag-row-selected.ag-row-odd,
.ag-theme-alpine .ag-row-selected.ag-row-even {{
    background-color: #DBEAFE !important;
}}

/* Cells */
.ag-theme-alpine .ag-cell {{
    color: #1E293B !important;
    border-right: 1px solid #E2E8F0 !important;
}}
.ag-theme-alpine .ag-cell-range-selected {{
    background-color: rgba(37,99,235,0.10) !important;
}}

/* Pinned left columns */
.ag-theme-alpine .ag-pinned-left-cols-container .ag-cell {{
    background-color: #F8FAFC !important;
    border-right: 2px solid #CBD5E1 !important;
    font-weight: 600 !important;
    color: #0F172A !important;
}}
.ag-theme-alpine .ag-pinned-left-cols-container .ag-row-odd .ag-cell {{
    background-color: #F1F5F9 !important;
}}

/* Filter inputs / floating filters */
.ag-theme-alpine .ag-filter-toolpanel-search-input input,
.ag-theme-alpine .ag-floating-filter-input input,
.ag-theme-alpine input.ag-input-field-input {{
    background-color: #FFFFFF !important;
    color: #0F172A !important;
    border-color: #CBD5E1 !important;
    border-radius: 6px !important;
}}

/* Column menu popup */
.ag-theme-alpine .ag-menu {{
    background-color: #FFFFFF !important;
    border: 1px solid #D8E0EA !important;
    border-radius: 10px !important;
    box-shadow: 0 8px 24px rgba(15,23,42,0.12) !important;
}}
.ag-theme-alpine .ag-menu-option:hover {{
    background-color: #EFF6FF !important;
}}
.ag-theme-alpine .ag-menu-option-text {{
    color: #1E293B !important;
}}

/* Tooltip */
.ag-theme-alpine .ag-tooltip {{
    background-color: #F8FAFC !important;
    color: #1E293B !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: 8px !important;
    padding: 6px 10px !important;
}}

/* Scrollbar inside AgGrid */
.ag-theme-alpine .ag-body-horizontal-scroll-viewport::-webkit-scrollbar,
.ag-theme-alpine .ag-body-viewport::-webkit-scrollbar {{ width: 8px; height: 8px; }}
.ag-theme-alpine .ag-body-horizontal-scroll-viewport::-webkit-scrollbar-track,
.ag-theme-alpine .ag-body-viewport::-webkit-scrollbar-track {{ background: #F1F5F9; }}
.ag-theme-alpine .ag-body-horizontal-scroll-viewport::-webkit-scrollbar-thumb,
.ag-theme-alpine .ag-body-viewport::-webkit-scrollbar-thumb {{
    background: #CBD5E1; border-radius: 999px;
}}

/* ══════════════════════════════════════════════════════════════
   GDG CANVAS (st.dataframe / st.data_editor) — light mode
   These rules control the CONTAINER frame and empty-scroll areas.
   Per-cell colors come from pandas Styler via light_df() helper.
   GDG renders cell content on canvas (JS) — CSS cannot override
   individual cell colors, only the container/scrollbar chrome.
   ══════════════════════════════════════════════════════════════ */

/* ── st.dataframe container ─────────────────────────────── */
[data-testid="stDataFrame"] {{
    border: 1px solid #D8E0EA !important;
    border-radius: 14px !important;
    overflow: hidden !important;
    background-color: #FFFFFF !important;
}}
[data-testid="stDataFrame"] > div {{
    background-color: #FFFFFF !important;
    border-radius: 14px !important;
}}

/* ── st.data_editor container (simulacion.py) ───────────── */
[data-testid="stDataEditor"] {{
    border: 1px solid #D8E0EA !important;
    border-radius: 14px !important;
    overflow: hidden !important;
    background-color: #FFFFFF !important;
}}
[data-testid="stDataEditor"] > div {{
    background-color: #FFFFFF !important;
    border-radius: 14px !important;
}}

/* GDG canvas scroller — empty-area background */
.dvn-scroller {{
    background-color: #FFFFFF !important;
}}
[data-testid="stDataFrame"] canvas,
[data-testid="stDataEditor"] canvas {{
    background-color: #FFFFFF !important;
}}

/* ══════════════════════════════════════════════════════════════
   HTML <table> — st.table(), Styler HTML export, st.markdown
   These targets CSS-styled HTML tables (not GDG canvas).
   Covers: stMarkdownContainer, element-container, stTable.
   ══════════════════════════════════════════════════════════════ */
[data-testid="stTable"] table,
[data-testid="stTable"] {{
    border: 1px solid #D8E0EA !important;
    border-radius: 14px !important;
    overflow: hidden !important;
    background-color: #FFFFFF !important;
    color: #1E293B !important;
}}
.stDataFrame table,
[data-testid="stDataFrame"] table,
[data-testid="stMarkdownContainer"] table,
[data-testid="stTable"] table,
.element-container table {{
    background: #FFFFFF !important;
    color: #1E293B !important;
    border: 1px solid #D8E0EA !important;
    border-radius: 12px !important;
    overflow: hidden !important;
    width: 100% !important;
    border-collapse: separate !important;
    border-spacing: 0 !important;
}}
/* Table headers */
.stDataFrame thead, .stDataFrame th,
[data-testid="stDataFrame"] thead,
[data-testid="stDataFrame"] th,
[data-testid="stMarkdownContainer"] thead,
[data-testid="stMarkdownContainer"] th,
[data-testid="stTable"] thead,
[data-testid="stTable"] th,
.element-container thead,
.element-container th {{
    background-color: #EAF1FB !important;
    color: #0F172A !important;
    font-weight: 800 !important;
    border-bottom: 2px solid #CBD5E1 !important;
    padding: 0.55rem 0.75rem !important;
    white-space: nowrap !important;
}}
/* Table data cells */
.stDataFrame td,
[data-testid="stDataFrame"] td,
[data-testid="stMarkdownContainer"] td,
[data-testid="stTable"] td,
.element-container td {{
    background-color: #FFFFFF !important;
    color: #1E293B !important;
    border-bottom: 1px solid #E2E8F0 !important;
    font-weight: 500 !important;
    padding: 0.45rem 0.75rem !important;
}}
/* Alternating rows */
.stDataFrame tr:nth-child(even) td,
[data-testid="stDataFrame"] tr:nth-child(even) td,
[data-testid="stMarkdownContainer"] tr:nth-child(even) td,
[data-testid="stTable"] tr:nth-child(even) td {{
    background-color: #F8FAFC !important;
}}
/* Hover */
.stDataFrame tr:hover td,
[data-testid="stDataFrame"] tr:hover td,
[data-testid="stMarkdownContainer"] tr:hover td,
[data-testid="stTable"] tr:hover td {{
    background-color: #EFF6FF !important;
}}

/* ── LABELS ──────────────────────────────────────────────── */
label {{
    color: #0F172A !important;
    font-weight: 700 !important;
    font-size: 0.92rem !important;
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
[data-testid="stHeadingContainer"] {{
    color: {T["TEXT_PRIMARY"]} !important;
    font-weight: 800 !important;
}}
hr, [data-testid="stDivider"] {{ border-color: {T["BORDER_SOFT"]} !important; }}

/* Expander — glass panel */
[data-testid="stExpander"] {{
    background: rgba(255,255,255,0.72) !important;
    backdrop-filter: blur(16px) saturate(140%) !important;
    -webkit-backdrop-filter: blur(16px) saturate(140%) !important;
    border: 1px solid rgba(203,213,225,0.72) !important;
    border-radius: 18px !important;
    box-shadow:
        0 12px 32px rgba(15,23,42,0.08),
        inset 0 1px 0 rgba(255,255,255,0.65) !important;
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
    background: rgba(255,255,255,0.68) !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: 14px !important;
}}
[data-testid="stFileUploadDropzone"] * {{
    color: #0F172A !important;
    opacity: 1 !important;
}}
[data-testid="stNumberInput"] [data-baseweb="input"] {{
    background-color: {T["INPUT_BG"]} !important;
}}
[data-testid="stRadio"] label,
[data-testid="stCheckbox"] label {{ color: {T["TEXT_SECONDARY"]} !important; }}

/* ── Sidebar navigation radio — light mode ──────────────────
   Uses section[data-testid] for highest specificity. Forces
   opacity:1 on * to defeat any BaseWeb opacity reduction.     */

/* Container — kill any inherited opacity */
section[data-testid="stSidebar"] [data-testid="stRadio"] {{
    opacity: 1 !important;
    background: transparent !important;
    padding: 0 !important;
}}
section[data-testid="stSidebar"] [data-testid="stRadio"] * {{
    opacity: 1 !important;
}}

/* Widget label "NAVEGACION" — subtle uppercase heading */
section[data-testid="stSidebar"] [data-testid="stRadio"] [data-testid="stWidgetLabel"] p,
section[data-testid="stSidebar"] [data-testid="stRadio"] [data-testid="stWidgetLabel"] label,
section[data-testid="stSidebar"] [data-testid="stRadio"] [data-testid="stWidgetLabel"] span {{
    color: #475569 !important;
    font-weight: 700 !important;
    font-size: 0.7rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    opacity: 1 !important;
}}

/* Each nav option */
section[data-testid="stSidebar"] [data-testid="stRadio"] label {{
    padding: 10px 14px !important;
    border-radius: 12px !important;
    display: flex !important;
    align-items: center !important;
    width: 100% !important;
    box-sizing: border-box !important;
    cursor: pointer !important;
    margin: 2px 0 !important;
    background: transparent !important;
    color: #334155 !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    line-height: 1.4 !important;
    border-left: 3px solid transparent !important;
    opacity: 1 !important;
}}

/* Explicit color on all text children — not just inherit */
section[data-testid="stSidebar"] [data-testid="stRadio"] label p,
section[data-testid="stSidebar"] [data-testid="stRadio"] label span {{
    color: #334155 !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    opacity: 1 !important;
    margin: 0 !important;
    padding: 0 !important;
    line-height: 1.4 !important;
}}

/* Hover */
section[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {{
    background: rgba(255,255,255,0.72) !important;
    color: #0F172A !important;
}}
section[data-testid="stSidebar"] [data-testid="stRadio"] label:hover p,
section[data-testid="stSidebar"] [data-testid="stRadio"] label:hover span {{
    color: #0F172A !important;
}}

/* Selected */
section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {{
    background: #DBEAFE !important;
    color: #0F172A !important;
    font-weight: 800 !important;
    border-left: 3px solid #2563EB !important;
    box-shadow: 0 6px 16px rgba(37,99,235,0.12) !important;
}}
section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) p,
section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) span {{
    color: #0F172A !important;
    font-weight: 800 !important;
}}

/* Expander radios (not nav): restore normal style in light mode */
section[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stRadio"] label {{
    color: {T["TEXT_SECONDARY"]} !important;
    font-weight: 500 !important;
    background: transparent !important;
    border-left: none !important;
    box-shadow: none !important;
    padding: 6px 10px !important;
}}
section[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stRadio"] label p,
section[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stRadio"] label span {{
    color: {T["TEXT_SECONDARY"]} !important;
    font-weight: 500 !important;
    opacity: 1 !important;
}}
section[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stRadio"] label:has(input:checked) {{
    background: {T["PRIMARY_SOFT"]} !important;
    color: {T["PRIMARY"]} !important;
    border-left: none !important;
    box-shadow: none !important;
}}
section[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stRadio"] label:has(input:checked) p,
section[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stRadio"] label:has(input:checked) span {{
    color: {T["PRIMARY"]} !important;
}}
section[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stRadio"] label > div:first-child {{
    display: flex !important;
}}

/* ── st.metric — glass card ──────────────────────────────── */
[data-testid="stMetric"] {{
    background: rgba(255,255,255,0.82) !important;
    backdrop-filter: blur(12px) saturate(130%) !important;
    -webkit-backdrop-filter: blur(12px) saturate(130%) !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 16px !important;
    box-shadow: 0 10px 28px rgba(15,23,42,0.07) !important;
    padding: 1rem 1.1rem !important;
}}
[data-testid="stMetricLabel"] p {{
    color: #64748B !important;
    font-weight: 700 !important;
    font-size: 0.75rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}}
[data-testid="stMetricValue"] {{
    color: #0F172A !important;
    font-weight: 800 !important;
}}

/* ── KPI cards — glass panel ─────────────────────────────── */
.kpi-card {{
    background: rgba(255,255,255,0.72) !important;
    backdrop-filter: blur(16px) saturate(140%) !important;
    -webkit-backdrop-filter: blur(16px) saturate(140%) !important;
    border: 1px solid rgba(203,213,225,0.72) !important;
    border-radius: 18px !important;
    box-shadow:
        0 12px 32px rgba(15,23,42,0.08),
        inset 0 1px 0 rgba(255,255,255,0.65) !important;
    padding: 1.1rem 1.25rem !important;
}}

/* ── Premium header — glass ──────────────────────────────── */
.premium-header {{
    background: rgba(255,255,255,0.72) !important;
    backdrop-filter: blur(18px) saturate(140%) !important;
    -webkit-backdrop-filter: blur(18px) saturate(140%) !important;
    border: 1px solid rgba(203,213,225,0.72) !important;
    box-shadow:
        0 12px 32px rgba(15,23,42,0.08),
        inset 0 1px 0 rgba(255,255,255,0.65) !important;
}}

/* ── Plotly chart container — glass panel ────────────────── */
[data-testid="stPlotlyChart"] {{
    background: rgba(255,255,255,0.72) !important;
    backdrop-filter: blur(16px) saturate(140%) !important;
    -webkit-backdrop-filter: blur(16px) saturate(140%) !important;
    border: 1px solid rgba(203,213,225,0.72) !important;
    border-radius: 18px !important;
    box-shadow:
        0 12px 32px rgba(15,23,42,0.08),
        inset 0 1px 0 rgba(255,255,255,0.65) !important;
}}
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

/* ── Sidebar navigation (st.radio styled as nav menu) ────────
   Dark-mode base. Light-mode overrides are in _native below.
   Uses section[data-testid] prefix for maximum specificity and
   forces opacity:1 on all children to defeat BaseWeb defaults. */
section[data-testid="stSidebar"] [data-testid="stRadio"],
section[data-testid="stSidebar"] [data-testid="stRadio"] > div {{
    background: transparent !important;
    background-color: transparent !important;
    padding: 0 !important;
    margin: 0 !important;
    gap: 0 !important;
    opacity: 1 !important;
}}
section[data-testid="stSidebar"] [data-testid="stRadio"] * {{
    opacity: 1 !important;
}}
section[data-testid="stSidebar"] [data-testid="stRadio"] label {{
    padding: 10px 14px !important;
    border-radius: 12px !important;
    display: flex !important;
    align-items: center !important;
    width: 100% !important;
    box-sizing: border-box !important;
    cursor: pointer !important;
    margin: 2px 0 !important;
    background: transparent !important;
    color: #CBD5E1 !important;
    font-weight: 500 !important;
    font-size: 13px !important;
    line-height: 1.4 !important;
    transition: background 0.15s ease, color 0.15s ease !important;
    border-left: 3px solid transparent !important;
    opacity: 1 !important;
}}
section[data-testid="stSidebar"] [data-testid="stRadio"] label p,
section[data-testid="stSidebar"] [data-testid="stRadio"] label span {{
    color: #CBD5E1 !important;
    font-weight: 500 !important;
    font-size: 13px !important;
    margin: 0 !important;
    padding: 0 !important;
    line-height: 1.4 !important;
    opacity: 1 !important;
}}
section[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {{
    background: rgba(255,255,255,0.07) !important;
    color: #F1F5F9 !important;
}}
section[data-testid="stSidebar"] [data-testid="stRadio"] label:hover p,
section[data-testid="stSidebar"] [data-testid="stRadio"] label:hover span {{
    color: #F1F5F9 !important;
}}
section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {{
    background: rgba(37,99,235,0.18) !important;
    color: #DBEAFE !important;
    font-weight: 700 !important;
    border-left: 3px solid #2563EB !important;
}}
section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) p,
section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) span {{
    color: #DBEAFE !important;
    font-weight: 700 !important;
}}
/* Hide the BaseWeb radio circle in sidebar nav */
section[data-testid="stSidebar"] [data-testid="stRadio"] label > div:first-child {{
    display: none !important;
}}
/* Restore radio circle + normal style inside expanders (not nav) */
section[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stRadio"] label {{
    padding: 6px 10px !important;
    border-radius: 8px !important;
    margin: 3px 0 !important;
    font-size: 13px !important;
    font-weight: 400 !important;
    color: var(--text-secondary) !important;
    border-left: none !important;
    background: transparent !important;
}}
section[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stRadio"] label p,
section[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stRadio"] label span {{
    color: var(--text-secondary) !important;
    font-weight: 400 !important;
}}
section[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stRadio"] label > div:first-child {{
    display: flex !important;
}}
section[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stRadio"] label:has(input:checked) {{
    background: rgba(37,99,235,0.15) !important;
    color: #93C5FD !important;
    border-left: none !important;
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
