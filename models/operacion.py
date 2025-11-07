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

    # ========================================================
    # 🔗 Relación 1:N con los movimientos
    # ========================================================
    movimientos = db.relationship(
        "MovimientoBarco",  # Modelo definido en movimiento.py
        backref="operacion",
        lazy=True,
        cascade="all, delete-orphan"
    )

    # ========================================================
    # ⚙️ Métodos de control
    # ========================================================
    def finalizar(self):
        """
        Finaliza la operación solo si todos los movimientos están cerrados.
        Retorna True si se pudo finalizar, False si aún hay movimientos abiertos.
        """
        if all(m.estado == "finalizado" for m in self.movimientos) and self.movimientos:
            self.estado = "finalizada"
            return True
        return False

    def __repr__(self):
        return f"<Operacion {self.nombre} - {self.estado}>"