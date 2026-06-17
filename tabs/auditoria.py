import streamlit as st
import pandas as pd
from data.database import load_audit_log

_ACCION_COLOR = {
    "LOGIN":            "#22C55E",
    "LOGIN_FAIL":       "#EF4444",
    "LOGOUT":           "#94A3B8",
    "UPLOAD":           "#3B82F6",
    "DELETE":           "#F97316",
    "WIPE":             "#EF4444",
    "EDIT_PRICE":       "#A855F7",
    "BULK_EDIT_PRICE":  "#7C3AED",
    "RESTORE_PRICES":   "#F97316",
    "PRICE_ERROR":      "#EF4444",
    "CREATE_USER":      "#22C55E",
    "UPDATE_USER":      "#F59E0B",
    "DELETE_USER":      "#EF4444",
    "MARK_PRICE":       "#F59E0B",
    "UNMARK_PRICE":     "#94A3B8",
}

_ACCION_LABEL = {
    "LOGIN":            "Inicio de sesion",
    "LOGIN_FAIL":       "Intento fallido de login",
    "LOGOUT":           "Cierre de sesion",
    "UPLOAD":           "Archivo subido",
    "DELETE":           "Eliminacion de datos",
    "WIPE":             "Limpieza de base de datos",
    "EDIT_PRICE":       "Precio modificado",
    "BULK_EDIT_PRICE":  "Edicion masiva de precios",
    "RESTORE_PRICES":   "Precios restablecidos",
    "PRICE_ERROR":      "Error al guardar precio",
    "CREATE_USER":      "Usuario creado",
    "UPDATE_USER":      "Usuario modificado",
    "DELETE_USER":      "Usuario eliminado",
    "MARK_PRICE":       "Precio marcado",
    "UNMARK_PRICE":     "Precio desmarcado",
}


def _parse_detalle_precio(detalle):
    """Extrae campos clave=valor del detalle de EDIT_PRICE. Soporta formato antiguo tambien."""
    result = {}
    s = str(detalle or "")
    if "|" in s:
        for part in s.split("|"):
            if "=" in part:
                k, v = part.split("=", 1)
                result[k.strip()] = v.strip()
    else:
        # formato antiguo: "producto · presentacion · supermercado · semana"
        parts = [p.strip() for p in s.split("·")]
        if len(parts) >= 4:
            result = {
                "producto":     parts[0],
                "presentacion": parts[1],
                "supermercado": parts[2],
                "semana":       parts[3],
            }
    return result


def render_auditoria():
    st.subheader("Auditoria del Sistema")

    df = load_audit_log(limit=2000)

    if df.empty:
        st.info("No hay registros de auditoria aun.")
        return

    tab_precios, tab_general = st.tabs(["Cambios de Precios", "Registro General"])

    # ─────────────────────────────────────────────────────────────
    # TAB 1: Cambios de Precios
    # ─────────────────────────────────────────────────────────────
    with tab_precios:
        st.caption(
            "Historial de cambios de precios: ediciones individuales, ediciones masivas, "
            "restablecimientos y errores al guardar."
        )

        _ACCIONES_PRECIO = {"EDIT_PRICE", "BULK_EDIT_PRICE", "RESTORE_PRICES", "PRICE_ERROR"}
        df_edits = df[df["accion"].isin(_ACCIONES_PRECIO)].copy()

        if df_edits.empty:
            st.info("Aun no se han registrado cambios de precios.")
        else:
            parsed = df_edits["detalle"].apply(_parse_detalle_precio)
            df_edits["semana_ed"]       = parsed.apply(lambda d: d.get("semana", ""))
            df_edits["provincia_ed"]    = parsed.apply(lambda d: d.get("provincia", ""))
            df_edits["supermercado_ed"] = parsed.apply(lambda d: d.get("supermercado", ""))
            df_edits["categoria_ed"]    = parsed.apply(lambda d: d.get("categoria", ""))
            df_edits["producto_ed"]     = parsed.apply(lambda d: d.get("producto", ""))
            df_edits["presentacion_ed"] = parsed.apply(lambda d: d.get("presentacion", ""))

            # ── Filtros ──
            fe1, fe2, fe3 = st.columns(3)
            fe4, fe5 = st.columns(2)

            usuarios_ed = ["Todos"] + sorted(df_edits["usuario"].dropna().unique())
            usr_sel = fe1.selectbox("Usuario", usuarios_ed, key="aud_e_usr")

            semanas_ed = ["Todas"] + sorted([s for s in df_edits["semana_ed"].unique() if s])
            sem_sel = fe2.selectbox("Semana", semanas_ed, key="aud_e_sem")

            cats_ed = ["Todas"] + sorted([c for c in df_edits["categoria_ed"].unique() if c])
            cat_sel = fe3.selectbox("Categoria", cats_ed, key="aud_e_cat")

            provs_ed = ["Todas"] + sorted([p for p in df_edits["provincia_ed"].unique() if p])
            prov_sel = fe4.selectbox("Provincia", provs_ed, key="aud_e_prov")

            sups_ed = ["Todos"] + sorted([s for s in df_edits["supermercado_ed"].unique() if s])
            sup_sel = fe5.selectbox("Supermercado", sups_ed, key="aud_e_sup")

            df_fe = df_edits.copy()
            if usr_sel != "Todos":
                df_fe = df_fe[df_fe["usuario"] == usr_sel]
            if sem_sel != "Todas":
                df_fe = df_fe[df_fe["semana_ed"] == sem_sel]
            if cat_sel != "Todas":
                df_fe = df_fe[df_fe["categoria_ed"] == cat_sel]
            if prov_sel != "Todas":
                df_fe = df_fe[df_fe["provincia_ed"] == prov_sel]
            if sup_sel != "Todos":
                df_fe = df_fe[df_fe["supermercado_ed"] == sup_sel]

            st.caption(f"{len(df_fe):,} cambios encontrados.")

            if df_fe.empty:
                st.info("No hay cambios con estos filtros.")
            else:
                df_tabla = df_fe[[
                    "timestamp", "usuario", "semana_ed", "categoria_ed",
                    "provincia_ed", "supermercado_ed", "producto_ed",
                    "presentacion_ed", "valor_ant", "valor_nuevo",
                ]].rename(columns={
                    "timestamp":       "Fecha / Hora",
                    "usuario":         "Usuario",
                    "semana_ed":       "Semana",
                    "categoria_ed":    "Categoria",
                    "provincia_ed":    "Provincia",
                    "supermercado_ed": "Supermercado",
                    "producto_ed":     "Producto",
                    "presentacion_ed": "Presentacion",
                    "valor_ant":       "Precio Anterior",
                    "valor_nuevo":     "Precio Nuevo",
                }).reset_index(drop=True)

                st.dataframe(df_tabla, use_container_width=True, hide_index=True)

                st.divider()
                if st.button("Exportar a CSV", key="aud_e_export"):
                    st.download_button(
                        "Descargar CSV",
                        data=df_tabla.to_csv(index=False).encode("utf-8"),
                        file_name="cambios_precios.csv",
                        mime="text/csv",
                        key="aud_e_dl",
                    )

    # ─────────────────────────────────────────────────────────────
    # TAB 2: Registro General
    # ─────────────────────────────────────────────────────────────
    with tab_general:
        st.caption("Registro completo de todas las acciones: inicios de sesion, subidas de archivos, eliminaciones, etc.")

        fa1, fa2, fa3 = st.columns(3)

        usuarios_g = ["Todos"] + sorted(df["usuario"].dropna().unique().tolist())
        usr_sel_g = fa1.selectbox("Usuario", usuarios_g, key="aud_usr")

        acciones_g = ["Todas"] + sorted(df["accion"].dropna().unique().tolist())
        acc_sel = fa2.selectbox("Tipo de accion", acciones_g, key="aud_acc")

        entidades_g = ["Todas"] + sorted(df["entidad"].dropna().unique().tolist())
        ent_sel = fa3.selectbox("Entidad", entidades_g, key="aud_ent")

        df_g = df.copy()
        if usr_sel_g != "Todos":
            df_g = df_g[df_g["usuario"] == usr_sel_g]
        if acc_sel != "Todas":
            df_g = df_g[df_g["accion"] == acc_sel]
        if ent_sel != "Todas":
            df_g = df_g[df_g["entidad"] == ent_sel]

        st.caption(f"{len(df_g):,} registros encontrados.")
        st.divider()

        for _, row in df_g.iterrows():
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

            # Para EDIT_PRICE en el registro general mostramos un resumen legible
            if accion == "EDIT_PRICE":
                parsed = _parse_detalle_precio(detalle)
                detalle_display = (
                    f"{parsed.get('producto', '')} {parsed.get('presentacion', '')} "
                    f"— {parsed.get('supermercado', '')} · {parsed.get('provincia', '')} "
                    f"· {parsed.get('semana', '')}"
                ).strip(" —·")
            else:
                detalle_display = str(detalle or "")

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
                f"{' — ' + detalle_display if detalle_display else ''}"
                f"</div>"
                f"{cambio_html}"
                f"</div>",
                unsafe_allow_html=True,
            )

        st.divider()
        if st.button("Exportar a CSV", key="aud_export"):
            output = df_g[["id", "timestamp", "usuario", "rol", "accion",
                           "entidad", "detalle", "valor_ant", "valor_nuevo"]].copy()
            output.columns = ["ID", "Fecha/Hora", "Usuario", "Rol", "Accion",
                              "Entidad", "Detalle", "Valor Anterior", "Valor Nuevo"]
            st.download_button(
                "Descargar CSV",
                data=output.to_csv(index=False).encode("utf-8"),
                file_name="auditoria_general.csv",
                mime="text/csv",
                key="aud_download",
            )
