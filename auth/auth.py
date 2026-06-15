import hashlib
import os
import pandas as pd
import streamlit as st
from datetime import datetime
from sqlalchemy import text

from data.database import get_conn, get_engine, _is_postgres


# ============================================================
# HASHING
# ============================================================
def hash_password(password: str) -> tuple:
    """Devuelve (password_hash_hex, salt_hex)."""
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return key.hex(), salt.hex()


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    salt_bytes = bytes.fromhex(salt)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, 100_000)
    return key.hex() == password_hash


# ============================================================
# MIGRACION E INICIALIZACION
# ============================================================
def init_auth_db():
    """Agrega columnas de autenticacion si no existen y crea usuarios por defecto."""
    with get_conn() as con:
        if _is_postgres():
            con.execute(text("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS username TEXT"))
            con.execute(text("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS password_hash TEXT"))
            con.execute(text("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS salt TEXT"))
        else:
            existing = {
                row[1] for row in con.execute(text("PRAGMA table_info(usuarios)")).fetchall()
            }
            for col in ("username", "password_hash", "salt"):
                if col not in existing:
                    con.execute(text(f"ALTER TABLE usuarios ADD COLUMN {col} TEXT"))

        count = con.execute(text(
            "SELECT COUNT(*) FROM usuarios WHERE username IS NOT NULL AND username != ''"
        )).fetchone()[0]
        if count == 0:
            defaults = [
                ("Admin1",  "1234", "Administrador"),
                ("Guest",   "1234", "Visualizador"),
                ("Viewer1", "1234", "Visualizador"),
            ]
            now = datetime.now().strftime("%d/%m/%Y %I:%M %p")
            for username, password, rol in defaults:
                ph, salt = hash_password(password)
                con.execute(text("""
                    INSERT INTO usuarios
                       (nombre, email, rol, activo, fecha_creacion, username, password_hash, salt)
                       VALUES (:nombre, :email, :rol, 1, :fecha, :username, :ph, :salt)
                """), {
                    "nombre": username, "email": "", "rol": rol,
                    "fecha": now, "username": username, "ph": ph, "salt": salt,
                })


# ============================================================
# CRUD DE USUARIOS
# ============================================================
def create_user(username: str, password: str, rol: str,
                nombre: str = "", email: str = "") -> bool:
    """Crea un usuario con contrasena hasheada. Devuelve False si el username ya existe."""
    with get_conn() as con:
        exists = con.execute(
            text("SELECT 1 FROM usuarios WHERE username=:u"), {"u": username}
        ).fetchone()
        if exists:
            return False
        ph, salt = hash_password(password)
        now = datetime.now().strftime("%d/%m/%Y %I:%M %p")
        con.execute(text("""
            INSERT INTO usuarios
               (nombre, email, rol, activo, fecha_creacion, username, password_hash, salt)
               VALUES (:nombre, :email, :rol, 1, :fecha, :username, :ph, :salt)
        """), {
            "nombre": nombre or username, "email": email or "",
            "rol": rol, "fecha": now,
            "username": username, "ph": ph, "salt": salt,
        })
    return True


def update_user_auth(uid: int, nombre: str, email: str, rol: str,
                     activo: bool, new_password: str = None):
    """Actualiza datos de usuario. Si new_password se pasa, tambien cambia la contrasena."""
    with get_conn() as con:
        if new_password and new_password.strip():
            ph, salt = hash_password(new_password.strip())
            con.execute(text("""
                UPDATE usuarios
                SET nombre=:nombre, email=:email, rol=:rol, activo=:activo,
                    password_hash=:ph, salt=:salt
                WHERE id=:uid
            """), {
                "nombre": nombre.strip(), "email": email.strip(),
                "rol": rol, "activo": int(activo),
                "ph": ph, "salt": salt, "uid": uid,
            })
        else:
            con.execute(text("""
                UPDATE usuarios
                SET nombre=:nombre, email=:email, rol=:rol, activo=:activo
                WHERE id=:uid
            """), {
                "nombre": nombre.strip(), "email": email.strip(),
                "rol": rol, "activo": int(activo), "uid": uid,
            })


def delete_user(uid: int):
    with get_conn() as con:
        con.execute(text("DELETE FROM usuarios WHERE id=:uid"), {"uid": uid})


def load_users_safe() -> pd.DataFrame:
    """Carga usuarios sin exponer password_hash ni salt."""
    try:
        return pd.read_sql(
            "SELECT id, username, nombre, email, rol, activo, fecha_creacion "
            "FROM usuarios ORDER BY nombre",
            get_engine(),
        )
    except Exception:
        return pd.DataFrame(
            columns=["id", "username", "nombre", "email", "rol", "activo", "fecha_creacion"]
        )


# ============================================================
# VERIFICACION DE LOGIN
# ============================================================
def verify_login(username: str, password: str):
    """Devuelve dict con datos del usuario si las credenciales son correctas, None si no."""
    with get_conn() as con:
        row = con.execute(text(
            "SELECT id, username, password_hash, salt, rol, activo, nombre "
            "FROM usuarios WHERE username=:u"
        ), {"u": username}).fetchone()
    if not row:
        return None
    uid, uname, ph, salt, rol, activo, nombre = row
    if not activo:
        return None
    if not ph or not salt:
        return None
    if verify_password(password, ph, salt):
        return {"id": uid, "username": uname, "rol": rol, "nombre": nombre}
    return None


# ============================================================
# GUARDS DE SESION
# ============================================================
def require_login():
    """Muestra login y detiene la ejecucion si el usuario no esta autenticado."""
    if not st.session_state.get("authenticated"):
        _render_login()
        st.stop()


def require_role(rol_requerido: str):
    """Detiene la ejecucion si el usuario no tiene el rol requerido."""
    if st.session_state.get("rol") != rol_requerido:
        st.warning("No tienes permiso para acceder a esta seccion.")
        st.stop()


def logout():
    for key in ("authenticated", "username", "rol", "user_id", "nombre"):
        st.session_state.pop(key, None)
    st.rerun()


def is_admin() -> bool:
    return st.session_state.get("rol") == "Administrador"


def is_viewer() -> bool:
    return st.session_state.get("rol") in ("Visualizador", "Analista")


# ============================================================
# RENDERIZADO DEL LOGIN
# ============================================================
def _render_login():
    _, col, _ = st.columns([1, 1.6, 1])
    with col:
        st.markdown(
            "<div style='text-align:center;margin-bottom:1.5rem;'>"
            "<span style='font-size:2.4rem;'>📊</span>"
            "<h2 style='margin:.4rem 0 .2rem 0;font-weight:800;'>Monitor de Precios</h2>"
            "<p style='color:#94A3B8;font-size:.9rem;margin:0;'>DOSAC · Inicia sesion para continuar</p>"
            "</div>",
            unsafe_allow_html=True,
        )
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Usuario", placeholder="Tu nombre de usuario")
            password = st.text_input("Contrasena", type="password", placeholder="Contrasena")
            submitted = st.form_submit_button("Iniciar sesion", use_container_width=True)

        if submitted:
            if not username.strip() or not password.strip():
                st.error("Ingresa usuario y contrasena.")
                return
            user = verify_login(username.strip(), password.strip())
            if user:
                st.session_state["authenticated"] = True
                st.session_state["username"] = user["username"]
                st.session_state["rol"] = user["rol"]
                st.session_state["user_id"] = user["id"]
                st.session_state["nombre"] = user["nombre"]
                st.rerun()
            else:
                st.error("Usuario o contrasena incorrectos, o usuario inactivo.")


# ============================================================
# INFO DE USUARIO EN SIDEBAR
# ============================================================
def render_sidebar_user():
    username = st.session_state.get("username", "")
    rol = st.session_state.get("rol", "")
    rol_color = {"Administrador": "#EF4444", "Visualizador": "#64748B", "Analista": "#3B82F6"}.get(rol, "#94A3B8")

    st.markdown(
        f"<div style='padding:.55rem .75rem;border-radius:12px;"
        f"background:rgba(30,41,59,0.85);border:1px solid rgba(148,163,184,0.16);"
        f"margin-bottom:.6rem;'>"
        f"<div style='font-size:.72rem;color:#94A3B8;text-transform:uppercase;letter-spacing:.06em;'>Usuario activo</div>"
        f"<div style='font-size:.95rem;font-weight:700;color:#F8FAFC;margin-top:.1rem;'>{username}</div>"
        f"<div style='margin-top:.15rem;'>"
        f"<span style='background:{rol_color}22;color:{rol_color};font-size:.7rem;font-weight:700;"
        f"padding:.12rem .45rem;border-radius:999px;border:1px solid {rol_color}44;'>{rol}</span>"
        f"</div></div>",
        unsafe_allow_html=True,
    )
    if st.button("Cerrar sesion", key="btn_logout", use_container_width=True):
        logout()
