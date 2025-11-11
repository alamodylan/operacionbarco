# routes/movimiento_routes.py
from flask import Blueprint, render_template, request, flash, jsonify, current_app
from flask_login import login_required
from models.base import db
from models.movimiento import MovimientoBarco
from models.operacion import Operacion
from datetime import datetime
import pytz
CR_TZ = pytz.timezone("America/Costa_Rica")

movimiento_bp = Blueprint("movimiento_bp", __name__)

# ============================================================
# 📋 LISTAR MOVIMIENTOS FINALIZADOS (operaciones finalizadas)
# ============================================================
@movimiento_bp.route("/", methods=["GET"])
@login_required
def listar_movimientos():
    try:
        # 🔹 Buscar operaciones finalizadas
        operaciones = (
            Operacion.query
            .filter_by(estado="finalizada")
            .order_by(Operacion.fecha_creacion.desc())
            .all()
        )

        # 🔹 Filtrar solo los movimientos finalizados dentro de cada operación
        datos = []
        for op in operaciones:
            movimientos_finalizados = [
                m for m in op.movimientos if m.estado == "finalizado"
            ]
            if movimientos_finalizados:
                datos.append({
                    "operacion": op,
                    "movimientos": movimientos_finalizados
                })

        return render_template("movimientos.html", datos=datos)

    except Exception as e:
        current_app.logger.exception(f"Error al listar movimientos: {e}")
        flash("Ocurrió un error al cargar los movimientos.", "danger")
        return render_template("movimientos.html", datos=[])

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

        # ✅ Hora correcta de Costa Rica
        movimiento.hora_llegada = datetime.now(CR_TZ).replace(tzinfo=None)
        movimiento.estado = "finalizado"
        db.session.commit()

        return jsonify({"mensaje": f"Movimiento {movimiento.contenedor} finalizado correctamente"}), 200

    except Exception as e:
        current_app.logger.exception(f"Error al registrar llegada del movimiento: {e}")
        return jsonify({"error": "Error interno al registrar llegada"}), 500
    
