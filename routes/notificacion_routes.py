# routes/notificacion_routes.py
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required
from models.notificacion import enviar_notificacion

notificacion_bp = Blueprint("notificacion_bp", __name__)

# ---- Ruta para verificar estado del módulo ----
@notificacion_bp.route("/check", methods=["GET"])
@login_required
def check():
    """
    Verifica que el sistema de notificaciones esté activo.
    """
    return jsonify({"status": "ok", "message": "✅ Sistema de notificaciones activo"}), 200


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