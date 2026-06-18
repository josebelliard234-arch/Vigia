import streamlit as st
import pandas as pd

from data.database import ROLES_USUARIO, _ROL_COLOR, get_engine, load_audit_log
from auth.auth import (
    create_user, update_user_auth, delete_user,
    load_users_safe, is_admin,
)

# ── Utilidades visuales ───────────────────────────────────────
_AVATAR_COLORS = [
    "#2563EB", "#6D28D9", "#BE185D", "#EA580C",
    "#16A34A", "#DC2626", "#0E7490", "#D97706",
]

def _av_color(name: str) -> str:
    return _AVATAR_COLORS[ord((name or "A")[0].upper()) % len(_AVATAR_COLORS)]

def _avatar(name: str, size: int = 34) -> str:
    c = _av_color(name)
    l = (name or "?")[0].upper()
    return (
        f'<div style="width:{size}px;height:{size}px;border-radius:50%;background:{c};'
        f'display:flex;align-items:center;justify-content:center;'
        f'font-size:{int(size*.42)}px;font-weight:700;color:#fff;flex-shrink:0;">{l}</div>'
    )

_ROL_SHORT = {"Administrador": "Admin", "Visualizador": "Visualizador"}
_ROL_BC    = {"Administrador": "#DC2626", "Visualizador": "#2563EB"}

def _badge(rol: str) -> str:
    c = _ROL_BC.get(rol, "#64748B")
    return (
        f'<span style="background:{c}22;color:{c};font-size:.72rem;font-weight:700;'
        f'padding:.13rem .5rem;border-radius:999px;border:1px solid {c}44;">'
        f'{_ROL_SHORT.get(rol, rol)}</span>'
    )

def _th(label: str) -> str:
    return (
        f"<small style='color:#475569;font-weight:700;"
        f"letter-spacing:.06em;font-size:.7rem;'>{label}</small>"
    )


# ── Dialogs ───────────────────────────────────────────────────
@st.dialog("Nuevo usuario", width="small")
def _dlg_crear():
    nombre_in   = st.text_input("Nombre para mostrar *", key="dc_nom")
    username_in = st.text_input("Username (login) *",    key="dc_user")
    email_in    = st.text_input("Email (opcional)",      key="dc_email")
    rol_in      = st.selectbox("Rol", ROLES_USUARIO, index=1, key="dc_rol")
    pw_in       = st.text_input("Contrasena *", type="password", key="dc_pw")
    st.markdown("<div style='margin-top:.3rem'></div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    if c1.button("Crear usuario", use_container_width=True, type="primary", key="dc_ok"):
        if not nombre_in.strip():
            st.error("El nombre es obligatorio.")
        elif not username_in.strip():
            st.error("El username es obligatorio.")
        elif not pw_in.strip():
            st.error("La contrasena es obligatoria.")
        else:
            ok = create_user(username_in.strip(), pw_in.strip(),
                             rol_in, nombre_in.strip(), email_in.strip())
            if ok:
                st.success(f"Usuario @{username_in.strip()} creado.")
                st.rerun()
            else:
                st.error(f"El username @{username_in.strip()} ya existe.")
    if c2.button("Cancelar", use_container_width=True, key="dc_cancel"):
        st.rerun()


@st.dialog("Editar usuario", width="small")
def _dlg_editar():
    row = st.session_state.get("_edit_row", {})
    if not row:
        st.rerun()
        return
    uid       = int(row["id"])
    nombre_in = st.text_input("Nombre", value=row.get("nombre", ""), key="de_nom")
    st.text_input("Username", value=row.get("username", ""),
                  disabled=True, key="de_user",
                  help="El username no se puede modificar.")
    email_in  = st.text_input("Email", value=row.get("email") or "", key="de_email")
    rol_opts  = ROLES_USUARIO
    rol_idx   = rol_opts.index(row["rol"]) if row.get("rol") in rol_opts else 1
    rol_in    = st.selectbox("Rol", rol_opts, index=rol_idx, key="de_rol")
    pw_in     = st.text_input("Nueva contrasena (vacío = sin cambio)",
                               type="password", key="de_pw")
    activo_in = st.checkbox("Cuenta activa", value=bool(row.get("activo", 1)),
                             key="de_act")
    st.markdown("<div style='margin-top:.3rem'></div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    if c1.button("Guardar cambios", use_container_width=True,
                 type="primary", key="de_ok"):
        if not nombre_in.strip():
            st.error("El nombre es obligatorio.")
        else:
            update_user_auth(
                uid, nombre_in.strip(), email_in.strip(),
                rol_in, activo_in,
                new_password=pw_in.strip() if pw_in.strip() else None,
            )
            st.session_state.pop("_edit_row", None)
            st.success("Cambios guardados.")
            st.rerun()
    if c2.button("Cancelar", use_container_width=True, key="de_cancel"):
        st.session_state.pop("_edit_row", None)
        st.rerun()


# ── Vista principal ───────────────────────────────────────────
def render_usuarios():
    if not is_admin():
        st.warning("No tienes permiso para acceder a esta seccion.")
        st.stop()

    # Abrir dialogs si corresponde
    if st.session_state.pop("_show_crear", False):
        _dlg_crear()
    if st.session_state.pop("_show_editar", False):
        _dlg_editar()

    usuarios_df = load_users_safe()
    current_uid = st.session_state.get("user_id")

    # ── MÉTRICAS ─────────────────────────────────────────────
    total_u   = len(usuarios_df)
    admins_u  = int((usuarios_df["rol"] == "Administrador").sum()) if not usuarios_df.empty else 0
    views_u   = int((usuarios_df["rol"] == "Visualizador").sum())  if not usuarios_df.empty else 0
    try:
        n_provs = int(pd.read_sql(
            "SELECT COUNT(DISTINCT provincia) FROM precios", get_engine()
        ).iloc[0, 0])
    except Exception:
        n_provs = 0

    m1, m2, m3, m4 = st.columns(4)
    for col, label, val, color, icon in [
        (m1, "Usuarios totales",   total_u,  "#2563EB", "👥"),
        (m2, "Visualizadores",     views_u,  "#16A34A", "✏️"),
        (m3, "Administradores",    admins_u, "#DC2626", "🛡️"),
        (m4, "Provincias activas", n_provs,  "#EA580C", "📍"),
    ]:
        col.markdown(
            f'<div style="padding:.85rem 1rem 1rem 1rem;border-radius:14px;'
            f'background:var(--bg-card);border:1px solid var(--bd);">'
            f'<div style="font-size:1.4rem;margin-bottom:.2rem;">{icon}</div>'
            f'<div style="font-size:2rem;font-weight:800;color:{color};line-height:1;">{val}</div>'
            f'<div style="font-size:.77rem;color:var(--t2);margin-top:.18rem;">{label}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin:.75rem 0 .1rem 0'></div>", unsafe_allow_html=True)

    # ── ÚLTIMOS 5 USUARIOS ACTIVOS ───────────────────────────
    try:
        audit_df = load_audit_log(limit=2000)
        logins = (
            audit_df[audit_df["accion"] == "LOGIN"]
            .sort_values("timestamp", ascending=False)
            .drop_duplicates(subset="usuario")
            .head(5)
        ) if not audit_df.empty else pd.DataFrame()
    except Exception:
        logins = pd.DataFrame()

    if not logins.empty:
        st.markdown(
            '<div style="display:flex;align-items:center;gap:.5rem;'
            'margin-bottom:.5rem;padding:.6rem .85rem;border-radius:10px;'
            'background:var(--bg-subtle);border:1px solid var(--bd);">'
            '<span style="font-size:.95rem;">🕐</span>'
            '<span style="font-weight:700;font-size:.88rem;color:var(--t0);">'
            'Últimos 5 usuarios activos</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        hc = st.columns([.42, 2.8, 2.6, 1.5, 1.4])
        for col, lbl in zip(hc, ["", "NOMBRE", "ÚLTIMO ACCESO", "ROL", "ESTADO"]):
            col.markdown(_th(lbl), unsafe_allow_html=True)

        for _, row in logins.iterrows():
            um = (usuarios_df[usuarios_df["username"] == row["usuario"]]
                  if not usuarios_df.empty else pd.DataFrame())
            nom_r = um.iloc[0]["nombre"] if not um.empty else row["usuario"]
            rol_r = um.iloc[0]["rol"]    if not um.empty else ""
            act_r = bool(um.iloc[0]["activo"]) if not um.empty else True
            sc = "#16A34A" if act_r else "#D97706"
            rc = st.columns([.42, 2.8, 2.6, 1.5, 1.4])
            rc[0].markdown(_avatar(nom_r, 30), unsafe_allow_html=True)
            rc[1].markdown(
                f'<div style="line-height:1.35;padding:.05rem 0;">'
                f'<span style="font-size:.84rem;font-weight:600;color:var(--t0);">{nom_r}</span><br>'
                f'<span style="font-size:.71rem;color:#2563EB;font-family:monospace;">@{row["usuario"]}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
            rc[2].markdown(
                f'<div style="font-size:.79rem;color:var(--t2);padding:.05rem 0;">{row["timestamp"]}</div>',
                unsafe_allow_html=True,
            )
            rc[3].markdown(_badge(rol_r), unsafe_allow_html=True)
            rc[4].markdown(
                f'<span style="font-size:.78rem;color:{sc};font-weight:600;">'
                f'● {"Activo" if act_r else "Inactivo"}</span>',
                unsafe_allow_html=True,
            )
        st.divider()

    # ── LISTA DE USUARIOS ────────────────────────────────────
    lh1, lh2 = st.columns([5, 2])
    with lh1:
        st.markdown(
            '<span style="font-weight:700;font-size:.9rem;">👤 Lista de usuarios</span>',
            unsafe_allow_html=True,
        )
    with lh2:
        if st.button("＋ Nuevo usuario", key="btn_new_usr",
                     use_container_width=True, type="primary"):
            st.session_state["_show_crear"] = True
            st.rerun()

    if usuarios_df.empty:
        st.info("No hay usuarios registrados.")
        return

    # Filtros
    fc1, fc2, fc3 = st.columns([3, 1.5, 1.5])
    buscar   = fc1.text_input("", placeholder="🔍  Buscar por nombre o usuario...",
                               key="usr_search", label_visibility="collapsed")
    rol_f    = fc2.selectbox("", ["Todos los roles"] + ROLES_USUARIO,
                              key="usr_rol_f", label_visibility="collapsed")
    activo_f = fc3.selectbox("", ["Todos", "Activos", "Inactivos"],
                              key="usr_act_f", label_visibility="collapsed")

    df_f = usuarios_df.copy()
    if buscar.strip():
        bl = buscar.strip().lower()
        df_f = df_f[
            df_f["nombre"].str.lower().str.contains(bl, na=False) |
            df_f["username"].str.lower().str.contains(bl, na=False)
        ]
    if rol_f != "Todos los roles":
        df_f = df_f[df_f["rol"] == rol_f]
    if activo_f == "Activos":
        df_f = df_f[df_f["activo"] == 1]
    elif activo_f == "Inactivos":
        df_f = df_f[df_f["activo"] != 1]
    df_f = df_f.reset_index(drop=True)

    # Paginación
    PER_PAGE = 10
    n_total  = len(df_f)
    n_pages  = max(1, -(-n_total // PER_PAGE))
    fk = (buscar, rol_f, activo_f)
    if st.session_state.get("_usr_fk") != fk:
        st.session_state["_usr_fk"] = fk
        st.session_state["usr_page"] = 1
    page    = max(1, min(st.session_state.get("usr_page", 1), n_pages))
    df_page = df_f.iloc[(page - 1) * PER_PAGE: page * PER_PAGE]

    st.markdown("<div style='margin:.35rem 0'></div>", unsafe_allow_html=True)

    # Encabezados de tabla
    th = st.columns([.38, 3.2, 1.6, 1.2, .85])
    for col, lbl in zip(th, ["", "NOMBRE", "ROL", "ESTADO", "ACCIONES"]):
        col.markdown(_th(lbl), unsafe_allow_html=True)

    for _, u in df_page.iterrows():
        uid    = int(u["id"])
        nombre = str(u["nombre"] or "")
        uname  = str(u["username"] or "")
        rol    = str(u["rol"] or "")
        activo = u["activo"] == 1
        es_yo  = uid == current_uid
        sc     = "#16A34A" if activo else "#D97706"

        rc = st.columns([.38, 3.2, 1.6, 1.2, .85])
        rc[0].markdown(_avatar(nombre or "?", 34), unsafe_allow_html=True)
        rc[1].markdown(
            f'<div style="line-height:1.35;padding:.12rem 0;">'
            f'<span style="font-size:.87rem;font-weight:600;color:var(--t0);">{nombre}</span>'
            + (f'<span style="margin-left:.35rem;font-size:.64rem;background:#172554;'
               f'color:#93C5FD;padding:.04rem .28rem;border-radius:4px;font-weight:700;">TÚ</span>'
               if es_yo else "")
            + f'<br><span style="font-size:.72rem;color:#2563EB;'
              f'font-family:monospace;">@{uname}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        rc[2].markdown(_badge(rol), unsafe_allow_html=True)
        rc[3].markdown(
            f'<span style="font-size:.78rem;color:{sc};font-weight:600;">'
            f'{"● Activo" if activo else "● Inactivo"}</span>',
            unsafe_allow_html=True,
        )
        ba, bb = rc[4].columns(2)
        if ba.button("✏️", key=f"edit_{uid}", help="Editar"):
            st.session_state["_edit_row"]    = u.to_dict()
            st.session_state["_show_editar"] = True
            st.rerun()
        if bb.button("🗑️", key=f"del_{uid}", help="Eliminar",
                     disabled=es_yo):
            delete_user(uid)
            st.rerun()

    # Footer
    st.markdown("<div style='margin:.5rem 0 .15rem 0'></div>", unsafe_allow_html=True)
    pcols = st.columns([1.2] + [.38] * min(7, n_pages) + [1.2])
    if pcols[0].button("‹ Ant.", key="pg_prev",
                        disabled=(page <= 1), use_container_width=True):
        st.session_state["usr_page"] = page - 1
        st.rerun()
    for i in range(min(7, n_pages)):
        p = i + 1
        if pcols[i + 1].button(
            str(p), key=f"pg_{p}",
            type="primary" if p == page else "secondary",
            use_container_width=True,
        ):
            st.session_state["usr_page"] = p
            st.rerun()
    if pcols[min(7, n_pages) + 1].button("Sig. ›", key="pg_next",
                                           disabled=(page >= n_pages),
                                           use_container_width=True):
        st.session_state["usr_page"] = page + 1
        st.rerun()

    st.caption(
        f"{(page - 1) * PER_PAGE + 1}–{min(page * PER_PAGE, n_total)} "
        f"de {n_total} usuario(s)"
    )
