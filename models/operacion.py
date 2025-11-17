from datetime import datetime
import pytz
from models.base import db

# ============================================================
# 🟦 MODELO PRINCIPAL: Operación de Barco
# ============================================================

CR_TZ = pytz.timezone("America/Costa_Rica")

class Operacion(db.Model):
    __tablename__ = "operaciones_barco"
    __table_args__ = {"schema": "operacionbarco"}

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    fecha_creacion = db.Column(
        db.DateTime,
        default=lambda: datetime.now(CR_TZ).replace(tzinfo=None)
    )
    estado = db.Column(db.String(20), default="en_proceso", nullable=False)

    tipo_operacion = db.Column(
        db.String(20),
        nullable=False,
        default="exportacion"
    )

    movimientos = db.relationship(
        "MovimientoBarco",
        backref="operacion",
        lazy=True,
        cascade="all, delete-orphan"
    )

    # ============================================================
    # ⚙️ MÉTODOS DE CONTROL
    # ============================================================
    def finalizar(self):
        if all(m.estado == "finalizado" for m in self.movimientos) and self.movimientos:
            self.estado = "finalizada"
            return True
        return False

    # ============================================================
    # 🔐 PERMISOS (NO afectan BD, pero sí la lógica del sistema)
    # ============================================================
    def puede_iniciar_salida(self, user):
        if user.rol == "admin":
            return True

        if self.tipo_operacion == "exportacion":
            return user.rol == "usuario_predio"
        else:  # importacion
            return user.rol == "usuario_muelle"

    def puede_finalizar(self, user):
        if user.rol == "admin":
            return True

        if self.tipo_operacion == "exportacion":
            return user.rol == "usuario_muelle"
        else:  # importacion
            return user.rol == "usuario_predio"

    def __repr__(self):
        return f"<Operacion {self.nombre} - {self.estado} - {self.tipo_operacion}>"