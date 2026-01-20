from datetime import datetime
from models.base import db


class ConfigTiempos(db.Model):
    __tablename__ = "config_tiempos"
    __table_args__ = {"schema": "operacionbarco"}

    id = db.Column(db.Integer, primary_key=True)

    min_import = db.Column(db.Integer, nullable=False, default=20)
    min_export = db.Column(db.Integer, nullable=False, default=30)

    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_by = db.Column(db.Integer, nullable=True)