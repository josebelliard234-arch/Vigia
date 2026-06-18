# ============================================================
# DESIGN SYSTEM - DARK PROFESSIONAL
# ============================================================
import plotly.io as pio

BG_MAIN       = "#0F172A"
BG_SECONDARY  = "#111827"
CARD_BG       = "#1E293B"
CARD_ELEVATED = "#273449"
TEXT_MAIN      = "#F1F5F9"
TEXT_SECONDARY = "#CBD5E1"
TEXT_MUTED     = "#94A3B8"

# Paleta corporativa — contraste WCAG-AA sobre blanco y visible en oscuro
BLUE   = "#2563EB"   # Azul royal
GREEN  = "#16A34A"   # Verde bosque
RED    = "#DC2626"   # Rojo carmesí
YELLOW = "#D97706"   # Ámbar profundo
GRAY   = "#4B5563"   # Gris pizarra

pio.templates.default = "plotly_dark"


def get_mode() -> str:
    """Returns 'dark' or 'light' based on session state."""
    try:
        import streamlit as st
        return st.session_state.get("theme_mode", "dark")
    except Exception:
        return "dark"
