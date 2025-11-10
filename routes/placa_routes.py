from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from models.base import db
from models.placa import Placa

placa_bp = Blueprint("placa_bp", __name__)

# ---- Listar placas ----
@placa_bp.route("/", methods=["GET"])
@login_required
def listar_placas():
    try:
        placas = Placa.query.order_by(Placa.fecha_registro.desc()).all()
        return render_template("placas.html", placas=placas)
    except Exception as e:
        current_app.logger.exception(f"Error al listar placas: {e}")
        flash("Ocurrió un error al cargar las placas.", "danger")
        return render_template("placas.html", placas=[])

# ---- Registrar nueva placa ----
@placa_bp.route("/nueva", methods=["POST"])
@login_required
def nueva_placa():
    try:
        numero_placa = request.form.get("numero_placa")
        propietario = request.form.get("propietario", None)

        if not numero_placa:
            flash("Debe ingresar un número de placa.", "warning")
            return redirect(url_for("placa_bp.listar_placas"))

        # Verificar duplicados
        if Placa.query.filter_by(numero_placa=numero_placa.upper().strip()).first():
            flash("Esta placa ya está registrada.", "danger")
            return redirect(url_for("placa_bp.listar_placas"))

        nueva = Placa(
            numero_placa=numero_placa.upper().strip(),
            propietario=propietario,
            usuario_id=current_user.id if current_user else None
        )
        db.session.add(nueva)
        db.session.commit()

        flash(f"Placa {numero_placa.upper()} agregada exitosamente.", "success")
        return redirect(url_for("placa_bp.listar_placas"))

    except Exception as e:
        current_app.logger.exception(f"Error al agregar placa: {e}")
        flash("Error al registrar la placa.", "danger")
        return redirect(url_for("placa_bp.listar_placas"))

# ---- Cambiar estado (Activa / Inactiva) ----
@placa_bp.route("/estado/<int:placa_id>", methods=["POST"])
@login_required
def cambiar_estado(placa_id):
    try:
        placa = Placa.query.get_or_404(placa_id)
        nuevo_estado = request.form.get("estado")

        if nuevo_estado not in ["Activa", "Inactiva"]:
            flash("Estado inválido.", "warning")
            return redirect(url_for("placa_bp.listar_placas"))

        placa.estado = nuevo_estado
        db.session.commit()

        flash(f"Estado de la placa {placa.numero_placa} cambiado a {nuevo_estado}.", "info")
        return redirect(url_for("placa_bp.listar_placas"))
    except Exception as e:
        current_app.logger.exception(f"Error al cambiar estado de placa: {e}")
        flash("Error al actualizar el estado de la placa.", "danger")
        return redirect(url_for("placa_bp.listar_placas"))