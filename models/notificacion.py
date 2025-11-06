# models/notificacion.py
import requests
from urllib.parse import quote_plus
from flask import current_app

def enviar_notificacion(mensaje: str) -> bool:
    """
    Envía una notificación por WhatsApp usando la API de CallMeBot.
    Retorna True si se envía correctamente, False en caso de error.
    """

    try:
        telefono = current_app.config.get("WHATSAPP_PHONE")
        apikey = current_app.config.get("CALLMEBOT_API_KEY")

        if not telefono or not apikey:
            current_app.logger.warning("⚠️ Faltan variables de entorno para WhatsApp (WHATSAPP_PHONE o CALLMEBOT_API_KEY).")
            return False

        # Codificamos el texto para evitar errores con espacios o emojis
        mensaje_codificado = quote_plus(mensaje)

        url = f"https://api.callmebot.com/whatsapp.php?phone={telefono}&text={mensaje_codificado}&apikey={apikey}"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            current_app.logger.info(f"✅ Notificación enviada por WhatsApp: {mensaje}")
            return True
        else:
            current_app.logger.error(f"⚠️ Error al enviar notificación: {response.status_code}")
            return False

    except Exception as e:
        current_app.logger.exception(f"❌ Error al conectar con CallMeBot: {e}")
        return False