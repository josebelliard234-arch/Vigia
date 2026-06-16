import streamlit as st
import pandas as pd
from sqlalchemy import text

from data.database import load_all, get_conn, DEMO_MODE, log_action


def render_edicion_datos():
    st.subheader("Edicion de Datos")
    st.caption("Modifica precios de forma permanente en la base de datos.")

    if DEMO_MODE:
        st.warning("Modo demo activo. No se pueden guardar cambios permanentes.")
        return

    df = load_all()
    if df.empty:
        st.info("No hay datos disponibles. Carga primero el historial.")
        return

    # ---- Filtros ----
    st.markdown("#### Filtros")
    fc1, fc2, fc3 = st.columns(3)
    semanas = sorted(df["semana"].unique())
    sem_sel = fc1.selectbox("Semana", semanas, index=len(semanas) - 1, key="ed_sem")

    df_f = df[df["semana"] == sem_sel].copy()

    cats = ["Todas"] + sorted(df_f["categoria"].dropna().unique())
    cat_sel = fc2.selectbox("Categoria", cats, key="ed_cat")

    provincias = sorted(df_f["provincia"].dropna().unique())
    prov_sel = fc3.multiselect("Provincia", provincias, default=provincias, key="ed_prov")

    fd1, fd2 = st.columns(2)
    sups = sorted(df_f["supermercado"].dropna().unique())
    sup_sel = fd1.multiselect("Supermercado", sups, default=sups, key="ed_sup")

    prods = ["Todos"] + sorted(df_f["producto"].dropna().unique())
    prod_sel = fd2.selectbox("Producto", prods, key="ed_prod")

    if prov_sel:
        df_f = df_f[df_f["provincia"].isin(prov_sel)]
    else:
        df_f = df_f.iloc[0:0]
    if sup_sel:
        df_f = df_f[df_f["supermercado"].isin(sup_sel)]
    else:
        df_f = df_f.iloc[0:0]
    if cat_sel != "Todas":
        df_f = df_f[df_f["categoria"] == cat_sel]
    if prod_sel != "Todos":
        df_f = df_f[df_f["producto"] == prod_sel]

    st.caption(f"{len(df_f):,} registros con los filtros actuales.")

    if df_f.empty:
        st.info("No hay registros con estos filtros.")
        return

    pk_cols = ["semana", "provincia", "supermercado", "id_producto", "presentacion"]
    df_pks = df_f[pk_cols].copy().reset_index(drop=True)

    cols_show = ["semana", "provincia", "supermercado", "categoria",
                 "producto", "presentacion", "precio"]
    df_edit_base = df_f[cols_show].copy().reset_index(drop=True)

    st.markdown("#### Tabla editable — solo el campo **Precio** es modificable")
    edited = st.data_editor(
        df_edit_base,
        column_config={
            "semana":        st.column_config.TextColumn("Semana",        disabled=True),
            "provincia":     st.column_config.TextColumn("Provincia",     disabled=True),
            "supermercado":  st.column_config.TextColumn("Supermercado",  disabled=True),
            "categoria":     st.column_config.TextColumn("Categoria",     disabled=True),
            "producto":      st.column_config.TextColumn("Producto",      disabled=True),
            "presentacion":  st.column_config.TextColumn("Presentacion",  disabled=True),
            "precio":        st.column_config.NumberColumn("Precio (RD$)", min_value=0.0, format="%.2f"),
        },
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        key="editor_precios_perm",
    )

    st.divider()
    st.warning(
        "⚠️ **Atencion:** Los cambios que guardes aqui son PERMANENTES en la base de datos "
        "y no se pueden deshacer. Verifica bien antes de confirmar."
    )
    confirmar = st.checkbox(
        "Entiendo que los cambios son permanentes y deseo guardar.",
        key="ed_confirm",
    )

    if st.button("Guardar cambios permanentes", disabled=not confirmar, use_container_width=True, key="ed_save"):
        try:
            diff = edited["precio"].compare(df_edit_base["precio"])
        except Exception:
            diff = pd.Series(dtype=float)

        if diff.empty:
            st.info("No se detectaron cambios en los precios.")
            return

        with get_conn() as con:
            for idx in diff.index:
                new_price = edited.loc[idx, "precio"]
                old_price = df_edit_base.loc[idx, "precio"]
                pk = df_pks.loc[idx]
                con.execute(text(
                    "UPDATE precios SET precio=:precio "
                    "WHERE semana=:semana AND provincia=:provincia AND supermercado=:supermercado "
                    "AND id_producto=:id_producto AND presentacion=:presentacion"
                ), {
                    "precio":        float(new_price),
                    "semana":        str(pk["semana"]),
                    "provincia":     str(pk["provincia"]),
                    "supermercado":  str(pk["supermercado"]),
                    "id_producto":   int(pk["id_producto"]),
                    "presentacion":  str(pk["presentacion"]),
                })
                log_action(
                    "EDIT_PRICE", "precio",
                    (
                        f"semana={pk['semana']}|provincia={pk['provincia']}"
                        f"|supermercado={pk['supermercado']}"
                        f"|categoria={df_edit_base.loc[idx, 'categoria']}"
                        f"|producto={df_edit_base.loc[idx, 'producto']}"
                        f"|presentacion={df_edit_base.loc[idx, 'presentacion']}"
                    ),
                    f"RD${old_price:.2f}", f"RD${new_price:.2f}",
                )

        st.success(f"{len(diff)} precio(s) actualizado(s) permanentemente.")
        st.rerun()
