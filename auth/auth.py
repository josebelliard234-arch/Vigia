import hashlib
import os
import sqlite3 as _sqlite3
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
from sqlalchemy import text

from data.database import get_conn, get_engine, _is_postgres, log_action
from styles.theme import get_mode


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
    if _is_postgres():
        for col in ("username", "password_hash", "salt"):
            try:
                with get_conn() as con:
                    con.execute(text(f"""
                        DO $$ BEGIN
                            ALTER TABLE usuarios ADD COLUMN {col} TEXT;
                        EXCEPTION WHEN duplicate_column THEN NULL;
                        END $$;
                    """))
            except Exception:
                pass
        try:
            with get_conn() as con:
                con.execute(text("""
                    DO $$ BEGIN
                        ALTER TABLE usuarios ADD COLUMN must_change_password INTEGER DEFAULT 1;
                    EXCEPTION WHEN duplicate_column THEN NULL;
                    END $$;
                """))
        except Exception:
            pass
    else:
        # Para SQLite usamos sqlite3 nativo: SQLAlchemy engine.begin() no garantiza
        # commit de DDL (ALTER TABLE) en todas las versiones de SQLite/SQLAlchemy.
        _db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "datos.db")
        _raw = _sqlite3.connect(_db_path)
        _cur = _raw.cursor()
        _existing = {row[1] for row in _cur.execute("PRAGMA table_info(usuarios)").fetchall()}
        _ddl = [
            ("username",             "TEXT"),
            ("password_hash",        "TEXT"),
            ("salt",                 "TEXT"),
            ("must_change_password", "INTEGER DEFAULT 1"),
        ]
        for _col, _defn in _ddl:
            if _col not in _existing:
                _cur.execute(f"ALTER TABLE usuarios ADD COLUMN {_col} {_defn}")
        _raw.commit()
        _raw.close()

    try:
        with get_conn() as con:
            con.execute(text(
                "UPDATE usuarios SET must_change_password=1 WHERE must_change_password IS NULL"
            ))
    except Exception:
        pass

    with get_conn() as con:
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
                       (nombre, email, rol, activo, fecha_creacion,
                        username, password_hash, salt, must_change_password)
                       VALUES (:nombre, :email, :rol, 1, :fecha, :username, :ph, :salt, 1)
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
               (nombre, email, rol, activo, fecha_creacion,
                username, password_hash, salt, must_change_password)
               VALUES (:nombre, :email, :rol, 1, :fecha, :username, :ph, :salt, 1)
        """), {
            "nombre": nombre or username, "email": email or "",
            "rol": rol, "fecha": now,
            "username": username, "ph": ph, "salt": salt,
        })
    log_action("CREATE_USER", "usuario", f"username={username}", "", f"rol={rol}")
    return True


def update_user_auth(uid: int, nombre: str, email: str, rol: str,
                     activo: bool, new_password: str = None):
    """Actualiza datos de usuario. Si new_password se pasa, tambien cambia la contrasena."""
    with get_conn() as con:
        row = con.execute(text("SELECT username, rol, activo FROM usuarios WHERE id=:uid"), {"uid": uid}).fetchone()
        uname_prev = row[0] if row else str(uid)
        rol_prev   = row[1] if row else ""
        activo_prev = row[2] if row else None
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
    cambios = []
    if rol_prev != rol:
        cambios.append(f"rol: {rol_prev}→{rol}")
    if activo_prev is not None and int(activo_prev) != int(activo):
        cambios.append(f"activo: {bool(activo_prev)}→{activo}")
    if new_password and new_password.strip():
        cambios.append("password cambiado")
    if cambios:
        log_action("UPDATE_USER", "usuario", f"username={uname_prev}", "", " | ".join(cambios))


def delete_user(uid: int):
    with get_conn() as con:
        row = con.execute(text("SELECT username, rol FROM usuarios WHERE id=:uid"), {"uid": uid}).fetchone()
        uname = row[0] if row else str(uid)
        rol_u = row[1] if row else ""
        con.execute(text("DELETE FROM usuarios WHERE id=:uid"), {"uid": uid})
    log_action("DELETE_USER", "usuario", f"username={uname}", f"rol={rol_u}", "")


def change_password_first_login(uid: int, new_password: str):
    """Cambia la contrasena y marca must_change_password=0."""
    ph, salt = hash_password(new_password)
    with get_conn() as con:
        con.execute(text("""
            UPDATE usuarios
            SET password_hash=:ph, salt=:salt, must_change_password=0
            WHERE id=:uid
        """), {"ph": ph, "salt": salt, "uid": uid})
    log_action("UPDATE_USER", "usuario", f"id={uid}", "", "password cambiado (primer acceso)")


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
            "SELECT id, username, password_hash, salt, rol, activo, nombre, must_change_password "
            "FROM usuarios WHERE username=:u"
        ), {"u": username}).fetchone()
    if not row:
        return None
    uid, uname, ph, salt, rol, activo, nombre, must_chg = row
    if not activo:
        return None
    if not ph or not salt:
        return None
    if verify_password(password, ph, salt):
        log_action("LOGIN", "sesion", f"username={uname}", "", "")
        return {
            "id": uid, "username": uname, "rol": rol, "nombre": nombre,
            "must_change_password": int(must_chg) if must_chg is not None else 1,
        }
    log_action("LOGIN_FAIL", "sesion", f"username={username}", "", "")
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
    log_action("LOGOUT", "sesion", "", "", "")
    for key in ("authenticated", "username", "rol", "user_id", "nombre"):
        st.session_state.pop(key, None)
    st.rerun()


def is_admin() -> bool:
    return st.session_state.get("rol") == "Administrador"


def is_viewer() -> bool:
    return st.session_state.get("rol") == "Visualizador"


# ============================================================
# RENDERIZADO DEL LOGIN
# ============================================================
def _render_login():
    _, col, _ = st.columns([1, 1.6, 1])
    with col:
        st.markdown(
            "<div style='text-align:center;margin-bottom:1.5rem;'>"
            "<span style='font-size:2.4rem;'>📊</span>"
            "<h2 style='margin:.4rem 0 .2rem 0;font-weight:800;color:var(--t0);'>Monitor de Precios</h2>"
            "<p style='color:var(--t2);font-size:.9rem;margin:0;'>DOSAC · Inicia sesion para continuar</p>"
            "</div>",
            unsafe_allow_html=True,
        )

        # ── Fase 2: cambio obligatorio (primer acceso) ─────────
        pending = st.session_state.get("_login_pending")
        if pending:
            st.info(
                f"**{pending['nombre']}**, tu cuenta requiere una nueva contrasena "
                "antes de continuar."
            )
            with st.form("form_force_chpw"):
                nueva     = st.text_input("Nueva contrasena",    type="password")
                confirmar = st.text_input("Confirmar contrasena", type="password")
                components.html("""
                <script>
                (function() {
                    function setup() {
                        var doc = window.parent.document;
                        var inputs = doc.querySelectorAll('input[type="password"]');
                        if (!inputs.length) { setTimeout(setup, 200); return; }
                        inputs.forEach(function(input) {
                            if (input._capsDetected) return;
                            input._capsDetected = true;
                            var warn = doc.createElement('div');
                            warn.style.cssText = 'color:#F59E0B;font-size:0.75rem;margin-top:3px;'
                                + 'display:none;font-family:Inter,sans-serif;font-weight:600;padding:2px 0;';
                            warn.textContent = '⚠️ Mayúsculas activadas (Caps Lock ON)';
                            var container = input.closest('[data-baseweb="base-input"]') || input.parentNode;
                            container.parentNode.insertBefore(warn, container.nextSibling);
                            function check(e) {
                                warn.style.display = e.getModifierState('CapsLock') ? 'block' : 'none';
                            }
                            input.addEventListener('keyup', check);
                            input.addEventListener('keydown', check);
                        });
                    }
                    setup();
                })();
                </script>
                """, height=0, scrolling=False)
                ok = st.form_submit_button(
                    "Guardar contrasena e ingresar", use_container_width=True
                )
            if ok:
                if not nueva.strip():
                    st.error("La contrasena no puede estar vacia.")
                elif len(nueva.strip()) < 6:
                    st.error("Minimo 6 caracteres.")
                elif nueva != confirmar:
                    st.error("Las contrasenas no coinciden.")
                else:
                    change_password_first_login(pending["id"], nueva.strip())
                    st.session_state.update({
                        "authenticated": True,
                        "username": pending["username"],
                        "rol":      pending["rol"],
                        "user_id":  pending["id"],
                        "nombre":   pending["nombre"],
                    })
                    st.session_state.pop("_login_pending", None)
                    st.rerun()
            st.markdown(
                "<div style='text-align:center;margin-top:.6rem;'>"
                "<small style='color:#64748B;cursor:pointer;'>",
                unsafe_allow_html=True,
            )
            if st.button("← Volver al inicio de sesion", key="btn_cancel_force"):
                st.session_state.pop("_login_pending", None)
                st.rerun()
            return

        # ── Fase 1: login normal ───────────────────────────────
        username  = st.text_input("Usuario",    placeholder="Tu nombre de usuario", key="li_user")
        password  = st.text_input("Contrasena", placeholder="Contrasena",
                                  type="password", key="li_pass")

        components.html("""
        <script>
        (function() {
            function setup() {
                var doc = window.parent.document;
                var inputs = doc.querySelectorAll('input[type="password"]');
                if (!inputs.length) { setTimeout(setup, 200); return; }
                inputs.forEach(function(input) {
                    if (input._capsDetected) return;
                    input._capsDetected = true;
                    var warn = doc.createElement('div');
                    warn.style.cssText = 'color:#F59E0B;font-size:0.75rem;margin-top:3px;'
                        + 'display:none;font-family:Inter,sans-serif;font-weight:600;'
                        + 'padding:2px 0;';
                    warn.textContent = '⚠️ Mayúsculas activadas (Caps Lock ON)';
                    var container = input.closest('[data-baseweb="base-input"]') || input.parentNode;
                    container.parentNode.insertBefore(warn, container.nextSibling);
                    function check(e) {
                        warn.style.display = e.getModifierState('CapsLock') ? 'block' : 'none';
                    }
                    input.addEventListener('keyup', check);
                    input.addEventListener('keydown', check);
                });
            }
            setup();
        })();
        </script>
        """, height=0, scrolling=False)

        # Checkbox pequeño "Cambiar contrasena" — debajo del campo contraseña
        st.markdown(
            "<style>"
            "div[data-testid='stCheckbox'] label {"
            "  font-size:.8rem !important; color:#94A3B8 !important;"
            "}"
            "</style>",
            unsafe_allow_html=True,
        )
        show_chpw = st.checkbox("Cambiar contrasena", key="li_show_chpw")

        new_pass = conf_pass = ""
        if show_chpw:
            new_pass  = st.text_input("Nueva contrasena",    type="password", key="li_new_pass")
            conf_pass = st.text_input("Confirmar contrasena", type="password", key="li_conf_pass")

        st.markdown("<div style='margin-top:.3rem'></div>", unsafe_allow_html=True)
        login_btn = st.button("Iniciar sesion", use_container_width=True, key="li_btn")

        if login_btn:
            if not username.strip() or not password.strip():
                st.error("Ingresa usuario y contrasena.")
                return
            user = verify_login(username.strip(), password.strip())
            if not user:
                st.error("Usuario o contrasena incorrectos, o usuario inactivo.")
                return

            # Primer acceso: redirigir a cambio obligatorio
            if user.get("must_change_password"):
                st.session_state["_login_pending"] = user
                st.rerun()
                return

            # Cambio voluntario de contrasena
            if show_chpw:
                if not new_pass.strip():
                    st.error("Ingresa la nueva contrasena.")
                    return
                if len(new_pass.strip()) < 6:
                    st.error("La nueva contrasena debe tener al menos 6 caracteres.")
                    return
                if new_pass != conf_pass:
                    st.error("Las contrasenas no coinciden.")
                    return
                change_password_first_login(user["id"], new_pass.strip())

            # Login completo
            st.session_state.update({
                "authenticated": True,
                "username": user["username"],
                "rol":      user["rol"],
                "user_id":  user["id"],
                "nombre":   user["nombre"],
            })
            st.session_state.pop("_login_pending", None)
            st.rerun()


# ============================================================
# INFO DE USUARIO EN SIDEBAR
# ============================================================
def render_sidebar_user():
    username = st.session_state.get("username", "")
    rol      = st.session_state.get("rol", "")
    is_lm    = get_mode() == "light"

    # Card container
    card_bg     = "rgba(255,255,255,0.78)" if is_lm else "var(--card-bg)"
    card_border = "#CBD5E1"                if is_lm else "var(--border)"
    card_shadow = "0 8px 24px rgba(15,23,42,0.08)" if is_lm else "none"
    text_main   = "#0F172A"  if is_lm else "var(--text-primary)"
    text_sub    = "#334155"  if is_lm else "var(--text-muted)"

    # Role badge
    if rol == "Administrador":
        badge_bg  = "#FEE2E2" if is_lm else "rgba(220,38,38,0.15)"
        badge_fg  = "#DC2626"
        badge_bd  = "#FCA5A5" if is_lm else "rgba(220,38,38,0.30)"
    else:
        badge_bg  = "#F1F5F9" if is_lm else "rgba(148,163,184,0.15)"
        badge_fg  = "#475569" if is_lm else "#94A3B8"
        badge_bd  = "#CBD5E1" if is_lm else "rgba(148,163,184,0.25)"

    st.markdown(
        f"<div style='padding:.6rem .8rem;border-radius:14px;"
        f"background:{card_bg};border:1px solid {card_border};"
        f"box-shadow:{card_shadow};margin-bottom:.65rem;'>"
        f"<div style='font-size:.70rem;color:{text_sub};text-transform:uppercase;"
        f"letter-spacing:.07em;font-weight:600;'>Usuario activo</div>"
        f"<div style='font-size:.95rem;font-weight:700;color:{text_main};"
        f"margin-top:.15rem;'>{username}</div>"
        f"<div style='margin-top:.2rem;'>"
        f"<span style='background:{badge_bg};color:{badge_fg};font-size:.7rem;"
        f"font-weight:700;padding:.1rem .5rem;border-radius:999px;"
        f"border:1px solid {badge_bd};'>{rol}</span>"
        f"</div></div>",
        unsafe_allow_html=True,
    )
    if st.button("Cerrar sesion", key="btn_logout", use_container_width=True, type="primary"):
        logout()
