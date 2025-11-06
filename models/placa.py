# models/placa.py
from datetime import datetime
from models.base import db

class Placa(db.Model):
    __tablename__ = "placas"

    id = db.Column(db.Integer, primary_key=True)
    numero_placa = db.Column(db.String(20), unique=True, nullable=False)
    propietario = db.Column(db.String(100))
    estado = db.Column(db.String(20), default="activa")
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relación con el usuario que registró la placa
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    usuario = db.relationship("Usuario", backref=db.backref("placas", lazy=True))

    def __repr__(self):
        return f"<Placa {self.numero_placa} - Estado: {self.estado}>"