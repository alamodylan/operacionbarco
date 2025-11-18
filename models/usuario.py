# models/usuario.py
from models.base import db
from flask_login import UserMixin
from flask_bcrypt import Bcrypt
from datetime import datetime
import pytz

CR_TZ = pytz.timezone("America/Costa_Rica")
bcrypt = Bcrypt()

class Usuario(UserMixin, db.Model):
    __tablename__ = "usuarios"
    __table_args__ = {"schema": "operacionbarco"}

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    # 🔥 Roles unificados
    rol = db.Column(
        db.String(20),
        nullable=False,
        default="UsuarioPredio"
    )

    fecha_creacion = db.Column(
        db.DateTime,
        default=lambda: datetime.now(CR_TZ).replace(tzinfo=None)
    )

    def __repr__(self):
        return f"<Usuario {self.nombre} ({self.rol})>"

    # --- Métodos de seguridad ---
    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    # --- Métodos de permisos ---
    def es_admin(self):
        return self.rol == "Admin"

    def es_predio(self):
        return self.rol == "UsuarioPredio"

    def es_muelle(self):
        return self.rol == "UsuarioMuelle"