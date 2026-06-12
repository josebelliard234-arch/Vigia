import re
import pandas as pd


def clean_text(s):
    """Limpia un texto para mostrar: quita espacios sobrantes pero conserva mayusculas/acentos."""
    if pd.isna(s):
        return ""
    return re.sub(r"\s+", " ", str(s)).strip()


def norm_key(s):
    """Clave normalizada SOLO para comparar/cruzar (mayusculas + sin espacios extra)."""
    if pd.isna(s):
        return ""
    return re.sub(r"\s+", " ", str(s)).strip().upper()


def fmt_rdp(x):
    return f"RD$ {x:,.2f}"


def fmt_pct(v):
    if v > 0:   return f"+{v:.1f}%"
    elif v < 0: return f"{v:.1f}%"
    return "0.0%"


def nivel_alerta(v, u1=35, u2=60, u3=100):
    v = abs(v)
    if v > u3:   return "CRITICO"
    elif v > u2: return "ALTO"
    elif v > u1: return "MEDIO"
    return "OK"
