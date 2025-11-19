# models/notificacion.py
import requests
from urllib.parse import quote_plus
from flask import current_app


def enviar_notificacion(mensaje: str) -> bool:
    """
    Envía una notificación por WhatsApp usando la API de CallMeBot.
    Ahora soporta múltiples números (WHATSAPP_PHONE, WHATSAPP_PHONE_1, _2, etc.)
    Retorna True si al menos una notificación se envía correctamente.
    """

    try:
        # Obtener todos los números configurados
        telefonos = []
        apikeys = []

        # Número principal
        t1 = current_app.config.get("WHATSAPP_PHONE")
        k1 = current_app.config.get("CALLMEBOT_API_KEY")
        if t1 and k1:
            telefonos.append(t1)
            apikeys.append(k1)

        # Número secundario
        t2 = current_app.config.get("WHATSAPP_PHONE_1")
        k2 = current_app.config.get("CALLMEBOT_API_KEY_1")
        if t2 and k2:
            telefonos.append(t2)
            apikeys.append(k2)

        if not telefonos:
            current_app.logger.warning("⚠️ No hay teléfonos configurados para notificar.")
            return False

        # Sanitiza el mensaje
        mensaje = mensaje.strip()
        mensaje_codificado = quote_plus(mensaje)

        exito = False

        # Enviar a cada número
        for telefono, apikey in zip(telefonos, apikeys):
            url = (
                f"https://api.callmebot.com/whatsapp.php?"
                f"phone={telefono}&text={mensaje_codificado}&apikey={apikey}"
            )

            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                current_app.logger.info(f"✅ Notificación enviada a {telefono}")
                exito = True
            else:
                current_app.logger.error(
                    f"❌ Error al enviar a {telefono}: {response.status_code} - {response.text}"
                )

        return exito

    except Exception as e:
        current_app.logger.exception(f"❌ Error inesperado al enviar la notificación: {e}")
        return False