# ============================================================
# DESIGN SYSTEM — Centralized Theme Token Registry
# ============================================================
import plotly.io as pio

# ── Accent colors — same in both modes (WCAG-AA on white & dark) ──
BLUE   = "#2563EB"
GREEN  = "#16A34A"
RED    = "#DC2626"
YELLOW = "#D97706"
GRAY   = "#4B5563"

# ── Legacy dark-mode constants (kept for backward compatibility) ──
BG_MAIN       = "#0F172A"
BG_SECONDARY  = "#111827"
CARD_BG       = "#1E293B"
CARD_ELEVATED = "#273449"
TEXT_MAIN      = "#F1F5F9"
TEXT_SECONDARY = "#CBD5E1"
TEXT_MUTED     = "#94A3B8"

pio.templates.default = "plotly_dark"


# ════════════════════════════════════════════════════════════
#  LIGHT MODE TOKENS
# ════════════════════════════════════════════════════════════
_LIGHT_TOKENS: dict = {
    # ── Backgrounds ────────────────────────────────────────
    "MAIN_BG":           "#F6F8FC",
    "SIDEBAR_BG":        "#EAF1FB",
    "SIDEBAR_BG_2":      "#F3F7FD",
    "CARD_BG":           "rgba(255,255,255,0.86)",
    "CARD_BG_SOLID":     "#FFFFFF",
    "GLASS_BG":          "rgba(241,245,249,0.85)",

    # ── Typography ─────────────────────────────────────────
    "TEXT_PRIMARY":      "#0F172A",
    "TEXT_SECONDARY":    "#334155",
    "TEXT_MUTED":        "#64748B",
    "TEXT_FAINT":        "#94A3B8",
    "FW_BODY":           "500",

    # ── Borders ────────────────────────────────────────────
    "BORDER":            "#CBD5E1",
    "BORDER_SOFT":       "#E2E8F0",
    "BORDER_STRONG":     "rgba(15,23,42,0.26)",

    # ── Inputs ─────────────────────────────────────────────
    "INPUT_BG":          "#FFFFFF",
    "INPUT_BORDER":      "#CBD5E1",
    "INPUT_FOCUS":       "#2563EB",

    # ── Actions / Brand ────────────────────────────────────
    "PRIMARY":           "#2563EB",
    "PRIMARY_HOVER":     "#1D4ED8",
    "PRIMARY_SOFT":      "#DBEAFE",
    "SUCCESS":           "#16A34A",
    "DANGER":            "#DC2626",
    "WARNING":           "#D97706",

    # ── Tables ─────────────────────────────────────────────
    "TABLE_BG":          "#FFFFFF",
    "TABLE_HEADER_BG":   "#EAF1FB",
    "TABLE_ROW_BG":      "#FFFFFF",
    "TABLE_ROW_ALT_BG":  "#F8FAFC",
    "TABLE_BORDER":      "#D8E0EA",

    # ── Misc (header, scrollbar, shadow) ───────────────────
    "HDR_BG":            "rgba(248,250,252,0.96)",
    "SHADOW":            "rgba(15,23,42,0.08)",
    "SCROLL_TRACK":      "#F1F5F9",
    "SCROLL_THUMB":      "#CBD5E1",

    # ── Plotly / Chart ─────────────────────────────────────
    "CHART_BG":          "#FFFFFF",
    "CHART_PAPER_BG":    "rgba(255,255,255,0)",
    "CHART_TEXT":        "#0F172A",
    "CHART_MUTED":       "#334155",
    "CHART_GRID":        "#E2E8F0",
    "CHART_ZEROLINE":    "#94A3B8",
    "CHART_HOVER_BG":    "#F1F5F9",
    "PLOT_RGB":          "255,255,255",

    # ── AG Grid cell styles ────────────────────────────────
    "GRID_HIGH_BG":      "#FEE2E2",
    "GRID_HIGH_FG":      "#991B1B",
    "GRID_LOW_BG":       "#DCFCE7",
    "GRID_LOW_FG":       "#166534",
    "GRID_DELTA_POS":    "#DC2626",
    "GRID_DELTA_NEG":    "#16A34A",
    "GRID_DELTA_NEU":    "#64748B",
    "GRID_DELTA_FAINT":  "#94A3B8",
    "GRID_OT_HIGH":      "#991B1B",
    "GRID_OT_LOW":       "#166534",
}

# ════════════════════════════════════════════════════════════
#  DARK MODE TOKENS
# ════════════════════════════════════════════════════════════
_DARK_TOKENS: dict = {
    # ── Backgrounds ────────────────────────────────────────
    "MAIN_BG":           "#0F172A",
    "SIDEBAR_BG":        "#111827",
    "SIDEBAR_BG_2":      "#0F172A",
    "CARD_BG":           "rgba(15,23,42,0.75)",
    "CARD_BG_SOLID":     "#1E293B",
    "GLASS_BG":          "rgba(30,41,59,0.55)",

    # ── Typography ─────────────────────────────────────────
    "TEXT_PRIMARY":      "#F1F5F9",
    "TEXT_SECONDARY":    "#CBD5E1",
    "TEXT_MUTED":        "#94A3B8",
    "TEXT_FAINT":        "#64748B",
    "FW_BODY":           "400",

    # ── Borders ────────────────────────────────────────────
    "BORDER":            "rgba(148,163,184,0.20)",
    "BORDER_SOFT":       "rgba(148,163,184,0.13)",
    "BORDER_STRONG":     "rgba(148,163,184,0.28)",

    # ── Inputs ─────────────────────────────────────────────
    "INPUT_BG":          "#1E293B",
    "INPUT_BORDER":      "rgba(148,163,184,0.25)",
    "INPUT_FOCUS":       "#2563EB",

    # ── Actions / Brand ────────────────────────────────────
    "PRIMARY":           "#2563EB",
    "PRIMARY_HOVER":     "#1D4ED8",
    "PRIMARY_SOFT":      "rgba(37,99,235,0.15)",
    "SUCCESS":           "#16A34A",
    "DANGER":            "#DC2626",
    "WARNING":           "#D97706",

    # ── Tables ─────────────────────────────────────────────
    "TABLE_BG":          "#1E293B",
    "TABLE_HEADER_BG":   "rgba(15,23,42,0.95)",
    "TABLE_ROW_BG":      "#1E293B",
    "TABLE_ROW_ALT_BG":  "rgba(30,41,59,0.60)",
    "TABLE_BORDER":      "rgba(148,163,184,0.15)",

    # ── Misc ───────────────────────────────────────────────
    "HDR_BG":            "rgba(15,23,42,0.88)",
    "SHADOW":            "rgba(0,0,0,0.25)",
    "SCROLL_TRACK":      "#111827",
    "SCROLL_THUMB":      "#4B5563",

    # ── Plotly / Chart ─────────────────────────────────────
    "CHART_BG":          "#1E293B",
    "CHART_PAPER_BG":    "#1E293B",
    "CHART_TEXT":        "#CBD5E1",
    "CHART_MUTED":       "#94A3B8",
    "CHART_GRID":        "rgba(148,163,184,0.14)",
    "CHART_ZEROLINE":    "rgba(248,250,252,0.35)",
    "CHART_HOVER_BG":    "#273449",
    "PLOT_RGB":          "15,23,42",

    # ── AG Grid cell styles ────────────────────────────────
    "GRID_HIGH_BG":      "#450a0a",
    "GRID_HIGH_FG":      "#fca5a5",
    "GRID_LOW_BG":       "#172554",
    "GRID_LOW_FG":       "#93c5fd",
    "GRID_DELTA_POS":    "#f87171",
    "GRID_DELTA_NEG":    "#4ade80",
    "GRID_DELTA_NEU":    "#64748b",
    "GRID_DELTA_FAINT":  "#94a3b8",
    "GRID_OT_HIGH":      "#f87171",
    "GRID_OT_LOW":       "#93c5fd",
}


def get_theme_tokens(mode: str = "dark") -> dict:
    """Return the full token set for the given mode ('light' or 'dark').

    Accent colors (BLUE, GREEN, RED, YELLOW, GRAY) are the same in both modes
    and are not included — import them directly from this module.
    """
    return _LIGHT_TOKENS if mode == "light" else _DARK_TOKENS


def get_mode() -> str:
    """Return 'dark' or 'light' based on current session state."""
    try:
        import streamlit as st
        return st.session_state.get("theme_mode", "dark")
    except Exception:
        return "dark"


def light_df(df):
    """Apply light-mode cell styling for st.dataframe when in light mode.

    Accepts a pd.DataFrame or an existing pd.Styler (e.g. df.style.format(...)).
    In dark mode returns df unchanged so no alternation is wasted.
    GDG reads per-cell background-color from the Styler and renders it on canvas.
    """
    import pandas as pd
    if get_mode() != "light":
        return df

    if type(df).__name__ == "Styler":
        styler = df
    elif isinstance(df, pd.DataFrame):
        styler = df.style
    else:
        return df

    counter = [0]

    def _row(row):
        bg = "#FFFFFF" if counter[0] % 2 == 0 else "#F8FAFC"
        counter[0] += 1
        return [f"background-color: {bg}; color: #1E293B; font-weight: 500;"] * len(row)

    return styler.apply(_row, axis=1)
