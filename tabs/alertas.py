import streamlit as st
import pandas as pd

from styles.theme import light_df
from utils.dates import fmt_sem


def render_alertas(ctx):
    st.subheader("Alertas de Precio")
    st.caption(
        "Detecta alzas, bajas y estabilidad de precio entre la semana actual "
        "y la semana comparada seleccionadas en los filtros principales."
    )

    df_all    = ctx.df_all
    sem_act   = ctx.semana_actual
    sem_comp  = ctx.semana_comp
    sa_lbl    = ctx.sa_lbl
    sc_lbl    = ctx.sc_lbl

    if df_all.empty:
        st.info("No hay datos disponibles.")
        return

    if not sem_act or not sem_comp:
        st.info("Selecciona dos semanas en los filtros principales.")
        return

    # ---- Umbrales configurables ----
    st.markdown("#### Umbrales de clasificacion")
    ua1, ua2, ua3 = st.columns(3)
    umbral_alza  = ua1.slider("Alza (%)", min_value=1,  max_value=30, value=5,  step=1, key="alerta_alza")
    umbral_baja  = ua2.slider("Baja (%)", min_value=-30, max_value=-1, value=-5, step=1, key="alerta_baja")
    umbral_estab = ua3.slider("Estabilidad +/- (%)", min_value=0, max_value=5, value=1, step=1, key="alerta_estab")

    # ---- Datos por semana ----
    df_act  = df_all[df_all["semana"] == sem_act].copy()
    df_cmp  = df_all[df_all["semana"] == sem_comp].copy()

    if df_act.empty or df_cmp.empty:
        st.warning("No hay datos para una o ambas semanas seleccionadas.")
        return

    # Promedio por producto+presentacion+categoria (agrupado para evitar duplicados por provincia)
    agg_act = (
        df_act.groupby(["producto", "presentacion", "categoria"])["precio"]
        .mean().reset_index().rename(columns={"precio": "precio_actual"})
    )
    agg_cmp = (
        df_cmp.groupby(["producto", "presentacion", "categoria"])["precio"]
        .mean().reset_index().rename(columns={"precio": "precio_comp"})
    )

    merged = pd.merge(agg_act, agg_cmp, on=["producto", "presentacion", "categoria"])

    if merged.empty:
        st.warning("No hay productos en comun entre las dos semanas.")
        return

    merged["var_abs"] = merged["precio_actual"] - merged["precio_comp"]
    merged["var_pct"] = (merged["var_abs"] / merged["precio_comp"].replace(0, pd.NA)) * 100

    def clasificar(pct):
        if pd.isna(pct):
            return "Sin datos"
        if pct >= umbral_alza:
            return "Alza de precio"
        if pct <= umbral_baja:
            return "Baja de precio"
        if abs(pct) <= umbral_estab:
            return "Estabilidad de precio"
        return "Variacion moderada"

    merged["tipo_alerta"] = merged["var_pct"].apply(clasificar)
    merged["semana_actual"]    = sa_lbl
    merged["semana_comparada"] = sc_lbl

    # ---- KPIs ----
    kc1, kc2, kc3, kc4 = st.columns(4)
    kc1.metric("Total productos",    len(merged))
    kc2.metric("Alzas detectadas",   int((merged["tipo_alerta"] == "Alza de precio").sum()))
    kc3.metric("Bajas detectadas",   int((merged["tipo_alerta"] == "Baja de precio").sum()))
    kc4.metric("Estables",           int((merged["tipo_alerta"] == "Estabilidad de precio").sum()))

    st.divider()

    # ---- Filtro por tipo ----
    tipos_disp = ["Todos"] + sorted(merged["tipo_alerta"].unique().tolist())
    tipo_sel   = st.selectbox("Filtrar por tipo de alerta", tipos_disp, key="alerta_tipo")

    df_show = merged if tipo_sel == "Todos" else merged[merged["tipo_alerta"] == tipo_sel]

    cols_tabla = [
        "tipo_alerta", "producto", "presentacion", "categoria",
        "precio_comp", "precio_actual", "var_abs", "var_pct",
        "semana_comparada", "semana_actual",
    ]

    st.dataframe(
        light_df(
            df_show[cols_tabla].rename(columns={
                "tipo_alerta":      "Tipo",
                "producto":         "Producto",
                "presentacion":     "Presentacion",
                "categoria":        "Categoria",
                "precio_comp":      f"Precio {sc_lbl}",
                "precio_actual":    f"Precio {sa_lbl}",
                "var_abs":          "Var. Absoluta",
                "var_pct":          "Var. %",
                "semana_comparada":  "Semana comparada",
                "semana_actual":    "Semana actual",
            }).style.format({
                f"Precio {sc_lbl}": "RD$ {:.2f}",
                f"Precio {sa_lbl}": "RD$ {:.2f}",
                "Var. Absoluta":    "{:+.2f}",
                "Var. %":           "{:+.2f}%",
            })
        ),
        use_container_width=True,
        hide_index=True,
    )

    # ---- Descarga CSV ----
    csv = df_show[cols_tabla].to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Descargar alertas como CSV",
        data=csv,
        file_name=f"alertas_{sem_act}_vs_{sem_comp}.csv",
        mime="text/csv",
        key="alerta_dl",
    )
