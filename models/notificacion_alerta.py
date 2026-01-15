from datetime import datetime
import pytz
from models.base import db

CR_TZ = pytz.timezone("America/Costa_Rica")

class NotificacionAlerta(db.Model):
    __tablename__ = "notificaciones_alerta"
    __table_args__ = {"schema": "operacionbarco"}

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(30), nullable=False, default="alerta")  # alerta / emergencia / resuelta
    titulo = db.Column(db.String(200), nullable=False)
    mensaje = db.Column(db.Text, nullable=False)
    fecha = db.Column(db.DateTime, default=lambda: datetime.now(CR_TZ).replace(tzinfo=None))
    operacion_id = db.Column(db.Integer, nullable=True)
    movimiento_id = db.Column(db.Integer, nullable=True)