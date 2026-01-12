from flask import Blueprint, jsonify, request, current_app, render_template
from flask_login import login_required
from models.notificacion import enviar_notificacion
from models.movimiento import MovimientoBarco
from models.placa import Placa
from models.base import db
from datetime import datetime, timedelta
import pytz
import os
from pywebpush import webpush, WebPushException
import json

# Prefijo correcto
notificacion_bp = Blueprint(
    "notificacion_bp",
    __name__,
    url_prefix="/notificaciones"
)

CR_TZ = pytz.timezone("America/Costa_Rica")


# -----------------------------------------------------------
# ✅ NUEVO: Quitar formato WhatsApp (*negritas*) para Push
# -----------------------------------------------------------
def _push_text(texto: str) -> str:
    # Push no interpreta *negritas* y se verían los asteriscos.
    return (texto or "").replace("*", "")


# -----------------------------------------------------------
# ✅ NUEVO: Enviar Push usando el MISMO mensaje que WhatsApp
# -----------------------------------------------------------
def enviar_push_mismo_mensaje(mensaje: str, titulo: str = "Operación Barco") -> dict:
    """
    Envía push a todos los dispositivos registrados en push_subs.json.
    Si no hay dispositivos o no hay VAPID, no rompe nada: solo no envía.
    """
    try:
        ruta = os.path.join(current_app.root_path, "push_subs.json")
        if not os.path.exists(ruta):
            return {"enviados": 0, "fallidos": 0}

        with open(ruta, "r", encoding="utf-8") as f:
            subs = json.load(f) or []

        vapid_private = os.getenv("VAPID_PRIVATE_KEY", "")
        vapid_subject = os.getenv("VAPID_SUBJECT", "mailto:ti@alamo.com")

        if not vapid_private or not subs:
            return {"enviados": 0, "fallidos": 0}

        payload = json.dumps({
            "title": titulo,
            "body": _push_text(mensaje)
        })

        enviados, fallidos = 0, 0
        vivos = []

        for s in subs:
            sub_info = {
                "endpoint": s["endpoint"],
                "keys": {"p256dh": s["p256dh"], "auth": s["auth"]}
            }
            try:
                webpush(
                    subscription_info=sub_info,
                    data=payload,
                    vapid_private_key=vapid_private,
                    vapid_claims={"sub": vapid_subject}
                )
                enviados += 1
                vivos.append(s)
            except WebPushException:
                fallidos += 1

        # Limpia endpoints muertos
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(vivos, f, ensure_ascii=False, indent=2)

        return {"enviados": enviados, "fallidos": fallidos}

    except Exception:
        # Cero riesgo: si push falla, NO afecta el sistema de WhatsApp ni la emergencia.
        current_app.logger.exception("Error enviando push")
        return {"enviados": 0, "fallidos": 0}


# -----------------------------------------------------------
# CHECK VISUAL
# -----------------------------------------------------------
@notificacion_bp.route("/check", methods=["GET"])
@login_required
def check():
    hora_cr = datetime.now(CR_TZ).strftime("%d/%m/%Y %H:%M:%S")
    vapid_public_key = os.getenv("VAPID_PUBLIC_KEY", "")
    return render_template("notificacion.html", hora_cr=hora_cr, vapid_public_key=vapid_public_key)


# -----------------------------------------------------------
# PRUEBA MANUAL (WHATSAPP)
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
            f" *ALERTA DE EMERGENCIA*\n"
            f"Un vehículo lleva *más de 15 minutos sin cerrarse*.\n\n"
            f"👤 Chofer: {nombre_chofer}\n"
            f"🚛 Placa: {placa.numero_placa}\n"
            f"📦 Identificador: {mov.contenedor}\n"
            f"🕒 Salida: {mov.hora_salida.strftime('%d/%m/%Y %H:%M')}\n"
            f"⏳ Tiempo transcurrido: {horas}h {minutos}m {segundos}s\n\n"
            f"⚠️ Revisar urgentemente.\n"
            f"🚨🚨🚨🚨🚨🚨🚨🚨🚨"
        )

        # ✅ WhatsApp (igual que siempre)
        enviar_notificacion(mensaje)

        # ✅ Push (mismo mensaje, sin asteriscos)
        enviar_push_mismo_mensaje(mensaje, titulo="🚨 Emergencia: +15 min")

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

                # ✅ WhatsApp (igual que siempre)
                enviar_notificacion(mensaje)

                # ✅ Push (mismo mensaje, sin asteriscos)
                enviar_push_mismo_mensaje(mensaje, titulo="🚨 Orden incorrecto")

                mov_x.alerta_orden_enviada = True
                db.session.commit()

                total_alertas += 1

    return jsonify({
        "status": "ok",
        "alertas_enviadas": total_alertas,
        "timestamp": ahora.strftime("%d/%m/%Y %H:%M:%S")
    })


# -----------------------------------------------------------
# PUSH: Guardar suscripción del dispositivo (SEGURO)
# -----------------------------------------------------------
@notificacion_bp.route("/api/push/subscribe", methods=["POST"])
@login_required
def push_subscribe():
    try:
        data = request.get_json() or {}
        endpoint = data.get("endpoint")
        keys = data.get("keys") or {}
        p256dh = keys.get("p256dh")
        auth = keys.get("auth")

        if not endpoint or not p256dh or not auth:
            return jsonify({"status": "error", "message": "Suscripción inválida"}), 400

        ruta = os.path.join(current_app.root_path, "push_subs.json")

        subs = []
        if os.path.exists(ruta):
            try:
                with open(ruta, "r", encoding="utf-8") as f:
                    subs = json.load(f)
            except Exception:
                subs = []

        subs = [s for s in subs if s.get("endpoint") != endpoint]
        subs.append({"endpoint": endpoint, "p256dh": p256dh, "auth": auth})

        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(subs, f, ensure_ascii=False, indent=2)

        return "", 204

    except Exception as e:
        current_app.logger.exception(f"Error en push_subscribe: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# -----------------------------------------------------------
# PUSH: Ver cuántos dispositivos están registrados (SEGURO)
# -----------------------------------------------------------
@notificacion_bp.route("/api/push/status", methods=["GET"])
@login_required
def push_status():
    try:
        ruta = os.path.join(current_app.root_path, "push_subs.json")
        if not os.path.exists(ruta):
            return jsonify({"status": "ok", "dispositivos": 0}), 200

        with open(ruta, "r", encoding="utf-8") as f:
            subs = json.load(f)

        return jsonify({"status": "ok", "dispositivos": len(subs)}), 200

    except Exception as e:
        current_app.logger.exception(f"Error en push_status: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# -----------------------------------------------------------
# PUSH: Enviar notificación a dispositivos registrados (PRUEBA)
# -----------------------------------------------------------
@notificacion_bp.route("/api/push/send", methods=["POST"])
@login_required
def push_send():
    try:
        data = request.get_json() or {}
        mensaje = data.get("mensaje", "🔔 Push desde Operación Barco")

        # Reutilizamos la misma función para que sea idéntico al WhatsApp
        r = enviar_push_mismo_mensaje(mensaje, titulo="Operación Barco")
        return jsonify({"status": "ok", **r}), 200

    except Exception as e:
        current_app.logger.exception(f"Error en push_send: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500