import re
import numpy as np
import pandas as pd

from utils.dates import semana_label_a_datetime
from utils.formatting import norm_key, fmt_rdp, fmt_pct


# ============================================================
# PROYECCION LINEAL
# ============================================================
def linear_projection(semanas, precios, n_weeks=4):
    x = np.arange(len(semanas))
    if len(x) < 2:
        return [], []
    m, b = np.polyfit(x, precios, 1)
    future_x      = np.arange(len(semanas), len(semanas) + n_weeks)
    future_prices = m * future_x + b
    last = semanas[-1]
    year, wk = int(last[:4]), int(last[6:])
    future_labels = []
    for i in range(1, n_weeks + 1):
        nwk = wk + i
        yr  = year
        while nwk > 52:
            nwk -= 52
            yr  += 1
        future_labels.append(f"{yr}-W{nwk:02d}")
    return future_labels, future_prices.tolist()


def proyeccion_despues_de_semana_corte(semanas, precios, n_weeks=4, semana_corte=None):
    """
    Calcula proyecciones evitando que la semana actual/bruta salga como proyeccion.

    Si existe una semana actual bruta posterior al ultimo dato validado, la proyeccion
    empieza DESPUES de esa semana. Ejemplo: si el historico validado termina en W21
    y la semana actual bruta es W23, la proyeccion visible empieza en W24.
    """
    if len(semanas) < 2:
        return [], []

    extra = 0
    fecha_ultima = semana_label_a_datetime(semanas[-1])
    fecha_corte = semana_label_a_datetime(semana_corte) if semana_corte else None

    if fecha_ultima and fecha_corte and fecha_corte > fecha_ultima:
        extra = max(0, int((fecha_corte - fecha_ultima).days // 7))

    labels, prices = linear_projection(semanas, precios, n_weeks + extra)

    if fecha_corte:
        pares = []
        for lbl, price in zip(labels, prices):
            fecha_lbl = semana_label_a_datetime(lbl)
            if fecha_lbl is None or fecha_lbl > fecha_corte:
                pares.append((lbl, price))
        pares = pares[:n_weeks]
        return [lbl for lbl, _ in pares], [price for _, price in pares]

    return labels[:n_weeks], prices[:n_weeks]


# ============================================================
# NORMALIZACION DE CATEGORIA
# ============================================================
def normalizar_categoria(cat):
    """
    Limpia visualmente el nombre de una categoria eliminando prefijos numericos
    tipo '1-', '2-', '3-' y espacios innecesarios.
    No cambia el significado de la categoria.
    """
    if not cat or (isinstance(cat, float) and pd.isna(cat)):
        return "Sin categoria"
    cat = str(cat).strip()
    cat = re.sub(r"^\d+[\-.\s]+", "", cat)
    return cat.strip() or "Sin categoria"


_CLASIFICACION_AUXILIAR = [
    ("Aceites",              ["aceite", "soya", "canola", "oliva", "vegetal"]),
    ("Arroz y cereales",     ["arroz", "cereal", "avena"]),
    ("Carnes y pollos",      ["carne", "res", "cerdo", "pollo", "pechuga", "muslo",
                              "chuleta", "costilla"]),
    ("Embutidos",            ["salami", "jamon", "salchicha", "mortadela",
                              "longaniza"]),
    ("Lacteos y derivados",  ["leche", "queso", "yogur", "yogurt", "mantequilla",
                              "margarina", "crema"]),
    ("Agricolas / viveres",  ["papa", "yuca", "platano", "cebolla", "ajo",
                              "tomate", "aji", "zanahoria", "auyama", "guineo",
                              "vegetales", "viveres"]),
    ("Enlatados y conservas", ["lata", "enlatado", "sardina", "tuna", "atun",
                               "pasta de tomate", "maiz enlatado"]),
    ("Harinas, pastas y granos", ["harina", "pasta", "espagueti", "spaghetti", "fideo",
                                  "habichuela", "gandul", "lenteja", "grano",
                                  "maiz"]),
    ("Panaderia",            ["pan", "sobao", "galleta", "bizcocho"]),
    ("Condimentos y sazones", ["sal", "azucar", "sazon", "caldo",
                               "vinagre", "salsa", "condimento", "oregano"]),
    ("Bebidas",              ["agua", "jugo", "refresco", "cafe",
                              "chocolate", "bebida"]),
    ("Higiene y limpieza",   ["jabon", "detergente", "cloro", "suavizante",
                              "papel", "servilleta", "pasta dental", "shampoo",
                              "desinfectante"]),
]


def _clasificar_por_nombre(nombre_producto):
    """
    Clasifica un producto por su nombre cuando no hay categoria oficial.
    Devuelve (categoria_str, es_estimada:bool).
    """
    nom = str(nombre_producto).lower()
    for cat, palabras in _CLASIFICACION_AUXILIAR:
        if any(p in nom for p in palabras):
            return cat, True
    return "Otros", True


def preparar_productos_con_cambio(merged_df, cat_display, cats_norm_map,
                                   vista, sup_sel, solo_cambios):
    """
    Prepara los datos para 'Productos con cambio de precio'.
    """
    empty = pd.DataFrame()
    if merged_df is None or merged_df.empty:
        return empty, empty, empty

    df = merged_df.copy()

    # -- Normalizar categoria --
    df["_cat_norm"] = (
        df["categoria"]
        .astype(str)
        .map(lambda c: cats_norm_map.get(c, normalizar_categoria(c)))
    )

    # -- Rellenar categorias vacias con clasificacion auxiliar --
    sin_cat_mask = df["_cat_norm"].isin(["Sin categoria", "nan", "", "None"])
    if sin_cat_mask.any():
        df.loc[sin_cat_mask, "_cat_norm"] = (
            df.loc[sin_cat_mask, "producto"]
            .apply(lambda p: _clasificar_por_nombre(p)[0])
        )

    # -- Filtro por categoria --
    if cat_display != "Todas las categorias":
        df = df[df["_cat_norm"] == cat_display]

    if df.empty:
        return empty, empty, empty

    # -- Filtro por establecimiento --
    if vista == "Por establecimiento" and sup_sel:
        df = df[df["supermercado"] == sup_sel]
        if df.empty:
            return empty, empty, empty

    # -- Agrupacion --
    if vista == "General":
        grp = (
            df.groupby(["_cat_norm", "id_producto", "producto", "presentacion"],
                       as_index=False)
            .agg(precio_comp=("precio_comp", "mean"),
                 precio_actual=("precio_actual", "mean"))
        )
        grp["var_rdp"] = grp["precio_actual"] - grp["precio_comp"]
        grp["var_pct"] = (grp["var_rdp"] / grp["precio_comp"] * 100).round(2)
        grp["supermercado"] = ""
    else:
        grp = df[["_cat_norm", "id_producto", "producto", "presentacion",
                  "supermercado", "precio_comp", "precio_actual"]].copy()
        grp["var_rdp"] = grp["precio_actual"] - grp["precio_comp"]
        grp["var_pct"] = (grp["var_rdp"] / grp["precio_comp"] * 100).round(2)

    # -- Estado --
    grp["Estado"] = grp["var_pct"].apply(
        lambda v: "Subio" if v > 0.01 else ("Bajo" if v < -0.01 else "Estable")
    )

    # -- Filtro solo_cambios --
    if solo_cambios:
        grp = grp[grp["var_pct"].abs() > 0.01]

    df_cnt = grp.copy()

    # -- Para grafica: solo con cambio, ordenar por |var_pct| desc --
    df_graf = (
        grp[grp["var_pct"].abs() > 0.01]
        .sort_values("var_pct", key=lambda s: s.abs(), ascending=False)
        .copy()
    )
    df_graf["etiqueta"] = df_graf["producto"] + " (" + df_graf["presentacion"] + ")"

    # -- Para tabla: columnas limpias y formateadas --
    if vista == "General":
        df_tabla = grp[["_cat_norm", "producto", "presentacion",
                        "precio_comp", "precio_actual", "var_rdp", "var_pct",
                        "Estado"]].copy()
        df_tabla.columns = ["Categoria", "Producto", "Presentacion",
                            "Precio base", "Precio actual",
                            "Variacion RD$", "Variacion %", "Estado"]
    else:
        df_tabla = grp[["_cat_norm", "producto", "presentacion", "supermercado",
                        "precio_comp", "precio_actual", "var_rdp", "var_pct",
                        "Estado"]].copy()
        df_tabla.columns = ["Categoria", "Producto", "Presentacion", "Supermercado",
                            "Precio base", "Precio actual",
                            "Variacion RD$", "Variacion %", "Estado"]

    df_tabla["Precio base"]   = df_tabla["Precio base"].apply(fmt_rdp)
    df_tabla["Precio actual"] = df_tabla["Precio actual"].apply(fmt_rdp)
    df_tabla["Variacion RD$"] = df_tabla["Variacion RD$"].apply(lambda x: f"RD$ {x:+,.2f}")
    df_tabla["Variacion %"]   = df_tabla["Variacion %"].apply(fmt_pct)

    return df_cnt, df_graf, df_tabla


# ============================================================
# CRUCE ROBUSTO ENTRE DOS SEMANAS
# ============================================================
def cruzar_semanas(df_actual, df_comp):
    """
    Cruza la semana actual contra la comparada usando id_producto + presentacion
    NORMALIZADA, para que diferencias de espacios/mayusculas no rompan el merge.
    Devuelve el DataFrame con columnas precio_actual / precio_comp y la variacion.
    """
    if df_actual is None or df_comp is None or df_actual.empty or df_comp.empty:
        return pd.DataFrame()

    a = df_actual.copy()
    c = df_comp.copy()
    a["_pres_key"] = a["presentacion"].map(norm_key)
    c["_pres_key"] = c["presentacion"].map(norm_key)

    # La semana comparada se reduce a un precio por (producto, presentacion)
    c_red = (c.groupby(["id_producto", "_pres_key"], as_index=False)["precio"]
               .mean()
               .rename(columns={"precio": "precio_comp"}))

    merged = a.merge(c_red, on=["id_producto", "_pres_key"], how="inner")
    merged = merged.rename(columns={"precio": "precio_actual"})

    if merged.empty:
        return merged

    merged["Variacion RD$"] = merged["precio_actual"] - merged["precio_comp"]
    merged["Variacion %"]   = (merged["Variacion RD$"] / merged["precio_comp"] * 100).round(2)
    return merged


# ============================================================
# RESOLVER QUE DATOS USAR PARA UNA SEMANA
# ============================================================
def resolver_semana(df_all, semana, preferir="bruto"):
    """
    Devuelve (df_de_esa_semana, fuente) eligiendo la fuente disponible.
    - preferir='bruto'    -> usa bruto si existe, si no validado.
    - preferir='validado' -> usa validado si existe, si no bruto.
    Asi cualquier semana puede usarse como actual o como comparada.
    """
    if not semana:
        return pd.DataFrame(), ""
    sub = df_all[df_all["semana"] == semana]
    if sub.empty:
        return pd.DataFrame(), ""
    b = sub[sub["fuente"] == "bruto"]
    v = sub[sub["fuente"] == "validado"]
    if preferir == "bruto":
        if not b.empty:
            return b.copy(), "bruto"
        if not v.empty:
            return v.copy(), "validado"
    else:
        if not v.empty:
            return v.copy(), "validado"
        if not b.empty:
            return b.copy(), "bruto"
    return sub.copy(), "mixto"


# ============================================================
# HELPERS PARA RESOLVER FUENTES DE PRECIO (por supermercado)
# ============================================================
def precios_supermercado_para(semana, producto, presentacion, supers_sel,
                              df_sup, df_bruto, df_validado):
    """
    Devuelve [supermercado, precio, fuente] para (semana, producto, presentacion).
    Compara producto/presentacion con clave normalizada.
    """
    pn  = norm_key(producto)
    prn = norm_key(presentacion)

    def _filtra(df):
        return df[
            (df["semana"] == semana) &
            (df["producto"].map(norm_key) == pn) &
            (df["presentacion"].map(norm_key) == prn)
        ]

    # 1) Validado desglosado por supermercado
    if df_sup is not None and not df_sup.empty:
        df_a = _filtra(df_sup)
        if supers_sel:
            df_a = df_a[df_a["supermercado"].isin(supers_sel)]
        if not df_a.empty:
            out = df_a.groupby("supermercado", as_index=False)["precio"].mean()
            out["fuente"] = "validado"
            return out.sort_values("precio").reset_index(drop=True)

    # 2) Bruto: promediar por supermercado entre provincias
    if df_bruto is not None and not df_bruto.empty:
        df_b = _filtra(df_bruto)
        if supers_sel:
            df_b = df_b[df_b["supermercado"].isin(supers_sel)]
        if not df_b.empty:
            out = df_b.groupby("supermercado", as_index=False)["precio"].mean()
            out["fuente"] = "bruto"
            return out.sort_values("precio").reset_index(drop=True)

    # 3) Validado plano (sin desglose) -- solo como referencia
    if df_validado is not None and not df_validado.empty:
        df_v = _filtra(df_validado)
        if not df_v.empty:
            out = df_v.groupby("supermercado", as_index=False)["precio"].mean()
            out["fuente"] = "validado"
            return out.sort_values("precio").reset_index(drop=True)

    return pd.DataFrame(columns=["supermercado", "precio", "fuente"])


def precio_promedio_semana(df_all, semana, producto, presentacion, preferir_bruto=False):
    """
    Devuelve (precio_promedio, fuente) para un producto en una semana dada.
    Compara producto/presentacion con clave normalizada.
    """
    pn  = norm_key(producto)
    prn = norm_key(presentacion)
    df_x = df_all[
        (df_all["semana"] == semana) &
        (df_all["producto"].map(norm_key) == pn) &
        (df_all["presentacion"].map(norm_key) == prn)
    ]
    if df_x.empty:
        return None, None

    if preferir_bruto:
        df_b = df_x[df_x["fuente"] == "bruto"]
        if not df_b.empty:
            return float(df_b["precio"].mean()), "bruto"
        df_v = df_x[df_x["fuente"] == "validado"]
        if not df_v.empty:
            return float(df_v["precio"].mean()), "validado"
    else:
        df_v = df_x[df_x["fuente"] == "validado"]
        if not df_v.empty:
            return float(df_v["precio"].mean()), "validado"
        df_b = df_x[df_x["fuente"] == "bruto"]
        if not df_b.empty:
            return float(df_b["precio"].mean()), "bruto"

    return float(df_x["precio"].mean()), "mixto"
