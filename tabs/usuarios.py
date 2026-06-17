import streamlit as st

from styles.theme import TEXT_MAIN, TEXT_MUTED, BLUE, GREEN, RED, YELLOW, GRAY
from data.database import ROLES_USUARIO, _ROL_COLOR
from auth.auth import (
    create_user, update_user_auth, delete_user,
    load_users_safe, is_admin,
)


def render_usuarios():
    st.subheader("Administracion de Usuarios")

    if not is_admin():
        st.warning("No tienes permiso para acceder a esta seccion.")
        st.stop()

    st.caption("Gestion de accesos al dashboard. Solo el Administrador puede operar aqui.")

    usuarios_df = load_users_safe()

    # ---- KPIs ----
    ku1, ku2, ku3, ku4 = st.columns(4)
    total_u   = len(usuarios_df)
    activos_u = int(usuarios_df["activo"].sum()) if not usuarios_df.empty else 0
    admins_u  = int((usuarios_df["rol"] == "Administrador").sum()) if not usuarios_df.empty else 0
    views_u   = int((usuarios_df["rol"] == "Visualizador").sum()) if not usuarios_df.empty else 0

    def _kpi(label, valor, color):
        return (
            f'<div class="kpi-card" style="border-left:4px solid {color};">'
            f'<div class="kpi-label">{label}</div>'
            f'<div class="kpi-value">{valor}</div>'
            f'</div>'
        )

    ku1.markdown(_kpi("Total usuarios",  total_u,   BLUE),   unsafe_allow_html=True)
    ku2.markdown(_kpi("Activos",         activos_u, GREEN),  unsafe_allow_html=True)
    ku3.markdown(_kpi("Administradores", admins_u,  RED),    unsafe_allow_html=True)
    ku4.markdown(_kpi("Visualizadores",  views_u,   YELLOW), unsafe_allow_html=True)

    st.divider()

    col_lista, col_form = st.columns([3, 2])

    # ---- Lista de usuarios ----
    with col_lista:
        st.markdown("##### Usuarios registrados")
        if usuarios_df.empty:
            st.info("No hay usuarios. Agrega el primero desde el formulario.")
        else:
            current_uid = st.session_state.get("user_id")
            for _, u in usuarios_df.iterrows():
                uid        = int(u["id"])
                rol_color  = _ROL_COLOR.get(u["rol"], GRAY)
                s_color    = GREEN if u["activo"] == 1 else YELLOW
                s_txt      = "Activo" if u["activo"] == 1 else "Inactivo"
                email_txt  = u["email"] if u["email"] else "Sin email"
                fecha_txt  = u["fecha_creacion"] if u["fecha_creacion"] else "N/D"
                username_txt = u["username"] if u["username"] else "(sin username)"

                st.markdown(
                    f'<div class="kpi-card" style="margin-bottom:.3rem;border-left:4px solid {rol_color};">'
                    f'<div style="display:flex;justify-content:space-between;align-items:flex-start;">'
                    f'<div>'
                    f'<div style="font-size:.95rem;font-weight:700;color:{TEXT_MAIN};">{u["nombre"]}</div>'
                    f'<div style="font-size:.78rem;color:#3B82F6;margin-top:.05rem;font-family:monospace;">'
                    f'@{username_txt}</div>'
                    f'<div style="font-size:.75rem;color:{TEXT_MUTED};margin-top:.06rem;">{email_txt}</div>'
                    f'</div>'
                    f'<div style="text-align:right;">'
                    f'<span style="background:{rol_color}22;color:{rol_color};font-size:.72rem;font-weight:700;'
                    f'padding:.15rem .55rem;border-radius:999px;border:1px solid {rol_color}55;">{u["rol"]}</span>'
                    f'<br><span style="font-size:.72rem;color:{s_color};font-weight:600;margin-top:.2rem;display:block;">'
                    f'● {s_txt}</span>'
                    f'</div>'
                    f'</div>'
                    f'<div style="font-size:.7rem;color:#475569;margin-top:.35rem;">Desde: {fecha_txt}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                bc1, bc2, bc3 = st.columns([1, 1, 5])
                if bc1.button("Editar", key=f"edit_usr_{uid}"):
                    st.session_state["usr_edit_id"] = uid
                    st.rerun()
                # No permitir que el admin se elimine a si mismo
                can_delete = uid != current_uid
                if bc2.button("Eliminar", key=f"del_usr_{uid}", disabled=not can_delete,
                              help="No puedes eliminarte a ti mismo."):
                    delete_user(uid)
                    if st.session_state.get("usr_edit_id") == uid:
                        st.session_state["usr_edit_id"] = None
                    st.rerun()

    # ---- Formulario agregar / editar ----
    with col_form:
        edit_id = st.session_state.get("usr_edit_id")
        u_edit = None
        if edit_id and not usuarios_df.empty:
            mask = usuarios_df["id"] == edit_id
            if mask.any():
                u_edit = usuarios_df[mask].iloc[0]

        form_key   = edit_id or "new"
        es_edicion = u_edit is not None

        st.markdown(f"##### {'Editar usuario' if es_edicion else 'Nuevo usuario'}")

        if es_edicion:
            if st.button("Cancelar edicion", key="usr_cancel"):
                st.session_state["usr_edit_id"] = None
                st.rerun()
            st.divider()

        nombre_in = st.text_input(
            "Nombre para mostrar *",
            value=u_edit["nombre"] if es_edicion else "",
            key=f"usr_nombre_{form_key}",
        )

        if not es_edicion:
            username_in = st.text_input(
                "Username (para login) *",
                key=f"usr_username_{form_key}",
                help="Nombre de usuario unico para iniciar sesion. No se puede cambiar despues.",
            )
        else:
            st.text_input(
                "Username",
                value=u_edit["username"] if u_edit["username"] else "",
                disabled=True,
                key=f"usr_username_dis_{form_key}",
                help="El username no se puede modificar.",
            )

        email_in = st.text_input(
            "Email (opcional)",
            value=u_edit["email"] if (es_edicion and u_edit["email"]) else "",
            key=f"usr_email_{form_key}",
        )

        rol_opts = ROLES_USUARIO
        rol_idx  = rol_opts.index(u_edit["rol"]) if (es_edicion and u_edit["rol"] in rol_opts) else 1
        rol_in   = st.selectbox("Rol", rol_opts, index=rol_idx, key=f"usr_rol_{form_key}")

        password_in = st.text_input(
            "Contrasena *" if not es_edicion else "Nueva contrasena (dejar vacio para no cambiar)",
            type="password",
            key=f"usr_pw_{form_key}",
        )

        activo_in = True
        if es_edicion:
            activo_in = st.checkbox(
                "Usuario activo",
                value=bool(u_edit["activo"]),
                key=f"usr_activo_{form_key}",
            )

        rol_color = _ROL_COLOR.get(rol_in, GRAY)
        st.markdown(
            f'<div style="margin:.5rem 0 .3rem 0;padding:.4rem .7rem;border-radius:10px;'
            f'background:{rol_color}18;border:1px solid {rol_color}44;'
            f'font-size:.78rem;color:{rol_color};font-weight:600;">'
            f'Rol seleccionado: {rol_in}</div>',
            unsafe_allow_html=True,
        )

        if st.button(
            "Guardar cambios" if es_edicion else "Crear usuario",
            key="usr_submit",
            use_container_width=True,
        ):
            if not nombre_in.strip():
                st.warning("El nombre es obligatorio.")
            elif not es_edicion and not username_in.strip():
                st.warning("El username es obligatorio.")
            elif not es_edicion and not password_in.strip():
                st.warning("La contrasena es obligatoria para usuarios nuevos.")
            else:
                if es_edicion:
                    update_user_auth(
                        edit_id, nombre_in, email_in, rol_in, activo_in,
                        new_password=password_in if password_in.strip() else None,
                    )
                    st.session_state["usr_edit_id"] = None
                    st.success(f"Usuario **{nombre_in}** actualizado.")
                else:
                    ok = create_user(username_in.strip(), password_in.strip(),
                                     rol_in, nombre_in.strip(), email_in.strip())
                    if ok:
                        st.success(f"Usuario **{nombre_in}** creado con username @{username_in}.")
                    else:
                        st.error(f"El username **@{username_in}** ya existe. Elige otro.")
                st.rerun()

        st.divider()
        st.caption(
            "Roles: **Administrador** — acceso total. "
            "**Visualizador** — solo lectura y simulacion."
        )
