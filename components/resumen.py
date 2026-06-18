import streamlit as st
import pandas as pd
from datetime import datetime

from styles.theme import BLUE, GREEN, RED, YELLOW
from utils.dates import fmt_sem
from utils.formatting import fmt_rdp


def render_header(semana_actual, semana_comp, registros, promedio, fuente_actual,
                  producto_sel=None, presentacion_sel=None, promedio_comp=None):
    updated    = datetime.now().strftime("%d/%m/%Y %I:%M %p")
    fuente_txt = fuente_actual.upper() if fuente_actual else "N/D"
    sem_act    = fmt_sem(semana_actual, "corta") if semana_actual else "N/D"
    sem_cmp    = fmt_sem(semana_comp,   "corta") if semana_comp   else "N/D"

    promedio_txt = fmt_rdp(promedio) if (promedio is not None and not pd.isna(promedio)) else "N/D"

    if (promedio is not None and not pd.isna(promedio) and
            promedio_comp is not None and not pd.isna(promedio_comp) and promedio_comp != 0):
        var_abs   = promedio - promedio_comp
        var_pct   = var_abs / promedio_comp * 100
        signo     = "+" if var_abs > 0 else ("-" if var_abs < 0 else "")
        color_var = RED if var_abs > 0 else (GREEN if var_abs < 0 else "var(--text-muted)")
        var_html  = (
            '<span style="color:' + color_var + ';font-size:0.95rem;font-weight:700;">'
            + signo + " " + fmt_rdp(abs(var_abs)) + " (" + f"{var_pct:+.1f}%" + ")"
            + "</span>"
        )
        comp_precio_txt = fmt_rdp(promedio_comp)
    else:
        var_html        = '<span style="color:var(--text-muted);font-size:0.88rem;">Sin dato comparado</span>'
        comp_precio_txt = "N/D"

    if producto_sel:
        prod_label  = producto_sel
        pres_label  = presentacion_sel or "Todas las presentaciones"
        nota_precio = pres_label
    else:
        prod_label  = "Todos los productos"
        pres_label  = ""
        nota_precio = "promedio general"

    html = (
        '<div class="premium-header">'

        '<div style="display:flex;justify-content:space-between;gap:1rem;'
        'align-items:flex-start;flex-wrap:wrap;">'
        '<div>'
        '<div class="header-title">Visualizacion de Datos - Supermercados Santo Domingo</div>'
        '</div>'
        '<div style="text-align:right;color:var(--text-muted);font-size:.86rem;">'
        'Semana actual: <b style="color:var(--text-primary);">' + sem_act + '</b><br>'
        'Actualizado: <b style="color:var(--text-primary);">' + updated + '</b>'
        '</div>'
        '</div>'

        '<div style="display:grid;grid-template-columns:repeat(4,minmax(150px,1fr));'
        'gap:.8rem;margin-top:1rem;">'

        '<div class="kpi-card kpi-blue">'
        '<div class="kpi-label">Semana actual</div>'
        '<div class="kpi-value">' + sem_act + '</div>'
        '<div class="kpi-note">Fuente: ' + fuente_txt + '</div>'
        '</div>'

        '<div class="kpi-card kpi-green">'
        '<div class="kpi-label">Producto seleccionado</div>'
        '<div class="kpi-value" style="font-size:1.05rem;line-height:1.3;">'
        + prod_label +
        '</div>'
        '<div class="kpi-note">' + pres_label + '</div>'
        '</div>'

        '<div class="kpi-card kpi-yellow">'
        '<div class="kpi-label">Precio promedio - ' + sem_act + '</div>'
        '<div class="kpi-value">' + promedio_txt + '</div>'
        '<div class="kpi-note">' + nota_precio + '</div>'
        '<div style="margin-top:.4rem;">' + var_html + '</div>'
        '</div>'

        '<div class="kpi-card kpi-red">'
        '<div class="kpi-label">Precio promedio - ' + sem_cmp + '</div>'
        '<div class="kpi-value">' + comp_precio_txt + '</div>'
        '<div class="kpi-note">base comparada</div>'
        '</div>'

        '</div>'
        '</div>'
    )

    st.markdown(html, unsafe_allow_html=True)


def render_franja_compacta(sa_lbl, sc_lbl, prod_label, promedio, promedio_comp, fuente_actual):
    """Franja compacta de una linea -- siempre visible en todas las pestanas."""
    var_txt   = "N/D"
    color_var = "var(--text-muted)"
    if (promedio is not None and not pd.isna(promedio)
            and promedio_comp is not None and not pd.isna(promedio_comp)
            and promedio_comp != 0):
        var_pct   = (promedio - promedio_comp) / promedio_comp * 100
        var_txt   = f"{var_pct:+.1f}%"
        color_var = RED if var_pct > 0 else (GREEN if var_pct < 0 else "var(--text-muted)")

    fuente_badge = (
        f' <span style="background:rgba(245,158,11,0.18);color:{YELLOW};'
        f'font-size:.68rem;font-weight:700;padding:.05rem .38rem;border-radius:5px;'
        f'border:1px solid rgba(245,158,11,0.35);vertical-align:middle;">BRUTO</span>'
        if fuente_actual == "bruto" else ""
    )

    st.markdown(
        f'<div style="padding:.42rem 1rem;border-radius:12px;'
        f'background:var(--glass-bg);border:1px solid var(--border-soft);'
        f'margin-bottom:.55rem;font-size:.81rem;color:var(--text-muted);'
        f'display:flex;flex-wrap:wrap;gap:.25rem .55rem;align-items:center;">'
        f'<span>Actual: <b style="color:var(--text-primary);">{sa_lbl}</b>{fuente_badge}</span>'
        f'<span style="opacity:.3;">·</span>'
        f'<span>Comparada: <b style="color:var(--text-primary);">{sc_lbl}</b></span>'
        f'<span style="opacity:.3;">·</span>'
        f'<span>Producto: <b style="color:var(--text-primary);">{prod_label}</b></span>'
        f'<span style="opacity:.3;">·</span>'
        f'<span>Variación: <b style="color:{color_var};">{var_txt}</b></span>'
        f'</div>',
        unsafe_allow_html=True
    )


def render_resumen_general(semana_actual, semana_comp, registros, promedio,
                           fuente_actual, producto_sel, presentacion_sel, promedio_comp):
    """Panel detallado de resumen -- disenado para usarse dentro de un st.expander."""
    sa_lbl   = fmt_sem(semana_actual, "corta") if semana_actual else "N/D"
    sc_lbl   = fmt_sem(semana_comp,   "corta") if semana_comp   else "N/D"
    sa_lbl_l = fmt_sem(semana_actual, "larga") if semana_actual else "N/D"
    sc_lbl_l = fmt_sem(semana_comp,   "larga") if semana_comp   else "N/D"

    fuente_txt = fuente_actual.upper() if fuente_actual else "N/D"
    prod_label = producto_sel or "Todos los productos"
    pres_label = (
        presentacion_sel
        if presentacion_sel and presentacion_sel not in ("- Todas -", "Todas las presentaciones")
        else ("Todas las presentaciones" if producto_sel else "Promedio general")
    )
    updated = datetime.now().strftime("%d/%m/%Y %I:%M %p")

    promedio_txt = fmt_rdp(promedio) if (promedio is not None and not pd.isna(promedio)) else "N/D"
    comp_txt     = fmt_rdp(promedio_comp) if (promedio_comp is not None and not pd.isna(promedio_comp)) else "N/D"

    var_abs = var_pct = delta_rdp = delta_pct = None
    if (promedio is not None and not pd.isna(promedio)
            and promedio_comp is not None and not pd.isna(promedio_comp)
            and promedio_comp != 0):
        var_abs   = promedio - promedio_comp
        var_pct   = var_abs / promedio_comp * 100
        delta_rdp = f"{'+' if var_abs >= 0 else ''}{fmt_rdp(var_abs)}"
        delta_pct = f"{var_pct:+.1f}%"

    r1, r2, r3, r4 = st.columns(4)
    r1.metric(
        "Semana actual",
        sa_lbl,
        help=f"Rango principal de analisis: {sa_lbl_l}. Fuente: {fuente_txt}."
    )
    r2.metric(
        "Semana comparada",
        sc_lbl,
        help=f"Rango usado como base de comparacion: {sc_lbl_l}."
    )
    r3.metric(
        "Producto seleccionado",
        prod_label,
        help=f"Filtro aplicado actualmente. Presentacion: {pres_label}."
    )
    r4.metric(
        "Registros actuales",
        f"{registros:,}",
        help="Cantidad de registros incluidos en el calculo segun los filtros aplicados."
    )

    st.markdown("<div style='margin:.4rem 0'></div>", unsafe_allow_html=True)

    s1, s2, s3, s4 = st.columns(4)
    s1.metric(
        "Precio prom. actual",
        promedio_txt,
        delta=delta_pct,
        help=f"Promedio en la semana seleccionada ({sa_lbl_l}). Calculado segun los filtros aplicados."
    )
    s2.metric(
        "Precio prom. base",
        comp_txt,
        help=f"Promedio de la semana comparada ({sc_lbl_l}). Sirve como base de comparacion."
    )
    s3.metric(
        "Variacion RD$",
        fmt_rdp(abs(var_abs)) if var_abs is not None else "N/D",
        delta=delta_rdp,
        help="Cambio absoluto en pesos dominicanos frente a la semana comparada."
    )
    s4.metric(
        "Fuente de datos",
        fuente_txt,
        help="Bruto = reporte semanal sin validar. Validado = historial oficial procesado."
    )

    notas = [f"Actualizado: {updated}", "Calculado segun los filtros aplicados"]
    if fuente_actual == "bruto":
        notas.append(f"Semana actual ({sa_lbl_l}) usa datos brutos")
    st.caption("  ·  ".join(notas))
