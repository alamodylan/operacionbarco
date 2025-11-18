from flask import Blueprint, jsonify, request, current_app, render_template
from flask_login import login_required
from models.notificacion import enviar_notificacion
from models.movimiento import MovimientoBarco
from models.placa import Placa
from models.base import db
from datetime import datetime, timedelta
import pytz

# 📌 Corrección: ahora sí tiene el prefijo correcto
notificacion_bp = Blueprint(
    "notificacion_bp",
    __name__,
    url_prefix="/notificaciones"   # ← ESTE ES EL CAMBIO
)

CR_TZ = pytz.timezone("America/Costa_Rica")


@notificacion_bp.route("/check", methods=["GET"])
@login_required
def check():
    hora_cr = datetime.now(CR_TZ).strftime("%d/%m/%Y %H:%M:%S")
    return render_template("notificacion.html", hora_cr=hora_cr)


@notificacion_bp.route("/test", methods=["POST"])
@login_required
def test_notificacion():
    try:
        data = request.get_json()
        mensaje = data.get("mensaje", "🧪 Notificación de prueba desde Operación Barco")

        ok = enviar_notificacion(mensaje)
        if ok:
            return jsonify({"status": "success", "message": "Notificación enviada"}), 200
        return jsonify({"status": "error", "message": "No se pudo enviar la notificación"}), 500

    except Exception as e:
        current_app.logger.exception(f"Error en test_notificacion: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@notificacion_bp.route("/emergencia", methods=["GET"])
def alerta_emergencia():
    ahora = datetime.now(CR_TZ).replace(tzinfo=None)
    movimientos = MovimientoBarco.query.filter_by(estado="en_ruta").all()
    total_alertas = 0

    for mov in movimientos:
        tiempo_trans = ahora - mov.hora_salida

        if tiempo_trans < timedelta(minutes=15):
            continue

        if mov.ultima_notificacion:
            delta = ahora - mov.ultima_notificacion
            if delta < timedelta(minutes=2):
                continue

        placa = Placa.query.get(mov.placa_id)
        nombre_chofer = placa.chofer if hasattr(placa, "chofer") else "Chofer no registrado"

        horas, resto = divmod(tiempo_trans.seconds, 3600)
        minutos, segundos = divmod(resto, 60)

        mensaje = (
            f"🚨🚨🚨🚨🚨🚨🚨🚨🚨"
            f"🚨 *ALERTA DE EMERGENCIA*\n"
            f"Un vehículo lleva *más de 15 minutos sin cerrarse*.\n\n"
            f"👤 Chofer: {nombre_chofer}\n"
            f"🚛 Placa: {placa.numero_placa}\n"
            f"📦 Identificador: {mov.contenedor}\n"
            f"🕒 Salida: {mov.hora_salida.strftime('%d/%m/%Y %H:%M')}\n"
            f"⏳ Tiempo transcurrido: {horas}h {minutos}m {segundos}s\n\n"
            f"⚠️ Revisar urgentemente."
            f"🚨🚨🚨🚨🚨🚨🚨🚨🚨"
        )

        enviar_notificacion(mensaje)

        mov.ultima_notificacion = ahora
        db.session.commit()

        total_alertas += 1

    return jsonify({
        "status": "ok",
        "alertas_enviadas": total_alertas,
        "timestamp": ahora.strftime("%d/%m/%Y %H:%M:%S")
    })