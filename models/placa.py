from datetime import datetime
from models.base import db

class Placa(db.Model):
    __tablename__ = "placas"
    __table_args__ = {"schema": "operacionbarco"}  # 👈 Se crea en el schema correcto

    id = db.Column(db.Integer, primary_key=True)
    numero_placa = db.Column(db.String(20), unique=True, nullable=False)
    propietario = db.Column(db.String(100))
    estado = db.Column(db.String(20), default="Activa")  # 👈 Mayúscula inicial estándar
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    # 🔗 Relación con el usuario que registró la placa
    usuario_id = db.Column(db.Integer, db.ForeignKey("operacionbarco.usuarios.id"), nullable=True)
    usuario = db.relationship("Usuario", backref=db.backref("placas", lazy=True))

    def __repr__(self):
        return f"<Placa {self.numero_placa} - Estado: {self.estado}>"

    # 🔹 Método auxiliar para normalizar estado
    def estado_normalizado(self):
        """Devuelve el estado con la primera letra mayúscula."""
        return self.estado.capitalize() if self.estado else "Desconocido"