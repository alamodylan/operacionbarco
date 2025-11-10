# models/usuario.py
from models.base import db
from flask_login import UserMixin
from flask_bcrypt import Bcrypt
from datetime import datetime

bcrypt = Bcrypt()

class Usuario(UserMixin, db.Model):
    __tablename__ = "usuarios"
    __table_args__ = {"schema": "operacionbarco"}  # 👈 Usa tu mismo esquema

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    rol = db.Column(db.String(20), default="Usuario")  # 👈 Nuevo campo: Admin / Usuario
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Usuario {self.nombre} ({self.rol})>"

    # --- Métodos de seguridad ---
    def set_password(self, password):
        """Genera el hash de la contraseña usando Flask-Bcrypt."""
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        """Verifica la contraseña comparando con el hash almacenado."""
        return bcrypt.check_password_hash(self.password_hash, password)

    # --- Métodos de permisos ---
    def es_admin(self):
        """Devuelve True si el usuario tiene rol de administrador."""
        return self.rol == "Admin"