import streamlit as st
import pandas as pd
from sqlalchemy import text

from data.database import load_all, get_conn, DEMO_MODE, log_action
from utils.dates import fmt_sem


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

    # ─── FILTROS ─────────────────────────────────────────────
    st.markdown("#### Filtros")
    fc1, fc2, fc3 = st.columns(3)

    semanas = sorted(df["semana"].unique())
    sem_sel = fc1.selectbox("Semana", semanas, index=len(semanas) - 1, key="ed_sem")
    df_sem = df[df["semana"] == sem_sel].copy()

    cats = ["Todas"] + sorted(df_sem["categoria"].dropna().unique())
    cat_sel = fc2.selectbox("Categoria", cats, key="ed_cat")
    df_cat = df_sem if cat_sel == "Todas" else df_sem[df_sem["categoria"] == cat_sel]

    provincias = sorted(df_sem["provincia"].dropna().unique())
    sups_all   = sorted(df_sem["supermercado"].dropna().unique())

    fd1, fd2 = st.columns(2)
    prov_sel = fd1.multiselect("Provincia", provincias, default=[], key="ed_prov")
    sup_sel  = fd2.multiselect("Supermercado", sups_all, default=[], key="ed_sup")

    if not sup_sel:
        st.info("Selecciona uno o mas supermercados para cargar la tabla de edicion.")
        return

    fe1, fe2 = st.columns(2)
    prods = ["Todos"] + sorted(df_cat["producto"].dropna().unique())
    prod_sel = fe1.selectbox("Producto", prods, key="ed_prod")

    df_for_pres = df_cat if prod_sel == "Todos" else df_cat[df_cat["producto"] == prod_sel]
    pres_opts = ["Todas"] + sorted(df_for_pres["presentacion"].dropna().unique())
    pres_sel = fe2.selectbox("Presentacion", pres_opts, key="ed_pres")

    # ─── APLICAR FILTROS ─────────────────────────────────────
    df_f = df_sem.copy()
    if prov_sel:
        df_f = df_f[df_f["provincia"].isin(prov_sel)]
    if cat_sel != "Todas":
        df_f = df_f[df_f["categoria"] == cat_sel]
    if prod_sel != "Todos":
        df_f = df_f[df_f["producto"] == prod_sel]
    if pres_sel != "Todas":
        df_f = df_f[df_f["presentacion"] == pres_sel]

    if df_f.empty:
        st.info("No hay registros con estos filtros.")
        return

    # ─── MODO SOLO LECTURA si hay ambiguedad de provincia ────
    readonly_mode = False
    if len(prov_sel) != 1:
        st.warning(
            "Selecciona exactamente **una provincia** para habilitar la edicion. "
            "Con varias provincias o sin provincia seleccionada la tabla es solo lectura."
        )
        readonly_mode = True

    # ─── PROMEDIO (todos los supermercados, no solo los seleccionados) ───
    idx_cols = ["categoria", "producto", "presentacion"]
    df_prom = (
        df_f.groupby(idx_cols, sort=False)["precio"]
        .mean()
        .round(2)
        .reset_index()
        .rename(columns={"precio": "_prom_"})
    )

    # ─── PIVOT: supermercados seleccionados como columnas ────
    df_sup_f = df_f[df_f["supermercado"].isin(sup_sel)].copy()
    if df_sup_f.empty:
        st.info("No hay datos para los supermercados seleccionados con estos filtros.")
        return

    # Verificar duplicados antes de pivotar
    dup_counts = df_sup_f.groupby(idx_cols + ["supermercado"]).size()
    dups = dup_counts[dup_counts > 1]
    if not dups.empty and not readonly_mode:
        st.warning(
            f"Se detectaron {len(dups)} combinaciones duplicadas en la base de datos. "
            "La tabla esta en modo solo lectura hasta resolver los duplicados."
        )
        readonly_mode = True

    df_pivot = (
        df_sup_f
        .pivot_table(
            index=idx_cols,
            columns="supermercado",
            values="precio",
            aggfunc="first",
        )
        .reset_index()
    )
    df_pivot.columns.name = None
    df_pivot = df_pivot.merge(df_prom, on=idx_cols, how="left").reset_index(drop=True)

    sup_cols  = [c for c in df_pivot.columns if c not in idx_cols + ["_prom_"]]
    show_pres = pres_sel == "Todas"

    # df_full conserva presentacion siempre (para lookup al guardar)
    df_full = df_pivot[idx_cols + sup_cols + ["_prom_"]].copy().reset_index(drop=True)

    fixed_disp = ["categoria", "producto"] + (["presentacion"] if show_pres else [])
    all_cols   = fixed_disp + sup_cols + ["_prom_"]

    df_display  = df_pivot[all_cols].rename(columns={"_prom_": "Promedio"}).reset_index(drop=True)
    df_original = df_display.copy()

    # ─── SUBTITULO ───────────────────────────────────────────
    st.divider()
    st.markdown(f"**Semana:** {fmt_sem(sem_sel, 'larga')}")
    info_parts = []
    if prov_sel:
        info_parts.append(f"Provincia: {', '.join(prov_sel)}")
    info_parts.append(f"{len(df_display):,} productos")
    info_parts.append(f"{len(sup_cols)} supermercado(s)")
    st.caption(" · ".join(info_parts))

    # ─── COLUMN CONFIG ───────────────────────────────────────
    col_cfg = {}
    for c in fixed_disp:
        col_cfg[c] = st.column_config.TextColumn(c.capitalize(), disabled=True)
    for c in sup_cols:
        col_cfg[c] = st.column_config.NumberColumn(c, min_value=0.0, format="RD$ %.2f")
    col_cfg["Promedio"] = st.column_config.NumberColumn(
        "Promedio", disabled=True, format="RD$ %.2f"
    )

    # ─── TABLA ───────────────────────────────────────────────
    if readonly_mode:
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        return

    st.markdown("#### Precios por supermercado — solo las columnas de supermercados son editables")

    edited = st.data_editor(
        df_display,
        column_config=col_cfg,
        disabled=fixed_disp + ["Promedio"],
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        key="editor_precios_perm",
    )

    st.divider()
    st.warning(
        "⚠️ **Atencion:** Los cambios que guardes aqui son PERMANENTES "
        "y no se pueden deshacer. Verifica bien antes de confirmar."
    )
    confirmar = st.checkbox(
        "Entiendo que los cambios son permanentes y deseo guardar.",
        key="ed_confirm",
    )

    if not st.button(
        "Guardar cambios permanentes",
        disabled=not confirmar,
        use_container_width=True,
        key="ed_save",
    ):
        return

    # ─── DETECTAR Y VALIDAR CAMBIOS ──────────────────────────
    cambios      = []
    advertencias = []
    prov_unica   = prov_sel[0]

    for i in range(len(edited)):
        for sup_col in sup_cols:
            new_val = edited.loc[i, sup_col]
            old_val = df_original.loc[i, sup_col]

            # Sin cambio
            if pd.isna(new_val) and pd.isna(old_val):
                continue
            if not pd.isna(new_val) and not pd.isna(old_val):
                if round(float(new_val), 4) == round(float(old_val), 4):
                    continue

            prod_i = str(df_full.loc[i, "producto"])
            pres_i = str(df_full.loc[i, "presentacion"])
            cat_i  = str(df_full.loc[i, "categoria"])

            # Usuario borró un precio — no permitido
            if pd.isna(new_val) and not pd.isna(old_val):
                advertencias.append(
                    f"**{prod_i}** / {sup_col}: se borro el precio. No se permite. Ingresa un valor."
                )
                continue

            # Celda nueva sin registro original — no insertar
            if pd.isna(old_val):
                advertencias.append(
                    f"**{prod_i}** / {sup_col}: no existe registro original en la base de datos. No se guardara."
                )
                continue

            # Verificar unicidad del registro en df_f
            mask = (
                (df_f["supermercado"] == sup_col) &
                (df_f["producto"]     == prod_i) &
                (df_f["presentacion"] == pres_i) &
                (df_f["categoria"]    == cat_i) &
                (df_f["provincia"]    == prov_unica)
            )
            matches = df_f[mask]

            if len(matches) == 0:
                advertencias.append(
                    f"**{prod_i}** / {sup_col}: no se encontro el registro en la base de datos."
                )
                continue
            if len(matches) > 1:
                advertencias.append(
                    f"**{prod_i}** / {sup_col}: {len(matches)} registros ambiguos — no se guardara."
                )
                continue

            rec = matches.iloc[0]
            cambios.append({
                "semana":       str(rec["semana"]),
                "provincia":    str(rec["provincia"]),
                "supermercado": str(rec["supermercado"]),
                "categoria":    cat_i,
                "producto":     prod_i,
                "presentacion": pres_i,
                "id_producto":  int(rec["id_producto"]),
                "precio_ant":   float(old_val),
                "precio_new":   float(new_val),
            })

    for w in advertencias:
        st.warning(w)

    if not cambios:
        st.info("No se detectaron cambios validos para guardar.")
        return

    # ─── GUARDAR ─────────────────────────────────────────────
    with get_conn() as con:
        for c in cambios:
            con.execute(text(
                "UPDATE precios SET precio=:precio "
                "WHERE semana=:semana AND provincia=:provincia "
                "AND supermercado=:supermercado "
                "AND id_producto=:id_producto AND presentacion=:presentacion"
            ), {
                "precio":       float(c["precio_new"]),
                "semana":       c["semana"],
                "provincia":    c["provincia"],
                "supermercado": c["supermercado"],
                "id_producto":  c["id_producto"],
                "presentacion": c["presentacion"],
            })
            log_action(
                "EDIT_PRICE", "precio",
                (
                    f"semana={c['semana']}|provincia={c['provincia']}"
                    f"|supermercado={c['supermercado']}"
                    f"|categoria={c['categoria']}"
                    f"|producto={c['producto']}"
                    f"|presentacion={c['presentacion']}"
                ),
                f"RD${c['precio_ant']:.2f}",
                f"RD${c['precio_new']:.2f}",
            )

    st.success(f"{len(cambios)} precio(s) actualizado(s) permanentemente.")
    if advertencias:
        st.info(f"{len(advertencias)} celda(s) no guardadas — revisa las advertencias de arriba.")
    st.rerun()
