import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from utils.dates import fmt_sem
from utils.formatting import fmt_rdp
from utils.transformations import normalizar_categoria
from components.charts import apply_dark_layout
from styles.theme import TEXT_MAIN, TEXT_SECONDARY, TEXT_MUTED, RED, GREEN, YELLOW, BLUE
from styles.theme import get_theme_tokens, get_mode as _get_mode


# ── Helpers visuales ──────────────────────────────────────────
def _card_cat(nombre, pct, n_prods, n_sub, n_baj, size="normal"):
    color = RED if pct > 0.5 else (GREEN if pct < -0.5 else "#94A3B8")
    sign  = "+" if pct > 0 else ""
    icon  = "▲" if pct > 0.5 else ("▼" if pct < -0.5 else "—")
    val_fs = "1.7rem" if size == "normal" else "1.35rem"
    return (
        f'<div style="padding:.9rem 1rem;border-radius:13px;'
        f'background:linear-gradient(135deg,{color}18 0%,{color}08 100%);'
        f'border:1px solid {color}44;border-top:3px solid {color};height:100%;">'
        f'<div style="font-size:.68rem;color:{color}cc;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:.07em;margin-bottom:.25rem;">{nombre}</div>'
        f'<div style="font-size:{val_fs};font-weight:800;color:{color};line-height:1;">'
        f'{icon} {sign}{pct:.1f}%</div>'
        f'<div style="font-size:.7rem;color:var(--t3);margin-top:.3rem;">'
        f'{n_prods} productos&nbsp;&nbsp;'
        f'<span style="color:{RED};">▲{n_sub}</span>&nbsp;'
        f'<span style="color:{GREEN};">▼{n_baj}</span>'
        f'</div>'
        f'</div>'
    )


def _kpi_mini(label, value, color="#94A3B8", badge=""):
    return (
        f'<div style="padding:.7rem .9rem;border-radius:11px;'
        f'background:var(--bg-card);border:1px solid {color}33;'
        f'border-left:3px solid {color};">'
        f'<div style="font-size:.67rem;color:{color}99;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:.06em;">{label}</div>'
        f'<div style="font-size:1.25rem;font-weight:800;color:{color};margin-top:.15rem;">'
        f'{value}{badge}</div>'
        f'</div>'
    )


def _fuente_badge(fuente):
    if fuente == "bruto":
        return (
            f'<span style="margin-left:.4rem;background:rgba(245,158,11,0.18);color:{YELLOW};'
            f'font-size:.62rem;font-weight:700;padding:.03rem .3rem;border-radius:5px;'
            f'border:1px solid rgba(245,158,11,0.35);vertical-align:middle;">BRUTO</span>'
        )
    if fuente == "validado":
        return (
            f'<span style="margin-left:.4rem;background:rgba(34,197,94,0.15);color:{GREEN};'
            f'font-size:.62rem;font-weight:700;padding:.03rem .3rem;border-radius:5px;'
            f'border:1px solid rgba(34,197,94,0.3);vertical-align:middle;">VALIDADO</span>'
        )
    return ""


# ── Calculo de deltas por categoría ──────────────────────────
def _calc_categoria_delta(df_all, semana_act, semana_ref):
    """
    Para cada categoría calcula el cambio % promedio entre dos semanas.
    Devuelve (agg_df, productos_df) donde productos_df tiene detalle por producto.
    """
    df_a = df_all[df_all["semana"] == semana_act]
    df_r = df_all[df_all["semana"] == semana_ref]
    if df_a.empty or df_r.empty:
        return pd.DataFrame(), pd.DataFrame()

    grp_a = (df_a.groupby(["id_producto", "presentacion", "categoria", "producto"])["precio"]
             .mean().reset_index())
    grp_r = (df_r.groupby(["id_producto", "presentacion"])["precio"]
             .mean().reset_index().rename(columns={"precio": "precio_ref"}))

    m = grp_a.merge(grp_r, on=["id_producto", "presentacion"], how="inner")
    m = m[m["precio_ref"] > 0].copy()
    if m.empty:
        return pd.DataFrame(), pd.DataFrame()

    m["pct"]      = (m["precio"] - m["precio_ref"]) / m["precio_ref"] * 100
    m["cat_norm"] = m["categoria"].apply(normalizar_categoria)
    m = m[~m["cat_norm"].isin(["Sin categoria", "nan", ""])]

    agg = m.groupby("cat_norm").agg(
        pct_cambio  =("pct", "mean"),
        n_productos =("id_producto", "nunique"),
        n_subio     =("pct", lambda x: int((x > 0.5).sum())),
        n_bajo      =("pct", lambda x: int((x < -0.5).sum())),
    ).reset_index()
    agg["n_estable"] = agg["n_productos"] - agg["n_subio"] - agg["n_bajo"]
    return agg.sort_values("pct_cambio", ascending=False).reset_index(drop=True), m


# ── Tarjeta desplegable con detalle de productos ──────────────
def _render_card_expandible(r, m_productos, tipo="subio"):
    color = RED if tipo == "subio" else GREEN
    sign  = "+" if r["pct_cambio"] > 0 else ""
    icon  = "▲" if r["pct_cambio"] > 0.5 else ("▼" if r["pct_cambio"] < -0.5 else "—")

    df_cat = m_productos[m_productos["cat_norm"] == r["cat_norm"]].copy()
    if tipo == "subio":
        df_det = df_cat[df_cat["pct"] > 0.5].sort_values("pct", ascending=False)
    else:
        df_det = df_cat[df_cat["pct"] < -0.5].sort_values("pct", ascending=True)

    rows_html = ""
    for _, p in df_det.iterrows():
        s  = "+" if p["pct"] > 0 else ""
        ic = "▲" if p["pct"] > 0 else "▼"
        c  = RED if p["pct"] > 0 else GREEN
        rows_html += (
            f'<div class="vc-row" style="display:flex;justify-content:space-between;'
            f'align-items:center;padding:.32rem .6rem;border-radius:8px;margin-bottom:.18rem;'
            f'background:{c}0D;border-left:2px solid {c}55;">'
            f'<div style="min-width:0;">'
            f'<span style="font-size:.78rem;font-weight:600;color:var(--t0);">{p["producto"]}</span>'
            f'<span style="font-size:.67rem;color:var(--t2);margin-left:.35rem;">{p["presentacion"]}</span>'
            f'</div>'
            f'<span style="font-size:.82rem;font-weight:800;color:{c};'
            f'white-space:nowrap;margin-left:.5rem;">{ic} {s}{p["pct"]:.1f}%</span>'
            f'</div>'
        )

    productos_html = f'<div class="vc-body">{rows_html}</div>' if rows_html else ""

    st.markdown(
        f'<details class="vc-card" style="margin-bottom:.5rem;">'
        f'<summary style="list-style:none;cursor:pointer;outline:none;">'
        f'<div style="padding:.9rem 1rem;border-radius:13px;'
        f'background:linear-gradient(135deg,{color}18 0%,{color}08 100%);'
        f'border:1px solid {color}44;border-top:3px solid {color};">'
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;">'
        f'<div>'
        f'<div style="font-size:.68rem;color:{color}cc;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:.07em;margin-bottom:.25rem;">{r["cat_norm"]}</div>'
        f'<div style="font-size:1.35rem;font-weight:800;color:{color};line-height:1;">'
        f'{icon} {sign}{r["pct_cambio"]:.1f}%</div>'
        f'<div style="font-size:.7rem;color:var(--t3);margin-top:.3rem;">'
        f'{r["n_productos"]} productos&nbsp;&nbsp;'
        f'<span style="color:{RED};">▲{r["n_subio"]}</span>&nbsp;'
        f'<span style="color:{GREEN};">▼{r["n_bajo"]}</span>'
        f'</div></div>'
        f'<span class="vc-chevron" style="font-size:1.1rem;color:{color}88;">▾</span>'
        f'</div></div>'
        f'</summary>'
        f'{productos_html}'
        f'</details>',
        unsafe_allow_html=True,
    )


def _semana_n_atras(todas_semanas, semana_act, n):
    """Devuelve la semana N posiciones antes de semana_act en la lista ordenada."""
    if semana_act not in todas_semanas:
        return None
    idx = todas_semanas.index(semana_act)
    ref_idx = idx - n
    return todas_semanas[ref_idx] if ref_idx >= 0 else None


# ── Render principal ──────────────────────────────────────────
def render_inicio(ctx):
    df_all      = ctx.df_all
    df_actual   = ctx.df_actual
    semana_act  = ctx.semana_actual
    sa_lbl      = ctx.sa_lbl
    sa_lbl_l    = ctx.sa_lbl_l
    sc_lbl      = ctx.sc_lbl
    sc_lbl_l    = ctx.sc_lbl_l
    fuente_act  = ctx.fuente_actual or ""

    todas_semanas = sorted(df_all["semana"].dropna().unique())

    st.markdown(
        '<div style="margin-bottom:.75rem;">'
        '<span style="font-size:1.35rem;font-weight:800;color:var(--t0);">📊 Panel de Control</span>'
        '<span style="font-size:.8rem;color:var(--t3);margin-left:.7rem;">'
        'Situación de precios por categoría</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Filtros de la pestaña ─────────────────────────────────
    fc1, fc2, fc3 = st.columns([2, 2, 2])
    periodos = {
        "vs semana anterior": 1,
        "Últimas 4 semanas":  4,
        "Últimas 6 semanas":  6,
    }
    periodo_lbl = fc1.selectbox(
        "Período de análisis",
        list(periodos.keys()),
        index=0,
        key="inicio_periodo",
    )
    n_semanas = periodos[periodo_lbl]

    # Filtro de provincia (avanzado)
    provincias_disp = (
        sorted(df_actual["provincia"].dropna().unique())
        if df_actual is not None and not df_actual.empty else []
    )
    prov_sel = fc2.multiselect(
        "Provincia",
        provincias_disp,
        default=provincias_disp,
        key="inicio_prov",
        placeholder="Todas las provincias",
    )
    buscar_cat = fc3.text_input(
        "Buscar categoría",
        value="",
        key="inicio_buscar_cat",
        placeholder="Filtrar categorías...",
    )

    # Aplicar filtro de provincia a df_all para el análisis
    df_analisis = df_all.copy()
    if prov_sel and len(prov_sel) < len(provincias_disp):
        df_analisis = df_analisis[df_analisis["provincia"].isin(prov_sel)]

    # ── Semana de referencia ──────────────────────────────────
    semana_ref = _semana_n_atras(todas_semanas, semana_act, n_semanas)

    if not semana_ref:
        st.warning(
            f"No hay suficientes semanas en la base de datos para el período "
            f"'{periodo_lbl}'. Hay {len(todas_semanas)} semana(s) disponibles."
        )
        return

    ref_lbl   = fmt_sem(semana_ref, "corta")
    ref_lbl_l = fmt_sem(semana_ref, "larga")

    # ── Calcular deltas ───────────────────────────────────────
    delta_df, m_productos = _calc_categoria_delta(df_analisis, semana_act, semana_ref)

    if delta_df.empty:
        st.info("No hay productos en común entre las semanas para calcular variaciones.")
        return

    # Filtro por nombre de categoría
    if buscar_cat.strip():
        bl = buscar_cat.strip().lower()
        delta_df   = delta_df[delta_df["cat_norm"].str.lower().str.contains(bl, na=False)]
        m_productos = m_productos[m_productos["cat_norm"].str.lower().str.contains(bl, na=False)]
        if delta_df.empty:
            st.info(f"No se encontraron categorías que coincidan con '{buscar_cat}'.")
            return

    # ── Métricas resumen ──────────────────────────────────────
    n_total  = len(delta_df)
    n_subio  = int((delta_df["pct_cambio"] >  0.5).sum())
    n_bajo   = int((delta_df["pct_cambio"] < -0.5).sum())
    n_estbl  = n_total - n_subio - n_bajo
    n_prods_total = int(delta_df["n_productos"].sum())

    m1, m2, m3, m4 = st.columns(4)
    m1.markdown(_kpi_mini("Categorías analizadas", str(n_total),       "#94A3B8"), unsafe_allow_html=True)
    m2.markdown(_kpi_mini("Con alza",              str(n_subio),       RED),       unsafe_allow_html=True)
    m3.markdown(_kpi_mini("Con baja",              str(n_bajo),        GREEN),     unsafe_allow_html=True)
    m4.markdown(_kpi_mini("Estables",              str(n_estbl),       "#64748B"), unsafe_allow_html=True)

    st.markdown(
        f'<div style="font-size:.73rem;color:var(--t3);margin:.4rem 0 .6rem 0;">'
        f'Comparando <b style="color:var(--t0);">{sa_lbl_l}</b> vs '
        f'<b style="color:var(--t0);">{ref_lbl_l}</b>'
        f' · {n_prods_total} productos con datos en ambas semanas'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Gráfico de barras horizontales ────────────────────────
    df_chart = delta_df.sort_values("pct_cambio").copy()
    bar_colors = [
        RED if v > 0.5 else (GREEN if v < -0.5 else "#475569")
        for v in df_chart["pct_cambio"]
    ]

    fig = go.Figure(go.Bar(
        x=df_chart["pct_cambio"],
        y=df_chart["cat_norm"],
        orientation="h",
        marker_color=bar_colors,
        customdata=df_chart[["n_productos", "n_subio", "n_bajo"]].values,
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Variación promedio: %{x:+.2f}%<br>"
            "Productos rastreados: %{customdata[0]}<br>"
            "Subieron: %{customdata[1]} · Bajaron: %{customdata[2]}"
            "<extra></extra>"
        ),
        text=[f"{'+' if v >= 0 else ''}{v:.1f}%" for v in df_chart["pct_cambio"]],
        textposition="outside",
        textfont=dict(size=11, family="Inter"),
    ))

    _CT = get_theme_tokens(_get_mode())
    _tc       = _CT["CHART_TEXT"]
    _tm       = _CT["CHART_MUTED"]
    _zc       = _CT["CHART_ZEROLINE"]
    _tc_title = _CT["CHART_TEXT"]

    max_abs = df_chart["pct_cambio"].abs().max() or 1
    fig.update_layout(
        title=dict(
            text=f"Variación de precios por categoría — {sa_lbl} vs {ref_lbl} ({periodo_lbl})",
            font=dict(size=13, color=_tc_title, family="Inter"), x=0,
        ),
        height=max(320, len(df_chart) * 34),
        margin=dict(l=10, r=80, t=50, b=30),
        bargap=0.28,
        xaxis=dict(
            zeroline=True,
            zerolinecolor=_zc,
            zerolinewidth=2,
            range=[-(max_abs * 1.35), max_abs * 1.35],
            ticksuffix="%",
            tickfont=dict(size=10, color=_tm),
        ),
        yaxis=dict(tickfont=dict(size=11, color=_tc)),
    )
    apply_dark_layout(fig)
    st.plotly_chart(fig, use_container_width=True)

    # ── Top movers (desplegables) ─────────────────────────────
    top_sub = delta_df[delta_df["pct_cambio"] >  0.5].head(3)
    top_baj = delta_df[delta_df["pct_cambio"] < -0.5].sort_values("pct_cambio").head(3)

    if not top_sub.empty or not top_baj.empty:
        col_up, col_dn = st.columns(2)
        with col_up:
            st.markdown(
                f'<div style="font-size:.78rem;font-weight:700;color:{RED};'
                f'margin-bottom:.4rem;">▲ Mayor alza</div>',
                unsafe_allow_html=True,
            )
            for _, r in top_sub.iterrows():
                _render_card_expandible(r, m_productos, tipo="subio")

        with col_dn:
            st.markdown(
                f'<div style="font-size:.78rem;font-weight:700;color:{GREEN};'
                f'margin-bottom:.4rem;">▼ Mayor baja</div>',
                unsafe_allow_html=True,
            )
            for _, r in top_baj.iterrows():
                _render_card_expandible(r, m_productos, tipo="bajo")

    # ── Info de contexto ──────────────────────────────────────
    st.divider()
    i1, i2, i3 = st.columns(3)
    i1.markdown(
        f'<div style="padding:.65rem .9rem;border-radius:11px;'
        f'background:rgba(59,130,246,0.08);border:1px solid rgba(59,130,246,0.25);">'
        f'<div style="font-size:.67rem;color:#2563EB88;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:.05em;">Semana actual</div>'
        f'<div style="font-size:1rem;font-weight:800;color:#2563EB;margin:.15rem 0;">'
        f'{sa_lbl}{_fuente_badge(fuente_act)}</div>'
        f'<div style="font-size:.72rem;color:var(--t3);">{sa_lbl_l}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    i2.markdown(
        f'<div style="padding:.65rem .9rem;border-radius:11px;'
        f'background:rgba(139,92,246,0.08);border:1px solid rgba(139,92,246,0.25);">'
        f'<div style="font-size:.67rem;color:#6D28D988;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:.05em;">Semana de referencia</div>'
        f'<div style="font-size:1rem;font-weight:800;color:#6D28D9;margin:.15rem 0;">'
        f'{ref_lbl}</div>'
        f'<div style="font-size:.72rem;color:var(--t3);">{ref_lbl_l}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    n_reg = len(df_actual) if df_actual is not None else 0
    n_sups = int(df_actual["supermercado"].nunique()) if (df_actual is not None and not df_actual.empty) else 0
    i3.markdown(
        f'<div style="padding:.65rem .9rem;border-radius:11px;'
        f'background:rgba(249,115,22,0.08);border:1px solid rgba(249,115,22,0.25);">'
        f'<div style="font-size:.67rem;color:#EA580C88;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:.05em;">Cobertura semana actual</div>'
        f'<div style="font-size:1rem;font-weight:800;color:#EA580C;margin:.15rem 0;">'
        f'{n_reg:,} registros</div>'
        f'<div style="font-size:.72rem;color:var(--t3);">{n_sups} supermercados</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
