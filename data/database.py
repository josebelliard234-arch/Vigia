import os
import re
import sqlite3
import pandas as pd
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "datos.db")

DEMO_MODE = os.environ.get("DASHBOARD_PJ_DEMO", "0").strip().lower() in {"1", "true", "yes", "si"}

ROLES_USUARIO = ["Administrador", "Analista", "Visualizador"]

_ROL_COLOR = {
    "Administrador": "#EF4444",
    "Analista":      "#3B82F6",
    "Visualizador":  "#64748B",
}


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
# CONEXION Y ESQUEMA
# ------------------------------------------------------------
def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    with get_conn() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS precios (
                semana       TEXT,
                provincia    TEXT,
                supermercado TEXT,
                categoria    TEXT,
                id_producto  INTEGER,
                producto     TEXT,
                presentacion TEXT,
                precio       REAL,
                fuente       TEXT DEFAULT 'bruto',
                PRIMARY KEY (semana, provincia, supermercado, id_producto, presentacion)
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS precios_supermercado (
                semana       TEXT,
                id_producto  INTEGER,
                producto     TEXT,
                presentacion TEXT,
                supermercado TEXT,
                precio       REAL,
                PRIMARY KEY (semana, id_producto, presentacion, supermercado)
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS productos_clave (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                producto     TEXT,
                presentacion TEXT,
                precio_sem_ant REAL,
                precio_sem_act REAL,
                variacion_abs  REAL,
                variacion_pct  REAL,
                fecha_ant    TEXT,
                fecha_act    TEXT
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS monitoreos_cargados (
                semana       TEXT PRIMARY KEY,
                nombre_archivo TEXT,
                fecha_carga  TEXT,
                registros    INTEGER
            )
        """)
        # Tabla usuarios base — las columnas de auth se agregan en init_auth_db()
        con.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre         TEXT NOT NULL,
                email          TEXT,
                rol            TEXT DEFAULT 'Visualizador',
                activo         INTEGER DEFAULT 1,
                fecha_creacion TEXT
            )
        """)
        con.commit()


# ------------------------------------------------------------
# ESCRITURA
# ------------------------------------------------------------
def save_to_db(df, fuente='bruto'):
    with get_conn() as con:
        for _, r in df.iterrows():
            con.execute("""
                INSERT OR REPLACE INTO precios
                    (semana, provincia, supermercado, categoria,
                     id_producto, producto, presentacion, precio, fuente)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (r.semana, r.provincia, r.supermercado, r.categoria,
                  r.id_producto, r.producto, r.presentacion, r.precio, fuente))
        con.commit()


def save_supermercado_to_db(df):
    with get_conn() as con:
        con.execute("DELETE FROM precios_supermercado")
        for _, r in df.iterrows():
            con.execute("""
                INSERT OR REPLACE INTO precios_supermercado
                    (semana, id_producto, producto, presentacion, supermercado, precio)
                VALUES (?,?,?,?,?,?)
            """, (r.semana, r.id_producto, r.producto, r.presentacion,
                  r.supermercado, r.precio))
        con.commit()


def save_productos_clave_to_db(df):
    with get_conn() as con:
        con.execute("DELETE FROM productos_clave")
        for _, r in df.iterrows():
            con.execute("""
                INSERT INTO productos_clave
                    (producto, presentacion, precio_sem_ant, precio_sem_act,
                     variacion_abs, variacion_pct, fecha_ant, fecha_act)
                VALUES (?,?,?,?,?,?,?,?)
            """, (r.producto, r.presentacion, r.precio_sem_ant, r.precio_sem_act,
                  r.variacion_abs, r.variacion_pct, r.fecha_ant, r.fecha_act))
        con.commit()


# ------------------------------------------------------------
# LECTURA
# ------------------------------------------------------------
def load_all():
    with get_conn() as con:
        df = pd.read_sql("SELECT * FROM precios ORDER BY semana", con)
    return _normalizar_columnas(df)


def load_validados():
    with get_conn() as con:
        df = pd.read_sql(
            "SELECT * FROM precios WHERE fuente='validado' ORDER BY semana", con)
    return _normalizar_columnas(df)


def load_supermercado():
    with get_conn() as con:
        try:
            df = pd.read_sql("SELECT * FROM precios_supermercado", con)
        except Exception:
            return pd.DataFrame()
    return _normalizar_columnas(df)


def load_productos_clave():
    with get_conn() as con:
        try:
            df = pd.read_sql("SELECT * FROM productos_clave", con)
        except Exception:
            return pd.DataFrame()
    return _normalizar_columnas(df)


def semanas_en_db():
    with get_conn() as con:
        cur = con.execute("SELECT DISTINCT semana FROM precios ORDER BY semana")
        return [r[0] for r in cur.fetchall()]


def count_validados():
    with get_conn() as con:
        try:
            cur = con.execute("SELECT COUNT(*) FROM precios WHERE fuente='validado'")
            return cur.fetchone()[0]
        except Exception:
            return 0


def semanas_validadas():
    with get_conn() as con:
        cur = con.execute(
            "SELECT DISTINCT semana FROM precios WHERE fuente='validado' ORDER BY semana")
        return [r[0] for r in cur.fetchall()]


def count_supermercado():
    with get_conn() as con:
        try:
            cur = con.execute("SELECT COUNT(*) FROM precios_supermercado")
            return cur.fetchone()[0]
        except Exception:
            return 0


def count_productos_clave():
    with get_conn() as con:
        try:
            cur = con.execute("SELECT COUNT(*) FROM productos_clave")
            return cur.fetchone()[0]
        except Exception:
            return 0


def registrar_monitoreo_cargado(semana, nombre_archivo, registros):
    with get_conn() as con:
        con.execute("""
            INSERT OR REPLACE INTO monitoreos_cargados
                (semana, nombre_archivo, fecha_carga, registros)
            VALUES (?,?,?,?)
        """, (semana, nombre_archivo,
              datetime.now().strftime("%d/%m/%Y %I:%M %p"), int(registros)))
        con.commit()


def load_monitoreos_cargados():
    with get_conn() as con:
        try:
            cur = con.execute(
                "SELECT semana, nombre_archivo, fecha_carga, registros "
                "FROM monitoreos_cargados ORDER BY semana DESC"
            )
            return cur.fetchall()
        except Exception:
            return []


def eliminar_monitoreo_cargado(semana):
    with get_conn() as con:
        con.execute("DELETE FROM monitoreos_cargados WHERE semana=?", (semana,))
        con.execute("DELETE FROM precios WHERE semana=? AND fuente='bruto'", (semana,))
        con.commit()


def wipe_db(que="todo"):
    antes = {"precios": 0, "precios_supermercado": 0, "productos_clave": 0}
    with get_conn() as con:
        for t in antes:
            try:
                antes[t] = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            except Exception:
                antes[t] = 0

        if que == "todo":
            con.execute("DELETE FROM precios")
            con.execute("DELETE FROM precios_supermercado")
            con.execute("DELETE FROM productos_clave")
            con.execute("DELETE FROM monitoreos_cargados")
        elif que == "bruto":
            con.execute("DELETE FROM precios WHERE fuente='bruto'")
            con.execute("DELETE FROM monitoreos_cargados")
        elif que == "validado":
            con.execute("DELETE FROM precios WHERE fuente='validado'")
            con.execute("DELETE FROM precios_supermercado")
            con.execute("DELETE FROM productos_clave")
        con.commit()
    return antes
