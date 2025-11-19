# models/notificacion.py
import requests
from urllib.parse import quote_plus
from flask import current_app


def enviar_notificacion(mensaje: str) -> bool:
    """
    Envía una notificación por WhatsApp usando CallMeBot a uno o varios números.
    Usa WHATSAPP_PHONE y WHATSAPP_PHONE_X si existen.
    """
    try:
        mensaje = mensaje.strip()
        mensaje_codificado = quote_plus(mensaje)

        # ================
        # 1️⃣ Cargar todos los números disponibles
        # ================
        numeros = []

        # Principal
        tel_base = current_app.config.get("WHATSAPP_PHONE")
        api_base = current_app.config.get("CALLMEBOT_API_KEY")

        if tel_base and api_base:
            numeros.append((tel_base, api_base))

        # Adicionales WHATSAPP_PHONE_1, WHATSAPP_PHONE_2, ...
        for i in range(1, 10):  # soporta hasta 10 números (se puede ampliar)
            tel = current_app.config.get(f"WHATSAPP_PHONE_{i}")
            api = current_app.config.get(f"CALLMEBOT_API_KEY_{i}")
            if tel and api:
                numeros.append((tel, api))

        if not numeros:
            current_app.logger.warning("⚠️ No hay números configurados para enviar notificaciones.")
            return False

        # ================
        # 2️⃣ Enviar mensaje a todos los números encontrados
        # ================
        exito_total = True

        for tel, api in numeros:
            url = (
                f"https://api.callmebot.com/whatsapp.php?"
                f"phone={tel}&text={mensaje_codificado}&apikey={api}"
            )

            try:
                response = requests.get(url, timeout=10)

                if response.status_code == 200:
                    current_app.logger.info(f"📨 Notificación enviada a {tel}")
                else:
                    exito_total = False
                    current_app.logger.error(
                        f"❌ Error al enviar a {tel}: {response.status_code} - {response.text}"
                    )

            except Exception as e:
                exito_total = False
                current_app.logger.error(f"❌ Error enviando a {tel}: {e}")

        return exito_total

    except Exception as e:
        current_app.logger.exception(f"❌ Error inesperado al enviar notificación: {e}")
        return False