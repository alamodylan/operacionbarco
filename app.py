# app.py
from flask import Flask, render_template
from flask_login import LoginManager, login_required, current_user
from config import Config
from models.base import db
from models.usuario import Usuario, bcrypt  # bcrypt importado del modelo

# Importación de Blueprints
from routes.auth_routes import auth_bp
from routes.placa_routes import placa_bp
from routes.operacion_routes import operacion_bp
from routes.movimiento_routes import movimiento_bp
from routes.notificacion_routes import notificacion_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Inicialización de extensiones
    db.init_app(app)
    bcrypt.init_app(app)

    # Configuración del Login Manager
    login_manager = LoginManager()
    login_manager.login_view = "auth_bp.login"  # 🔧 corregido
    login_manager.login_message = "Por favor, inicia sesión para continuar."
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))

    # Registro de Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(placa_bp, url_prefix="/api/placas")
    app.register_blueprint(operacion_bp, url_prefix="/api/operaciones")
    app.register_blueprint(movimiento_bp, url_prefix="/api/movimientos")
    app.register_blueprint(notificacion_bp, url_prefix="/api/notificaciones")

    # Página principal (dashboard protegido)
    @app.route("/")
    @login_required
    def dashboard():
        return render_template("dashboard.html", user=current_user)

    # Manejo básico de errores
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_error(e):
        return render_template("500.html"), 500

# 🔹 Crear usuario admin automáticamente si no existe
    with app.app_context():
        if not Usuario.query.first():
            from werkzeug.security import generate_password_hash
            admin = Usuario(
                usuario="Dylan Bustos",
                correo="italamo@alamoterminales.com",
                password=generate_password_hash("atm4261")
            )
            db.session.add(admin)
            db.session.commit()
            print("✅ Usuario administrador creado automáticamente.")
    return app


# Ejecución local
if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        # Solo para desarrollo (no usar en Render)
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)