from datetime import datetime
from models.base import db

# ============================================================
# 🟦 MODELO PRINCIPAL: Operación de Barco
# ============================================================
class Operacion(db.Model):
    __tablename__ = "operaciones_barco"
    __table_args__ = {"schema": "operacionbarco"}  # Schema correcto en PostgreSQL

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    estado = db.Column(db.String(20), default="en_proceso", nullable=False)

    # Relación 1:N con los movimientos (cada placa/contenedor pertenece a una operación)
    movimientos = db.relationship(
        "Movimiento",
        backref="operacion",
        lazy=True,
        cascade="all, delete-orphan"
    )

    def finalizar(self):
        """Finaliza la operación solo si todos los movimientos están cerrados."""
        if all(m.estado == "finalizado" for m in self.movimientos) and self.movimientos:
            self.estado = "finalizada"
            return True
        return False

    def __repr__(self):
        return f"<Operacion {self.nombre} - {self.estado}>"

# ============================================================
# 🟩 MODELO SECUNDARIO: Movimiento dentro de una operación
# ============================================================
class Movimiento(db.Model):
    __tablename__ = "movimientos_barco"
    __table_args__ = {"schema": "operacionbarco"}

    id = db.Column(db.Integer, primary_key=True)
    operacion_id = db.Column(db.Integer, db.ForeignKey("operacionbarco.operaciones_barco.id"), nullable=False)
    placa_id = db.Column(db.Integer, db.ForeignKey("operacionbarco.placas.id"), nullable=False)
    contenedor = db.Column(db.String(50), nullable=False)

    hora_salida = db.Column(db.DateTime, default=datetime.utcnow)
    hora_llegada = db.Column(db.DateTime, nullable=True)
    estado = db.Column(db.String(20), default="en_ruta")

    def finalizar(self):
        """Marca el movimiento como finalizado y guarda la hora de llegada."""
        self.hora_llegada = datetime.utcnow()
        self.estado = "finalizado"

    def tiempo_total(self, formato=False):
        """
        Devuelve el tiempo total del viaje en minutos.
        Si formato=True, lo retorna en formato legible 'Xh Ym'.
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