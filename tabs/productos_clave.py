import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from styles.theme import (
    TEXT_MAIN, TEXT_SECONDARY,
    GREEN, RED, GRAY, light_df,
)
from utils.formatting import fmt_rdp, fmt_pct
from utils.transformations import precio_promedio_semana
from components.charts import apply_dark_layout


def render_productos_clave(ctx):
    df_clave      = ctx.df_clave
    df_all        = ctx.df_all
    semana_actual  = ctx.semana_actual
    semana_comp    = ctx.semana_comp
    sa_lbl         = ctx.sa_lbl
    sc_lbl         = ctx.sc_lbl
    sa_lbl_l       = ctx.sa_lbl_l
    sc_lbl_l       = ctx.sc_lbl_l
    fuente_actual  = ctx.fuente_actual
    fuente_comp    = ctx.fuente_comp

    st.subheader("Productos Clave - Canasta Prioritaria")

    if df_clave.empty:
        st.info("Carga el archivo de herramientas para ver esta seccion.")
        return

    if not semana_actual or not semana_comp:
        st.info("Selecciona 'Semana actual' y 'Semana a comparar' en los filtros principales.")
        return

    st.caption(
        f"Productos definidos en la Tabla 21 del archivo de herramientas. "
        f"Variaciones recalculadas con: **{sc_lbl_l}** ({fuente_comp or 'N/D'}) vs "
        f"**{sa_lbl_l}** ({fuente_actual or 'N/D'})."
    )

    canasta = df_clave[["producto", "presentacion"]].drop_duplicates()
    rows = []
    for _, p in canasta.iterrows():
        producto_n     = p["producto"]
        presentacion_n = p["presentacion"]

        precio_act, fuente_a = precio_promedio_semana(
            df_all, semana_actual, producto_n, presentacion_n,
            preferir_bruto=(fuente_actual == "bruto")
        )
        precio_ant, fuente_b = precio_promedio_semana(
            df_all, semana_comp, producto_n, presentacion_n,
            preferir_bruto=False
        )

        if precio_act is None or precio_ant is None or precio_ant == 0:
            rows.append({
                "producto":       producto_n,
                "presentacion":   presentacion_n,
                "precio_sem_ant": precio_ant,
                "precio_sem_act": precio_act,
                "variacion_abs":  None,
                "variacion_pct":  None,
                "fuente_act":     fuente_a or "N/D",
                "fuente_ant":     fuente_b or "N/D",
                "disponible":     False,
            })
        else:
            var_abs = precio_act - precio_ant
            var_pct = var_abs / precio_ant * 100
            rows.append({
                "producto":       producto_n,
                "presentacion":   presentacion_n,
                "precio_sem_ant": precio_ant,
                "precio_sem_act": precio_act,
                "variacion_abs":  var_abs,
                "variacion_pct":  var_pct,
                "fuente_act":     fuente_a,
                "fuente_ant":     fuente_b,
                "disponible":     True,
            })

    df_clave_calc = pd.DataFrame(rows)
    df_clave_disp = df_clave_calc[df_clave_calc["disponible"]].copy()
    n_no_disp     = int((~df_clave_calc["disponible"]).sum())

    if df_clave_disp.empty:
        st.warning(
            f"Ninguno de los {len(canasta)} productos de la canasta tiene precio en ambas semanas "
            f"({sa_lbl_l} y {sc_lbl_l})."
        )
        if n_no_disp > 0:
            with st.expander(f"Ver productos sin datos completos ({n_no_disp})"):
                no_disp_view = df_clave_calc[~df_clave_calc["disponible"]][
                    ["producto", "presentacion", "fuente_ant", "fuente_act"]
                ].rename(columns={
                    "fuente_ant": f"Fuente {sc_lbl}",
                    "fuente_act": f"Fuente {sa_lbl}",
                })
                st.dataframe(light_df(no_disp_view), use_container_width=True, hide_index=True)
        return

    f1, f2 = st.columns(2)
    with f1:
        solo_cambios_clave = st.checkbox("Solo productos con cambio", value=False, key="clave_cambios")
    with f2:
        orden_clave = st.selectbox(
            "Ordenar por",
            ["Variacion % (mayor a menor)", "Variacion % (menor a mayor)", "Producto A-Z"],
            key="clave_orden"
        )

    df_clave_filt = df_clave_disp.copy()
    if solo_cambios_clave:
        df_clave_filt = df_clave_filt[df_clave_filt["variacion_pct"].abs() > 0.5]

    if orden_clave == "Variacion % (mayor a menor)":
        df_clave_filt = df_clave_filt.sort_values("variacion_pct", ascending=False)
    elif orden_clave == "Variacion % (menor a mayor)":
        df_clave_filt = df_clave_filt.sort_values("variacion_pct", ascending=True)
    else:
        df_clave_filt = df_clave_filt.sort_values("producto")

    subidas_clave  = int((df_clave_filt["variacion_pct"] > 0.5).sum())
    bajadas_clave  = int((df_clave_filt["variacion_pct"] < -0.5).sum())
    estables_clave = len(df_clave_filt) - subidas_clave - bajadas_clave

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total productos clave", len(df_clave_filt))
    k2.metric("Subieron", subidas_clave)
    k3.metric("Bajaron",  bajadas_clave)
    k4.metric("Estables", estables_clave)

    if n_no_disp > 0:
        st.caption(
            f"⚠️ {n_no_disp} producto(s) de la canasta no se incluyen porque les faltan datos "
            f"en alguna de las dos semanas seleccionadas."
        )

    st.subheader(
        f"Variacion de precios — Canasta Prioritaria ({sc_lbl} → {sa_lbl})"
    )
    df_graf = df_clave_filt.copy()
    df_graf["etiqueta"] = df_graf["producto"] + " (" + df_graf["presentacion"] + ")"
    df_graf = df_graf.sort_values("variacion_pct")

    colors_clave = [GREEN if v < -0.5 else (RED if v > 0.5 else GRAY)
                    for v in df_graf["variacion_pct"]]

    max_abs = df_graf["variacion_pct"].abs().max()
    if pd.isna(max_abs) or max_abs == 0:
        max_abs = 1
    pad = max_abs * 0.08

    fig_clave = go.Figure(go.Bar(
        x=df_graf["variacion_pct"],
        y=df_graf["etiqueta"],
        orientation="h",
        marker_color=colors_clave,
        customdata=df_graf[["precio_sem_ant", "precio_sem_act", "variacion_abs", "fuente_ant", "fuente_act"]].values,
        hovertemplate=(
            "<b>%{y}</b><br>"
            f"Precio {sc_lbl_l} (%{{customdata[3]}}): RD$ %{{customdata[0]:,.2f}}<br>"
            f"Precio {sa_lbl_l} (%{{customdata[4]}}): RD$ %{{customdata[1]:,.2f}}<br>"
            "Variacion RD$: %{customdata[2]:+,.2f}<br>"
            "Variacion %: %{x:+.2f}%<br>"
            "<extra></extra>"
        )
    ))

    annotations = []
    for _, row in df_graf.iterrows():
        v = row["variacion_pct"]
        label = (
            f"{fmt_pct(v)}  RD$ {row['precio_sem_act']:,.0f}  "
            f"(ant: RD$ {row['precio_sem_ant']:,.0f})"
        )
        if v >= 0:
            x_pos, xanchor = v + pad, "left"
        else:
            x_pos, xanchor = v - pad, "right"
        annotations.append(dict(
            x=x_pos, y=row["etiqueta"],
            text=label,
            xanchor=xanchor, yanchor="middle",
            showarrow=False,
            font=dict(size=11, color=TEXT_SECONDARY, family="Inter")
        ))

    fig_clave.update_layout(
        title=dict(
            text=f"Canasta Prioritaria — {sc_lbl} → {sa_lbl}",
            font=dict(size=16, color=TEXT_MAIN, family="Inter"), x=0
        ),
        annotations=annotations,
        height=max(650, len(df_graf) * 42),
        bargap=0.25,
        xaxis_title="Variacion %", yaxis_title="",
        margin=dict(l=10, r=350, t=70, b=40),
        xaxis=dict(
            zeroline=True, zerolinecolor="rgba(248,250,252,0.45)", zerolinewidth=2,
            showgrid=True, gridcolor="rgba(148,163,184,0.14)",
            range=[-(max_abs * 1.05), max_abs * 1.05]
        ),
        yaxis=dict(tickfont=dict(size=12, color=TEXT_SECONDARY))
    )
    apply_dark_layout(fig_clave)
    st.plotly_chart(fig_clave, use_container_width=True)

    st.subheader("Tabla de productos clave")
    display_clave = df_clave_filt[[
        "producto", "presentacion",
        "precio_sem_ant", "precio_sem_act",
        "variacion_abs", "variacion_pct",
        "fuente_ant", "fuente_act"
    ]].copy()
    display_clave.columns = [
        "Producto", "Presentacion",
        f"Precio {sc_lbl}", f"Precio {sa_lbl}",
        "Variacion RD$", "Variacion %",
        f"Fuente {sc_lbl}", f"Fuente {sa_lbl}"
    ]
    display_clave[f"Precio {sc_lbl}"] = display_clave[f"Precio {sc_lbl}"].apply(fmt_rdp)
    display_clave[f"Precio {sa_lbl}"] = display_clave[f"Precio {sa_lbl}"].apply(fmt_rdp)
    display_clave["Variacion RD$"]     = display_clave["Variacion RD$"].apply(lambda x: f"RD$ {x:+,.2f}")
    display_clave["Variacion %"]       = display_clave["Variacion %"].apply(fmt_pct)
    st.caption(f"📅 {sc_lbl_l} → {sa_lbl_l}")
    st.dataframe(light_df(display_clave), use_container_width=True, hide_index=True)
