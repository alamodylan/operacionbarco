# models/operacion.py
from datetime import datetime
from models.base import db

class Operacion(db.Model):
    __tablename__ = "operaciones"

    id = db.Column(db.Integer, primary_key=True)
    
    # Relación con la tabla de placas
    placa_id = db.Column(db.Integer, db.ForeignKey("placas.id"), nullable=False)
    placa_obj = db.relationship("Placa", backref=db.backref("operaciones", lazy=True))
    
    contenedor = db.Column(db.String(20), nullable=False)
    hora_salida = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    hora_llegada = db.Column(db.DateTime, nullable=True)
    estado = db.Column(db.String(20), default="EN_RUTA", nullable=False)
    alerta_enviada = db.Column(db.Boolean, default=False)

    def finalizar(self):
        """Marca la operación como finalizada y registra la hora de llegada."""
        self.estado = "FINALIZADA"
        self.hora_llegada = datetime.utcnow()

    def __repr__(self):
        return f"<Operacion {self.id} - {self.contenedor} ({self.estado})>"