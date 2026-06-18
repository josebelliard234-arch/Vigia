from styles.theme import CARD_BG, CARD_ELEVATED, TEXT_MAIN, TEXT_SECONDARY, TEXT_MUTED


def _is_light() -> bool:
    try:
        import streamlit as st
        return st.session_state.get("theme_mode", "dark") == "light"
    except Exception:
        return False


def apply_dark_layout(fig, title=None, height=None):
    light = _is_light()

    if light:
        bg       = "#FFFFFF"
        paper_bg = "#F8FAFC"
        text_col = "#1E293B"
        muted    = "#64748B"
        grid_c   = "rgba(15,23,42,0.08)"
        zero_c   = "rgba(15,23,42,0.20)"
        hover_bg = "#F1F5F9"
        tpl      = "plotly_white"
    else:
        bg       = CARD_BG
        paper_bg = CARD_BG
        text_col = TEXT_SECONDARY
        muted    = TEXT_MUTED
        grid_c   = "rgba(148,163,184,0.14)"
        zero_c   = "rgba(248,250,252,0.35)"
        hover_bg = CARD_ELEVATED
        tpl      = "plotly_dark"

    if title:
        title_color = "#0F172A" if light else TEXT_MAIN
        fig.update_layout(
            title=dict(text=title, font=dict(size=16, color=title_color, family="Inter"), x=0)
        )

    fig.update_layout(
        template=tpl,
        plot_bgcolor=bg,
        paper_bgcolor=paper_bg,
        font=dict(color=text_col, family="Inter"),
        hoverlabel=dict(bgcolor=hover_bg, font_size=12, font_family="Inter"),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=text_col)),
        margin=dict(l=20, r=30, t=65, b=50),
    )
    fig.update_xaxes(gridcolor=grid_c, zerolinecolor=zero_c, color=muted)
    fig.update_yaxes(gridcolor=grid_c, zerolinecolor=zero_c, color=muted)
    if height:
        fig.update_layout(height=height)
    return fig


def plot_bg(opacity: float = 1.0) -> str:
    """Returns current-theme plot background color at the given opacity."""
    if _is_light():
        return f"rgba(255,255,255,{opacity})"
    return f"rgba(15,23,42,{opacity})"
