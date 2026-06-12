import streamlit as st

from data.database import load_monitoreos_cargados, eliminar_monitoreo_cargado, DEMO_MODE
from utils.dates import fmt_sem


def render_archivos_cargados():
    st.subheader("Archivos Cargados")
    st.caption("Monitoreos importados a la base de datos.")

    monitoreos = load_monitoreos_cargados()

    if not monitoreos:
        st.info("No hay monitoreos cargados todavia.")
        return

    st.markdown(f"**{len(monitoreos)} monitoreo(s) registrado(s)**")
    st.divider()

    for semana_m, nombre_m, fecha_m, registros_m in monitoreos:
        col_info, col_btn = st.columns([5, 1])
        with col_info:
            st.markdown(
                f"<div style='padding:.6rem .8rem;border:1px solid rgba(148,163,184,0.18);"
                f"border-radius:12px;background:rgba(30,41,59,0.55);'>"
                f"<div style='font-size:.82rem;color:#F8FAFC;font-weight:600;"
                f"word-break:break-word;'>{nombre_m or 'Archivo'}</div>"
                f"<div style='font-size:.92rem;color:#3B82F6;font-weight:700;"
                f"margin-top:.12rem;'>{fmt_sem(semana_m, 'corta')}</div>"
                f"<div style='font-size:.72rem;color:#94A3B8;margin-top:.08rem;'>"
                f"{registros_m:,} registros &nbsp;·&nbsp; Cargado: {fecha_m}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        with col_btn:
            st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
            if st.button(
                "Eliminar",
                key=f"arch_del_{semana_m}",
                disabled=DEMO_MODE,
                help="Elimina este monitoreo y sus datos brutos de la DB",
            ):
                eliminar_monitoreo_cargado(semana_m)
                st.rerun()

    if DEMO_MODE:
        st.caption("Modo demo activo: la eliminacion esta deshabilitada.")
