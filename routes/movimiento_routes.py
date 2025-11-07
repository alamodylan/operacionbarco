# routes/movimiento_routes.py
from flask import Blueprint, render_template, request, flash, jsonify, current_app
from flask_login import login_required
from models.base import db
from models.movimiento import MovimientoBarco
from models.operacion import Operacion
from datetime import datetime

movimiento_bp = Blueprint("movimiento_bp", __name__)

# ============================================================
# 📋 LISTAR MOVIMIENTOS FINALIZADOS (operaciones finalizadas)
# ============================================================
@movimiento_bp.route("/", methods=["GET"])
@login_required
def listar_movimientos():
    try:
        # Mostrar operaciones finalizadas junto a sus movimientos
        operaciones = (
            Operacion.query
            .filter_by(estado="finalizada")
            .order_by(Operacion.fecha_creacion.desc())
            .all()
        )
        return render_template("movimientos.html", operaciones=operaciones)
    except Exception as e:
        current_app.logger.exception(f"Error al listar movimientos: {e}")
        flash("Ocurrió un error al cargar los movimientos.", "danger")
        return render_template("movimientos.html", operaciones=[])

# ============================================================
# 🏁 REGISTRAR LLEGADA / FINALIZAR MOVIMIENTO
# ============================================================
@movimiento_bp.route("/llegada/<int:id>", methods=["POST"])
@login_required
def registrar_llegada_movimiento(id):
    try:
        movimiento = MovimientoBarco.query.get(id)
        if not movimiento:
            return jsonify({"error": "Movimiento no encontrado"}), 404

        if movimiento.estado == "finalizado":
            return jsonify({"mensaje": "El movimiento ya fue finalizado"}), 200

        movimiento.hora_llegada = datetime.utcnow()
        movimiento.estado = "finalizado"
        db.session.commit()

        return jsonify({"mensaje": f"Movimiento {movimiento.contenedor} finalizado correctamente"}), 200

    except Exception as e:
        current_app.logger.exception(f"Error al registrar llegada del movimiento: {e}")
        return jsonify({"error": "Error interno al registrar llegada"}), 500
    
