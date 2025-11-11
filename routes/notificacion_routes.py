# routes/notificacion_routes.py
from flask import Blueprint, jsonify, request, current_app, render_template
from flask_login import login_required
from models.notificacion import enviar_notificacion
from datetime import datetime
import pytz

notificacion_bp = Blueprint("notificacion_bp", __name__)

# ---- Ruta para verificar estado del módulo ----
@notificacion_bp.route("/check", methods=["GET"])
@login_required
def check():
    """
    Verifica que el sistema de notificaciones esté activo (versión visual con HTML).
    """
    CR_TZ = pytz.timezone("America/Costa_Rica")
    hora_cr = datetime.now(CR_TZ).strftime("%d/%m/%Y %H:%M:%S")
    return render_template("notificacion.html", hora_cr=hora_cr)


# ---- Ruta para enviar prueba de notificación manual ----
@notificacion_bp.route("/test", methods=["POST"])
@login_required
def test_notificacion():
    """
    Permite enviar una notificación de prueba manual a WhatsApp.
    Ejemplo: POST /notificaciones/test con body {"mensaje": "Hola desde Operación Barco"}
    """
    try:
        data = request.get_json()
        mensaje = data.get("mensaje", "🧪 Prueba de notificación desde Operación Barco")
        ok = enviar_notificacion(mensaje)
        if ok:
            return jsonify({"status": "success", "message": "Notificación enviada correctamente"}), 200
        else:
            return jsonify({"status": "error", "message": "No se pudo enviar la notificación"}), 500
    except Exception as e:
        current_app.logger.exception(f"Error al enviar notificación de prueba: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500