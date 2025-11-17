from datetime import datetime
import pytz
from models.base import db
from models.notificacion import enviar_notificacion  # Envío de alertas

# Zona horaria de Costa Rica
CR_TZ = pytz.timezone("America/Costa_Rica")

class MovimientoBarco(db.Model):
    __tablename__ = "movimientos_barco"
    __table_args__ = {"schema": "operacionbarco"}

    id = db.Column(db.Integer, primary_key=True)

    # Relación con operación
    operacion_id = db.Column(
        db.Integer,
        db.ForeignKey("operacionbarco.operaciones_barco.id"),
        nullable=False
    )

    # Relación con placa
    placa_id = db.Column(
        db.Integer,
        db.ForeignKey("operacionbarco.placas.id"),
        nullable=False
    )

    # Datos del movimiento
    contenedor = db.Column(db.String(50), nullable=False)
    hora_salida = db.Column(
        db.DateTime,
        default=lambda: datetime.now(CR_TZ).replace(tzinfo=None)
    )
    hora_llegada = db.Column(db.DateTime, nullable=True)

    # 🚨 SE RESPETA tu estructura existente
    estado = db.Column(db.String(20), default="en_ruta")

    # 🔔 Control de notificaciones
    ultima_notificacion = db.Column(db.DateTime, nullable=True)

    placa = db.relationship("Placa", backref="movimientos")

    # ======================================================
    # 🔥 MÉTODOS DE URGENCIA
    # ======================================================

    def es_urgente(self):
        """Un movimiento es urgente si han pasado 15 minutos y no está finalizado."""
        if self.estado != "en_ruta":  # RESPETAMOS TU ESTADO
            return False

        minutos = (datetime.now() - self.hora_salida).total_seconds() / 60
        return minutos >= 15

    def debe_notificar(self):
        """Debe notificar solo si es urgente y cumple tiempo de espera."""
        if not self.es_urgente():
            return False

        # Primera notificación
        if self.ultima_notificacion is None:
            return True

        # Cada 3 minutos
        minutos = (datetime.now() - self.ultima_notificacion).total_seconds() / 60
        return minutos >= 3

    def marcar_notificado(self):
        """Registra la hora en que se envió la notificación."""
        self.ultima_notificacion = datetime.now()

    # ======================================================
    # 🟩 FINALIZAR MOVIMIENTO
    # ======================================================

    def finalizar(self):
        """Finaliza el movimiento y envía una notificación."""
        self.hora_llegada = datetime.now(CR_TZ).replace(tzinfo=None)
        self.estado = "finalizado"  # RESPETAMOS TU ESTADO

        # Cálculo de duración
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

    # ======================================================
    # ⏱️ Duración total
    # ======================================================

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