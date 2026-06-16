import streamlit as st
import pandas as pd
from data.database import load_audit_log

_ACCION_COLOR = {
    "LOGIN":       "#22C55E",
    "LOGIN_FAIL":  "#EF4444",
    "LOGOUT":      "#94A3B8",
    "UPLOAD":      "#3B82F6",
    "DELETE":      "#F97316",
    "WIPE":        "#EF4444",
    "EDIT_PRICE":  "#A855F7",
    "CREATE_USER": "#22C55E",
    "UPDATE_USER": "#F59E0B",
    "DELETE_USER": "#EF4444",
}

_ACCION_LABEL = {
    "LOGIN":       "Inicio sesion",
    "LOGIN_FAIL":  "Login fallido",
    "LOGOUT":      "Cierre sesion",
    "UPLOAD":      "Subida archivo",
    "DELETE":      "Eliminacion",
    "WIPE":        "Limpieza DB",
    "EDIT_PRICE":  "Edicion precio",
    "CREATE_USER": "Crear usuario",
    "UPDATE_USER": "Modificar usuario",
    "DELETE_USER": "Eliminar usuario",
}


def render_auditoria():
    st.subheader("Auditoria del Sistema")
    st.caption("Registro de todas las acciones importantes. Solo lectura.")

    df = load_audit_log(limit=1000)

    if df.empty:
        st.info("No hay registros de auditoria aun.")
        return

    # ---- Filtros ----
    fa1, fa2, fa3 = st.columns(3)

    usuarios = ["Todos"] + sorted(df["usuario"].dropna().unique().tolist())
    usr_sel = fa1.selectbox("Usuario", usuarios, key="aud_usr")

    acciones = ["Todas"] + sorted(df["accion"].dropna().unique().tolist())
    acc_sel = fa2.selectbox("Accion", acciones, key="aud_acc")

    entidades = ["Todas"] + sorted(df["entidad"].dropna().unique().tolist())
    ent_sel = fa3.selectbox("Entidad", entidades, key="aud_ent")

    df_f = df.copy()
    if usr_sel != "Todos":
        df_f = df_f[df_f["usuario"] == usr_sel]
    if acc_sel != "Todas":
        df_f = df_f[df_f["accion"] == acc_sel]
    if ent_sel != "Todas":
        df_f = df_f[df_f["entidad"] == ent_sel]

    st.caption(f"{len(df_f):,} registros encontrados.")
    st.divider()

    # ---- Tabla con badge de color ----
    for _, row in df_f.iterrows():
        accion  = str(row.get("accion", ""))
        color   = _ACCION_COLOR.get(accion, "#64748B")
        label   = _ACCION_LABEL.get(accion, accion)
        usuario = row.get("usuario", "")
        rol     = row.get("rol", "")
        ts      = row.get("timestamp", "")
        entidad = row.get("entidad", "")
        detalle = row.get("detalle", "")
        val_ant = row.get("valor_ant", "")
        val_new = row.get("valor_nuevo", "")

        cambio_html = ""
        if val_ant or val_new:
            cambio_html = (
                f"<span style='color:#94A3B8;font-size:.75rem;'>"
                f"<b>Antes:</b> {val_ant or '—'} &nbsp;→&nbsp; <b>Despues:</b> {val_new or '—'}"
                f"</span><br>"
            )

        st.markdown(
            f"<div style='padding:.55rem .85rem;margin-bottom:.4rem;"
            f"border:1px solid rgba(148,163,184,0.15);border-radius:10px;"
            f"background:rgba(15,23,42,0.6);'>"
            f"<div style='display:flex;align-items:center;gap:.6rem;flex-wrap:wrap;'>"
            f"<span style='background:{color}22;color:{color};font-size:.7rem;font-weight:700;"
            f"padding:.15rem .5rem;border-radius:999px;border:1px solid {color}44;white-space:nowrap;'>"
            f"{label}</span>"
            f"<span style='color:#F8FAFC;font-size:.82rem;font-weight:600;'>{usuario}</span>"
            f"<span style='color:#64748B;font-size:.75rem;'>({rol})</span>"
            f"<span style='color:#475569;font-size:.72rem;margin-left:auto;'>{ts}</span>"
            f"</div>"
            f"<div style='margin-top:.25rem;color:#CBD5E1;font-size:.78rem;'>"
            f"<b style='color:#94A3B8;'>{entidad}</b>"
            f"{' · ' + detalle if detalle else ''}"
            f"</div>"
            f"{cambio_html}"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.divider()
    if st.button("Exportar a Excel", key="aud_export"):
        output = df_f.copy()
        output.columns = ["ID", "Fecha/Hora", "Usuario", "Rol", "Accion",
                          "Entidad", "Detalle", "Valor Anterior", "Valor Nuevo"]
        st.download_button(
            "Descargar Excel",
            data=output.to_csv(index=False).encode("utf-8"),
            file_name="auditoria.csv",
            mime="text/csv",
            key="aud_download",
        )
