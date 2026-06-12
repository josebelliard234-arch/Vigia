from styles.theme import CARD_BG, CARD_ELEVATED, TEXT_MAIN, TEXT_SECONDARY


def apply_dark_layout(fig, title=None, height=None):
    if title:
        fig.update_layout(title=dict(text=title, font=dict(size=16, color=TEXT_MAIN, family="Inter"), x=0))
    fig.update_layout(
        template="plotly_dark",
        plot_bgcolor=CARD_BG,
        paper_bgcolor=CARD_BG,
        font=dict(color=TEXT_SECONDARY, family="Inter"),
        hoverlabel=dict(bgcolor=CARD_ELEVATED, font_size=12, font_family="Inter"),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT_SECONDARY)),
        margin=dict(l=20, r=30, t=65, b=50),
    )
    fig.update_xaxes(gridcolor="rgba(148,163,184,0.14)", zerolinecolor="rgba(248,250,252,0.35)", color=TEXT_SECONDARY)
    fig.update_yaxes(gridcolor="rgba(148,163,184,0.14)", zerolinecolor="rgba(248,250,252,0.35)", color=TEXT_SECONDARY)
    if height:
        fig.update_layout(height=height)
    return fig
