import streamlit as st
import pandas as pd
from sqlalchemy import text
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode, JsCode

from data.database import (
    load_all, get_conn, DEMO_MODE, log_action,
    save_marcador, delete_marcador, load_marcadores,
    is_postgres,
)
from utils.dates import fmt_sem
from styles.theme import get_theme_tokens, get_mode, light_df

_COLORES = {
    "🟡 Amarillo — atencion":  "#D97706",
    "🔴 Rojo — problema":      "#DC2626",
    "🟢 Verde — validado":     "#16A34A",
    "🔵 Azul — pendiente":     "#2563EB",
    "🟠 Naranja — revisar":    "#EA580C",
}

_EMOJI = {
    "#D97706": "🟡",
    "#DC2626": "🔴",
    "#16A34A": "🟢",
    "#2563EB": "🔵",
    "#EA580C": "🟠",
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


_OUTLIER_THRESH = 0.15  # 15 % de desviacion respecto al promedio del grupo


def _detect_outliers_row(row_series, sup_cols, threshold=_OUTLIER_THRESH):
    """Supermercados cuyo precio se desvía más del umbral vs la media del grupo."""
    prices = []
    for c in sup_cols:
        try:
            v = float(row_series[c])
            if v > 0:
                prices.append((c, v))
        except (TypeError, ValueError):
            pass
    if len(prices) < 2:
        return ""
    mean_p = sum(v for _, v in prices) / len(prices)
    if mean_p == 0:
        return ""
    parts = []
    for sup, price in prices:
        dev = (price - mean_p) / mean_p * 100
        if abs(dev) > threshold * 100:
            icon = "▲" if dev > 0 else "▼"
            parts.append(f"{icon}{abs(dev):.0f}% {sup}")
    return " · ".join(parts)


def _fmt_delta(v):
    """Formatea la variacion porcentual vs semana anterior."""
    try:
        if v is None or pd.isna(v):
            return "—"
    except Exception:
        return "—"
    v = float(v)
    sign = "+" if v > 0 else ""
    alert = " ⚠️" if abs(v) > 3 else ""
    return f"{sign}{v:.1f}%{alert}"


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

    cats    = sorted(df_sem["categoria"].dropna().unique())
    cat_sel = fc2.multiselect("Categoria", cats, default=[], key="ed_cat",
                              placeholder="Todas las categorias")
    df_cat  = df_sem if not cat_sel else df_sem[df_sem["categoria"].isin(cat_sel)]

    provincias = sorted(df_sem["provincia"].dropna().unique())
    sups_all   = sorted(df_sem["supermercado"].dropna().unique())

    fd1, fd2 = st.columns(2)
    _prov_default = [p for p in ["Santo Domingo"] if p in provincias]
    prov_sel = fd1.multiselect("Provincia", provincias, default=_prov_default, key="ed_prov")
    sup_sel  = fd2.multiselect("Supermercado", sups_all, default=sups_all, key="ed_sup")

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
    if cat_sel:
        df_f = df_f[df_f["categoria"].isin(cat_sel)]
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

    # ─── SEMANA ANTERIOR (variacion semana a semana) ─────────
    idx_sem = semanas.index(sem_sel) if sem_sel in semanas else -1
    sem_ant = semanas[idx_sem - 1] if idx_sem > 0 else None
    df_prom_ant = pd.DataFrame()
    if sem_ant is not None:
        df_f_ant = df[df["semana"] == sem_ant].copy()
        if prov_sel:
            df_f_ant = df_f_ant[df_f_ant["provincia"].isin(prov_sel)]
        if not df_f_ant.empty:
            df_prom_ant = (
                df_f_ant.groupby(idx_cols, sort=False)["precio"]
                .mean().round(2).reset_index()
                .rename(columns={"precio": "_prom_ant_"})
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

    # ─── OUTLIERS ────────────────────────────────────────────
    df_pivot["_outlier_"] = df_pivot.apply(
        lambda r: _detect_outliers_row(r, sup_cols), axis=1
    )

    # ─── VARIACION VS SEMANA ANTERIOR ────────────────────────
    if not df_prom_ant.empty:
        df_pivot = df_pivot.merge(df_prom_ant, on=idx_cols, how="left")
        df_pivot["_delta_pct_"] = (
            (df_pivot["_prom_"] - df_pivot["_prom_ant_"]) / df_pivot["_prom_ant_"] * 100
        ).round(1)
    else:
        df_pivot["_delta_pct_"] = float("nan")
    df_pivot["_delta_str_"] = df_pivot["_delta_pct_"].apply(_fmt_delta)

    df_full = df_pivot[idx_cols + sup_cols + ["_prom_", "_delta_pct_", "_marcas_"]].copy().reset_index(drop=True)

    fixed_disp = ["categoria", "producto"] + (["presentacion"] if show_pres else [])
    all_cols   = fixed_disp + ["_outlier_"] + sup_cols + ["_prom_", "_delta_str_", "_marcas_"]

    df_display  = (
        df_pivot[all_cols]
        .rename(columns={
            "_prom_":      "Promedio",
            "_marcas_":    "\U0001f516 Marcas",
            "_outlier_":   "⚠️ Atipico",
            "_delta_str_": "\U0001f4ca Δ sem.ant.",
        })
        .reset_index(drop=True)
    )
    df_original = df_display.copy()

    # ─── CONTROLES DE VISTA ──────────────────────────────────
    cv1, cv2, cv3 = st.columns([2, 2, 1])
    with cv1:
        solo_marcados = st.checkbox(
            "Mostrar solo productos marcados", value=False, key="ed_solo_marc"
        )
    with cv2:
        solo_alertas = st.checkbox(
            "⚠️ Solo con precios atipicos", value=False, key="ed_solo_alertas",
            help="Muestra solo filas donde algun supermercado se desvía mas del 15% del promedio del grupo.",
        )
    with cv3:
        modo_ampliado = st.checkbox(
            "⛶ Modo ampliado", value=False, key="ed_ampliado",
            help="Oculta el sidebar y agranda la tabla para trabajar mas comodo.",
        )

    # Inyectar CSS si modo ampliado esta activo
    if modo_ampliado:
        st.markdown(_CSS_AMPLIADO, unsafe_allow_html=True)

    # Aplicar filtros de vista
    if solo_marcados:
        mask_m     = df_display["\U0001f516 Marcas"].str.len() > 0
        df_display = df_display[mask_m].reset_index(drop=True)
        df_full    = df_full[mask_m].reset_index(drop=True)
    if solo_alertas:
        mask_a     = df_display["⚠️ Atipico"].str.len() > 0
        df_display = df_display[mask_a].reset_index(drop=True)
        df_full    = df_full[mask_a].reset_index(drop=True)
    df_original = df_display.copy()
    if (solo_marcados or solo_alertas) and df_display.empty:
        msgs = []
        if solo_marcados:
            msgs.append("marcados")
        if solo_alertas:
            msgs.append("con alertas")
        st.info(f"No hay productos {' y '.join(msgs)} con los filtros actuales.")
        return

    # ─── SUBTITULO ───────────────────────────────────────────
    st.divider()
    info_parts = [f"**{fmt_sem(sem_sel, 'larga')}**"]
    if prov_sel:
        info_parts.append(f"Provincia: {', '.join(prov_sel)}")
    info_parts += [f"{len(df_display):,} productos", f"{len(sup_cols)} supermercado(s)"]
    st.caption("  ·  ".join(info_parts))

    tbl_height = _table_height(len(df_display), modo_ampliado)

    # ─── TABLA ───────────────────────────────────────────────
    if readonly_mode:
        st.caption("Modo solo lectura — selecciona exactamente una provincia para editar.")
        st.dataframe(light_df(df_display), use_container_width=True, hide_index=True, height=tbl_height)

    else:
        if not modo_ampliado:
            st.markdown(
                "#### Precios por supermercado  "
                "<small style='font-weight:normal;color:var(--t2);'>"
                "clic para editar · Tab/Enter para navegar · Ctrl+Z para deshacer</small>",
                unsafe_allow_html=True,
            )

        # ── Datos para AG Grid (columnas ocultas para JS styling) ────
        df_ag = df_display.copy()
        df_ag["_prom_raw_"]  = df_full["_prom_"].values
        df_ag["_delta_raw_"] = df_full["_delta_pct_"].values
        df_ag["_row_idx_"]   = range(len(df_ag))

        # Cache: preservar edits entre reruns; reiniciar cuando cambien los filtros
        _ag_ck = (f"{sem_sel}|{sorted(prov_sel)}|{sorted(cat_sel)}|{prod_sel}"
                  f"|{pres_sel}|{sorted(sup_sel)}|{solo_marcados}|{solo_alertas}")
        if st.session_state.get("_ed_ag_ckey") != _ag_ck:
            st.session_state["_ed_ag_df"]   = df_ag.copy()
            st.session_state["_ed_ag_ckey"] = _ag_ck

        # ── JS: estilos condicionales — colors from centralized token system ──
        _T = get_theme_tokens(get_mode())
        _js_px_style = JsCode(f"""
        function(params) {{
            if (params.value == null || params.value <= 0) return null;
            var p = params.data._prom_raw_;
            if (!p || p <= 0) return null;
            var d = (params.value - p) / p * 100;
            if (d > 15)  return {{backgroundColor:'{_T["GRID_HIGH_BG"]}', color:'{_T["GRID_HIGH_FG"]}', fontWeight:'700'}};
            if (d < -15) return {{backgroundColor:'{_T["GRID_LOW_BG"]}', color:'{_T["GRID_LOW_FG"]}', fontWeight:'700'}};
            return null;
        }}
        """)
        _js_px_fmt = JsCode("""
        function(params) {
            if (params.value == null || params.value === '') return '';
            return 'RD$ ' + parseFloat(params.value).toFixed(2);
        }
        """)
        _js_px_tip = JsCode("""
        function(params) {
            if (params.value == null || params.value <= 0) return '';
            var p = params.data._prom_raw_;
            if (!p || p <= 0) return 'RD$ ' + parseFloat(params.value).toFixed(2);
            var d = ((params.value - p) / p * 100).toFixed(1);
            var s = parseFloat(d) >= 0 ? '+' : '';
            return 'RD$ ' + parseFloat(params.value).toFixed(2) +
                   '  |  Prom: RD$ ' + parseFloat(p).toFixed(2) +
                   '  |  Desv: ' + s + d + '%';
        }
        """)
        _js_dt_style = JsCode(f"""
        function(params) {{
            var r = params.data._delta_raw_;
            if (r == null || isNaN(r)) return {{color:'{_T["GRID_DELTA_NEU"]}'}};
            if (r > 3)  return {{color:'{_T["GRID_DELTA_POS"]}', fontWeight:'600'}};
            if (r < -3) return {{color:'{_T["GRID_DELTA_NEG"]}', fontWeight:'600'}};
            return {{color:'{_T["GRID_DELTA_FAINT"]}'}};
        }}
        """)
        _js_ot_style = JsCode(f"""
        function(params) {{
            if (!params.value) return null;
            if (params.value.indexOf('▲') >= 0)
                return {{color:'{_T["GRID_OT_HIGH"]}', fontWeight:'700'}};
            if (params.value.indexOf('▼') >= 0)
                return {{color:'{_T["GRID_OT_LOW"]}', fontWeight:'700'}};
            return null;
        }}
        """)

        # ── Construir gridOptions ─────────────────────────────────────
        gb = GridOptionsBuilder.from_dataframe(st.session_state["_ed_ag_df"])
        gb.configure_default_column(
            resizable=True, sortable=True, filter=False,
            editable=False, suppressMovable=False,
            wrapHeaderText=True, autoHeaderHeight=True, minWidth=80,
        )
        for c in fixed_disp:
            gb.configure_column(c, pinned="left", editable=False,
                                width=130, suppressMovable=True, filter=True)
        gb.configure_column("⚠️ Atipico", editable=False, width=215,
                            cellStyle=_js_ot_style, tooltipField="⚠️ Atipico")
        for c in sup_cols:
            gb.configure_column(c, editable=True, type=["numericColumn"],
                                width=148, singleClickEdit=True,
                                cellStyle=_js_px_style,
                                valueFormatter=_js_px_fmt,
                                tooltipValueGetter=_js_px_tip)
        gb.configure_column("Promedio", editable=False, type=["numericColumn"],
                            width=130, valueFormatter=_js_px_fmt)
        gb.configure_column("\U0001f4ca Δ sem.ant.", editable=False,
                            width=130, cellStyle=_js_dt_style)
        gb.configure_column("\U0001f516 Marcas", editable=False, width=215)
        gb.configure_column("_prom_raw_",  hide=True)
        gb.configure_column("_delta_raw_", hide=True)
        gb.configure_column("_row_idx_",   hide=True)
        gb.configure_grid_options(
            rowHeight=38, headerHeight=44,
            suppressRowClickSelection=True,
            enableBrowserTooltips=True,
            stopEditingWhenCellsLoseFocus=True,
            undoRedoCellEditing=True,
            undoRedoCellEditingLimit=20,
        )
        go = gb.build()

        _ag_theme = "alpine"  # st_aggrid 1.0.5 only has alpine/balham/material/streamlit
        grid_resp = AgGrid(
            st.session_state["_ed_ag_df"],
            gridOptions=go,
            update_mode=GridUpdateMode.VALUE_CHANGED,
            data_return_mode=DataReturnMode.AS_INPUT,
            theme=_ag_theme,
            height=tbl_height,
            allow_unsafe_jscode=True,
            fit_columns_on_grid_load=False,
            key=f"aggrid_precios_{_ag_theme}",
        )

        # Persistir edits entre reruns del mismo conjunto de filtros
        _resp_data = grid_resp.get("data")
        if _resp_data is not None and len(_resp_data) > 0:
            st.session_state["_ed_ag_df"] = pd.DataFrame(_resp_data)
        edited_df = pd.DataFrame(st.session_state["_ed_ag_df"])

        # ── GUARDAR CAMBIOS ──────────────────────────────────────────
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

            for _, er in edited_df.iterrows():
                ri     = int(er["_row_idx_"])
                prod_i = str(df_full.loc[ri, "producto"])
                pres_i = str(df_full.loc[ri, "presentacion"])
                cat_i  = str(df_full.loc[ri, "categoria"])

                for sup_col in sup_cols:
                    # Valor editado
                    try:
                        _nv = er[sup_col]
                        if _nv is None or str(_nv) in ("", "None", "nan"):
                            new_val = None
                        else:
                            _nv_f = float(_nv)
                            new_val = None if pd.isna(_nv_f) else _nv_f
                    except (TypeError, ValueError, KeyError):
                        new_val = None

                    # Valor original
                    try:
                        _ov = df_original.iloc[ri][sup_col]
                        if _ov is None or str(_ov) in ("", "None"):
                            old_val = None
                        elif pd.isna(_ov):
                            old_val = None
                        else:
                            old_val = float(_ov)
                    except (TypeError, ValueError):
                        old_val = None

                    if new_val is None and old_val is None:
                        continue
                    if new_val is not None and old_val is not None:
                        if round(new_val, 4) == round(old_val, 4):
                            continue

                    if new_val is None and old_val is not None:
                        advertencias.append(f"**{prod_i}** / {sup_col}: precio borrado no permitido.")
                        continue

                    if old_val is None:
                        if new_val <= 0:
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
                            "precio_ant": None, "precio_new": new_val,
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
                        "precio_ant": old_val, "precio_new": new_val,
                        "es_insert": False,
                    })

            for w in advertencias:
                st.warning(w)

            if not cambios:
                st.info("No se detectaron cambios validos para guardar.")
            else:
                pg = is_postgres()
                n_insert = sum(1 for c in cambios if c.get("es_insert"))
                n_update = len(cambios) - n_insert
                try:
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
                            if c["precio_ant"] is not None and c["precio_ant"] != 0:
                                _diff_abs = c["precio_new"] - c["precio_ant"]
                                _diff_pct = _diff_abs / c["precio_ant"] * 100
                                _diff_str = f"|diff_abs={_diff_abs:+.2f}|diff_pct={_diff_pct:+.2f}"
                            else:
                                _diff_str = "|diff_abs=N/A|diff_pct=N/A"
                            log_action(
                                "EDIT_PRICE", "precio",
                                (f"semana={c['semana']}|provincia={c['provincia']}"
                                 f"|supermercado={c['supermercado']}|categoria={c['categoria']}"
                                 f"|producto={c['producto']}|presentacion={c['presentacion']}"
                                 f"{_diff_str}|success=true"),
                                ant_str, f"RD${c['precio_new']:.2f}",
                            )

                    if len(cambios) > 1:
                        log_action(
                            "BULK_EDIT_PRICE", "precio",
                            f"semana={sem_sel}|provincia={prov_unica}|n_update={n_update}|n_insert={n_insert}|success=true",
                            "", f"{n_update} actualizados · {n_insert} insertados",
                        )
                    partes = []
                    if n_update:
                        partes.append(f"{n_update} actualizado(s)")
                    if n_insert:
                        partes.append(f"{n_insert} insertado(s) nuevo(s)")
                    st.success(f"{' · '.join(partes)} permanentemente.")
                    if advertencias:
                        st.info(f"{len(advertencias)} celda(s) no guardadas — revisa las advertencias.")
                    st.session_state.pop("_ed_ag_df",   None)
                    st.session_state.pop("_ed_ag_ckey", None)
                    st.rerun()
                except Exception as _err:
                    log_action(
                        "PRICE_ERROR", "precio",
                        f"semana={sem_sel}|provincia={prov_unica}|success=false|error={str(_err)[:200]}",
                        "", "",
                    )
                    st.error(f"Error al guardar los cambios: {_err}")

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
                    _prev = df_marc[
                        (df_marc["supermercado"] == sup_m) &
                        (df_marc["producto"]     == prod_m) &
                        (df_marc["presentacion"] == pres_m)
                    ] if not df_marc.empty else pd.DataFrame()
                    _estado_ant_mk = f"color={_prev.iloc[0]['color']}" if not _prev.empty else "sin_marca"
                    save_marcador(sem_sel, prov_unica, sup_m, cat_m, prod_m, pres_m,
                                  color=color_hex, nota=nota_m.strip())
                    log_action(
                        "MARK_PRICE", "marcador",
                        (f"semana={sem_sel}|provincia={prov_unica}|supermercado={sup_m}"
                         f"|categoria={cat_m}|producto={prod_m}|presentacion={pres_m}"),
                        _estado_ant_mk,
                        f"color={color_hex}|nota={nota_m.strip()[:50]}",
                    )
                    st.success(f"Marcado: {prod_m} — {sup_m}")
                    st.rerun()

            if col_umk.button("Desmarcar", use_container_width=True, key="ed_m_unmark"):
                if prod_m and pres_m and sup_m:
                    _cur = df_marc[
                        (df_marc["supermercado"] == sup_m) &
                        (df_marc["producto"]     == prod_m) &
                        (df_marc["presentacion"] == pres_m)
                    ] if not df_marc.empty else pd.DataFrame()
                    _estado_ant_umk = f"color={_cur.iloc[0]['color']}" if not _cur.empty else "marcado"
                    delete_marcador(sem_sel, prov_unica, sup_m, cat_m, prod_m, pres_m)
                    log_action(
                        "UNMARK_PRICE", "marcador",
                        (f"semana={sem_sel}|provincia={prov_unica}|supermercado={sup_m}"
                         f"|categoria={cat_m}|producto={prod_m}|presentacion={pres_m}"),
                        _estado_ant_umk,
                        "sin_marca",
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
                            f"<div style='padding:.4rem .75rem;border:1px solid var(--bd);"
                            f"border-radius:8px;background:var(--bg-subtle);"
                            f"display:flex;align-items:center;gap:.65rem;flex-wrap:wrap;'>"
                            f"<span style='font-size:1.1rem;'>{emoji}</span>"
                            f"<span style='color:var(--t0);font-size:.82rem;font-weight:600;'>{prod_r}</span>"
                            f"<span style='color:var(--t2);font-size:.78rem;'>{pres_r}</span>"
                            f"<span style='color:#2563EB;font-size:.78rem;font-weight:600;'>{sup_r}</span>"
                            + (f"<span style='color:var(--t1);font-size:.75rem;font-style:italic;'>\"{nota_r}\"</span>" if nota_r else "")
                            + f"<span style='color:var(--t3);font-size:.72rem;margin-left:auto;'>{user_r} · {ts_r}</span>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                    with col_del:
                        if st.button("✕", key=f"del_marc_{row_idx}", help="Desmarcar este precio"):
                            cat_r = str(row_m.get("categoria", ""))
                            _estado_ant_r = (
                                f"color={row_m.get('color', '')}|nota={str(row_m.get('nota','') or '')[:50]}"
                            )
                            delete_marcador(sem_sel, prov_unica, sup_r, cat_r, prod_r, pres_r)
                            log_action(
                                "UNMARK_PRICE", "marcador",
                                f"semana={sem_sel}|provincia={prov_unica}|supermercado={sup_r}"
                                f"|categoria={cat_r}|producto={prod_r}|presentacion={pres_r}",
                                _estado_ant_r,
                                "sin_marca",
                            )
                            st.rerun()

    # ─── ZONA DE RIESGO: RESTABLECER PRECIOS ────────────────
    if not readonly_mode and not modo_ampliado:
        st.divider()
        with st.expander("⚠️ Zona de riesgo — Restablecer precios", expanded=False):
            st.warning(
                "**Accion destructiva e irreversible.** Elimina todos los precios registrados "
                "para la semana, provincia y supermercados indicados. "
                "Necesitaras volver a cargar los datos desde el archivo original."
            )
            rst_sups = st.multiselect(
                "Supermercados a restablecer", sup_sel, default=sup_sel, key="rst_sups",
                help="Solo se eliminaran los precios de los supermercados seleccionados.",
            )
            rst_confirm = st.checkbox(
                "Confirmo que esta accion es irreversible y deseo continuar.",
                key="rst_confirm",
            )
            if st.button(
                "Restablecer precios",
                key="rst_btn",
                disabled=(not rst_confirm or not rst_sups),
                use_container_width=True,
                type="primary",
            ):
                try:
                    with get_conn() as con:
                        for rst_sup in rst_sups:
                            con.execute(text(
                                "DELETE FROM precios "
                                "WHERE semana=:sem AND provincia=:prov AND supermercado=:sup"
                            ), {"sem": sem_sel, "prov": prov_unica, "sup": rst_sup})
                    log_action(
                        "RESTORE_PRICES", "precio",
                        f"semana={sem_sel}|provincia={prov_unica}|supermercados={','.join(rst_sups)}|success=true",
                        f"{len(rst_sups)} supermercado(s)",
                        "precios eliminados",
                    )
                    st.success(
                        f"Precios eliminados para {len(rst_sups)} supermercado(s). "
                        "Vuelve a cargar los datos desde Carga de Datos."
                    )
                    st.rerun()
                except Exception as _rst_err:
                    log_action(
                        "PRICE_ERROR", "precio",
                        f"semana={sem_sel}|provincia={prov_unica}|accion=restore|success=false|error={str(_rst_err)[:200]}",
                        "", "",
                    )
                    st.error(f"Error al restablecer precios: {_rst_err}")
