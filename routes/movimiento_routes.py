# routes/movimiento_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from models.base import db
from models.movimiento import Movimiento
from models.operacion import Operacion
from models.placa import Placa
from models.notificacion import enviar_notificacion
from datetime import datetime

movimiento_bp = Blueprint("movimiento_bp", __name__)

# ---- Listar movimientos ----
@movimiento_bp.route("/", methods=["GET"])
@login_required
def listar_movimientos():
    try:
        movimientos = Movimiento.query.order_by(Movimiento.hora_salida.desc()).all()
        return render_template("movimientos.html", movimientos=movimientos)
    except Exception as e:
        current_app.logger.exception(f"Error al listar movimientos: {e}")
        flash("Ocurrió un error al cargar los movimientos.", "danger")
        return render_template("movimientos.html", movimientos=[])

# ---- Registrar nuevo movimiento ----
@movimiento_bp.route("/nuevo", methods=["POST"])
@login_required
def registrar_movimiento():
    try:
        data = request.get_json() or request.form
        operacion_id = data.get("operacion_id")
        placa_id = data.get("placa_id")
        contenedor = data.get("numero_contenedor")

        if not operacion_id or not placa_id or not contenedor:
            return jsonify({"error": "Datos incompletos"}), 400

        nuevo_mov = Movimiento(
            operacion_id=operacion_id,
            placa_id=placa_id,
            numero_contenedor=contenedor,
            hora_salida=datetime.utcnow(),
            usuario_salida_id=current_user.id,
            estado="EN_TRANSITO"
        )

        db.session.add(nuevo_mov)
        db.session.commit()

        # Notificación automática
        placa = Placa.query.get(placa_id)
        enviar_notificacion(
            f"🚚 Movimiento iniciado: Cabezal {placa.numero_placa} con contenedor {contenedor} ha salido del punto intermedio."
        )

        return jsonify({"mensaje": "Movimiento registrado correctamente"}), 201

    except Exception as e:
        current_app.logger.exception(f"Error al registrar movimiento: {e}")
        return jsonify({"error": "Error interno al registrar movimiento"}), 500

# ---- Registrar llegada de un movimiento ----
@movimiento_bp.route("/llegada/<int:id>", methods=["POST"])
@login_required
def registrar_llegada_movimiento(id):
    try:
        movimiento = Movimiento.query.get(id)
        if not movimiento:
            return jsonify({"error": "Movimiento no encontrado"}), 404

        if movimiento.estado == "FINALIZADO":
            return jsonify({"mensaje": "El movimiento ya fue finalizado"}), 200

        movimiento.hora_llegada = datetime.utcnow()
        movimiento.usuario_llegada_id = current_user.id
        movimiento.estado = "FINALIZADO"
        db.session.commit()

        placa = movimiento.placa
        enviar_notificacion(
            f"✅ Movimiento completado: Cabezal {placa.numero_placa} con contenedor {movimiento.numero_contenedor} llegó correctamente al destino intermedio."
        )

        return jsonify({"mensaje": "Movimiento finalizado correctamente"}), 200

    except Exception as e:
        current_app.logger.exception(f"Error al registrar llegada del movimiento: {e}")
        return jsonify({"error": "Error interno al registrar llegada"}), 500