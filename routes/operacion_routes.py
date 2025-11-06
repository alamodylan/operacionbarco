# routes/operacion_routes.py
from flask import Blueprint, request, jsonify, render_template, current_app
from datetime import datetime
import threading, time
from models.notificacion import enviar_notificacion
from models.operacion import Operacion
from models.placa import Placa
from models.base import db

operacion_bp = Blueprint("operacion_bp", __name__)

# ---- Función interna que espera 15 minutos y revisa el estado ----
def verificar_llegada(operacion_id, placa_codigo, contenedor):
    """Hilo que espera 15 min y envía alerta si la operación no ha sido finalizada."""
    try:
        time.sleep(900)  # 900 segundos = 15 minutos
        with current_app.app_context():
            operacion = Operacion.query.get(operacion_id)
            if operacion and operacion.estado == "EN_RUTA" and not operacion.alerta_enviada:
                operacion.estado = "ALERTA"
                operacion.alerta_enviada = True
                db.session.commit()
                mensaje = (
                    f"⚠️ Cabezal {placa_codigo} con contenedor {contenedor} "
                    "NO HA LLEGADO A SU DESTINO EN EL TIEMPO LÍMITE."
                )
                enviar_notificacion(mensaje)
    except Exception as e:
        current_app.logger.exception(f"Error en verificación de llegada: {e}")

# ---- Ruta para registrar salida ----
@operacion_bp.route("/operacion/salida", methods=["POST"])
def registrar_salida():
    try:
        data = request.get_json()
        placa_codigo = data.get("placa")
        contenedor = data.get("contenedor")

        if not placa_codigo or not contenedor:
            return jsonify({"error": "Datos incompletos"}), 400

        placa = Placa.query.filter_by(numero_placa=placa_codigo).first()
        if not placa:
            return jsonify({"error": f"La placa {placa_codigo} no existe"}), 404

        nueva_operacion = Operacion(
            placa_id=placa.id,
            contenedor=contenedor,
            hora_salida=datetime.utcnow(),
            estado="EN_RUTA"
        )

        db.session.add(nueva_operacion)
        db.session.commit()

        mensaje = (
            f"🚛 Cabezal {placa_codigo} sale de muelle con contenedor "
            f"{contenedor} a las {nueva_operacion.hora_salida.strftime('%H:%M:%S')} UTC."
        )
        enviar_notificacion(mensaje)

        # Lanzar hilo de monitoreo (15 minutos)
        hilo = threading.Thread(target=verificar_llegada, args=(nueva_operacion.id, placa_codigo, contenedor))
        hilo.daemon = True
        hilo.start()

        return jsonify({"mensaje": "Salida registrada y monitoreo iniciado"}), 201

    except Exception as e:
        current_app.logger.exception(f"Error al registrar salida: {e}")
        return jsonify({"error": "Error interno al registrar salida"}), 500

# ---- Ruta para registrar llegada ----
@operacion_bp.route("/operacion/llegada/<int:id>", methods=["POST"])
def registrar_llegada(id):
    try:
        operacion = Operacion.query.get(id)
        if not operacion:
            return jsonify({"error": "Operación no encontrada"}), 404

        if operacion.estado == "FINALIZADA":
            return jsonify({"mensaje": "La operación ya estaba finalizada"}), 200

        operacion.finalizar()
        db.session.commit()

        placa_codigo = operacion.placa_obj.numero_placa
        mensaje = (
            f"✅ Cabezal {placa_codigo} ingresa a predio con contenedor "
            f"{operacion.contenedor} correctamente a las {operacion.hora_llegada.strftime('%H:%M:%S')} UTC."
        )
        enviar_notificacion(mensaje)

        return jsonify({"mensaje": "Llegada registrada correctamente"}), 200

    except Exception as e:
        current_app.logger.exception(f"Error al registrar llegada: {e}")
        return jsonify({"error": "Error interno al registrar llegada"}), 500

# ---- Ruta: Historial de operaciones ----
@operacion_bp.route("/historial")
def historial_operaciones():
    operaciones = Operacion.query.filter_by(estado="FINALIZADA").order_by(Operacion.hora_llegada.desc()).all()
    return render_template("historial.html", operaciones=operaciones)
