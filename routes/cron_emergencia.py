import os
from datetime import datetime, timedelta
from models.base import db
from models.movimiento import MovimientoBarco
from models.notificacion import enviar_notificacion
import pytz

def run_check():
    CR_TZ = pytz.timezone("America/Costa_Rica")
    ahora = datetime.now(CR_TZ).replace(tzinfo=None)

    # Movimientos abiertos (en ruta)
    abiertos = MovimientoBarco.query.filter_by(estado="en_ruta").all()

    for mov in abiertos:
        minutos = (ahora - mov.hora_salida).total_seconds() / 60

        if minutos >= 15:
            # última notificación fue hace más de 2 minutos
            if not mov.ultima_notificacion or (ahora - mov.ultima_notificacion).total_seconds() >= 120:

                placa = mov.placa.numero_placa
                tiempo = f"{int(minutos)} min"

                mensaje = (
                    f"🚨 *ALERTA DE EMERGENCIA*\n"
                    f"🚚 Placa: {placa}\n"
                    f"📝 Contenedor: {mov.contenedor}\n"
                    f"🕒 Hora salida: {mov.hora_salida.strftime('%H:%M %d/%m/%Y')}\n"
                    f"⌛ Tiempo en ruta: {tiempo}\n"
                    f"⚠️ Movimiento sin cerrar"
                )

                enviar_notificacion(mensaje)
                mov.ultima_notificacion = ahora
                db.session.commit()

if __name__ == "__main__":
    run_check()