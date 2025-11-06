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
    app.register_blueprint(placa_bp)
    app.register_blueprint(operacion_bp)
    app.register_blueprint(movimiento_bp)
    app.register_blueprint(notificacion_bp)

    # 🔹 Crear tablas y usuario admin solo una vez (seguro para Render)
    with app.app_context():
        db.create_all()
        if not Usuario.query.first():
            admin = Usuario(
                nombre="Dylan Bustos",
                email="italamo@alamoterminales.com"
            )
            admin.set_password("atm4261")
            db.session.add(admin)
            db.session.commit()
            print("✅ Usuario administrador creado automáticamente.")

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

    return app


# 🔹 Ejecución local (solo se ejecuta en tu PC, no en Render)
if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
with app.app_context():
    # 🔧 Eliminar la tabla vieja
    db.drop_all()
    # 🔧 Crear las tablas nuevas con las columnas correctas
    db.create_all()
    print("✅ Base de datos regenerada con la estructura actual.")