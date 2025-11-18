from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from models.usuario import Usuario
from models.base import db

usuario_bp = Blueprint("usuario_bp", __name__, url_prefix="/usuarios")

# ------------------------------------------------------------
# 📋 1️⃣ Listar todos los usuarios (solo Admin)
# ------------------------------------------------------------
@usuario_bp.route("/", methods=["GET"])
@login_required
def listar_usuarios():
    try:
        if current_user.rol != "Admin":
            flash("No tienes permiso para acceder a esta sección.", "danger")
            return redirect(url_for("dashboard"))

        usuarios = Usuario.query.order_by(Usuario.id.asc()).all()
        return render_template("usuarios.html", usuarios=usuarios)
    except Exception as e:
        current_app.logger.exception(f"Error al listar usuarios: {e}")
        flash("Ocurrió un error al cargar los usuarios.", "danger")
        return render_template("usuarios.html", usuarios=[])

# ------------------------------------------------------------
# ➕ 2️⃣ Crear nuevo usuario (solo Admin)
# ------------------------------------------------------------
@usuario_bp.route("/nuevo", methods=["POST"])
@login_required
def crear_usuario():
    try:
        if current_user.rol != "Admin":
            flash("No tienes permiso para crear usuarios.", "danger")
            return redirect(url_for("usuario_bp.listar_usuarios"))

        nombre = request.form.get("nombre")
        email = request.form.get("email")
        password = request.form.get("password")
        rol = request.form.get("rol")  # ← YA NO FORZAMOS "Usuario"

        if not nombre or not email or not password:
            flash("Todos los campos son obligatorios.", "warning")
            return redirect(url_for("usuario_bp.listar_usuarios"))

        # Verificar duplicado
        if Usuario.query.filter_by(email=email).first():
            flash("Ya existe un usuario con ese correo.", "danger")
            return redirect(url_for("usuario_bp.listar_usuarios"))

        # Crear nuevo usuario con rol correcto
        nuevo = Usuario(
            nombre=nombre.strip(),
            email=email.strip(),
            rol=rol  # ← LO GUARDAMOS DIRECTO
        )
        nuevo.set_password(password)

        db.session.add(nuevo)
        db.session.commit()

        flash(f"Usuario '{nombre}' creado exitosamente.", "success")
        return redirect(url_for("usuario_bp.listar_usuarios"))

    except Exception as e:
        current_app.logger.exception(f"Error al crear usuario: {e}")
        flash("Ocurrió un error al crear el usuario.", "danger")
        return redirect(url_for("usuario_bp.listar_usuarios"))

# ------------------------------------------------------------
# 🔄 3️⃣ Cambiar rol (Admin, UsuarioPredio, UsuarioMuelle)
# ------------------------------------------------------------
@usuario_bp.route("/cambiar_rol/<int:id>", methods=["POST"])
@login_required
def cambiar_rol(id):
    try:
        if current_user.rol != "Admin":
            flash("No tienes permiso para modificar roles.", "danger")
            return redirect(url_for("usuario_bp.listar_usuarios"))

        usuario = Usuario.query.get_or_404(id)
        nuevo_rol = request.form.get("rol")

        # Lista válida de roles
        ROLES_VALIDOS = ["Admin", "UsuarioPredio", "UsuarioMuelle"]

        if nuevo_rol not in ROLES_VALIDOS:
            flash("Rol inválido.", "warning")
            return redirect(url_for("usuario_bp.listar_usuarios"))

        usuario.rol = nuevo_rol
        db.session.commit()

        flash(f"Rol de {usuario.nombre} actualizado a {nuevo_rol}.", "info")
        return redirect(url_for("usuario_bp.listar_usuarios"))

    except Exception as e:
        current_app.logger.exception(f"Error al cambiar rol: {e}")
        flash("Error al cambiar el rol del usuario.", "danger")
        return redirect(url_for("usuario_bp.listar_usuarios"))

# ------------------------------------------------------------
# 🗑️ 4️⃣ Eliminar usuario (solo Admin)
# ------------------------------------------------------------
@usuario_bp.route("/eliminar/<int:id>", methods=["POST"])
@login_required
def eliminar_usuario(id):
    try:
        if current_user.rol != "Admin":
            flash("No tienes permiso para eliminar usuarios.", "danger")
            return redirect(url_for("usuario_bp.listar_usuarios"))

        usuario = Usuario.query.get_or_404(id)
        db.session.delete(usuario)
        db.session.commit()

        flash(f"Usuario '{usuario.nombre}' eliminado correctamente.", "success")
        return redirect(url_for("usuario_bp.listar_usuarios"))

    except Exception as e:
        current_app.logger.exception(f"Error al eliminar usuario: {e}")
        flash("Error al eliminar el usuario.", "danger")
        return redirect(url_for("usuario_bp.listar_usuarios"))