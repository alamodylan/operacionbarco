from datetime import datetime
import pytz
from models.base import db
from models.notificacion import enviar_notificacion

CR_TZ = pytz.timezone("America/Costa_Rica")

class MovimientoBarco(db.Model):
    __tablename__ = "movimientos_barco"
    __table_args__ = {"schema": "operacionbarco"}

    id = db.Column(db.Integer, primary_key=True)

    operacion_id = db.Column(
        db.Integer,
        db.ForeignKey("operacionbarco.operaciones_barco.id"),
        nullable=False
    )

    placa_id = db.Column(
        db.Integer,
        db.ForeignKey("operacionbarco.placas.id"),
        nullable=False
    )

    contenedor = db.Column(db.String(50), nullable=False)
    hora_salida = db.Column(
        db.DateTime,
        default=lambda: datetime.now(CR_TZ).replace(tzinfo=None)
    )
    hora_llegada = db.Column(db.DateTime, nullable=True)

    estado = db.Column(db.String(20), default="en_ruta")

    ultima_notificacion = db.Column(db.DateTime, nullable=True)

    alerta_orden_enviada = db.Column(db.Boolean, default=False)

    placa = db.relationship("Placa", backref="movimientos")

    # ======================================================
    # 🔥 URGENCIA
    # ======================================================

    def _ahora(self):
        """Devuelve el tiempo actual con la misma zona horaria usada en BD."""
        return datetime.now(CR_TZ).replace(tzinfo=None)

    def es_urgente(self):
        if self.estado != "en_ruta":
            return False

        ahora = self._ahora()
        minutos = (ahora - self.hora_salida).total_seconds() / 60
        return minutos >= 15

    def debe_notificar(self):
        if not self.es_urgente():
            return False

        ahora = self._ahora()

        # primera notificación
        if self.ultima_notificacion is None:
            return True

        minutos = (ahora - self.ultima_notificacion).total_seconds() / 60
        return minutos >= 3

    def marcar_notificado(self):
        self.ultima_notificacion = self._ahora()

    # ======================================================
    # 🟩 FINALIZAR
    # ======================================================

    def finalizar(self):
        self.hora_llegada = self._ahora()
        self.estado = "finalizado"

        duracion_min = int((self.hora_llegada - self.hora_salida).total_seconds() / 60)

        mensaje = (
            f"✅ *Movimiento finalizado*\n"
            f"🧱 Contenedor: {self.contenedor}\n"
            f"🚛 Placa: {self.placa.numero_placa}\n"
            f"🕒 Llegada: {self.hora_llegada.strftime('%H:%M %d/%m/%Y')}\n"
            f"⏱️ Duración total: {duracion_min} minutos"
        )

        try:
            enviar_notificacion(mensaje)
        except Exception as e:
            print(f"⚠️ Error al enviar notificación: {e}")

    def tiempo_total(self, formato=False):
        if self.hora_llegada:
            total_min = int((self.hora_llegada - self.hora_salida).total_seconds() / 60)
            if formato:
                h, m = divmod(total_min, 60)
                return f"{h}h {m}m"
            return total_min
        return None

    def __repr__(self):
        return f"<Movimiento {self.contenedor} - {self.estado}>"