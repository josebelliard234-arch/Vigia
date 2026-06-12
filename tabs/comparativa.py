import streamlit as st
import plotly.graph_objects as go

from styles.theme import (
    TEXT_MAIN, TEXT_SECONDARY, TEXT_MUTED,
    GREEN, RED,
)
from utils.formatting import fmt_rdp, fmt_pct
from utils.transformations import cruzar_semanas, normalizar_categoria, preparar_productos_con_cambio
from components.charts import apply_dark_layout


def render_comparativa(ctx):
    df_actual     = ctx.df_actual
    df_comp       = ctx.df_comp
    sa_lbl        = ctx.sa_lbl
    sc_lbl        = ctx.sc_lbl
    sa_lbl_l      = ctx.sa_lbl_l
    sc_lbl_l      = ctx.sc_lbl_l

    st.subheader(f"Comparativa: {sa_lbl} vs {sc_lbl}")

    if df_comp.empty or df_actual.empty:
        st.info("Selecciona dos semanas con datos para ver comparaciones.")
        return

    merged = cruzar_semanas(df_actual, df_comp)

    if merged.empty:
        st.warning("No hay productos en comun entre las dos semanas.")
        return

    display = merged[[
        "categoria", "producto", "presentacion",
        "provincia", "supermercado",
        "precio_comp", "precio_actual", "Variacion RD$", "Variacion %"
    ]].copy()
    display.columns = [
        "Categoria", "Producto", "Presentacion", "Provincia", "Supermercado",
        f"Precio {sc_lbl}", f"Precio {sa_lbl}",
        "Variacion RD$", "Variacion %"
    ]
    # Guardar variacion numerica ANTES de formatear, para el filtro
    var_pct_num = merged["Variacion %"].reset_index(drop=True).values

    display["Variacion %"]           = display["Variacion %"].apply(fmt_pct)
    display[f"Precio {sc_lbl}"]     = display[f"Precio {sc_lbl}"].apply(fmt_rdp)
    display[f"Precio {sa_lbl}"]     = display[f"Precio {sa_lbl}"].apply(fmt_rdp)
    display["Variacion RD$"]         = display["Variacion RD$"].apply(lambda x: f"RD$ {x:+,.2f}")
    display = display.reset_index(drop=True)

    solo_cambios = st.checkbox("Mostrar solo productos con cambio", value=False)
    if solo_cambios:
        import numpy as np
        mask_cambio = abs(var_pct_num) > 0.01
        display = display[mask_cambio]
    st.caption(f"📅 {sa_lbl_l} vs {sc_lbl_l}")
    st.dataframe(display, use_container_width=True, hide_index=True)

    # -- Productos con cambio de precio --
    st.subheader("Productos con cambio de precio")
    st.caption(
        "Filtra por categoria para analizar los productos de un grupo especifico. "
        "Usa la vista General para ver promedios entre establecimientos "
        "o selecciona un establecimiento para revisar sus productos."
    )

    # -- Construir mapa de categorias normalizadas --
    cats_raw_pcc  = sorted(merged["categoria"].dropna().astype(str).unique())
    cats_norm_pcc = {c: normalizar_categoria(c) for c in cats_raw_pcc}
    cats_display_pcc = ["Todas las categorias"] + sorted(
        set(cats_norm_pcc.values()) - {"Sin categoria"}
    )

    # -- Controles principales --
    pcc_col1, pcc_col2, pcc_col3 = st.columns([2, 2, 2])
    with pcc_col1:
        cat_pcc = st.selectbox(
            "Categoria",
            cats_display_pcc,
            key="pcc_categoria"
        )
    with pcc_col2:
        vista_pcc = st.selectbox(
            "Vista",
            ["General", "Por establecimiento"],
            key="pcc_vista"
        )
    with pcc_col3:
        n_opciones = [15, 30, 50, 100, "Todos"]
        n_mostrar_pcc = st.selectbox(
            "Cantidad a mostrar (grafica)",
            n_opciones,
            index=1,
            key="pcc_n_mostrar"
        )

    # -- Filtro de establecimiento (solo si vista = Por establecimiento) --
    sup_pcc = None
    if vista_pcc == "Por establecimiento":
        supers_pcc = sorted(merged["supermercado"].dropna().astype(str).unique())
        sup_pcc = st.selectbox(
            "Establecimiento",
            supers_pcc,
            key="pcc_supermercado"
        )

    solo_cambios_pcc = st.checkbox(
        "Mostrar solo productos con cambio",
        value=False,
        key="pcc_solo_cambios"
    )

    # -- Preparar datos --
    df_cnt_pcc, df_graf_pcc, df_tabla_pcc = preparar_productos_con_cambio(
        merged, cat_pcc, cats_norm_pcc,
        vista_pcc, sup_pcc, solo_cambios_pcc
    )

    if df_cnt_pcc.empty:
        st.info("No hay productos con datos comparables para los filtros seleccionados.")
        return

    # -- Contadores --
    n_subio  = int((df_cnt_pcc["var_pct"] >  0.01).sum())
    n_bajo   = int((df_cnt_pcc["var_pct"] < -0.01).sum())
    n_cambio = n_subio + n_bajo
    cc1, cc2, cc3 = st.columns(3)
    cc1.metric("Con cambio", n_cambio,
               help="Productos unicos con variacion detectada.")
    cc2.metric("Subieron",   n_subio,
               help="Precio actual mayor al precio de referencia.")
    cc3.metric("Bajaron",    n_bajo,
               help="Precio actual menor al precio de referencia.")

    # -- Grafica --
    if df_graf_pcc.empty:
        st.info("No hay productos con cambio en los filtros seleccionados.")
    else:
        # Aplicar limite de cantidad a mostrar
        df_graf_plot = (
            df_graf_pcc
            if n_mostrar_pcc == "Todos"
            else df_graf_pcc.head(int(n_mostrar_pcc))
        )
        # Revertir orden para que la barra mas alta quede arriba
        df_graf_plot = df_graf_plot.iloc[::-1].reset_index(drop=True)

        if vista_pcc == "General":
            titulo_pcc = (
                f"Productos con cambio — {cat_pcc} — General — "
                f"{sa_lbl} vs {sc_lbl}"
            )
            hover_extra = ""
        else:
            titulo_pcc = (
                f"Productos con cambio — {cat_pcc} — {sup_pcc} — "
                f"{sa_lbl} vs {sc_lbl}"
            )
            hover_extra = f"Establecimiento: {sup_pcc}<br>"

        colors_pcc = [
            GREEN if v < 0 else RED
            for v in df_graf_plot["var_pct"]
        ]
        fig_pcc = go.Figure(go.Bar(
            x=df_graf_plot["var_pct"],
            y=df_graf_plot["etiqueta"],
            orientation="h",
            marker_color=colors_pcc,
            customdata=df_graf_plot[["precio_comp", "precio_actual",
                                      "Estado"]].values,
            hovertemplate=(
                "<b>%{y}</b><br>"
                + hover_extra
                + f"Precio base ({sc_lbl_l}): RD$ %{{customdata[0]:,.2f}}<br>"
                + f"Precio actual ({sa_lbl_l}): RD$ %{{customdata[1]:,.2f}}<br>"
                + "Variacion: %{x:+.2f}%<br>"
                + "Estado: %{customdata[2]}<br>"
                + "<extra></extra>"
            )
        ))

        max_abs_pcc = df_graf_plot["var_pct"].abs().max() or 1
        pad_pcc = max_abs_pcc * 0.06
        ann_pcc = []
        for _, row in df_graf_plot.iterrows():
            v = row["var_pct"]
            lbl_txt = f"{fmt_pct(v)}  RD$ {row['precio_actual']:,.0f}"
            x_pos   = v + pad_pcc if v >= 0 else v - pad_pcc
            xanchor = "left"      if v >= 0 else "right"
            ann_pcc.append(dict(
                x=x_pos, y=row["etiqueta"], text=lbl_txt,
                xanchor=xanchor, yanchor="middle",
                showarrow=False,
                font=dict(size=10, color=TEXT_SECONDARY, family="Inter")
            ))

        fig_pcc.update_layout(
            title=dict(
                text=titulo_pcc,
                font=dict(size=14, color=TEXT_MAIN, family="Inter"), x=0
            ),
            annotations=ann_pcc,
            height=max(380, len(df_graf_plot) * 36),
            bargap=0.22,
            xaxis_title="Variacion %", yaxis_title="",
            margin=dict(l=10, r=300, t=60, b=40),
            xaxis=dict(
                zeroline=True,
                zerolinecolor="rgba(248,250,252,0.45)",
                zerolinewidth=2,
                range=[-(max_abs_pcc * 1.05), max_abs_pcc * 1.05]
            ),
            yaxis=dict(tickfont=dict(size=11, color=TEXT_SECONDARY))
        )
        apply_dark_layout(fig_pcc)
        st.plotly_chart(fig_pcc, use_container_width=True)

    # -- Tabla --
    st.caption(f"📅 {sa_lbl_l} vs {sc_lbl_l}  ·  {len(df_tabla_pcc)} productos")
    st.dataframe(df_tabla_pcc, use_container_width=True, hide_index=True)
