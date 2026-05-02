import bcrypt
from src.core.userdb import userdb


class UserService:

    def get_all_users(self):
        return userdb.get_all_users()

    def get_all_workspaces(self):
        ws_set = {"general"}
        for u in userdb.get_all_users():
            for ws in u.get("workspaces", ["general"]):
                if ws not in ("all", "admin-only"):
                    ws_set.add(ws)
        try:
            import sqlite3
            conn = sqlite3.connect("./db/cortexa_meta.db")
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM workspaces WHERE name NOT IN ('all','admin-only')")
            for (name,) in cursor.fetchall():
                if name:
                    ws_set.add(name)
            cursor.execute("SELECT workspace FROM documents WHERE workspace IS NOT NULL")
            for (ws_raw,) in cursor.fetchall():
                if ws_raw:
                    for part in str(ws_raw).split(","):
                        part = part.strip()
                        if part and part not in ("all", "admin-only"):
                            ws_set.add(part)
            conn.close()
        except Exception:
            pass
        return sorted(ws_set)

    def update_can_upload(self, username, can_upload: bool):
        if not userdb.get_user(username):
            return False, "Usuario no encontrado."
        userdb.update_user(username, can_upload=can_upload)
        return True, "Permiso de subida actualizado."

    def update_permissions(self, username, workspaces, can_upload, upload_groups,
                           can_delete, delete_groups, role=None):
        user = userdb.get_user(username)
        if not user:
            return False, "Usuario no encontrado."
        effective_role = role if role is not None else user["role"]
        if effective_role != "admin":
            workspaces = [w for w in workspaces if w not in ("all", "admin-only")]
        if not workspaces:
            workspaces = ["general"]
        updates = {
            "workspaces":    workspaces,
            "can_upload":    can_upload,
            "upload_groups": upload_groups if can_upload else [],
            "can_delete":    can_delete,
            "delete_groups": delete_groups if can_delete else [],
        }
        if role is not None:
            updates["role"] = role
        userdb.update_user(username, **updates)
        return True, "Permisos actualizados."

    def propagate_role(self, role_name, role_data):
        users = userdb.get_all_users()
        affected = 0
        for u in users:
            if u["role"] != role_name or role_name == "admin":
                continue
            updates = {
                "can_upload":    role_data["can_upload"],
                "upload_groups": role_data["upload_groups"] if role_data["can_upload"] else [],
                "can_delete":    role_data["can_delete"],
                "delete_groups": role_data["delete_groups"] if role_data["can_delete"] else [],
            }
            if role_data.get("workspaces") and role_data["workspaces"] != ["all"]:
                updates["workspaces"] = role_data["workspaces"]
            userdb.update_user(u["username"], **updates)
            affected += 1
        return affected

    def update_group_permissions(self, group_name, can_upload, can_delete):
        users = userdb.get_all_users()
        affected = 0
        for u in users:
            if u["role"] == "admin":
                continue
            if group_name not in u.get("workspaces", []):
                continue
            updates = {}
            if can_upload is not None:
                updates["can_upload"] = can_upload
                updates["upload_groups"] = (
                    sorted(set(u.get("upload_groups", [])) | {group_name})
                    if can_upload
                    else [g for g in u.get("upload_groups", []) if g != group_name]
                )
            if can_delete is not None:
                updates["can_delete"] = can_delete
                updates["delete_groups"] = (
                    sorted(set(u.get("delete_groups", [])) | {group_name})
                    if can_delete
                    else [g for g in u.get("delete_groups", []) if g != group_name]
                )
            if updates:
                userdb.update_user(u["username"], **updates)
                affected += 1
        return affected

    def add_user(self, username, name, email, password, role, workspaces,
                 can_upload=False, upload_groups=None, can_delete=False, delete_groups=None):
        if not username or not password:
            return False, "Usuario y contraseña son obligatorios."
        if userdb.get_user(username):
            return False, f"El usuario '{username}' ya existe."
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(12)).decode("utf-8")
        eff_cu = can_upload or role == "admin"
        eff_ug = upload_groups if upload_groups is not None else (["all"] if eff_cu else [])
        eff_cd = can_delete or role == "admin"
        eff_dg = delete_groups if delete_groups is not None else (["all"] if eff_cd else [])
        success = userdb.add_user(
            username, name, email, hashed, role,
            workspaces if workspaces else ["general"],
            eff_cu, eff_ug if eff_cu else [],
            eff_cd, eff_dg if eff_cd else [],
        )
        if success:
            return True, f"Usuario '{username}' creado correctamente."
        return False, f"El usuario '{username}' ya existe."

    def delete_user(self, username, current_user):
        if username == current_user:
            return False, "No puedes eliminar tu propia cuenta."
        if not userdb.get_user(username):
            return False, "Usuario no encontrado."
        userdb.delete_user(username)
        return True, f"Usuario '{username}' eliminado."

    def update_password(self, username, new_password, temp=False):
        if not new_password or len(new_password) < 8:
            return False, "La contraseña debe tener al menos 8 caracteres."
        if not userdb.get_user(username):
            return False, "Usuario no encontrado."
        hashed = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt(12)).decode("utf-8")
        userdb.update_password(username, hashed, temp=temp)
        return True, "Contraseña actualizada correctamente."

    def update_workspaces(self, username, workspaces):
        user = userdb.get_user(username)
        if not user:
            return False, "Usuario no encontrado."
        if user["role"] != "admin":
            workspaces = [w for w in workspaces if w not in ("all", "admin-only")]
        if not workspaces:
            workspaces = ["general"]
        userdb.update_user(username, workspaces=workspaces)
        return True, "Accesos actualizados."

    def rename_workspace(self, old_name, new_name):
        for u in userdb.get_all_users():
            ws = u.get("workspaces", ["general"])
            if old_name in ws:
                userdb.update_user(u["username"], workspaces=[new_name if w == old_name else w for w in ws])


user_service = UserService()
