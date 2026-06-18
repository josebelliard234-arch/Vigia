import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

from styles.theme import TEXT_MAIN, TEXT_SECONDARY, BLUE, RED, YELLOW, GREEN
from utils.dates import fmt_sem, semana_label_a_datetime, ordenar_semanas_iso
from utils.formatting import fmt_rdp, fmt_pct
from utils.transformations import proyeccion_despues_de_semana_corte
from data.loader import parsear_fecha_usuario
from components.charts import plot_bg, _is_light as _chart_light
_MESES    = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
             "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]


def _mes_label(sem):
    dt = semana_label_a_datetime(sem)
    return f"{_MESES[dt.month-1]} {dt.year}" if dt else sem


def _tickvals_limpios(all_x):
    """Devuelve un subconjunto de ticks para no saturar el eje X."""
    if len(all_x) <= 18:
        return all_x
    step = max(1, len(all_x) // 12)
    tv = all_x[::step]
    if all_x[0] not in tv:
        tv = [all_x[0]] + tv
    if all_x[-1] not in tv:
        tv = tv + [all_x[-1]]
    return tv


def render_historial(ctx):
    df_validado   = ctx.df_validado
    df_bruto      = ctx.df_bruto
    cat_sel       = ctx.cat_sel
    semana_actual = ctx.semana_actual

    st.subheader("Historial de precios y proyeccion")
    st.caption("Basado en datos validados.")

    if df_validado.empty:
        st.info("Carga el historial validado para ver esta seccion.")
        return

    df_val_filt = df_validado.copy()
    if cat_sel != "Todas":
        df_val_filt = df_val_filt[df_val_filt["categoria"] == cat_sel]

    productos_disp = sorted(df_val_filt["producto"].unique())
    if not productos_disp:
        st.info("No hay productos disponibles para la categoria seleccionada.")
        return

    prod_sel = st.selectbox("Selecciona un producto", productos_disp)
    presentaciones_disp = sorted(
        df_val_filt[df_val_filt["producto"] == prod_sel]["presentacion"].unique()
    )
    pres_sel = st.selectbox("Presentacion", presentaciones_disp)

    # ── Filtro de rango de fechas ────────────────────────────
    _sems_prod_todas = sorted(df_val_filt[
        (df_val_filt["producto"] == prod_sel) &
        (df_val_filt["presentacion"] == pres_sel)
    ]["semana"].unique())

    _fecha_min_dato = semana_label_a_datetime(_sems_prod_todas[0])  if _sems_prod_todas else None
    _fecha_max_dato = semana_label_a_datetime(_sems_prod_todas[-1]) if _sems_prod_todas else None

    with st.expander("Filtrar rango de fechas", expanded=False):
        st.caption(
            "Escribe las fechas en formato DD/MM/AA o DD/MM/AAAA "
            "(ej: 2/5/26, 02/05/2026). "
            + (f"Rango disponible: {_sems_prod_todas[0]} al {_sems_prod_todas[-1]}"
               if _sems_prod_todas else "")
        )
        _rf1, _rf2 = st.columns(2)
        with _rf1:
            _desde_str = st.text_input(
                "Desde (DD/MM/AA)",
                value=_fecha_min_dato.strftime("%d/%m/%y") if _fecha_min_dato else "",
                key="hist_desde", placeholder="ej: 01/01/25",
            )
            _cal_desde = st.date_input(
                "O elige en calendario",
                value=_fecha_min_dato if _fecha_min_dato else datetime(2024, 1, 1),
                key="hist_cal_desde", format="DD/MM/YYYY",
            )
        with _rf2:
            _hasta_str = st.text_input(
                "Hasta (DD/MM/AA)",
                value=_fecha_max_dato.strftime("%d/%m/%y") if _fecha_max_dato else "",
                key="hist_hasta", placeholder="ej: 31/12/26",
            )
            _cal_hasta = st.date_input(
                "O elige en calendario",
                value=_fecha_max_dato if _fecha_max_dato else datetime.today(),
                key="hist_cal_hasta", format="DD/MM/YYYY",
            )

        _fecha_desde = parsear_fecha_usuario(_desde_str) if _desde_str.strip() else None
        _fecha_hasta = parsear_fecha_usuario(_hasta_str) if _hasta_str.strip() else None
        if _fecha_desde is None:
            _fecha_desde = datetime(_cal_desde.year, _cal_desde.month, _cal_desde.day)
        if _fecha_hasta is None:
            _fecha_hasta = datetime(_cal_hasta.year, _cal_hasta.month, _cal_hasta.day)

        if _fecha_desde > _fecha_hasta:
            st.warning("La fecha de inicio es posterior a la fecha de fin.")
            _fecha_desde, _fecha_hasta = _fecha_hasta, _fecha_desde

        st.caption(
            f"Rango seleccionado: {_fecha_desde.strftime('%d/%m/%Y')} "
            f"al {_fecha_hasta.strftime('%d/%m/%Y')}"
        )

    def _semana_en_rango(lbl, desde, hasta):
        dt = semana_label_a_datetime(lbl)
        return (desde <= dt <= hasta) if dt else True

    df_prod = df_val_filt[
        (df_val_filt["producto"] == prod_sel) &
        (df_val_filt["presentacion"] == pres_sel)
    ].sort_values("semana")
    df_prod = df_prod[
        df_prod["semana"].apply(lambda s: _semana_en_rango(s, _fecha_desde, _fecha_hasta))
    ]

    n_proj = st.slider("Semanas a proyectar", 1, 8, 4)

    if df_prod.empty:
        st.info("No hay datos para el rango de fechas seleccionado.")
        return

    # ── Controles de visualizacion ───────────────────────────
    vc1, vc2, vc3 = st.columns([1.4, 2.2, 1.4])
    with vc1:
        mostrar_proyeccion = st.toggle("Mostrar proyeccion", value=True, key="hist_proj")
    with vc2:
        modo_grafica = st.radio(
            "Tipo de vista", ["Normal", "Suavizada"],
            horizontal=True, key="hist_modo",
        )
    with vc3:
        mostrar_picos = st.toggle("Picos mensuales", value=False, key="hist_picos")

    # ── Datos base ───────────────────────────────────────────
    sems    = df_prod["semana"].tolist()
    precios = df_prod["precio"].tolist()

    sem_bruta   = None
    precio_prom = None
    if not df_bruto.empty:
        df_b = df_bruto[
            (df_bruto["producto"] == prod_sel) &
            (df_bruto["presentacion"] == pres_sel) &
            (df_bruto["semana"] == semana_actual)
        ]
        if not df_b.empty:
            precio_prom = df_b["precio"].mean()
            sem_bruta   = semana_actual

    fut_labels, fut_prices = [], []
    if len(sems) >= 4 and mostrar_proyeccion:
        fut_labels, fut_prices = proyeccion_despues_de_semana_corte(
            sems, precios, n_proj, sem_bruta
        )

    # ── Eje X ────────────────────────────────────────────────
    all_x     = ordenar_semanas_iso(sems + fut_labels + ([sem_bruta] if sem_bruta else []))
    tickvals  = _tickvals_limpios(all_x)
    tick_text = [fmt_sem(v, "corta") for v in tickvals]

    # ── Forma de línea ───────────────────────────────────────
    suavizar  = modo_grafica == "Suavizada"
    l_shape   = "spline" if suavizar else "linear"
    l_smooth  = 0.8      if suavizar else 1.0

    # ── Figura ───────────────────────────────────────────────
    fig = go.Figure()

    # Trace 1 — Histórico validado (sin etiquetas en todos los puntos)
    fig.add_trace(go.Scatter(
        x=sems,
        y=precios,
        mode="lines+markers",
        name="Historico validado",
        line=dict(color=BLUE, width=2.5, shape=l_shape, smoothing=l_smooth),
        marker=dict(size=5, color=BLUE, opacity=0.85),
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Precio promedio: <b>RD$ %{y:,.2f}</b><br>"
            f"Producto: {prod_sel}<br>"
            f"Presentacion: {pres_sel}<br>"
            "Serie: Historico validado"
            "<extra></extra>"
        ),
    ))

    # Trace 2 — Proyección (solo etiqueta en el último punto)
    if fut_labels:
        proj_text        = [""] * len(fut_labels)
        proj_text[-1]    = f"RD$ {fut_prices[-1]:,.0f}"
        fig.add_trace(go.Scatter(
            x=fut_labels,
            y=fut_prices,
            mode="lines+markers+text",
            name="Proyeccion (reg. lineal)",
            line=dict(color=RED, width=2, dash="dot", shape=l_shape, smoothing=l_smooth),
            marker=dict(size=8, color=RED, symbol="diamond"),
            text=proj_text,
            textposition="top center",
            textfont=dict(size=11, color=RED, family="Inter"),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Proyeccion: <b>RD$ %{y:,.2f}</b><br>"
                "Metodo: Regresion lineal<br>"
                "<i>No es dato real</i>"
                "<extra></extra>"
            ),
        ))

    # Trace 3 — Dato bruto actual (estrella destacada + una etiqueta)
    if sem_bruta is not None:
        fig.add_trace(go.Scatter(
            x=[sem_bruta],
            y=[precio_prom],
            mode="markers+text",
            name=f"Semana actual ({fmt_sem(sem_bruta, 'corta')}) — bruto",
            marker=dict(size=14, color=YELLOW, symbol="star",
                        line=dict(width=1.5, color="#FFF")),
            text=[f"RD$ {precio_prom:,.0f}"],
            textposition="top right",
            textfont=dict(size=12, color=YELLOW, family="Inter"),
            hovertemplate=(
                f"<b>Semana actual: {fmt_sem(sem_bruta, 'larga')}</b><br>"
                f"Precio promedio bruto: <b>RD$ {precio_prom:,.2f}</b><br>"
                f"Producto: {prod_sel}<br>"
                f"Presentacion: {pres_sel}<br>"
                "<i>Dato bruto — pendiente de validacion</i>"
                "<extra></extra>"
            ),
        ))

    # Traces 4 & 5 — Picos mensuales
    if mostrar_picos and len(sems) > 1:
        df_p = pd.DataFrame({"semana": sems, "precio": precios})
        df_p["fecha_dt"] = df_p["semana"].apply(semana_label_a_datetime)
        df_p = df_p.dropna(subset=["fecha_dt"])
        if not df_p.empty:
            df_p["mes"] = df_p["fecha_dt"].dt.to_period("M").astype(str)
            df_max = df_p.loc[df_p.groupby("mes")["precio"].idxmax()].copy()
            df_min = df_p.loc[df_p.groupby("mes")["precio"].idxmin()].copy()

            # Pico máximo — triángulo verde arriba
            fig.add_trace(go.Scatter(
                x=df_max["semana"].tolist(),
                y=df_max["precio"].tolist(),
                mode="markers",
                name="Maximo mensual",
                marker=dict(size=11, color=GREEN, symbol="triangle-up",
                            line=dict(width=1.2, color="#FFF")),
                customdata=[[_mes_label(s)] for s in df_max["semana"].tolist()],
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    "Maximo de <b>%{customdata[0]}</b><br>"
                    f"Producto: {prod_sel}<br>"
                    "Precio maximo mensual: <b>RD$ %{y:,.2f}</b>"
                    "<extra></extra>"
                ),
            ))

            # Pico mínimo — triángulo naranja abajo
            fig.add_trace(go.Scatter(
                x=df_min["semana"].tolist(),
                y=df_min["precio"].tolist(),
                mode="markers",
                name="Minimo mensual",
                marker=dict(size=11, color="#D97706", symbol="triangle-down",
                            line=dict(width=1.2, color="#FFF")),
                customdata=[[_mes_label(s)] for s in df_min["semana"].tolist()],
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    "Minimo de <b>%{customdata[0]}</b><br>"
                    f"Producto: {prod_sel}<br>"
                    "Precio minimo mensual: <b>RD$ %{y:,.2f}</b>"
                    "<extra></extra>"
                ),
            ))

    # ── Layout ───────────────────────────────────────────────
    fig.update_layout(
        template="plotly_dark",
        title=dict(
            text=f"Historico — {prod_sel} | {pres_sel}",
            font=dict(size=16, color=TEXT_MAIN, family="Inter"),
            x=0,
        ),
        height=580,
        hovermode="x unified",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.22,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=12, color=TEXT_SECONDARY),
        ),
        margin=dict(l=70, r=40, t=70, b=145),
        plot_bgcolor=plot_bg(1.0),
        paper_bgcolor=plot_bg(0.0),
        font=dict(color=TEXT_SECONDARY, family="Inter"),
        hoverlabel=dict(bgcolor=plot_bg(0.9), font_size=12, font_family="Inter"),
        uirevision=f"{prod_sel}_{pres_sel}",
    )

    fig.update_xaxes(
        tickmode="array",
        tickvals=tickvals,
        ticktext=tick_text,
        tickangle=-45,
        tickfont=dict(size=10, color=TEXT_SECONDARY),
        showgrid=False,
        categoryorder="array",
        categoryarray=all_x,
    )

    fig.update_yaxes(
        title="Precio promedio (RD$)",
        tickprefix="RD$ ",
        tickformat=",.0f",
        gridcolor="rgba(15,23,42,0.08)" if _chart_light() else "rgba(148,163,184,0.18)",
        zeroline=False,
        tickfont=dict(size=10, color=TEXT_SECONDARY),
    )

    st.plotly_chart(fig, use_container_width=True, config={
        "displayModeBar": True,
        "responsive": True,
        "displaylogo": False,
        "modeBarButtonsToRemove": ["select2d", "lasso2d"],
    })

    # ── Tabla de proyección (siempre calcula, independiente del toggle) ──
    if len(sems) >= 4:
        st.subheader("Tabla de proyeccion")
        ultimo  = precios[-1]
        fut_l, fut_p = proyeccion_despues_de_semana_corte(sems, precios, n_proj, sem_bruta)
        proj_rows = [{
            "Semana proyectada":    lbl,
            "Precio estimado":      fmt_rdp(pr),
            "Variacion vs ultimo":  fmt_pct((pr - ultimo) / ultimo * 100),
        } for lbl, pr in zip(fut_l, fut_p)]
        st.dataframe(pd.DataFrame(proj_rows), use_container_width=True, hide_index=True)
