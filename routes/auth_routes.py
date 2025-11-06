from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from models.base import db
from models.usuario import Usuario

auth_bp = Blueprint("auth_bp", __name__, url_prefix="/auth")

# ---- Login ----
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        user = Usuario.query.filter_by(email=email).first()
        if user and user.check_password(password):
            # 🔒 Marca la sesión como "permanente" para que Flask aplique el temporizador
            session.permanent = True
            login_user(user)
            flash(f"Bienvenido, {user.nombre}", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Correo o contraseña incorrectos", "danger")

    return render_template("login.html")


# ---- Logout ----
@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    session.clear()  # 🔐 Limpia toda la sesión del navegador
    flash("Sesión cerrada correctamente", "info")
    return redirect(url_for("auth_bp.login"))


# ---- Registro de nuevo usuario ----
@auth_bp.route("/register", methods=["GET", "POST"])
@login_required
def register():
    if request.method == "POST":
        nombre = request.form.get("nombre")
        email = request.form.get("email")
        password = request.form.get("password")

        if not (nombre and email and password):
            flash("Todos los campos son obligatorios", "warning")
            return render_template("usuarios.html")

        # Verificar si ya existe el correo
        if Usuario.query.filter_by(email=email).first():
            flash("Ya existe un usuario con ese correo", "danger")
            return render_template("usuarios.html")

        nuevo_usuario = Usuario(nombre=nombre, email=email)
        nuevo_usuario.set_password(password)

        db.session.add(nuevo_usuario)
        db.session.commit()

        flash("Usuario creado exitosamente", "success")
        return redirect(url_for("auth_bp.login"))

    return render_template("usuarios.html")