import streamlit as st
import pandas as pd
from sqlalchemy import text

from data.database import (
    load_all, get_conn, DEMO_MODE, log_action,
    save_marcador, delete_marcador, load_marcadores,
    is_postgres,
)
from utils.dates import fmt_sem

_COLORES = {
    "🟡 Amarillo — atencion":  "#F59E0B",
    "🔴 Rojo — problema":      "#EF4444",
    "🟢 Verde — validado":     "#22C55E",
    "🔵 Azul — pendiente":     "#3B82F6",
    "🟠 Naranja — revisar":    "#F97316",
}

_EMOJI = {
    "#F59E0B": "🟡",
    "#EF4444": "🔴",
    "#22C55E": "🟢",
    "#3B82F6": "🔵",
    "#F97316": "🟠",
}

# CSS inyectado cuando el modo ampliado está activo
_CSS_AMPLIADO = """
<style>
/* Ocultar sidebar completo */
section[data-testid="stSidebar"] {
    display: none !important;
    width: 0px !important;
    min-width: 0px !important;
}
/* Ocultar el toggle de colapsar sidebar */
[data-testid="collapsedControl"] {
    display: none !important;
}
/* Expandir el area principal al 100% */
.main .block-container {
    max-width: 100% !important;
    padding-left: 0.75rem !important;
    padding-right: 0.75rem !important;
    padding-top: 0.4rem !important;
}
</style>
"""


def _build_marcas_str(df_marc, producto, presentacion, sup_cols):
    """Retorna string con emojis + supermercados marcados para una fila del pivot."""
    if df_marc.empty:
        return ""
    parts = []
    for sc in sup_cols:
        m = df_marc[
            (df_marc["supermercado"] == sc) &
            (df_marc["producto"]     == producto) &
            (df_marc["presentacion"] == presentacion)
        ]
        if not m.empty:
            emoji = _EMOJI.get(m.iloc[0]["color"], "●")
            nota  = str(m.iloc[0].get("nota", "") or "")
            parts.append(f"{emoji} {sc}" + (f" ({nota[:18]})" if nota else ""))
    return " · ".join(parts)


def _table_height(n_rows: int, ampliado: bool) -> int:
    """Altura dinamica del data_editor segun numero de filas y modo."""
    px_por_fila = 35
    px_header   = 42
    calculado   = n_rows * px_por_fila + px_header
    if ampliado:
        return max(620, min(calculado, 860))
    return max(380, min(calculado, 520))


def render_edicion_datos():
    st.subheader("Edicion de Datos")

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
    df_sem  = df[df["semana"] == sem_sel].copy()

    cats    = ["Todas"] + sorted(df_sem["categoria"].dropna().unique())
    cat_sel = fc2.selectbox("Categoria", cats, key="ed_cat")
    df_cat  = df_sem if cat_sel == "Todas" else df_sem[df_sem["categoria"] == cat_sel]

    provincias = sorted(df_sem["provincia"].dropna().unique())
    sups_all   = sorted(df_sem["supermercado"].dropna().unique())

    fd1, fd2 = st.columns(2)
    prov_sel = fd1.multiselect("Provincia", provincias, default=[], key="ed_prov")
    sup_sel  = fd2.multiselect("Supermercado", sups_all, default=[], key="ed_sup")

    if not sup_sel:
        st.info("Selecciona uno o mas supermercados para cargar la tabla de edicion.")
        return

    fe1, fe2 = st.columns(2)
    prods    = ["Todos"] + sorted(df_cat["producto"].dropna().unique())
    prod_sel = fe1.selectbox("Producto", prods, key="ed_prod")

    df_for_pres = df_cat if prod_sel == "Todos" else df_cat[df_cat["producto"] == prod_sel]
    pres_opts   = ["Todas"] + sorted(df_for_pres["presentacion"].dropna().unique())
    pres_sel    = fe2.selectbox("Presentacion", pres_opts, key="ed_pres")

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

    # ─── MODO SOLO LECTURA (requiere exactamente 1 provincia) ─
    readonly_mode = len(prov_sel) != 1
    prov_unica    = prov_sel[0] if len(prov_sel) == 1 else None

    if readonly_mode:
        st.warning(
            "Selecciona exactamente **una provincia** para habilitar edicion y marcadores. "
            "Con varias provincias o sin provincia la tabla es solo lectura."
        )

    # ─── CARGAR MARCADORES ───────────────────────────────────
    df_marc = pd.DataFrame()
    if not readonly_mode:
        _all_marc = load_marcadores()
        if not _all_marc.empty:
            df_marc = _all_marc[
                (_all_marc["semana"]    == sem_sel) &
                (_all_marc["provincia"] == prov_unica)
            ].copy().reset_index(drop=True)

    # ─── PROMEDIO (todos los supermercados) ──────────────────
    idx_cols = ["categoria", "producto", "presentacion"]
    df_prom  = (
        df_f.groupby(idx_cols, sort=False)["precio"]
        .mean().round(2).reset_index()
        .rename(columns={"precio": "_prom_"})
    )

    # ─── PIVOT ───────────────────────────────────────────────
    df_sup_f = df_f[df_f["supermercado"].isin(sup_sel)].copy()
    if df_sup_f.empty:
        st.info("No hay datos para los supermercados seleccionados.")
        return

    dup_counts = df_sup_f.groupby(idx_cols + ["supermercado"]).size()
    if (dup_counts > 1).any() and not readonly_mode:
        n_dups = int((dup_counts > 1).sum())
        st.warning(
            f"Se detectaron {n_dups} combinaciones duplicadas en la base de datos. "
            "Tabla en modo solo lectura hasta resolver los duplicados."
        )
        readonly_mode = True
        prov_unica    = None

    df_pivot = (
        df_sup_f
        .pivot_table(index=idx_cols, columns="supermercado", values="precio", aggfunc="first")
        .reset_index()
    )
    df_pivot.columns.name = None
    df_pivot = df_pivot.merge(df_prom, on=idx_cols, how="left").reset_index(drop=True)

    sup_cols  = [c for c in df_pivot.columns if c not in idx_cols + ["_prom_"]]
    show_pres = pres_sel == "Todas"

    df_pivot["_marcas_"] = [
        _build_marcas_str(df_marc, df_pivot.loc[i, "producto"],
                          df_pivot.loc[i, "presentacion"], sup_cols)
        for i in range(len(df_pivot))
    ]

    df_full = df_pivot[idx_cols + sup_cols + ["_prom_", "_marcas_"]].copy().reset_index(drop=True)

    fixed_disp = ["categoria", "producto"] + (["presentacion"] if show_pres else [])
    all_cols   = fixed_disp + sup_cols + ["_prom_", "_marcas_"]

    df_display  = (
        df_pivot[all_cols]
        .rename(columns={"_prom_": "Promedio", "_marcas_": "🔖 Marcas"})
        .reset_index(drop=True)
    )
    df_original = df_display.copy()

    # ─── CONTROLES DE VISTA ──────────────────────────────────
    cv1, cv2 = st.columns([3, 1])
    with cv1:
        solo_marcados = st.checkbox(
            "Mostrar solo productos marcados", value=False, key="ed_solo_marc"
        )
    with cv2:
        modo_ampliado = st.checkbox(
            "⛶ Modo ampliado", value=False, key="ed_ampliado",
            help="Oculta el sidebar y agranda la tabla para trabajar mas comodo.",
        )

    # Inyectar CSS si modo ampliado esta activo
    if modo_ampliado:
        st.markdown(_CSS_AMPLIADO, unsafe_allow_html=True)

    # Aplicar filtro solo marcados
    if solo_marcados:
        mask_m      = df_display["🔖 Marcas"].str.len() > 0
        df_display  = df_display[mask_m].reset_index(drop=True)
        df_full     = df_full[mask_m].reset_index(drop=True)
        df_original = df_display.copy()
        if df_display.empty:
            st.info("No hay productos marcados con los filtros actuales.")
            return

    # ─── SUBTITULO ───────────────────────────────────────────
    st.divider()
    info_parts = [f"**{fmt_sem(sem_sel, 'larga')}**"]
    if prov_sel:
        info_parts.append(f"Provincia: {', '.join(prov_sel)}")
    info_parts += [f"{len(df_display):,} productos", f"{len(sup_cols)} supermercado(s)"]
    st.caption("  ·  ".join(info_parts))

    # ─── COLUMN CONFIG ───────────────────────────────────────
    col_cfg = {}
    for c in fixed_disp:
        col_cfg[c] = st.column_config.TextColumn(c.capitalize(), disabled=True)
    for c in sup_cols:
        col_cfg[c] = st.column_config.NumberColumn(c, min_value=0.0, format="RD$ %.2f")
    col_cfg["Promedio"]   = st.column_config.NumberColumn("Promedio",   disabled=True, format="RD$ %.2f")
    col_cfg["🔖 Marcas"] = st.column_config.TextColumn("🔖 Marcas", disabled=True, width="medium")

    tbl_height = _table_height(len(df_display), modo_ampliado)

    # ─── TABLA ───────────────────────────────────────────────
    if readonly_mode:
        st.dataframe(df_display, use_container_width=True, hide_index=True, height=tbl_height)

    else:
        if not modo_ampliado:
            st.markdown("#### Precios por supermercado — columnas de supermercados son editables")

        edited = st.data_editor(
            df_display,
            column_config=col_cfg,
            disabled=fixed_disp + ["Promedio", "🔖 Marcas"],
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            height=tbl_height,
            key="editor_precios_perm",
        )

        # ── GUARDAR CAMBIOS ──────────────────────────────────
        st.divider()
        if not modo_ampliado:
            st.warning(
                "⚠️ **Atencion:** Los cambios de precio que guardes aqui son PERMANENTES "
                "y no se pueden deshacer. Verifica bien antes de confirmar."
            )
        else:
            st.caption("⚠️ Los cambios son permanentes e irreversibles.")

        confirmar = st.checkbox(
            "Entiendo que los cambios son permanentes y deseo guardar.",
            key="ed_confirm",
        )
        if st.button("Guardar cambios permanentes", disabled=not confirmar,
                     use_container_width=True, key="ed_save"):
            cambios = []
            advertencias = []

            for i in range(len(edited)):
                for sup_col in sup_cols:
                    new_val = edited.loc[i, sup_col]
                    old_val = df_original.loc[i, sup_col]

                    if pd.isna(new_val) and pd.isna(old_val):
                        continue
                    if not pd.isna(new_val) and not pd.isna(old_val):
                        if round(float(new_val), 4) == round(float(old_val), 4):
                            continue

                    prod_i = str(df_full.loc[i, "producto"])
                    pres_i = str(df_full.loc[i, "presentacion"])
                    cat_i  = str(df_full.loc[i, "categoria"])

                    if pd.isna(new_val) and not pd.isna(old_val):
                        advertencias.append(f"**{prod_i}** / {sup_col}: precio borrado no permitido.")
                        continue

                    if pd.isna(old_val):
                        # Celda vacía → intentar INSERT si el nuevo valor es válido
                        if pd.isna(new_val) or float(new_val) <= 0:
                            continue
                        id_match = df_f[
                            (df_f["producto"]     == prod_i) &
                            (df_f["presentacion"] == pres_i) &
                            (df_f["categoria"]    == cat_i)
                        ]["id_producto"]
                        if id_match.empty:
                            advertencias.append(
                                f"**{prod_i}** / {sup_col}: no se pudo determinar el ID del producto."
                            )
                            continue
                        cambios.append({
                            "semana": sem_sel, "provincia": prov_unica,
                            "supermercado": sup_col, "categoria": cat_i,
                            "producto": prod_i, "presentacion": pres_i,
                            "id_producto": int(id_match.iloc[0]),
                            "precio_ant": None, "precio_new": float(new_val),
                            "es_insert": True,
                        })
                        continue

                    mask = (
                        (df_f["supermercado"] == sup_col) &
                        (df_f["producto"]     == prod_i) &
                        (df_f["presentacion"] == pres_i) &
                        (df_f["categoria"]    == cat_i) &
                        (df_f["provincia"]    == prov_unica)
                    )
                    matches = df_f[mask]
                    if len(matches) == 0:
                        advertencias.append(f"**{prod_i}** / {sup_col}: registro no encontrado en la DB.")
                        continue
                    if len(matches) > 1:
                        advertencias.append(f"**{prod_i}** / {sup_col}: {len(matches)} registros ambiguos.")
                        continue

                    rec = matches.iloc[0]
                    cambios.append({
                        "semana": str(rec["semana"]), "provincia": str(rec["provincia"]),
                        "supermercado": str(rec["supermercado"]), "categoria": cat_i,
                        "producto": prod_i, "presentacion": pres_i,
                        "id_producto": int(rec["id_producto"]),
                        "precio_ant": float(old_val), "precio_new": float(new_val),
                        "es_insert": False,
                    })

            for w in advertencias:
                st.warning(w)

            if not cambios:
                st.info("No se detectaron cambios validos para guardar.")
            else:
                pg = is_postgres()
                with get_conn() as con:
                    for c in cambios:
                        if c.get("es_insert"):
                            if pg:
                                con.execute(text("""
                                    INSERT INTO precios
                                        (semana, provincia, supermercado, categoria,
                                         id_producto, producto, presentacion, precio, fuente)
                                    VALUES (:semana, :provincia, :supermercado, :categoria,
                                            :id_producto, :producto, :presentacion, :precio, 'bruto')
                                    ON CONFLICT (semana, provincia, supermercado, id_producto, presentacion)
                                    DO UPDATE SET precio = EXCLUDED.precio, fuente = EXCLUDED.fuente
                                """), {
                                    "semana": c["semana"], "provincia": c["provincia"],
                                    "supermercado": c["supermercado"], "categoria": c["categoria"],
                                    "id_producto": c["id_producto"], "producto": c["producto"],
                                    "presentacion": c["presentacion"], "precio": float(c["precio_new"]),
                                })
                            else:
                                con.execute(text("""
                                    INSERT OR REPLACE INTO precios
                                        (semana, provincia, supermercado, categoria,
                                         id_producto, producto, presentacion, precio, fuente)
                                    VALUES (:semana, :provincia, :supermercado, :categoria,
                                            :id_producto, :producto, :presentacion, :precio, 'bruto')
                                """), {
                                    "semana": c["semana"], "provincia": c["provincia"],
                                    "supermercado": c["supermercado"], "categoria": c["categoria"],
                                    "id_producto": c["id_producto"], "producto": c["producto"],
                                    "presentacion": c["presentacion"], "precio": float(c["precio_new"]),
                                })
                        else:
                            con.execute(text(
                                "UPDATE precios SET precio=:precio "
                                "WHERE semana=:semana AND provincia=:provincia "
                                "AND supermercado=:supermercado "
                                "AND id_producto=:id_producto AND presentacion=:presentacion"
                            ), {
                                "precio": float(c["precio_new"]),
                                "semana": c["semana"], "provincia": c["provincia"],
                                "supermercado": c["supermercado"],
                                "id_producto": c["id_producto"], "presentacion": c["presentacion"],
                            })

                        ant_str = f"RD${c['precio_ant']:.2f}" if c["precio_ant"] is not None else "(precio nuevo)"
                        log_action(
                            "EDIT_PRICE", "precio",
                            (f"semana={c['semana']}|provincia={c['provincia']}"
                             f"|supermercado={c['supermercado']}|categoria={c['categoria']}"
                             f"|producto={c['producto']}|presentacion={c['presentacion']}"),
                            ant_str, f"RD${c['precio_new']:.2f}",
                        )
                n_insert = sum(1 for c in cambios if c.get("es_insert"))
                n_update = len(cambios) - n_insert
                partes = []
                if n_update:
                    partes.append(f"{n_update} actualizado(s)")
                if n_insert:
                    partes.append(f"{n_insert} insertado(s) nuevo(s)")
                st.success(f"{' · '.join(partes)} permanentemente.")
                if advertencias:
                    st.info(f"{len(advertencias)} celda(s) no guardadas — revisa las advertencias.")
                st.rerun()

    # ─── GESTIONAR MARCADORES (oculto en modo ampliado) ──────
    if not readonly_mode and not modo_ampliado:
        st.divider()
        with st.expander("🔖 Gestionar marcadores", expanded=False):
            st.caption(
                "Marca precios especificos para destacarlos aqui y en Comparativa de Precios. "
                "Los marcadores se guardan en Supabase y persisten al recargar."
            )

            prods_m       = sorted(df_full["producto"].unique())
            gm1, gm2, gm3 = st.columns(3)

            prod_m = gm1.selectbox("Producto", prods_m, key="ed_m_prod")

            pres_m_opts = sorted(df_full[df_full["producto"] == prod_m]["presentacion"].unique())
            pres_m = gm2.selectbox("Presentacion", pres_m_opts, key="ed_m_pres") if pres_m_opts else None

            sup_m = gm3.selectbox("Supermercado", sup_sel, key="ed_m_sup")

            cat_row_m = df_full[df_full["producto"] == prod_m]
            cat_m     = str(cat_row_m.iloc[0]["categoria"]) if not cat_row_m.empty else ""

            gm4, gm5    = st.columns(2)
            color_label = gm4.selectbox("Color / tipo de marca", list(_COLORES.keys()), key="ed_m_color")
            color_hex   = _COLORES[color_label]
            nota_m      = gm5.text_input("Nota opcional (max 100 caracteres)", max_chars=100, key="ed_m_nota")

            col_mk, col_umk = st.columns(2)
            if col_mk.button("Marcar", use_container_width=True, key="ed_m_mark"):
                if prod_m and pres_m and sup_m:
                    save_marcador(sem_sel, prov_unica, sup_m, cat_m, prod_m, pres_m,
                                  color=color_hex, nota=nota_m.strip())
                    log_action(
                        "MARK_PRICE", "marcador",
                        (f"semana={sem_sel}|provincia={prov_unica}|supermercado={sup_m}"
                         f"|producto={prod_m}|presentacion={pres_m}|color={color_hex}"),
                        "", nota_m.strip(),
                    )
                    st.success(f"Marcado: {prod_m} — {sup_m}")
                    st.rerun()

            if col_umk.button("Desmarcar", use_container_width=True, key="ed_m_unmark"):
                if prod_m and pres_m and sup_m:
                    delete_marcador(sem_sel, prov_unica, sup_m, cat_m, prod_m, pres_m)
                    log_action(
                        "UNMARK_PRICE", "marcador",
                        (f"semana={sem_sel}|provincia={prov_unica}|supermercado={sup_m}"
                         f"|producto={prod_m}|presentacion={pres_m}"),
                        "", "",
                    )
                    st.success(f"Desmarcado: {prod_m} — {sup_m}")
                    st.rerun()

            st.divider()
            if df_marc.empty:
                st.caption("No hay marcas activas para esta semana y provincia.")
            else:
                st.caption(f"{len(df_marc)} marca(s) activa(s) — {fmt_sem(sem_sel, 'corta')} · {prov_unica}")
                for row_idx, row_m in df_marc.iterrows():
                    emoji  = _EMOJI.get(row_m.get("color", ""), "●")
                    prod_r = row_m.get("producto", "")
                    pres_r = row_m.get("presentacion", "")
                    sup_r  = row_m.get("supermercado", "")
                    nota_r = str(row_m.get("nota", "") or "")
                    user_r = row_m.get("username", "")
                    ts_r   = row_m.get("created_at", "")

                    col_card, col_del = st.columns([6, 1])
                    with col_card:
                        st.markdown(
                            f"<div style='padding:.4rem .75rem;border:1px solid rgba(148,163,184,0.12);"
                            f"border-radius:8px;background:rgba(15,23,42,0.5);"
                            f"display:flex;align-items:center;gap:.65rem;flex-wrap:wrap;'>"
                            f"<span style='font-size:1.1rem;'>{emoji}</span>"
                            f"<span style='color:#F8FAFC;font-size:.82rem;font-weight:600;'>{prod_r}</span>"
                            f"<span style='color:#94A3B8;font-size:.78rem;'>{pres_r}</span>"
                            f"<span style='color:#3B82F6;font-size:.78rem;font-weight:600;'>{sup_r}</span>"
                            + (f"<span style='color:#CBD5E1;font-size:.75rem;font-style:italic;'>\"{nota_r}\"</span>" if nota_r else "")
                            + f"<span style='color:#475569;font-size:.72rem;margin-left:auto;'>{user_r} · {ts_r}</span>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                    with col_del:
                        if st.button("✕", key=f"del_marc_{row_idx}", help="Desmarcar este precio"):
                            cat_r = str(row_m.get("categoria", ""))
                            delete_marcador(sem_sel, prov_unica, sup_r, cat_r, prod_r, pres_r)
                            log_action(
                                "UNMARK_PRICE", "marcador",
                                f"semana={sem_sel}|provincia={prov_unica}|supermercado={sup_r}"
                                f"|producto={prod_r}|presentacion={pres_r}",
                                "", "",
                            )
                            st.rerun()
