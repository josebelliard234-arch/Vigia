import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from styles.theme import (
    TEXT_MAIN, TEXT_SECONDARY,
    BLUE, GREEN, RED,
)
from utils.dates import fmt_sem
from utils.formatting import fmt_rdp, fmt_pct
from utils.transformations import precios_supermercado_para
from components.charts import apply_dark_layout


def render_por_supermercado(ctx):
    df_sup       = ctx.df_sup
    df_bruto     = ctx.df_bruto
    df_validado  = ctx.df_validado
    semana_actual = ctx.semana_actual
    sa_lbl        = ctx.sa_lbl

    todas_semanas = sorted(set(ctx.df_all["semana"].dropna().astype(str).unique()))

    st.subheader("Precios por Supermercado")

    fuente_dispo = (not df_sup.empty) or (not df_bruto.empty)

    if not fuente_dispo:
        st.info("Carga el archivo de herramientas (Resumen por supermercado) o un reporte semanal bruto para ver esta seccion.")
        return
    if not semana_actual:
        st.info("Selecciona una 'Semana actual' en los filtros principales.")
        return

    # Lista de productos disponibles segun la semana actual
    prods_sup_act = pd.DataFrame()
    if not df_sup.empty:
        prods_sup_act = df_sup[df_sup["semana"] == semana_actual][["producto", "presentacion"]].drop_duplicates()
    prods_bruto_act = pd.DataFrame()
    if not df_bruto.empty:
        prods_bruto_act = df_bruto[df_bruto["semana"] == semana_actual][["producto", "presentacion"]].drop_duplicates()

    productos_act_disp = pd.concat([prods_sup_act, prods_bruto_act], ignore_index=True).drop_duplicates()

    if productos_act_disp.empty:
        st.warning(f"No hay productos con desglose por supermercado para la semana actual ({sa_lbl}).")
        return

    # Filtros del tab
    f1, f2, f3 = st.columns(3)
    with f1:
        prod_sup = st.selectbox(
            "Producto",
            sorted(productos_act_disp["producto"].unique()),
            key="sup_prod"
        )
    with f2:
        pres_sup_opts = sorted(
            productos_act_disp[productos_act_disp["producto"] == prod_sup]["presentacion"].unique()
        )
        pres_sup = st.selectbox("Presentacion", pres_sup_opts, key="sup_pres")
    with f3:
        supers_universo = set()
        if not df_sup.empty:
            supers_universo |= set(df_sup["supermercado"].unique())
        if not df_bruto.empty:
            supers_universo |= set(df_bruto["supermercado"].unique())
        supers_opts = sorted([s for s in supers_universo if isinstance(s, str)])
        supers_sel  = st.multiselect(
            "Supermercados (ocultar/mostrar)",
            supers_opts,
            default=supers_opts,
            key="sup_supers"
        )

    # Selector de semanas PROPIO de esta vista
    sc1, sc2 = st.columns(2)

    # sup_sem_act se define primero (sc2) para calcular sup_comp_opts
    with sc2:
        idx_act = todas_semanas.index(semana_actual) if semana_actual in todas_semanas else len(todas_semanas) - 1
        sup_sem_act = st.selectbox(
            "Semana A (actual)", todas_semanas, index=idx_act, key="sup_sem_act",
            format_func=lambda x: fmt_sem(x, "larga"),
        )

    sup_comp_opts = [s for s in todas_semanas if s != sup_sem_act]
    default_idx = 0
    if sup_comp_opts:
        anteriores = [s for s in sorted(sup_comp_opts) if s < sup_sem_act]
        if anteriores:
            objetivo = anteriores[-1]
            if objetivo in sup_comp_opts:
                default_idx = sup_comp_opts.index(objetivo)

    with sc1:
        sup_sem_comp = st.selectbox(
            "Semana B (comparar)", sup_comp_opts, index=default_idx, key="sup_sem_comp",
            format_func=lambda x: fmt_sem(x, "larga"),
        ) if sup_comp_opts else None

    # Etiquetas legibles para esta seccion
    _ssa_lbl   = fmt_sem(sup_sem_act, "corta")
    _ssc_lbl   = fmt_sem(sup_sem_comp, "corta") if sup_sem_comp else "N/D"
    _ssa_lbl_l = fmt_sem(sup_sem_act, "larga")
    _ssc_lbl_l = fmt_sem(sup_sem_comp, "larga") if sup_sem_comp else "N/D"

    # Datos para semana A y semana B
    df_sup_act = precios_supermercado_para(
        sup_sem_act, prod_sup, pres_sup, supers_sel,
        df_sup, df_bruto, df_validado
    )
    df_sup_ant = pd.DataFrame()
    if sup_sem_comp:
        df_sup_ant = precios_supermercado_para(
            sup_sem_comp, prod_sup, pres_sup, supers_sel,
            df_sup, df_bruto, df_validado
        )

    fuente_act_lbl = df_sup_act["fuente"].iloc[0] if not df_sup_act.empty else "N/D"
    fuente_ant_lbl = df_sup_ant["fuente"].iloc[0] if not df_sup_ant.empty else "N/D"

    if df_sup_act.empty:
        st.warning(
            f"No hay precios desglosados por supermercado para {prod_sup} ({pres_sup}) "
            f"en la semana {_ssa_lbl_l}."
        )
        return

    min_p = df_sup_act["precio"].min()
    max_p = df_sup_act["precio"].max()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(f"Semana A ({fuente_act_lbl})", _ssa_lbl)
    m2.metric("Precio mas bajo",  fmt_rdp(min_p))
    m3.metric("Precio mas alto",  fmt_rdp(max_p))
    m4.metric("Diferencia",       fmt_rdp(max_p - min_p))

    # Grafico 1: precios semana A
    st.subheader(
        f"Precios por supermercado — {prod_sup} ({pres_sup}) — "
        f"{_ssa_lbl} ({fuente_act_lbl})"
    )
    colors_act = [
        GREEN if p == min_p else (RED if p == max_p else BLUE)
        for p in df_sup_act["precio"]
    ]
    fig_act = go.Figure(go.Bar(
        x=df_sup_act["supermercado"],
        y=df_sup_act["precio"],
        marker_color=colors_act,
        text=[f"RD$ {p:,.0f}" for p in df_sup_act["precio"]],
        textposition="outside",
        textfont=dict(size=13, color=TEXT_MAIN, family="Inter"),
        hovertemplate=(
            "<b>Supermercado: %{x}</b><br>"
            f"Producto: {prod_sup}<br>"
            f"Presentacion: {pres_sup}<br>"
            f"Semana: {_ssa_lbl_l} ({fuente_act_lbl})<br>"
            "Precio: RD$ %{y:,.2f}<br>"
            "Verde = mas barato | Rojo = mas caro"
            "<extra></extra>"
        )
    ))
    fig_act.update_layout(
        title=dict(
            text=(
                f"Precios en Supermercados — {prod_sup} ({pres_sup}) | "
                f"{_ssa_lbl} ({fuente_act_lbl})"
            ),
            font=dict(size=16, color=TEXT_MAIN, family="Inter"), x=0
        ),
        height=500, bargap=0.2,
        yaxis_title="Precio (RD$)", xaxis_title="",
        margin=dict(l=20, r=20, t=70, b=80),
        xaxis=dict(
            tickangle=0,
            tickfont=dict(size=12, color=TEXT_SECONDARY),
        ),
        yaxis=dict(range=[0, max_p * 1.25], showgrid=True, gridcolor="rgba(148,163,184,0.14)")
    )
    apply_dark_layout(fig_act)
    st.plotly_chart(fig_act, use_container_width=True)

    # Grafico 2: comparativa dos semanas
    if not df_sup_ant.empty:
        st.subheader(
            f"Comparativa — {prod_sup} ({pres_sup}) — "
            f"{_ssa_lbl} ({fuente_act_lbl}) vs {_ssc_lbl} ({fuente_ant_lbl})"
        )

        comp_sup = df_sup_act[["supermercado", "precio"]].rename(
            columns={"precio": "precio_A"}
        ).merge(
            df_sup_ant[["supermercado", "precio"]].rename(
                columns={"precio": "precio_B"}
            ),
            on="supermercado", how="outer"
        ).sort_values("precio_A")

        nombre_b = f"Semana B ({_ssc_lbl} · {fuente_ant_lbl})"
        nombre_a = f"Semana A ({_ssa_lbl} · {fuente_act_lbl})"

        fig_comp = go.Figure()
        fig_comp.add_trace(go.Bar(
            name=nombre_b,
            x=comp_sup["supermercado"],
            y=comp_sup["precio_B"],
            marker_color=RED,
            text=[f"RD$ {p:,.0f}" if pd.notna(p) else "" for p in comp_sup["precio_B"]],
            textposition="outside",
            textfont=dict(size=12, color=TEXT_MAIN, family="Inter"),
            hovertemplate=(
                "<b>Supermercado: %{x}</b><br>"
                f"{nombre_b}<br>"
                f"Producto: {prod_sup} ({pres_sup})<br>"
                "Precio: RD$ %{y:,.2f}"
                "<extra></extra>"
            )
        ))
        fig_comp.add_trace(go.Bar(
            name=nombre_a,
            x=comp_sup["supermercado"],
            y=comp_sup["precio_A"],
            marker_color=BLUE,
            text=[f"RD$ {p:,.0f}" if pd.notna(p) else "" for p in comp_sup["precio_A"]],
            textposition="outside",
            textfont=dict(size=12, color=TEXT_MAIN, family="Inter"),
            hovertemplate=(
                "<b>Supermercado: %{x}</b><br>"
                f"{nombre_a}<br>"
                f"Producto: {prod_sup} ({pres_sup})<br>"
                "Precio: RD$ %{y:,.2f}"
                "<extra></extra>"
            )
        ))
        max_a_val = comp_sup["precio_A"].max() if pd.notna(comp_sup["precio_A"].max()) else 0
        max_b_val = comp_sup["precio_B"].max() if pd.notna(comp_sup["precio_B"].max()) else 0
        max_comp = max(max_a_val, max_b_val)
        fig_comp.update_layout(
            title=dict(
                text=(
                    f"Comparativa — {prod_sup} ({pres_sup}) — "
                    f"{_ssa_lbl} ({fuente_act_lbl}) vs {_ssc_lbl} ({fuente_ant_lbl})"
                ),
                font=dict(size=16, color=TEXT_MAIN, family="Inter"), x=0
            ),
            barmode="group",
            bargap=0.15, bargroupgap=0.08,
            height=520, yaxis_title="Precio (RD$)", xaxis_title="",
            margin=dict(l=20, r=20, t=70, b=80),
            xaxis=dict(
                tickangle=0,
                tickfont=dict(size=12, color=TEXT_SECONDARY),
            ),
            yaxis=dict(range=[0, max_comp * 1.25], showgrid=True, gridcolor="rgba(148,163,184,0.14)"),
            legend=dict(
                orientation="h", yanchor="bottom", y=-0.18,
                xanchor="center", x=0.5, font=dict(size=14, color=TEXT_MAIN),
                bgcolor="rgba(15,23,42,0.65)", bordercolor="rgba(148,163,184,0.25)", borderwidth=1
            )
        )
        apply_dark_layout(fig_comp)
        st.plotly_chart(fig_comp, use_container_width=True)

        # Tabla con variacion
        st.subheader("Tabla comparativa")
        tabla_comp = comp_sup.copy()
        tabla_comp["Variacion RD$"] = tabla_comp["precio_A"] - tabla_comp["precio_B"]
        tabla_comp["Variacion %"]   = (tabla_comp["Variacion RD$"] / tabla_comp["precio_B"] * 100).round(1)
        tabla_comp["precio_B"]      = tabla_comp["precio_B"].apply(lambda x: fmt_rdp(x) if pd.notna(x) else "N/D")
        tabla_comp["precio_A"]      = tabla_comp["precio_A"].apply(lambda x: fmt_rdp(x) if pd.notna(x) else "N/D")
        tabla_comp["Variacion RD$"] = tabla_comp["Variacion RD$"].apply(lambda x: f"RD$ {x:+,.2f}" if pd.notna(x) else "N/D")
        tabla_comp["Variacion %"]   = tabla_comp["Variacion %"].apply(lambda x: fmt_pct(x) if pd.notna(x) else "N/D")
        tabla_comp = tabla_comp[["supermercado", "precio_B", "precio_A", "Variacion RD$", "Variacion %"]]
        tabla_comp.columns = [
            "Supermercado",
            f"Precio {_ssc_lbl} ({fuente_ant_lbl})",
            f"Precio {_ssa_lbl} ({fuente_act_lbl})",
            "Variacion RD$",
            "Variacion %"
        ]
        st.caption(f"📅 {_ssa_lbl_l} (Sem. A) · {_ssc_lbl_l} (Sem. B)")
        st.dataframe(tabla_comp, use_container_width=True, hide_index=True)
    else:
        st.caption(
            f"No hay datos desglosados por supermercado para la semana B "
            f"({_ssc_lbl_l}). Solo se muestra la semana A."
        )
