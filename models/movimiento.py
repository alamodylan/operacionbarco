from datetime import datetime
import pytz
from models.base import db

# ============================================================
# 🟩 MODELO: Movimiento dentro de una operación de barco
# ============================================================

# Zona horaria de Costa Rica
CR_TZ = pytz.timezone("America/Costa_Rica")

class MovimientoBarco(db.Model):
    __tablename__ = "movimientos_barco"
    __table_args__ = {"schema": "operacionbarco"}

    id = db.Column(db.Integer, primary_key=True)

    # Relación con la operación principal
    operacion_id = db.Column(
        db.Integer,
        db.ForeignKey("operacionbarco.operaciones_barco.id"),
        nullable=False
    )

    # Relación con la placa (cabezal)
    placa_id = db.Column(
        db.Integer,
        db.ForeignKey("operacionbarco.placas.id"),
        nullable=False
    )

    # Campos de movimiento
    contenedor = db.Column(db.String(50), nullable=False)
    hora_salida = db.Column(db.DateTime, default=lambda: datetime.now(CR_TZ))  # ✅ hora local CR
    hora_llegada = db.Column(db.DateTime, nullable=True)
    estado = db.Column(db.String(20), default="en_ruta")

    # ========================================================
    # 🔗 Relaciones
    # ========================================================
    placa = db.relationship("Placa", backref="movimientos")

    # ========================================================
    # 🕒 Métodos de utilidad
    # ========================================================
    def finalizar(self):
        """Marca el movimiento como finalizado y registra la hora de llegada."""
        self.hora_llegada = datetime.now(CR_TZ)  # ✅ hora local CR
        self.estado = "finalizado"

    def tiempo_total(self, formato=False):
        """
        Devuelve el tiempo total del viaje.
        Si formato=True, devuelve un texto como 'Xh Ym'.
        """
        if self.hora_llegada:
            total_min = int((self.hora_llegada - self.hora_salida).total_seconds() / 60)
            if formato:
                horas, minutos = divmod(total_min, 60)
                return f"{horas}h {minutos}m"
            return total_min
        return None

    def __repr__(self):
        return f"<Movimiento {self.contenedor} - {self.estado}>"