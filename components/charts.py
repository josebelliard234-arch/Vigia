from styles.theme import get_theme_tokens, get_mode, TEXT_MAIN, TEXT_SECONDARY

# Known legacy dark-mode text colors — these appear in trace-level textfont/font
# dicts in tab chart code that hasn't been updated to use tokens. In light mode
# they would render as near-invisible white text. apply_dark_layout replaces them.
_LEGACY_DARK_TEXT = frozenset({"#F1F5F9", "#CBD5E1", "#94A3B8", TEXT_MAIN, TEXT_SECONDARY})


def _is_light() -> bool:
    return get_mode() == "light"


def apply_dark_layout(fig, title=None, height=None):
    """Apply theme-aware layout to a Plotly figure using centralized tokens.

    Also walks all traces and replaces legacy dark-mode text colors in
    textfont/font dicts so charts stay readable when light mode is active.
    """
    mode = get_mode()
    T = get_theme_tokens(mode)

    if title:
        fig.update_layout(
            title=dict(
                text=title,
                font=dict(size=16, color=T["CHART_TEXT"], family="Inter"),
                x=0,
            )
        )

    fig.update_layout(
        template="plotly_white" if mode == "light" else "plotly_dark",
        plot_bgcolor=T["CHART_BG"],
        paper_bgcolor=T["CHART_PAPER_BG"],
        font=dict(color=T["CHART_TEXT"], family="Inter"),
        hoverlabel=dict(bgcolor=T["CHART_HOVER_BG"], font_size=12, font_family="Inter"),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=T["CHART_TEXT"])),
    )
    fig.update_xaxes(
        gridcolor=T["CHART_GRID"],
        zerolinecolor=T["CHART_ZEROLINE"],
        color=T["CHART_MUTED"],
    )
    fig.update_yaxes(
        gridcolor=T["CHART_GRID"],
        zerolinecolor=T["CHART_ZEROLINE"],
        color=T["CHART_MUTED"],
    )

    # Patch trace-level textfont/font that still use legacy dark constants.
    # Accent colors (RED, BLUE, YELLOW, etc.) are intentional and left untouched.
    for trace in fig.data:
        for attr in ("textfont", "font"):
            try:
                tf = getattr(trace, attr, None)
                if tf and getattr(tf, "color", None) in _LEGACY_DARK_TEXT:
                    tf.color = T["CHART_TEXT"]
            except Exception:
                pass

    if height:
        fig.update_layout(height=height)
    return fig


def plot_bg(opacity: float = 1.0) -> str:
    """Return current-theme plot background rgba string at the given opacity."""
    T = get_theme_tokens(get_mode())
    return f"rgba({T['PLOT_RGB']},{opacity})"
