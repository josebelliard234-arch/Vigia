# ============================================================
# IMPORTS
# ============================================================
import streamlit as st
import pandas as pd
import os
import re
from types import SimpleNamespace

try:
    from streamlit_option_menu import option_menu
except Exception:
    option_menu = None


# ============================================================
# CONFIGURACION DE LA PAGINA  (debe ir PRIMERO)
# ============================================================
st.set_page_config(
    page_title="Monitor de Precios | DOSAC",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# IMPORTS DE MODULOS PROPIOS
# ============================================================
from styles.theme import (
    BG_MAIN, BG_SECONDARY, CARD_BG, CARD_ELEVATED,
    TEXT_MAIN, TEXT_SECONDARY, TEXT_MUTED,
    BLUE, GREEN, RED, YELLOW, GRAY,
)
from styles.custom_css import apply_css

from sqlalchemy import text
from data.database import (
    DEMO_MODE, get_conn,
    init_db,
    save_to_db, save_supermercado_to_db, save_productos_clave_to_db,
    load_all, load_supermercado, load_productos_clave,
    semanas_en_db, count_validados, semanas_validadas,
    count_supermercado, count_productos_clave,
    registrar_monitoreo_cargado, load_monitoreos_cargados,
    eliminar_monitoreo_cargado, wipe_db, log_action,
)
from data.loader import (
    parse_excel_bruto, parse_historial_validado,
    parse_resumen_supermercado, parse_tabla21,
    parse_week_label, extraer_fechas_monitoreo,
)

from utils.dates import fmt_sem, semana_label_a_datetime
from utils.formatting import norm_key
from utils.transformations import resolver_semana

from tabs.inicio import render_inicio

from tabs.comparativa      import render_comparativa
from tabs.historial        import render_historial
from tabs.por_supermercado import render_por_supermercado
from tabs.productos_clave  import render_productos_clave
from tabs.posibles_errores import render_posibles_errores
from tabs.usuarios         import render_usuarios
from tabs.archivos_cargados import render_archivos_cargados
from tabs.edicion_datos    import render_edicion_datos
from tabs.simulacion       import render_simulacion
from tabs.alertas          import render_alertas
from tabs.auditoria        import render_auditoria

from auth.auth import (
    init_auth_db, require_login, render_sidebar_user,
    is_admin,
)


# ============================================================
# CSS + INICIALIZACION
# ============================================================
apply_css()
init_db()
init_auth_db()

# ============================================================
# GUARD DE LOGIN  — si no autenticado, muestra form y detiene
# ============================================================
require_login()

# A partir de aqui el usuario esta autenticado
_es_admin  = is_admin()


# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:

    render_sidebar_user()

    st.markdown("### 📊 Centro de Control")
    if DEMO_MODE:
        st.info("Modo demo: datos precargados. Carga, eliminacion y limpieza desactivadas.")

    # ---- Menu de navegacion segun rol ----
    if _es_admin:
        _nav_options = [
            "Inicio",
            "Comparativa de Precios",
            "Historial y Proyeccion",
            "Por Supermercado",
            "Productos Clave",
            "Posibles Errores",
            "Alertas",
            "Archivos Cargados",
            "Edicion de Datos",
            "Administracion de Usuarios",
            "Auditoria",
        ]
        _nav_icons = [
            "speedometer2",
            "bar-chart-line", "graph-up-arrow", "shop", "stars",
            "exclamation-triangle", "bell", "folder2-open",
            "pencil-square", "people", "shield-check",
        ]
    else:
        _nav_options = [
            "Inicio",
            "Comparativa de Precios",
            "Historial y Proyeccion",
            "Por Supermercado",
            "Productos Clave",
            "Posibles Errores",
            "Simulacion Temporal",
        ]
        _nav_icons = [
            "speedometer2",
            "bar-chart-line", "graph-up-arrow", "shop", "stars",
            "exclamation-triangle", "sliders",
        ]

    if option_menu:
        section = option_menu(
            menu_title=None,
            options=_nav_options,
            icons=_nav_icons,
            default_index=0,
            styles={
                "container":       {"padding": "0!important", "background-color": "transparent"},
                "icon":            {"color": "#94A3B8", "font-size": "16px"},
                "nav-link":        {"font-size": "13px", "text-align": "left", "margin": "4px 0",
                                    "border-radius": "12px", "color": "#CBD5E1"},
                "nav-link-selected": {"background-color": "#273449", "color": "#F8FAFC",
                                      "font-weight": "700"},
            },
        )
    else:
        section = st.radio(
            "Navegacion",
            _nav_options,
            label_visibility="collapsed",
        )

    st.divider()

    # ---- Secciones administrativas — solo Administrador ----
    if _es_admin:

        # CUADRO 1 — Monitoreo de Supermercados
        st.header("1. Monitoreo de Supermercados")
        st.caption("Sube el archivo de monitoreo semanal.")

        uploaded = st.file_uploader(
            "Archivo de monitoreo .xlsx",
            type=["xlsx"],
            accept_multiple_files=True,
            key="uploader_semanal",
            disabled=DEMO_MODE,
        )
        if uploaded:
            for f in uploaded:
                file_bytes = f.read()
                st.divider()
                st.markdown(f"**{f.name}**")

                fechas_det  = extraer_fechas_monitoreo(file_bytes)
                sem_nombre  = parse_week_label(f.name)
                sem_interna = fechas_det.get("monitoreo")
                if sem_nombre and not re.match(r"\d{4}-W\d{2}", str(sem_nombre)):
                    sem_nombre = None

                st.markdown("**Fechas detectadas:**")
                cN, cI = st.columns(2)
                cN.metric("Por nombre de archivo", sem_nombre or "N/D")
                cI.metric("Por texto interno",     sem_interna or "N/D")

                if sem_nombre and sem_interna and sem_nombre != sem_interna:
                    st.warning(
                        f"Las fechas NO coinciden. Nombre: **{sem_nombre}** | "
                        f"Interno: **{sem_interna}**. Revisa antes de importar."
                    )
                elif sem_nombre and sem_interna and sem_nombre == sem_interna:
                    st.success(f"Ambas fuentes coinciden: {sem_nombre}.")

                valor_defecto    = sem_nombre or sem_interna or ""
                semana_detectada = st.text_input(
                    "Semana (AAAA-Wnn). Edita si es necesario:",
                    value=valor_defecto,
                    key=f"semana_{f.name}",
                )

                with st.expander("Ver textos de fecha dentro del archivo"):
                    st.caption(f"Hoja Monitoreo: {fechas_det.get('monitoreo_txt') or 'N/D'}")
                    st.caption(f"Hoja Comparativa: {fechas_det.get('comparativa_txt') or 'N/D'}")
                    st.caption(f"Hoja Resumen: {fechas_det.get('resumen_txt') or 'N/D'}")

                df_preview = parse_excel_bruto(file_bytes, f.name)
                st.caption(f"{len(df_preview):,} registros encontrados")
                if not df_preview.empty and semana_detectada.strip():
                    if st.button(f"Importar {semana_detectada}", key=f"btn_{f.name}"):
                        sem_final = semana_detectada.strip()
                        df_preview["semana"] = sem_final
                        with get_conn() as con:
                            con.execute(
                                text("DELETE FROM precios WHERE semana=:s AND fuente='bruto'"),
                                {"s": sem_final}
                            )
                        save_to_db(df_preview, fuente="bruto")
                        registrar_monitoreo_cargado(sem_final, f.name, len(df_preview))
                        log_action("UPLOAD", "monitoreo", f"{f.name} · semana={sem_final} · {len(df_preview):,} registros")
                        st.success(f"Importado: {len(df_preview):,} registros")
                        st.rerun()
                elif df_preview.empty:
                    st.warning("No se encontraron datos.")

        # Monitoreos cargados (mini-lista en sidebar)
        monitoreos = load_monitoreos_cargados()
        if monitoreos:
            st.divider()
            st.subheader("Monitoreos cargados")
            for semana_m, nombre_m, fecha_m, registros_m in monitoreos:
                st.markdown(
                    f"<div style='padding:.55rem .7rem;margin-bottom:.5rem;"
                    f"border:1px solid rgba(148,163,184,0.18);border-radius:12px;"
                    f"background:rgba(30,41,59,0.55);'>"
                    f"<div style='font-size:.82rem;color:#F8FAFC;font-weight:600;"
                    f"word-break:break-word;'>{nombre_m or 'Archivo'}</div>"
                    f"<div style='font-size:.92rem;color:#3B82F6;font-weight:700;"
                    f"margin-top:.15rem;'>{fmt_sem(semana_m, 'corta')}</div>"
                    f"<div style='font-size:.72rem;color:#94A3B8;margin-top:.1rem;'>"
                    f"{registros_m:,} registros · {fecha_m}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                if st.button(f"Eliminar {semana_m}", key=f"del_monit_{semana_m}",
                             disabled=DEMO_MODE):
                    eliminar_monitoreo_cargado(semana_m)
                    log_action("DELETE", "monitoreo", f"semana={semana_m} · {nombre_m}")
                    st.rerun()

        st.divider()

        # CUADRO 2 — Herramienta de Informes
        st.header("2. Herramienta de Informes (historial)")
        st.caption("Sube el archivo completo de herramientas.")

        n_val    = count_validados()
        sems_val = semanas_validadas()
        if n_val > 0:
            st.caption(f"Historial: {n_val:,} registros | {len(sems_val)} semanas")
            st.caption(f"{fmt_sem(sems_val[0], 'larga')} → {fmt_sem(sems_val[-1], 'larga')}")
        else:
            st.caption("Sin historial cargado")

        n_sup   = count_supermercado()
        n_clave = count_productos_clave()
        if n_sup > 0:
            st.caption(f"Resumen supermercados: {n_sup:,} registros")
        if n_clave > 0:
            st.caption(f"Productos clave: {n_clave} productos")

        uploaded_hist = st.file_uploader(
            "Archivo de herramientas .xlsx (completo)",
            type=["xlsx"],
            key="uploader_historial",
            disabled=DEMO_MODE,
        )
        if uploaded_hist:
            hist_bytes = uploaded_hist.read()

            df_hist_prev  = parse_historial_validado(hist_bytes)
            df_sup_prev   = parse_resumen_supermercado(hist_bytes)
            df_clave_prev = parse_tabla21(hist_bytes)

            col_a, col_b = st.columns(2)
            col_a.metric("Registros historial",      f"{len(df_hist_prev):,}")
            col_b.metric("Registros supermercados",  f"{len(df_sup_prev):,}")
            st.metric("Productos clave (Tabla 21)", len(df_clave_prev))

            if not df_hist_prev.empty:
                if st.button("Confirmar e importar todo", key="btn_hist"):
                    with get_conn() as con:
                        con.execute(text("DELETE FROM precios WHERE fuente='validado'"))
                    save_to_db(df_hist_prev, fuente="validado")
                    if not df_sup_prev.empty:
                        save_supermercado_to_db(df_sup_prev)
                    if not df_clave_prev.empty:
                        save_productos_clave_to_db(df_clave_prev)
                    log_action("UPLOAD", "historial", f"{uploaded_hist.name} · {len(df_hist_prev):,} registros validados")
                    st.success("Historial importado correctamente")
                    st.rerun()
            else:
                st.warning("No se pudo leer la hoja 'Resumen'.")

        st.divider()
        st.caption(f"Total semanas en DB: **{len(semanas_en_db())}**")

        # ZONA PELIGROSA — limpiar DB
        st.divider()
        with st.expander("Limpiar base de datos", expanded=False):
            st.caption(
                "Esta accion borra datos de forma permanente y NO se puede deshacer."
            )
            que_borrar = st.radio(
                "Que deseas borrar?",
                options=["todo", "bruto", "validado"],
                format_func=lambda x: {
                    "todo":     "Todo (historial + reportes + supermercados + productos clave)",
                    "bruto":    "Solo reportes semanales brutos",
                    "validado": "Solo historial validado, supermercados y productos clave",
                }[x],
                key="wipe_que",
            )
            confirmar_wipe = st.checkbox(
                "Si, entiendo que es permanente y quiero borrar.",
                key="wipe_confirm",
            )
            if st.button("Borrar ahora", key="wipe_btn",
                         disabled=(not confirmar_wipe or DEMO_MODE)):
                antes = wipe_db(que_borrar)
                log_action("WIPE", "db", f"tipo={que_borrar}",
                           f"precios={antes['precios']:,} | sup={antes['precios_supermercado']:,} | clave={antes['productos_clave']:,}", "")
                st.success(
                    f"Base de datos limpiada. Eliminados → "
                    f"precios: {antes['precios']:,} | "
                    f"supermercados: {antes['precios_supermercado']:,} | "
                    f"productos clave: {antes['productos_clave']:,}."
                )
                st.rerun()

    else:
        # Visualizador — solo info
        st.caption(f"Total semanas en DB: **{len(semanas_en_db())}**")


# ============================================================
# CARGA DE DATOS
# ============================================================
df_all = load_all()

if df_all.empty:
    if _es_admin:
        st.info(
            "No hay datos cargados. Usa el panel lateral para importar el "
            "historial validado (archivo de herramientas)."
        )
    else:
        st.info(
            "No hay datos disponibles en este momento. "
            "Contacta al administrador para cargar los datos."
        )
    st.stop()

df_validado = df_all[df_all["fuente"] == "validado"]
df_bruto    = df_all[df_all["fuente"] == "bruto"]
df_sup      = load_supermercado()
df_clave    = load_productos_clave()


# ============================================================
# FILTROS PRINCIPALES  (solo si hay datos)
# ============================================================
todas_semanas = sorted(set(df_all["semana"].dropna().astype(str).unique()))
categorias    = sorted(df_all["categoria"].unique())
categorias    = [c for c in categorias if c != "Referencia"]

if section == "Por Supermercado":
    # Esta pestaña tiene sus propios selectores de semana — los filtros globales no aplican
    semana_actual = todas_semanas[-1] if todas_semanas else None
    semana_comp   = todas_semanas[-2] if len(todas_semanas) >= 2 else None
    cat_sel       = "Todas"
else:
    col1, col2, col3 = st.columns(3)

    # semana_actual se define primero (col3) para calcular comp_opts
    with col3:
        semana_actual = st.selectbox(
            "Semana actual",
            todas_semanas,
            index=len(todas_semanas) - 1,
            format_func=lambda x: fmt_sem(x, "larga"),
        ) if todas_semanas else None

    comp_opts = sorted([s for s in todas_semanas if s != semana_actual], reverse=True)

    with col1:
        semana_comp = st.selectbox(
            "Semana a comparar",
            comp_opts,
            index=0,
            format_func=lambda x: fmt_sem(x, "larga"),
        ) if comp_opts else None

    with col2:
        cat_sel = st.selectbox("Categoria", ["Todas"] + categorias)

df_actual, fuente_actual = resolver_semana(df_all, semana_actual, preferir="bruto")
df_comp,   fuente_comp   = resolver_semana(df_all, semana_comp,   preferir="validado")

_sa_lbl   = fmt_sem(semana_actual, "corta") if semana_actual else "N/D"
_sc_lbl   = fmt_sem(semana_comp,   "corta") if semana_comp   else "N/D"
_sa_lbl_l = fmt_sem(semana_actual, "larga") if semana_actual else "N/D"
_sc_lbl_l = fmt_sem(semana_comp,   "larga") if semana_comp   else "N/D"

if cat_sel != "Todas":
    df_actual = df_actual[df_actual["categoria"] == cat_sel]
    df_comp   = df_comp[df_comp["categoria"] == cat_sel]



# ============================================================
# CONTEXTO PARA LOS TABS
# ============================================================
ctx = SimpleNamespace(
    df_all=df_all,
    df_actual=df_actual,
    df_comp=df_comp,
    df_validado=df_validado,
    df_bruto=df_bruto,
    df_sup=df_sup,
    df_clave=df_clave,
    semana_actual=semana_actual,
    semana_comp=semana_comp,
    cat_sel=cat_sel,
    fuente_actual=fuente_actual,
    fuente_comp=fuente_comp,
    sa_lbl=_sa_lbl,
    sc_lbl=_sc_lbl,
    sa_lbl_l=_sa_lbl_l,
    sc_lbl_l=_sc_lbl_l,
)


# ============================================================
# ROUTING DE SECCIONES
# ============================================================

if section == "Inicio":
    render_inicio(ctx)

# --- Tabs compartidos ---
elif section == "Comparativa de Precios":
    render_comparativa(ctx)

elif section in ("Historial y Proyeccion", "Historial y Proyección"):
    render_historial(ctx)

elif section == "Por Supermercado":
    render_por_supermercado(ctx)

elif section == "Productos Clave":
    render_productos_clave(ctx)

elif section == "Posibles Errores":
    render_posibles_errores(ctx)

# --- Tabs solo Admin ---
elif section == "Alertas":
    if not _es_admin:
        st.warning("No tienes permiso para acceder a esta seccion.")
    else:
        render_alertas(ctx)

elif section == "Archivos Cargados":
    if not _es_admin:
        st.warning("No tienes permiso para acceder a esta seccion.")
    else:
        render_archivos_cargados()

elif section == "Edicion de Datos":
    if not _es_admin:
        st.warning("No tienes permiso para acceder a esta seccion.")
    else:
        render_edicion_datos()

elif section in ("Administracion de Usuarios", "Administración de Usuarios"):
    render_usuarios()

elif section == "Auditoria":
    if not _es_admin:
        st.warning("No tienes permiso para acceder a esta seccion.")
    else:
        render_auditoria()

# --- Tab solo Viewer ---
elif section == "Simulacion Temporal":
    if _es_admin:
        st.warning("Esta seccion es exclusiva para usuarios Visualizador.")
    else:
        render_simulacion(ctx)


# ============================================================
# PIE DE PAGINA
# ============================================================
st.divider()
st.markdown('''
<div style="text-align:center;color:#475569;font-size:0.78rem;padding:1rem 0 0.5rem 0;
border-top:1px solid rgba(148,163,184,0.10);margin-top:1rem;">
    Visualizacion de Datos - Supermercados Santo Domingo &nbsp;|&nbsp; DOSAC
    &nbsp;|&nbsp; Datos DGDC
    <br><span style="font-size:0.72rem;color:#334155;">Jose Belliard</span>
</div>
''', unsafe_allow_html=True)
