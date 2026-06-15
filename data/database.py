import os
import re
import sqlite3
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, text
import streamlit as st

DEMO_MODE = os.environ.get("DASHBOARD_PJ_DEMO", "0").strip().lower() in {"1", "true", "yes", "si"}

ROLES_USUARIO = ["Administrador", "Analista", "Visualizador"]

_ROL_COLOR = {
    "Administrador": "#EF4444",
    "Analista":      "#3B82F6",
    "Visualizador":  "#64748B",
}

_SQLITE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "datos.db")


# ------------------------------------------------------------
# NORMALIZACION DE TEXTO
# ------------------------------------------------------------
def clean_text(s):
    if pd.isna(s):
        return ""
    return re.sub(r"\s+", " ", str(s)).strip()


def norm_key(s):
    if pd.isna(s):
        return ""
    return re.sub(r"\s+", " ", str(s)).strip().upper()


def _normalizar_columnas(df):
    if df is None or df.empty:
        return df
    if "producto" in df.columns:
        df["producto"] = df["producto"].map(clean_text)
    if "presentacion" in df.columns:
        df["presentacion"] = df["presentacion"].map(clean_text)
    return df


# ------------------------------------------------------------
# CONEXION — PostgreSQL en la nube, SQLite en local
# ------------------------------------------------------------
def _get_db_url():
    try:
        url = st.secrets.get("DATABASE_URL", "")
    except Exception:
        url = ""
    if not url:
        url = os.environ.get("DATABASE_URL", "")
    return url or None


def _is_postgres():
    return _get_db_url() is not None


@st.cache_resource
def _get_engine():
    url = _get_db_url()
    if url:
        return create_engine(url)
    return create_engine(f"sqlite:///{_SQLITE_PATH}")


def get_engine():
    return _get_engine()


def get_conn():
    return _get_engine().begin()


# ------------------------------------------------------------
# ESQUEMA
# ------------------------------------------------------------
def init_db():
    pg = _is_postgres()
    serial = "SERIAL" if pg else "INTEGER"
    real   = "DOUBLE PRECISION" if pg else "REAL"

    with get_conn() as con:
        con.execute(text(f"""
            CREATE TABLE IF NOT EXISTS precios (
                semana       TEXT,
                provincia    TEXT,
                supermercado TEXT,
                categoria    TEXT,
                id_producto  INTEGER,
                producto     TEXT,
                presentacion TEXT,
                precio       {real},
                fuente       TEXT DEFAULT 'bruto',
                PRIMARY KEY (semana, provincia, supermercado, id_producto, presentacion)
            )
        """))
        con.execute(text(f"""
            CREATE TABLE IF NOT EXISTS precios_supermercado (
                semana       TEXT,
                id_producto  INTEGER,
                producto     TEXT,
                presentacion TEXT,
                supermercado TEXT,
                precio       {real},
                PRIMARY KEY (semana, id_producto, presentacion, supermercado)
            )
        """))
        con.execute(text(f"""
            CREATE TABLE IF NOT EXISTS productos_clave (
                id             {serial} PRIMARY KEY,
                producto       TEXT,
                presentacion   TEXT,
                precio_sem_ant {real},
                precio_sem_act {real},
                variacion_abs  {real},
                variacion_pct  {real},
                fecha_ant      TEXT,
                fecha_act      TEXT
            )
        """))
        con.execute(text("""
            CREATE TABLE IF NOT EXISTS monitoreos_cargados (
                semana         TEXT PRIMARY KEY,
                nombre_archivo TEXT,
                fecha_carga    TEXT,
                registros      INTEGER
            )
        """))
        con.execute(text(f"""
            CREATE TABLE IF NOT EXISTS usuarios (
                id             {serial} PRIMARY KEY,
                nombre         TEXT NOT NULL,
                email          TEXT,
                rol            TEXT DEFAULT 'Visualizador',
                activo         INTEGER DEFAULT 1,
                fecha_creacion TEXT
            )
        """))


# ------------------------------------------------------------
# ESCRITURA
# ------------------------------------------------------------
def save_to_db(df, fuente='bruto'):
    pg = _is_postgres()
    with get_conn() as con:
        for _, r in df.iterrows():
            if pg:
                sql = text("""
                    INSERT INTO precios
                        (semana, provincia, supermercado, categoria,
                         id_producto, producto, presentacion, precio, fuente)
                    VALUES (:semana, :provincia, :supermercado, :categoria,
                            :id_producto, :producto, :presentacion, :precio, :fuente)
                    ON CONFLICT (semana, provincia, supermercado, id_producto, presentacion)
                    DO UPDATE SET
                        precio    = EXCLUDED.precio,
                        fuente    = EXCLUDED.fuente,
                        categoria = EXCLUDED.categoria,
                        producto  = EXCLUDED.producto
                """)
            else:
                sql = text("""
                    INSERT OR REPLACE INTO precios
                        (semana, provincia, supermercado, categoria,
                         id_producto, producto, presentacion, precio, fuente)
                    VALUES (:semana, :provincia, :supermercado, :categoria,
                            :id_producto, :producto, :presentacion, :precio, :fuente)
                """)
            con.execute(sql, {
                "semana": r.semana, "provincia": r.provincia,
                "supermercado": r.supermercado, "categoria": r.categoria,
                "id_producto": int(r.id_producto), "producto": r.producto,
                "presentacion": r.presentacion, "precio": float(r.precio),
                "fuente": fuente,
            })


def save_supermercado_to_db(df):
    pg = _is_postgres()
    with get_conn() as con:
        con.execute(text("DELETE FROM precios_supermercado"))
        for _, r in df.iterrows():
            if pg:
                sql = text("""
                    INSERT INTO precios_supermercado
                        (semana, id_producto, producto, presentacion, supermercado, precio)
                    VALUES (:semana, :id_producto, :producto, :presentacion, :supermercado, :precio)
                    ON CONFLICT (semana, id_producto, presentacion, supermercado)
                    DO UPDATE SET precio = EXCLUDED.precio, producto = EXCLUDED.producto
                """)
            else:
                sql = text("""
                    INSERT OR REPLACE INTO precios_supermercado
                        (semana, id_producto, producto, presentacion, supermercado, precio)
                    VALUES (:semana, :id_producto, :producto, :presentacion, :supermercado, :precio)
                """)
            con.execute(sql, {
                "semana": r.semana, "id_producto": int(r.id_producto),
                "producto": r.producto, "presentacion": r.presentacion,
                "supermercado": r.supermercado, "precio": float(r.precio),
            })


def save_productos_clave_to_db(df):
    with get_conn() as con:
        con.execute(text("DELETE FROM productos_clave"))
        for _, r in df.iterrows():
            con.execute(text("""
                INSERT INTO productos_clave
                    (producto, presentacion, precio_sem_ant, precio_sem_act,
                     variacion_abs, variacion_pct, fecha_ant, fecha_act)
                VALUES (:producto, :presentacion, :precio_sem_ant, :precio_sem_act,
                        :variacion_abs, :variacion_pct, :fecha_ant, :fecha_act)
            """), {
                "producto": r.producto, "presentacion": r.presentacion,
                "precio_sem_ant": float(r.precio_sem_ant),
                "precio_sem_act": float(r.precio_sem_act),
                "variacion_abs": float(r.variacion_abs),
                "variacion_pct": float(r.variacion_pct),
                "fecha_ant": r.fecha_ant, "fecha_act": r.fecha_act,
            })


# ------------------------------------------------------------
# LECTURA
# ------------------------------------------------------------
def load_all():
    df = pd.read_sql("SELECT * FROM precios ORDER BY semana", get_engine())
    return _normalizar_columnas(df)


def load_validados():
    df = pd.read_sql(
        "SELECT * FROM precios WHERE fuente='validado' ORDER BY semana",
        get_engine(),
    )
    return _normalizar_columnas(df)


def load_supermercado():
    try:
        df = pd.read_sql("SELECT * FROM precios_supermercado", get_engine())
    except Exception:
        return pd.DataFrame()
    return _normalizar_columnas(df)


def load_productos_clave():
    try:
        df = pd.read_sql("SELECT * FROM productos_clave", get_engine())
    except Exception:
        return pd.DataFrame()
    return _normalizar_columnas(df)


def semanas_en_db():
    with get_conn() as con:
        cur = con.execute(text("SELECT DISTINCT semana FROM precios ORDER BY semana"))
        return [r[0] for r in cur.fetchall()]


def count_validados():
    with get_conn() as con:
        try:
            cur = con.execute(text("SELECT COUNT(*) FROM precios WHERE fuente='validado'"))
            return cur.fetchone()[0]
        except Exception:
            return 0


def semanas_validadas():
    with get_conn() as con:
        cur = con.execute(text(
            "SELECT DISTINCT semana FROM precios WHERE fuente='validado' ORDER BY semana"
        ))
        return [r[0] for r in cur.fetchall()]


def count_supermercado():
    with get_conn() as con:
        try:
            cur = con.execute(text("SELECT COUNT(*) FROM precios_supermercado"))
            return cur.fetchone()[0]
        except Exception:
            return 0


def count_productos_clave():
    with get_conn() as con:
        try:
            cur = con.execute(text("SELECT COUNT(*) FROM productos_clave"))
            return cur.fetchone()[0]
        except Exception:
            return 0


def registrar_monitoreo_cargado(semana, nombre_archivo, registros):
    pg = _is_postgres()
    with get_conn() as con:
        if pg:
            sql = text("""
                INSERT INTO monitoreos_cargados
                    (semana, nombre_archivo, fecha_carga, registros)
                VALUES (:semana, :nombre_archivo, :fecha_carga, :registros)
                ON CONFLICT (semana) DO UPDATE SET
                    nombre_archivo = EXCLUDED.nombre_archivo,
                    fecha_carga    = EXCLUDED.fecha_carga,
                    registros      = EXCLUDED.registros
            """)
        else:
            sql = text("""
                INSERT OR REPLACE INTO monitoreos_cargados
                    (semana, nombre_archivo, fecha_carga, registros)
                VALUES (:semana, :nombre_archivo, :fecha_carga, :registros)
            """)
        con.execute(sql, {
            "semana": semana,
            "nombre_archivo": nombre_archivo,
            "fecha_carga": datetime.now().strftime("%d/%m/%Y %I:%M %p"),
            "registros": int(registros),
        })


def load_monitoreos_cargados():
    with get_conn() as con:
        try:
            cur = con.execute(text(
                "SELECT semana, nombre_archivo, fecha_carga, registros "
                "FROM monitoreos_cargados ORDER BY semana DESC"
            ))
            return cur.fetchall()
        except Exception:
            return []


def eliminar_monitoreo_cargado(semana):
    with get_conn() as con:
        con.execute(text("DELETE FROM monitoreos_cargados WHERE semana=:semana"), {"semana": semana})
        con.execute(text("DELETE FROM precios WHERE semana=:semana AND fuente='bruto'"), {"semana": semana})


def wipe_db(que="todo"):
    antes = {"precios": 0, "precios_supermercado": 0, "productos_clave": 0}
    with get_conn() as con:
        for t in antes:
            try:
                antes[t] = con.execute(text(f"SELECT COUNT(*) FROM {t}")).fetchone()[0]
            except Exception:
                antes[t] = 0

        if que == "todo":
            con.execute(text("DELETE FROM precios"))
            con.execute(text("DELETE FROM precios_supermercado"))
            con.execute(text("DELETE FROM productos_clave"))
            con.execute(text("DELETE FROM monitoreos_cargados"))
        elif que == "bruto":
            con.execute(text("DELETE FROM precios WHERE fuente='bruto'"))
            con.execute(text("DELETE FROM monitoreos_cargados"))
        elif que == "validado":
            con.execute(text("DELETE FROM precios WHERE fuente='validado'"))
            con.execute(text("DELETE FROM precios_supermercado"))
            con.execute(text("DELETE FROM productos_clave"))
    return antes
