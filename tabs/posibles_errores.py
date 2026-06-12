import streamlit as st
import plotly.graph_objects as go

from styles.theme import (
    TEXT_MAIN, TEXT_SECONDARY,
    GREEN, RED,
)
from utils.formatting import fmt_rdp, fmt_pct, nivel_alerta
from utils.transformations import cruzar_semanas
from components.charts import apply_dark_layout


def render_posibles_errores(ctx):
    df_actual  = ctx.df_actual
    df_comp    = ctx.df_comp
    sa_lbl     = ctx.sa_lbl
    sc_lbl     = ctx.sc_lbl
    sa_lbl_l   = ctx.sa_lbl_l
    sc_lbl_l   = ctx.sc_lbl_l

    st.subheader("Posibles errores de digitacion")
    st.caption("Compara los datos brutos actuales contra el precio validado de la semana comparada.")

    if df_actual.empty or df_comp.empty:
        st.info("Necesitas el historial validado y el reporte semanal actual.")
        return

    merged_err = cruzar_semanas(df_actual, df_comp)
    if merged_err.empty:
        st.warning("No hay productos en comun entre las dos semanas para evaluar.")
        return

    merged_err = merged_err.rename(columns={
        "precio_actual": "precio_actual",
        "precio_comp":   "precio_validado",
    })
    merged_err["variacion_pct"] = (
        (merged_err["precio_actual"] - merged_err["precio_validado"]) /
        merged_err["precio_validado"] * 100
    ).round(1)

    umbral = st.number_input(
        "Umbral de alerta (%)",
        min_value=3.00,
        value=10.00,
        step=0.25,
        format="%.2f",
        help="Se marcaran como posibles errores las variaciones iguales o superiores a este porcentaje. Minimo permitido: 3%.",
        key="umbral_error"
    )
    errores = merged_err[merged_err["variacion_pct"].abs() >= umbral].copy()

    if errores.empty:
        st.success(f"No se detectaron variaciones >= {umbral:.2f}% vs el precio validado.")
        return

    errores["Alerta"] = errores["variacion_pct"].apply(
        lambda v: nivel_alerta(v, umbral, umbral * 1.7, umbral * 2.8)
    )

    e1, e2, e3 = st.columns(3)
    e1.metric("Total detectados",   len(errores))
    e2.metric("CRITICO", len(errores[errores["Alerta"] == "CRITICO"]))
    e3.metric("ALTO",    len(errores[errores["Alerta"] == "ALTO"]))

    display_err = errores[[
        "Alerta", "categoria", "producto", "presentacion",
        "provincia", "supermercado",
        "precio_validado", "precio_actual", "variacion_pct"
    ]].copy()
    display_err.columns = [
        "Alerta", "Categoria", "Producto", "Presentacion",
        "Provincia", "Supermercado",
        f"Precio validado {sc_lbl}",
        f"Precio actual {sa_lbl}",
        "Variacion %"
    ]
    display_err[f"Precio validado {sc_lbl}"] = display_err[f"Precio validado {sc_lbl}"].apply(fmt_rdp)
    display_err[f"Precio actual {sa_lbl}"]   = display_err[f"Precio actual {sa_lbl}"].apply(fmt_rdp)
    display_err["Variacion %"]                = display_err["Variacion %"].apply(fmt_pct)

    st.caption(f"📅 Precio actual {sa_lbl_l} · Referencia validada {sc_lbl_l}   |   Umbral aplicado: ±{umbral:.2f}%")
    st.dataframe(
        display_err.sort_values("Variacion %", ascending=False),
        use_container_width=True, hide_index=True
    )

    # Grafico
    graf_err = errores.copy()
    graf_err["etiqueta"] = (
        graf_err["producto"] + " | " +
        graf_err["presentacion"] + " | " +
        graf_err["supermercado"].astype(str)
    )
    graf_err   = graf_err.sort_values("variacion_pct")
    colors_err = [GREEN if v < 0 else RED for v in graf_err["variacion_pct"]]
    fig_err = go.Figure(go.Bar(
        x=graf_err["variacion_pct"],
        y=graf_err["etiqueta"],
        orientation="h",
        marker_color=colors_err,
        customdata=graf_err[["precio_validado", "precio_actual", "supermercado", "Alerta"]].values,
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Supermercado: %{customdata[2]}<br>"
            f"Precio validado ({sc_lbl_l}): RD$ %{{customdata[0]:,.2f}}<br>"
            f"Precio actual ({sa_lbl_l}): RD$ %{{customdata[1]:,.2f}}<br>"
            "Variacion: %{x:+.1f}%<br>"
            "Nivel: %{customdata[3]}<br>"
            "<extra></extra>"
        )
    ))
    max_abs_e = graf_err["variacion_pct"].abs().max()
    pad_e = max_abs_e * 0.06 if max_abs_e else 1
    ann_e = []
    for _, row in graf_err.iterrows():
        v = row["variacion_pct"]
        label = f"{fmt_pct(v)}  |  {row['Alerta']}  |  RD$ {row['precio_actual']:,.0f}"
        if v >= 0:
            x_pos, xanchor = v + pad_e, "left"
        else:
            x_pos, xanchor = v - pad_e, "right"
        ann_e.append(dict(
            x=x_pos, y=row["etiqueta"], text=label,
            xanchor=xanchor, yanchor="middle",
            showarrow=False, font=dict(size=10, color=TEXT_SECONDARY, family="Inter")
        ))
    fig_err.update_layout(
        title=dict(
            text=f"Posibles errores — {sa_lbl} vs {sc_lbl} | Umbral: >={umbral:.2f}%",
            font=dict(size=13, color=TEXT_MAIN, family="Inter"), x=0
        ),
        annotations=ann_e,
        height=max(450, len(graf_err) * 40),
        bargap=0.2,
        xaxis_title="Variacion vs precio validado %", yaxis_title="",
        margin=dict(l=10, r=350, t=60, b=40),
        xaxis=dict(
            zeroline=True, zerolinecolor="rgba(248,250,252,0.45)", zerolinewidth=2,
            range=[-(max_abs_e * 1.05), max_abs_e * 1.05] if max_abs_e else [-1, 1]
        ),
        yaxis=dict(tickfont=dict(size=11, color=TEXT_SECONDARY))
    )
    apply_dark_layout(fig_err)
    st.plotly_chart(fig_err, use_container_width=True)
