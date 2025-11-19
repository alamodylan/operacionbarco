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
        """Finaliza un movimiento y, si estaba en emergencia, envía aviso especial."""

        ahora = datetime.now(CR_TZ).replace(tzinfo=None)

        # Detectar si el viaje estaba en emergencia antes de cerrar
        estaba_en_emergencia = False

        # Condición 1: más de 15 minutos en ruta
        if self.estado == "en_ruta" and self.hora_salida:
            minutos = (ahora - self.hora_salida).total_seconds() / 60
            if minutos >= 15:
                estaba_en_emergencia = True

        # Condición 2: tenía alertas enviadas
        if self.ultima_notificacion:
            estaba_en_emergencia = True

        # Finalizar
        self.hora_llegada = ahora
        self.estado = "finalizado"

        # Limpiar controles
        self.ultima_notificacion = None
        self.alerta_orden_enviada = True

        # Enviar notificación solo si estaba en emergencia
        if estaba_en_emergencia:
            duracion_min = int((self.hora_llegada - self.hora_salida).total_seconds() / 60)

            mensaje = (
                f"🟢 *ALERTA RESUELTA*\n"
                f"El viaje que estaba en *EMERGENCIA* ha sido finalizado.\n\n"
                f"📦 Identificador: {self.contenedor}\n"
                f"🚛 Placa: {self.placa.numero_placa}\n"
                f"👤 Chofer: {self.placa.propietario or 'No registrado'}\n"
                f"🕒 Salida: {self.hora_salida.strftime('%d/%m/%Y %H:%M')}\n"
                f"🏁 Llegada: {self.hora_llegada.strftime('%d/%m/%Y %H:%M')}\n"
                f"⏱️ Duración total: {duracion_min} minutos\n\n"
                f"✔ Emergencia cerrada correctamente."
            )

            try:
                enviar_notificacion(mensaje)
            except Exception as e:
                print(f"⚠️ Error al enviar notificación de cierre de emergencia: {e}")

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