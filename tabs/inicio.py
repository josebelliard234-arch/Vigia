import streamlit as st
import pandas as pd

from utils.dates import fmt_sem
from utils.formatting import fmt_rdp, norm_key
from styles.theme import TEXT_MAIN, TEXT_MUTED, TEXT_SECONDARY, RED, GREEN, YELLOW


def _kpi_big(label: str, value: str, sub: str = "", color: str = "#3B82F6") -> str:
    return (
        f'<div style="padding:1.1rem 1.2rem 1rem 1.2rem;border-radius:14px;'
        f'background:rgba(15,23,42,0.8);border:1px solid rgba(148,163,184,0.13);'
        f'height:100%;box-sizing:border-box;">'
        f'<div style="font-size:.76rem;color:#64748B;font-weight:600;'
        f'text-transform:uppercase;letter-spacing:.06em;margin-bottom:.3rem;">{label}</div>'
        f'<div style="font-size:2.1rem;font-weight:800;color:{color};'
        f'line-height:1.1;word-break:break-word;">{value}</div>'
        f'<div style="font-size:.76rem;color:#64748B;margin-top:.3rem;">{sub}</div>'
        f'</div>'
    )


def _kpi_small(label: str, value: str, color: str = "#94A3B8") -> str:
    return (
        f'<div style="padding:.75rem .9rem .7rem .9rem;border-radius:12px;'
        f'background:rgba(15,23,42,0.6);border:1px solid rgba(148,163,184,0.1);">'
        f'<div style="font-size:.7rem;color:#475569;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:.05em;margin-bottom:.2rem;">{label}</div>'
        f'<div style="font-size:1.35rem;font-weight:700;color:{color};">{value}</div>'
        f'</div>'
    )


def _fuente_badge(fuente: str) -> str:
    if fuente == "bruto":
        return (
            f' <span style="background:rgba(245,158,11,0.18);color:{YELLOW};'
            f'font-size:.65rem;font-weight:700;padding:.04rem .32rem;border-radius:5px;'
            f'border:1px solid rgba(245,158,11,0.35);vertical-align:middle;">BRUTO</span>'
        )
    if fuente == "validado":
        return (
            f' <span style="background:rgba(34,197,94,0.15);color:{GREEN};'
            f'font-size:.65rem;font-weight:700;padding:.04rem .32rem;border-radius:5px;'
            f'border:1px solid rgba(34,197,94,0.3);vertical-align:middle;">VALIDADO</span>'
        )
    return ""


def render_inicio(ctx):
    df_actual  = ctx.df_actual
    df_comp    = ctx.df_comp
    df_all     = ctx.df_all
    sa_lbl     = ctx.sa_lbl
    sc_lbl     = ctx.sc_lbl
    sa_lbl_l   = ctx.sa_lbl_l
    sc_lbl_l   = ctx.sc_lbl_l
    fuente_act = ctx.fuente_actual or ""

    st.markdown(
        '<div style="margin-bottom:.9rem;">'
        '<span style="font-size:1.4rem;font-weight:800;color:#F8FAFC;">📊 Panel de Control</span>'
        '<span style="font-size:.8rem;color:#64748B;margin-left:.7rem;">'
        'Resumen general del monitoreo de precios</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Selector de producto ──────────────────────────────────
    with st.container():
        ps1, ps2, ps3 = st.columns([3, 2.5, 1])
        productos_opts = sorted(df_all["producto"].dropna().unique()) if not df_all.empty else []
        prod_sel = ps1.selectbox(
            "Producto",
            ["- Todos los productos -"] + productos_opts,
            index=0,
            key="inicio_prod",
        )
        if prod_sel and prod_sel != "- Todos los productos -":
            pres_opts = sorted(
                df_all[df_all["producto"] == prod_sel]["presentacion"].dropna().unique()
            )
            pres_all = ["- Todas -"] + pres_opts if len(pres_opts) > 1 else pres_opts
            pres_sel = ps2.selectbox("Presentacion", pres_all, index=0, key="inicio_pres")
        else:
            pres_sel = None
            ps2.selectbox("Presentacion", ["-"], disabled=True, key="inicio_pres_dis")

    # ── Calcular promedios ───────────────────────────────────
    def _prom(df_src, prod, pres):
        if df_src is None or df_src.empty:
            return None
        if not prod or prod == "- Todos los productos -":
            return float(df_src["precio"].mean())
        mask = df_src["producto"].map(norm_key) == norm_key(prod)
        if pres and pres not in ("- Todas -",):
            mask &= df_src["presentacion"].map(norm_key) == norm_key(pres)
        sub = df_src[mask]
        return float(sub["precio"].mean()) if not sub.empty else None

    prom_act  = _prom(df_actual, prod_sel, pres_sel)
    prom_comp = _prom(df_comp,   prod_sel, pres_sel)

    var_pct = var_rdp = None
    if prom_act is not None and prom_comp is not None and prom_comp != 0:
        var_rdp = prom_act - prom_comp
        var_pct = var_rdp / prom_comp * 100

    prom_act_txt  = fmt_rdp(prom_act)  if prom_act  is not None else "N/D"
    prom_comp_txt = fmt_rdp(prom_comp) if prom_comp is not None else "N/D"

    if var_pct is not None:
        sign       = "+" if var_pct > 0 else ""
        var_pct_txt = f"{sign}{var_pct:.1f}%"
        var_rdp_txt = f"{'+' if var_rdp >= 0 else ''}{fmt_rdp(var_rdp)}"
        var_color  = RED if var_pct > 0 else (GREEN if var_pct < 0 else "#94A3B8")
    else:
        var_pct_txt = "N/D"
        var_rdp_txt = "N/D"
        var_color   = "#94A3B8"

    # ── KPIs grandes ─────────────────────────────────────────
    st.markdown("<div style='margin:.55rem 0 .3rem 0'></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.markdown(
        _kpi_big(
            "Precio promedio — " + sa_lbl,
            prom_act_txt,
            sub=("Fuente: " + fuente_act.upper()) if fuente_act else "",
            color="#3B82F6",
        ),
        unsafe_allow_html=True,
    )
    c2.markdown(
        _kpi_big(
            "Precio promedio — " + sc_lbl,
            prom_comp_txt,
            sub="Semana base de comparacion",
            color="#8B5CF6",
        ),
        unsafe_allow_html=True,
    )
    c3.markdown(
        _kpi_big(
            "Variacion",
            var_pct_txt,
            sub=var_rdp_txt,
            color=var_color,
        ),
        unsafe_allow_html=True,
    )

    st.markdown("<div style='margin:.55rem 0 .3rem 0'></div>", unsafe_allow_html=True)

    # ── KPIs secundarios ─────────────────────────────────────
    n_registros = len(df_actual) if df_actual is not None else 0
    n_prods = int(df_actual["producto"].nunique()) if (df_actual is not None and not df_actual.empty) else 0
    n_sups  = int(df_actual["supermercado"].nunique()) if (df_actual is not None and not df_actual.empty) else 0
    n_provs = int(df_actual["provincia"].nunique())    if (df_actual is not None and not df_actual.empty) else 0

    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(_kpi_small("Registros actuales", f"{n_registros:,}",   "#94A3B8"), unsafe_allow_html=True)
    k2.markdown(_kpi_small("Productos",           str(n_prods),         "#06B6D4"), unsafe_allow_html=True)
    k3.markdown(_kpi_small("Supermercados",       str(n_sups),          "#A78BFA"), unsafe_allow_html=True)
    k4.markdown(_kpi_small("Provincias",          str(n_provs),         "#F97316"), unsafe_allow_html=True)

    st.markdown("<div style='margin:.6rem 0 .2rem 0'></div>", unsafe_allow_html=True)
    st.divider()

    # ── Detalle semanas ───────────────────────────────────────
    st.markdown(
        '<span style="font-size:.88rem;font-weight:700;color:#F8FAFC;">Semanas</span>',
        unsafe_allow_html=True,
    )
    d1, d2 = st.columns(2)
    with d1:
        st.markdown(
            f'<div style="padding:.75rem 1rem;border-radius:12px;'
            f'background:rgba(59,130,246,0.08);border:1px solid rgba(59,130,246,0.25);">'
            f'<div style="font-size:.72rem;color:#64748B;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:.05em;">Semana actual</div>'
            f'<div style="font-size:1.2rem;font-weight:800;color:#3B82F6;margin:.2rem 0;">'
            f'{sa_lbl}{_fuente_badge(fuente_act)}</div>'
            f'<div style="font-size:.77rem;color:#64748B;">{sa_lbl_l}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with d2:
        st.markdown(
            f'<div style="padding:.75rem 1rem;border-radius:12px;'
            f'background:rgba(139,92,246,0.08);border:1px solid rgba(139,92,246,0.25);">'
            f'<div style="font-size:.72rem;color:#64748B;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:.05em;">Semana comparada</div>'
            f'<div style="font-size:1.2rem;font-weight:800;color:#8B5CF6;margin:.2rem 0;">'
            f'{sc_lbl}</div>'
            f'<div style="font-size:.77rem;color:#64748B;">{sc_lbl_l}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Producto seleccionado ─────────────────────────────────
    if prod_sel and prod_sel != "- Todos los productos -":
        st.markdown("<div style='margin:.5rem 0'></div>", unsafe_allow_html=True)
        pres_txt = (
            pres_sel if (pres_sel and pres_sel != "- Todas -")
            else "Todas las presentaciones"
        )
        st.markdown(
            f'<div style="padding:.7rem 1rem;border-radius:12px;'
            f'background:rgba(15,23,42,0.6);border:1px solid rgba(148,163,184,0.1);">'
            f'<span style="font-size:.72rem;color:#64748B;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:.05em;">Producto seleccionado</span>&nbsp;&nbsp;'
            f'<span style="font-size:.9rem;font-weight:700;color:#F8FAFC;">{prod_sel}</span>'
            f'<span style="font-size:.8rem;color:#64748B;margin-left:.6rem;">· {pres_txt}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
