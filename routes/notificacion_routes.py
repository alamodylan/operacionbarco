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

# -----------------------------------------------------------
# Blueprint
# -----------------------------------------------------------
notificacion_bp = Blueprint(
    "notificacion_bp",
    __name__,
    url_prefix="/notificaciones"
)

CR_TZ = pytz.timezone("America/Costa_Rica")

# -----------------------------------------------------------
# Quitar formato WhatsApp (*negritas*) para Push
# -----------------------------------------------------------
def _push_text(texto: str, max_len: int = 180) -> str:
    # Quita * y reduce tamaño para que el push NO falle por payload largo
    t = (texto or "").replace("*", "")
    t = t.replace("\r", "\n")
    t = " ".join(t.split())  # quita saltos y espacios múltiples
    if len(t) > max_len:
        t = t[:max_len - 1] + "…"
    return t

# -----------------------------------------------------------
# Guardar última alerta (para ver en grande)
# -----------------------------------------------------------
def guardar_ultima_alerta(titulo: str, mensaje: str):
    try:
        ruta = os.path.join(current_app.root_path, "last_alert.json")
        data = {
            "titulo": titulo,
            "mensaje": mensaje,
            "fecha": datetime.now(CR_TZ).strftime("%d/%m/%Y %H:%M:%S")
        }
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        current_app.logger.exception("No se pudo guardar last_alert.json")

# -----------------------------------------------------------
# Enviar Push usando el MISMO mensaje que WhatsApp
# -----------------------------------------------------------
def enviar_push_mismo_mensaje(
    mensaje: str,
    titulo: str = "Operación Barco",
    url: str = "/notificaciones/alerta"
) -> dict:
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
            "body": _push_text(mensaje),
            "url": "/notificaciones/alerta"
        })

        enviados, fallidos = 0, 0
        vivos = []

        for s in subs:
            sub_info = {
                "endpoint": s["endpoint"],
                "keys": {
                    "p256dh": s["p256dh"],
                    "auth": s["auth"]
                }
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

        # limpiar endpoints muertos
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(vivos, f, ensure_ascii=False, indent=2)

        return {"enviados": enviados, "fallidos": fallidos}

    except Exception:
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
    return render_template(
        "notificacion.html",
        hora_cr=hora_cr,
        vapid_public_key=vapid_public_key
    )

# -----------------------------------------------------------
# VER ALERTA EN GRANDE
# -----------------------------------------------------------
@notificacion_bp.route("/alerta", methods=["GET"])
@login_required
def ver_alerta():
    ruta = os.path.join(current_app.root_path, "last_alert.json")
    data = {
        "titulo": "Sin alertas",
        "mensaje": "No hay alertas registradas.",
        "fecha": ""
    }
    if os.path.exists(ruta):
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                data = json.load(f) or data
        except Exception:
            pass

    return render_template("alerta_grande.html", **data)

# -----------------------------------------------------------
# PRUEBA MANUAL WHATSAPP
# -----------------------------------------------------------
@notificacion_bp.route("/test", methods=["POST"])
@login_required
def test_notificacion():
    data = request.get_json() or {}
    mensaje = data.get("mensaje", "🧪 Prueba desde Operación Barco")
    ok = enviar_notificacion(mensaje)
    return jsonify({"ok": bool(ok)}), (200 if ok else 500)

# -----------------------------------------------------------
# EMERGENCIAS AUTOMÁTICAS
# -----------------------------------------------------------
@notificacion_bp.route("/emergencia", methods=["GET"])
def alerta_emergencia():
    ahora = datetime.now(CR_TZ).replace(tzinfo=None)
    movimientos = MovimientoBarco.query.filter_by(estado="en_ruta").all()
    total_alertas = 0

    # 1) +20 MINUTOS EN RUTA
    for mov in movimientos:
        tiempo_trans = ahora - mov.hora_salida
        if tiempo_trans < timedelta(minutes=20):
            continue

        if mov.ultima_notificacion:
            if (ahora - mov.ultima_notificacion) < timedelta(minutes=2):
                continue

        placa = Placa.query.get(mov.placa_id)
        nombre_chofer = placa.propietario or "Chofer no registrado"

        h, r = divmod(tiempo_trans.seconds, 3600)
        m, s = divmod(r, 60)

        mensaje = (
            "🚨🚨🚨🚨🚨🚨🚨🚨🚨\n"
            "*ALERTA DE EMERGENCIA*\n"
            "Un vehículo lleva *más de 20 minutos sin cerrarse*.\n\n"
            f"👤 Chofer: {nombre_chofer}\n"
            f"🚛 Placa: {placa.numero_placa}\n"
            f"📦 Identificador: {mov.contenedor}\n"
            f"🕒 Salida: {mov.hora_salida.strftime('%d/%m/%Y %H:%M')}\n"
            f"⏳ Tiempo: {h}h {m}m {s}s\n\n"
            "⚠️ Revisar urgentemente."
        )

        enviar_notificacion(mensaje)
        guardar_ultima_alerta("🚨 Emergencia: +20 min", mensaje)
        enviar_push_mismo_mensaje(mensaje, "🚨 Emergencia: +20 min")

        mov.ultima_notificacion = ahora
        db.session.commit()
        total_alertas += 1

    # 2) ORDEN INCORRECTO
    todos = MovimientoBarco.query.all()
    orden_salida = sorted(todos, key=lambda m: m.hora_salida)

    for i in range(len(orden_salida)):
        mov_x = orden_salida[i]
        if mov_x.estado != "en_ruta":
            continue

        for j in range(i + 1, len(orden_salida)):
            mov_y = orden_salida[j]

            if mov_y.hora_llegada and not mov_x.hora_llegada:
                if mov_x.alerta_orden_enviada:
                    continue

                placa_x = Placa.query.get(mov_x.placa_id)
                placa_y = Placa.query.get(mov_y.placa_id)

                mensaje = (
                    "🚨 *ALERTA DE ORDEN INCORRECTO*\n\n"
                    "Un viaje salió antes y aún no ha llegado,\n"
                    "pero otro posterior ya fue cerrado.\n\n"
                    f"🚛 Placa retrasada: {placa_x.numero_placa}\n"
                    f"📦 Contenedor: {mov_x.contenedor}\n\n"
                    f"🚛 Placa que cerró antes: {placa_y.numero_placa}"
                )

                enviar_notificacion(mensaje)
                guardar_ultima_alerta("🚨 Orden incorrecto", mensaje)
                enviar_push_mismo_mensaje(mensaje, "🚨 Orden incorrecto")

                mov_x.alerta_orden_enviada = True
                db.session.commit()
                total_alertas += 1

    return jsonify({
        "status": "ok",
        "alertas_enviadas": total_alertas,
        "timestamp": ahora.strftime("%d/%m/%Y %H:%M:%S")
    })

# -----------------------------------------------------------
# PUSH: SUSCRIBIR DISPOSITIVO
# -----------------------------------------------------------
@notificacion_bp.route("/api/push/subscribe", methods=["POST"])
@login_required
def push_subscribe():
    data = request.get_json() or {}
    endpoint = data.get("endpoint")
    keys = data.get("keys") or {}

    if not endpoint or not keys.get("p256dh") or not keys.get("auth"):
        return jsonify({"error": "Suscripción inválida"}), 400

    ruta = os.path.join(current_app.root_path, "push_subs.json")
    subs = []

    if os.path.exists(ruta):
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                subs = json.load(f)
        except Exception:
            subs = []

    subs = [s for s in subs if s.get("endpoint") != endpoint]
    subs.append({
        "endpoint": endpoint,
        "p256dh": keys["p256dh"],
        "auth": keys["auth"]
    })

    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(subs, f, ensure_ascii=False, indent=2)

    return "", 204

# -----------------------------------------------------------
# PUSH: ESTADO
# -----------------------------------------------------------
@notificacion_bp.route("/api/push/status", methods=["GET"])
@login_required
def push_status():
    ruta = os.path.join(current_app.root_path, "push_subs.json")
    if not os.path.exists(ruta):
        return jsonify({"dispositivos": 0})

    with open(ruta, "r", encoding="utf-8") as f:
        subs = json.load(f)

    return jsonify({"dispositivos": len(subs)})

# -----------------------------------------------------------
# PUSH: PRUEBA MANUAL
# -----------------------------------------------------------
@notificacion_bp.route("/api/push/send", methods=["POST"])
@login_required
def push_send():
    data = request.get_json() or {}
    mensaje = data.get("mensaje", "🔔 Push de prueba")
    r = enviar_push_mismo_mensaje(mensaje, "Operación Barco")
    return jsonify({"status": "ok", **r})
    