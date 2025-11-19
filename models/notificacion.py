import requests
from urllib.parse import quote_plus
from flask import current_app


def enviar_notificacion(mensaje: str) -> bool:
    """
    Envía notificaciones por WhatsApp usando CallMeBot a múltiples números.
    Maneja fallos individuales sin afectar el resto.
    Retorna True si al menos uno se entrega correctamente.
    """

    try:
        telefonos = []
        apikeys = []

        # Cargar automáticamente WHATSAPP_PHONE, WHATSAPP_PHONE_1, ... hasta _9
        for i in range(0, 10):
            tel_key = f"WHATSAPP_PHONE{'' if i == 0 else '_' + str(i)}"
            api_key = f"CALLMEBOT_API_KEY{'' if i == 0 else '_' + str(i)}"

            tel = current_app.config.get(tel_key)
            key = current_app.config.get(api_key)

            if tel and key:
                telefonos.append(str(tel).strip())
                apikeys.append(str(key).strip())

        if not telefonos:
            current_app.logger.warning("⚠️ No hay teléfonos configurados para notificar.")
            return False

        mensaje_cod = quote_plus(mensaje.strip())
        enviado_al_menos_uno = False

        for tel, key in zip(telefonos, apikeys):

            # Intento 1 — sin “+”
            url1 = f"https://api.callmebot.com/whatsapp.php?phone={tel}&text={mensaje_cod}&apikey={key}"
            r1 = requests.get(url1, timeout=10)

            if r1.status_code == 200:
                current_app.logger.info(f"✅ Notificación enviada a {tel} (sin +)")
                enviado_al_menos_uno = True
                continue

            # Intento 2 — con “+”
            tel_plus = tel if tel.startswith("+") else "+" + tel
            url2 = f"https://api.callmebot.com/whatsapp.php?phone={tel_plus}&text={mensaje_cod}&apikey={key}"
            r2 = requests.get(url2, timeout=10)

            if r2.status_code == 200:
                current_app.logger.info(f"✅ Notificación enviada a {tel_plus} (con +)")
                enviado_al_menos_uno = True
            else:
                current_app.logger.error(
                    f"❌ Error enviando a {tel} → Código {r2.status_code} - {r2.text}"
                )

        return enviado_al_menos_uno

    except Exception as e:
        current_app.logger.exception(f"❌ Error inesperado al enviar notificación: {e}")
        return False