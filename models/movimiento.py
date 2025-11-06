# models/movimiento.py
from datetime import datetime
from models.base import db

class Movimiento(db.Model):
    __tablename__ = "movimientos"

    id = db.Column(db.Integer, primary_key=True)

    # Relaciones principales
    operacion_id = db.Column(db.Integer, db.ForeignKey("operaciones.id"), nullable=False)
    placa_id = db.Column(db.Integer, db.ForeignKey("placas.id"), nullable=False)
    numero_contenedor = db.Column(db.String(50), nullable=False)

    # Tiempos de movimiento
    hora_salida = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    hora_llegada = db.Column(db.DateTime, nullable=True)

    # Usuarios que registran la salida y llegada
    usuario_salida_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    usuario_llegada_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)

    # Estado actual del movimiento
    estado = db.Column(db.String(20), default="EN_TRANSITO", nullable=False)

    # Relaciones ORM
    operacion = db.relationship("Operacion", backref=db.backref("movimientos", lazy=True))
    placa = db.relationship("Placa", backref=db.backref("movimientos", lazy=True))
    usuario_salida = db.relationship(
        "Usuario", foreign_keys=[usuario_salida_id], backref=db.backref("movimientos_salida", lazy=True)
    )
    usuario_llegada = db.relationship(
        "Usuario", foreign_keys=[usuario_llegada_id], backref=db.backref("movimientos_llegada", lazy=True)
    )

    def __repr__(self):
        return f"<Movimiento {self.numero_contenedor} - Estado: {self.estado}>"