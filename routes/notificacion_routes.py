from flask import Blueprint, jsonify, request, current_app, render_template
from flask_login import login_required
from models.notificacion import enviar_notificacion
from models.movimiento import MovimientoBarco
from models.placa import Placa
from models.base import db
from datetime import datetime, timedelta
import pytz

# Prefijo correcto
notificacion_bp = Blueprint(
    "notificacion_bp",
    __name__,
    url_prefix="/notificaciones"
)

CR_TZ = pytz.timezone("America/Costa_Rica")


# -----------------------------------------------------------
# CHECK VISUAL
# -----------------------------------------------------------
@notificacion_bp.route("/check", methods=["GET"])
@login_required
def check():
    hora_cr = datetime.now(CR_TZ).strftime("%d/%m/%Y %H:%M:%S")
    return render_template("notificacion.html", hora_cr=hora_cr)


# -----------------------------------------------------------
# PRUEBA MANUAL
# -----------------------------------------------------------
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


# -----------------------------------------------------------
# EMERGENCIA AUTOMÁTICA
# -----------------------------------------------------------
@notificacion_bp.route("/emergencia", methods=["GET"])
def alerta_emergencia():

    # Siempre CR y sin tzinfo
    ahora = datetime.now(CR_TZ).replace(tzinfo=None)
    movimientos = MovimientoBarco.query.filter_by(estado="en_ruta").all()
    total_alertas = 0

    # =======================================================
    # 🔥 1) ALERTA POR MÁS DE 15 MINUTOS EN RUTA
    # =======================================================
    for mov in movimientos:

        tiempo_trans = ahora - mov.hora_salida

        # no antes de 15 minutos
        if tiempo_trans < timedelta(minutes=15):
            continue

        # Control para evitar spam
        if mov.ultima_notificacion:
            delta = ahora - mov.ultima_notificacion
            if delta < timedelta(minutes=2):
                continue

        placa = Placa.query.get(mov.placa_id)
        nombre_chofer = placa.propietario or "Chofer no registrado"

        horas, resto = divmod(tiempo_trans.seconds, 3600)
        minutos, segundos = divmod(resto, 60)

        mensaje = (
            f"🚨🚨🚨🚨🚨🚨🚨🚨🚨\n"
            f"🚨 *ALERTA DE EMERGENCIA*\n"
            f"Un vehículo lleva *más de 15 minutos sin cerrarse*.\n\n"
            f"👤 Chofer: {nombre_chofer}\n"
            f"🚛 Placa: {placa.numero_placa}\n"
            f"📦 Identificador: {mov.contenedor}\n"
            f"🕒 Salida: {mov.hora_salida.strftime('%d/%m/%Y %H:%M')}\n"
            f"⏳ Tiempo transcurrido: {horas}h {minutos}m {segundos}s\n\n"
            f"⚠️ Revisar urgentemente.\n"
            f"🚨🚨🚨🚨🚨🚨🚨🚨🚨"
        )

        enviar_notificacion(mensaje)

        mov.ultima_notificacion = ahora
        db.session.commit()

        total_alertas += 1

    # =======================================================
    # ⭐ 2) ALERTA POR ORDEN INCORRECTO (solo una vez)
    # =======================================================
    todos = MovimientoBarco.query.all()
    orden_salida = sorted(todos, key=lambda m: m.hora_salida)

    for i in range(len(orden_salida)):

        mov_x = orden_salida[i]

        # si ya llegó, no está atrasado
        if mov_x.estado != "en_ruta":
            continue

        for j in range(i + 1, len(orden_salida)):

            mov_y = orden_salida[j]

            # mov_y llegó pero mov_x no
            if mov_y.hora_llegada and not mov_x.hora_llegada:

                # Evitar notificación repetida
                if mov_x.alerta_orden_enviada:
                    continue

                placa_x = Placa.query.get(mov_x.placa_id)
                placa_y = Placa.query.get(mov_y.placa_id)

                chofer_x = placa_x.propietario or "No registrado"
                chofer_y = placa_y.propietario or "No registrado"

                tiempo_trans = ahora - mov_x.hora_salida
                horas, resto = divmod(tiempo_trans.seconds, 3600)
                minutos, segundos = divmod(resto, 60)

                mensaje = (
                    "🚨 *ALERTA DE ORDEN INCORRECTO*\n\n"
                    "Un viaje que salió ANTES aún no ha llegado, "
                    "pero un viaje posterior ya se finalizó.\n\n"
                    "🛑 Viaje retrasado:\n"
                    f"👤 Chofer: {chofer_x}\n"
                    f"🚛 Placa: {placa_x.numero_placa}\n"
                    f"📦 Identificador: {mov_x.contenedor}\n"
                    f"🕒 Salida: {mov_x.hora_salida.strftime('%d/%m/%Y %H:%M')}\n"
                    f"⏳ Tiempo transcurrido: {horas}h {minutos}m {segundos}s\n\n"
                    "🟢 Viaje posterior que llegó primero:\n"
                    f"👤 Chofer: {chofer_y}\n"
                    f"🚛 Placa: {placa_y.numero_placa}\n"
                    f"📦 Identificador: {mov_y.contenedor}\n"
                    f"🕒 Llegada: {mov_y.hora_llegada.strftime('%d/%m/%Y %H:%M')}\n\n"
                    "⚠️ Revisar posible atraso anómalo."
                )

                enviar_notificacion(mensaje)

                mov_x.alerta_orden_enviada = True
                db.session.commit()

                total_alertas += 1

    return jsonify({
        "status": "ok",
        "alertas_enviadas": total_alertas,
        "timestamp": ahora.strftime("%d/%m/%Y %H:%M:%S")
    })