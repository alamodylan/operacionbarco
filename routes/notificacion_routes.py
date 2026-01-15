from flask import (
    Blueprint,
    jsonify,
    request,
    current_app,
    render_template,
    make_response,
)
from flask_login import login_required, current_user
from models.notificacion import enviar_notificacion
from models.movimiento import MovimientoBarco
from models.placa import Placa
from models.base import db
from datetime import datetime, timedelta
import pytz
import os
from pywebpush import webpush, WebPushException
import json

# ✅ Persistencia push (PostgreSQL)
from models.push_subscription import PushSubscription

# ✅ Historial de alertas web (PostgreSQL)
from models.notificacion_alerta import NotificacionAlerta


# -----------------------------------------------------------
# Blueprint
# -----------------------------------------------------------
notificacion_bp = Blueprint(
    "notificacion_bp",
    __name__,
    url_prefix="/notificaciones",
)

CR_TZ = pytz.timezone("America/Costa_Rica")


# -----------------------------------------------------------
# Quitar formato WhatsApp (*negritas*) para Push
# -----------------------------------------------------------
def _push_text(texto: str, max_len: int = 180) -> str:
    t = (texto or "").replace("*", "")
    t = t.replace("\r", "\n")
    t = " ".join(t.split())
    if len(t) > max_len:
        t = t[: max_len - 1] + "…"
    return t


# -----------------------------------------------------------
# Guardar última alerta (para ver en grande)
# ✅ BD + JSON (compatibilidad)
# -----------------------------------------------------------
def guardar_ultima_alerta(
    titulo: str,
    mensaje: str,
    tipo: str = "alerta",
    operacion_id=None,
    movimiento_id=None
):
    alerta_id = None

    # 1) Guarda en BD (historial)
    try:
        alerta = NotificacionAlerta(
            tipo=(tipo or "alerta"),
            titulo=titulo,
            mensaje=mensaje,
            fecha=datetime.now(CR_TZ).replace(tzinfo=None),
            operacion_id=operacion_id,
            movimiento_id=movimiento_id
        )
        db.session.add(alerta)
        db.session.commit()
        alerta_id = alerta.id
    except Exception:
        db.session.rollback()
        current_app.logger.exception("No se pudo guardar alerta en PostgreSQL")

    # 2) Mantiene JSON (compatibilidad)
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

    return alerta_id


# -----------------------------------------------------------
# Enviar Push usando el MISMO mensaje que WhatsApp
# ✅ Ya NO usa push_subs.json, usa PostgreSQL
# ✅ Cambio mínimo: permite URL param (sigue igual si no lo usas)
# -----------------------------------------------------------
def enviar_push_mismo_mensaje(
    mensaje: str,
    titulo: str = "Operación Barco",
    url: str = "/notificaciones/alerta",
) -> dict:
    try:
        vapid_private = os.getenv("VAPID_PRIVATE_KEY", "")
        vapid_subject = os.getenv("VAPID_SUBJECT", "mailto:ti@alamo.com")

        if not vapid_private:
            return {"enviados": 0, "fallidos": 0}

        subs = PushSubscription.query.all()
        if not subs:
            return {"enviados": 0, "fallidos": 0}

        payload = json.dumps(
            {
                "title": titulo,
                "body": _push_text(mensaje),
                "url": url,
            }
        )

        enviados, fallidos = 0, 0

        for s in subs:
            sub_info = {
                "endpoint": s.endpoint,
                "keys": {
                    "p256dh": s.p256dh,
                    "auth": s.auth,
                },
            }

            try:
                webpush(
                    subscription_info=sub_info,
                    data=payload,
                    vapid_private_key=vapid_private,
                    vapid_claims={"sub": vapid_subject},
                )
                enviados += 1
                s.last_seen = datetime.utcnow()

            except WebPushException:
                fallidos += 1
                try:
                    db.session.delete(s)
                except Exception:
                    pass

        db.session.commit()
        return {"enviados": enviados, "fallidos": fallidos}

    except Exception:
        db.session.rollback()
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
        vapid_public_key=vapid_public_key,
    )


# -----------------------------------------------------------
# VER ALERTA EN GRANDE
# ✅ Pública (sin login)
# ✅ Lee última en BD
# ✅ No-cache para evitar que se “pegue”
# -----------------------------------------------------------
@notificacion_bp.route("/alerta", methods=["GET"])
def ver_alerta():
    alerta = (
        NotificacionAlerta.query
        .order_by(NotificacionAlerta.id.desc())
        .first()
    )

    if not alerta:
        data = {
            "titulo": "Sin alertas",
            "mensaje": "No hay alertas registradas.",
            "fecha": "",
            "tipo": "alerta",
        }
    else:
        data = {
            "titulo": alerta.titulo,
            "mensaje": alerta.mensaje,
            "fecha": alerta.fecha.strftime("%d/%m/%Y %H:%M:%S") if alerta.fecha else "",
            "tipo": alerta.tipo,
        }

    resp = make_response(render_template("alerta_grande.html", **data))
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    return resp


# -----------------------------------------------------------
# VER ALERTA POR ID (PÚBLICO)
# -----------------------------------------------------------
@notificacion_bp.route("/alerta/<int:alerta_id>", methods=["GET"])
def ver_alerta_por_id(alerta_id):
    alerta = NotificacionAlerta.query.get_or_404(alerta_id)

    data = {
        "titulo": alerta.titulo,
        "mensaje": alerta.mensaje,
        "fecha": alerta.fecha.strftime("%d/%m/%Y %H:%M:%S") if alerta.fecha else "",
        "tipo": alerta.tipo,
    }

    resp = make_response(render_template("alerta_grande.html", **data))
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    return resp


# -----------------------------------------------------------
# LISTAR ALERTAS (HISTORIAL, PÚBLICO)
# -----------------------------------------------------------
@notificacion_bp.route("/alertas", methods=["GET"])
def listar_alertas():
    alertas = (
        NotificacionAlerta.query
        .order_by(NotificacionAlerta.id.desc())
        .limit(200)
        .all()
    )
    return render_template("alertas_lista.html", alertas=alertas)


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
        if not placa:
            continue

        nombre_chofer = placa.propietario or "Chofer no registrado"

        h, r = divmod(tiempo_trans.seconds, 3600)
        m, s = divmod(r, 60)

        mensaje = (
            "🚨🚨🚨🚨🚨🚨🚨🚨🚨\n"
            "*ALERTA DE EMERGENCIA*\n"
            "Un vehículo lleva *más de 20 minutos sin cerrarse*.\n\n"
            f"👤 Chofer: {nombre_chofer}\n"
            f"🚛 Placa: {placa.numero_placa}\n"
            f"🎨 Color cabezal: {placa.color_cabezal or 'No registrado'}\n"
            f"📦 Identificador: {mov.contenedor}\n"
            f"🕒 Salida: {mov.hora_salida.strftime('%d/%m/%Y %H:%M')}\n"
            f"⏳ Tiempo: {h}h {m}m {s}s\n\n"
            "⚠️ Revisar urgentemente."
        )

        enviar_notificacion(mensaje)

        alerta_id = guardar_ultima_alerta(
            "🚨 Emergencia: +20 min",
            mensaje,
            tipo="emergencia",
            operacion_id=getattr(mov, "operacion_id", None),
            movimiento_id=mov.id,
        )
        url_alerta = f"/notificaciones/alerta/{alerta_id}" if alerta_id else "/notificaciones/alerta"
        enviar_push_mismo_mensaje(mensaje, "🚨 Emergencia: +20 min", url=url_alerta)


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
                if not placa_x or not placa_y:
                    continue

                mensaje = (
                    "🚨 *ALERTA DE ORDEN INCORRECTO*\n\n"
                    "Un viaje salió antes y aún no ha llegado,\n"
                    "pero otro posterior ya fue cerrado.\n\n"
                    f"🚛 Placa retrasada: {placa_x.numero_placa}\n"
                    f"🎨 Color cabezal: {placa_x.color_cabezal or 'No registrado'}\n"
                    f"📦 Contenedor: {mov_x.contenedor}\n\n"
                    f"🚛 Placa que cerró antes: {placa_y.numero_placa}\n"
                    f"🎨 Color cabezal: {placa_y.color_cabezal or 'No registrado'}"
                )

                enviar_notificacion(mensaje)

                alerta_id = guardar_ultima_alerta(
                    "🚨 Orden incorrecto",
                    mensaje,
                    tipo="alerta",
                    operacion_id=getattr(mov_x, "operacion_id", None),
                    movimiento_id=mov_x.id,
                )
                url_alerta = f"/notificaciones/alerta/{alerta_id}" if alerta_id else "/notificaciones/alerta"
                enviar_push_mismo_mensaje(mensaje, "🚨 Orden incorrecto", url=url_alerta)     

                mov_x.alerta_orden_enviada = True
                db.session.commit()
                total_alertas += 1

    return jsonify(
        {
            "status": "ok",
            "alertas_enviadas": total_alertas,
            "timestamp": ahora.strftime("%d/%m/%Y %H:%M:%S"),
        }
    )


# -----------------------------------------------------------
# PUSH: SUSCRIBIR DISPOSITIVO (PostgreSQL)
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
            return jsonify({"error": "Suscripción inválida"}), 400

        # ♻️ RESCATE AUTOMÁTICO desde push_subs.json (si existe)
        try:
            ruta_json = os.path.join(current_app.root_path, "push_subs.json")
            if os.path.exists(ruta_json):
                with open(ruta_json, "r", encoding="utf-8") as f:
                    subs_json = json.load(f) or []

                for s in subs_json:
                    ep = s.get("endpoint")
                    p = s.get("p256dh")
                    a = s.get("auth")
                    if not ep or not p or not a:
                        continue

                    existe = PushSubscription.query.filter_by(endpoint=ep).first()
                    if not existe:
                        db.session.add(PushSubscription(endpoint=ep, p256dh=p, auth=a))

                db.session.commit()
        except Exception:
            db.session.rollback()
            pass

        sub = PushSubscription.query.filter_by(endpoint=endpoint).first()
        if not sub:
            sub = PushSubscription(endpoint=endpoint, p256dh=p256dh, auth=auth)
            db.session.add(sub)
        else:
            sub.p256dh = p256dh
            sub.auth = auth
            sub.last_seen = datetime.utcnow()

        db.session.commit()
        return "", 204

    except Exception:
        db.session.rollback()
        current_app.logger.exception("Error guardando suscripción push")
        return jsonify({"error": "No se pudo guardar la suscripción"}), 500


# -----------------------------------------------------------
# PUSH: ESTADO (cuenta desde PostgreSQL)
# -----------------------------------------------------------
@notificacion_bp.route("/api/push/status", methods=["GET"])
@login_required
def push_status():
    try:
        total = PushSubscription.query.count()
        return jsonify({"dispositivos": total})
    except Exception:
        current_app.logger.exception("Error consultando status push")
        return jsonify({"dispositivos": 0})


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


# -----------------------------------------------------------
# MIGRACIÓN 1 VEZ: push_subs.json -> PostgreSQL (SOLO Admin)
# -----------------------------------------------------------
@notificacion_bp.route("/api/push/migrate", methods=["POST"])
@login_required
def push_migrate():
    try:
        if getattr(current_user, "rol", "") != "Admin":
            return jsonify({"ok": False, "error": "No autorizado"}), 403

        ruta = os.path.join(current_app.root_path, "push_subs.json")
        if not os.path.exists(ruta):
            return jsonify({"ok": False, "error": "push_subs.json no existe", "migrados": 0}), 404

        try:
            with open(ruta, "r", encoding="utf-8") as f:
                subs = json.load(f) or []
        except Exception:
            subs = []

        if not subs:
            return jsonify({"ok": True, "migrados": 0, "mensaje": "No hay suscripciones en push_subs.json"}), 200

        migrados = 0
        for s in subs:
            endpoint = s.get("endpoint")
            p256dh = s.get("p256dh")
            auth = s.get("auth")

            if not endpoint or not p256dh or not auth:
                continue

            existe = PushSubscription.query.filter_by(endpoint=endpoint).first()
            if not existe:
                db.session.add(
                    PushSubscription(
                        endpoint=endpoint,
                        p256dh=p256dh,
                        auth=auth,
                    )
                )
                migrados += 1
            else:
                existe.p256dh = p256dh
                existe.auth = auth
                existe.last_seen = datetime.utcnow()

        db.session.commit()

        return jsonify({"ok": True, "migrados": migrados, "total_en_json": len(subs)}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"Error migrando push_subs.json a PostgreSQL: {e}")
        return jsonify({"ok": False, "error": "Fallo la migración"}), 500