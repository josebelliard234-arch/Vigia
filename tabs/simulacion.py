import streamlit as st
import pandas as pd

from utils.dates import fmt_sem


def render_simulacion(ctx):
    st.subheader("Simulacion Temporal de Precios")
    st.info(
        "**Modo simulacion:** Los cambios que hagas aqui NO se guardan en la base de datos. "
        "Son temporales y se descartan al cerrar la sesion o al restablecer."
    )

    df_all = ctx.df_all

    if df_all.empty:
        st.warning("No hay datos disponibles. Contacta al administrador para cargar datos.")
        return

    # Inicializar o restaurar DataFrame de simulacion en session_state
    if "sim_df" not in st.session_state:
        st.session_state["sim_df"] = df_all.copy()

    col_reset, _ = st.columns([1, 4])
    with col_reset:
        if st.button("Restablecer simulacion", key="sim_reset_btn"):
            st.session_state["sim_df"] = df_all.copy()
            st.rerun()

    sim_df = st.session_state["sim_df"]

    # ---- Filtros ----
    st.markdown("#### Filtros")
    sf1, sf2, sf3 = st.columns(3)
    semanas = sorted(sim_df["semana"].dropna().unique())
    sem_sel = sf1.selectbox(
        "Semana", semanas, index=len(semanas) - 1, key="sim_sem",
        format_func=fmt_sem
    )
    df_f = sim_df[sim_df["semana"] == sem_sel].copy()

    cats = sorted(df_f["categoria"].dropna().unique())
    cat_sel = sf2.multiselect("Categoria", cats, default=[], key="sim_cat",
                              placeholder="Todas las categorias")
    if cat_sel:
        df_f = df_f[df_f["categoria"].isin(cat_sel)]

    prods = ["Todos"] + sorted(df_f["producto"].dropna().unique())
    prod_sel = sf3.selectbox("Producto", prods, key="sim_prod")
    if prod_sel != "Todos":
        df_f = df_f[df_f["producto"] == prod_sel]

    if df_f.empty:
        st.info("No hay registros con estos filtros.")
        return

    # Indices reales en sim_df para actualizar luego
    idx_originales = df_f.index.tolist()
    df_f_reset = df_f.reset_index(drop=True)

    cols_show = ["semana", "provincia", "supermercado", "categoria",
                 "producto", "presentacion", "precio"]
    df_show = df_f_reset[cols_show].copy()

    st.markdown("#### Edita los precios — solo visualizacion temporal")
    edited = st.data_editor(
        df_show,
        column_config={
            "semana":       st.column_config.TextColumn("Semana",       disabled=True),
            "provincia":    st.column_config.TextColumn("Provincia",    disabled=True),
            "supermercado": st.column_config.TextColumn("Supermercado", disabled=True),
            "categoria":    st.column_config.TextColumn("Categoria",    disabled=True),
            "producto":     st.column_config.TextColumn("Producto",     disabled=True),
            "presentacion": st.column_config.TextColumn("Presentacion", disabled=True),
            "precio":       st.column_config.NumberColumn("Precio (RD$)", min_value=0.0, format="%.2f"),
        },
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        key="sim_editor",
    )

    # Propagar cambios al sim_df en session_state
    if not edited["precio"].equals(df_show["precio"]):
        for local_idx, orig_idx in enumerate(idx_originales):
            st.session_state["sim_df"].loc[orig_idx, "precio"] = edited.loc[local_idx, "precio"]

    # ---- Metricas simuladas ----
    sim_sem = st.session_state["sim_df"][st.session_state["sim_df"]["semana"] == sem_sel]
    if cat_sel != "Todas":
        sim_sem = sim_sem[sim_sem["categoria"] == cat_sel]
    if prod_sel != "Todos":
        sim_sem = sim_sem[sim_sem["producto"] == prod_sel]

    st.divider()
    st.markdown("#### Metricas simuladas (basadas en los cambios de arriba)")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Precio promedio simulado",
              f"RD$ {sim_sem['precio'].mean():,.2f}" if not sim_sem.empty else "N/D")
    m2.metric("Precio minimo simulado",
              f"RD$ {sim_sem['precio'].min():,.2f}" if not sim_sem.empty else "N/D")
    m3.metric("Precio maximo simulado",
              f"RD$ {sim_sem['precio'].max():,.2f}" if not sim_sem.empty else "N/D")
    m4.metric("Registros simulados", f"{len(sim_sem):,}")

    # Comparacion contra datos originales
    orig_sem = df_all[df_all["semana"] == sem_sel]
    if cat_sel != "Todas":
        orig_sem = orig_sem[orig_sem["categoria"] == cat_sel]
    if prod_sel != "Todos":
        orig_sem = orig_sem[orig_sem["producto"] == prod_sel]

    if not orig_sem.empty and not sim_sem.empty:
        delta_prom = sim_sem["precio"].mean() - orig_sem["precio"].mean()
        st.caption(
            f"Variacion promedio vs datos originales: "
            f"**{'+'if delta_prom>=0 else ''}{delta_prom:,.2f} RD$**"
        )

    st.markdown(
        "<div style='margin-top:1rem;padding:.5rem .8rem;border-radius:10px;"
        "background:rgba(245,158,11,0.12);border:1px solid rgba(245,158,11,0.3);"
        "font-size:.8rem;color:#D97706;'>"
        "Estos datos son solo una simulacion. Ningun cambio fue guardado en la base de datos.</div>",
        unsafe_allow_html=True,
    )
