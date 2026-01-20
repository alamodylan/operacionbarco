from flask import Flask, render_template, send_from_directory, session
from flask_login import LoginManager, login_required, current_user
from datetime import datetime, timedelta
import pytz
import threading
import time

from dotenv import load_dotenv
from config import Config

from models.base import db
from models.usuario import Usuario, bcrypt
from models.movimiento import MovimientoBarco
from models.notificacion import enviar_notificacion

# Blueprints
from routes.auth_routes import auth_bp
from routes.placa_routes import placa_bp
from routes.operacion_routes import operacion_bp
from routes.movimiento_routes import movimiento_bp
from routes.notificacion_routes import notificacion_bp
from routes.usuario_routes import usuario_bp


# -----------------------------------------------------------
# Cargar variables de entorno
# -----------------------------------------------------------
load_dotenv()

# -----------------------------------------------------------
# Zona horaria Costa Rica
# -----------------------------------------------------------
CR_TZ = pytz.timezone("America/Costa_Rica")


# -----------------------------------------------------------
# Application Factory
# -----------------------------------------------------------
def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # ✅ CAMBIO CLAVE: sesión persistente real (móvil friendly)
    app.config["SESSION_PERMANENT"] = True
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=1)

    # ✅ CAMBIO CLAVE: cookies más estables/seguras (Render usa HTTPS)
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = True

    # -------------------------------------------------------
    # Inicializar extensiones
    # -------------------------------------------------------
    db.init_app(app)
    bcrypt.init_app(app)

    # -------------------------------------------------------
    # Login Manager
    # -------------------------------------------------------
    login_manager = LoginManager()
    login_manager.login_view = "auth_bp.login"
    login_manager.login_message = "Por favor, inicia sesión para continuar."
    login_manager.refresh_view = "auth_bp.login"
    login_manager.needs_refresh_message = "Tu sesión ha expirado. Vuelve a iniciar sesión."
    login_manager.needs_refresh_message_category = "info"
    login_manager.init_app(app)

    # ✅ CAMBIO CLAVE: evita cierres raros en móvil/redes cambiantes
    login_manager.session_protection = "basic"

    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))

    # ✅ CAMBIO CLAVE: mantener sesión permanente en cada request
    @app.before_request
    def mantener_sesion():
        session.permanent = True

    # -------------------------------------------------------
    # Registro de Blueprints
    # -------------------------------------------------------
    app.register_blueprint(auth_bp)
    app.register_blueprint(placa_bp)
    app.register_blueprint(operacion_bp)
    app.register_blueprint(movimiento_bp)
    app.register_blueprint(notificacion_bp)
    app.register_blueprint(usuario_bp)

    # -------------------------------------------------------
    # Service Worker (scope raíz)
    # -------------------------------------------------------
    @app.route("/sw.js")
    def sw():
        return send_from_directory("static", "sw.js")

    # -------------------------------------------------------
    # Dashboard protegido
    # -------------------------------------------------------
    @app.route("/")
    @login_required
    def dashboard():
        return render_template("dashboard.html", user=current_user)

    # -------------------------------------------------------
    # Manejo de errores
    # -------------------------------------------------------
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_error(e):
        return render_template("500.html"), 500

    # -------------------------------------------------------
    # Crear tablas y usuario admin (solo una vez)
    # -------------------------------------------------------
    with app.app_context():
        db.create_all()

        if not Usuario.query.filter_by(email="italamo@alamoterminales.com").first():
            admin = Usuario(
                nombre="Dylan Bustos",
                email="italamo@alamoterminales.com",
            )
            admin.set_password("atm4261")
            db.session.add(admin)
            db.session.commit()
            print("✅ Usuario administrador creado automáticamente.")
        else:
            print("ℹ️ Usuario administrador ya existe.")

    return app


# -----------------------------------------------------------
# Verificación automática de movimientos prolongados
# -----------------------------------------------------------
def verificar_movimientos_periodicamente(app):
    """
    Revisa cada minuto si hay movimientos en ruta por más de 20 minutos
    y reenvía alertas cada 4 minutos mientras sigan abiertos.
    """
    ultima_alerta = {}

    while True:
        try:
            with app.app_context():
                ahora = datetime.now(CR_TZ).replace(tzinfo=None)
                movimientos = MovimientoBarco.query.filter_by(estado="en_ruta").all()

                print(
                    "⏱️ Verificando movimientos activos...",
                    datetime.now(CR_TZ).strftime("%H:%M:%S %d/%m/%Y"),
                )

                for mov in movimientos:
                    if not mov.hora_salida:
                        continue

                    minutos = (ahora - mov.hora_salida).total_seconds() / 60

                    if minutos >= 20:
                        ultimo_envio = ultima_alerta.get(mov.id)

                        if not ultimo_envio or (ahora - ultimo_envio).total_seconds() >= 240:
                            mensaje = (
                                "🚨 *ALERTA DE RETRASO EN RUTA!*\n"
                                f"🧱 Contenedor: {mov.contenedor}\n"
                                f"🚛 Placa: {mov.placa.numero_placa}\n"
                                f"👨‍🔧 Chofer: {mov.placa.propietario or 'Desconocido'}\n"
                                f"🕒 Inicio: {mov.hora_salida.strftime('%H:%M %d/%m/%Y')}\n"
                                f"⏱️ Tiempo transcurrido: {int(minutos)} minutos"
                            )

                            enviar_notificacion(mensaje)
                            ultima_alerta[mov.id] = ahora

                # 🧹 Limpiar alertas de movimientos cerrados
                ids_activos = {m.id for m in movimientos}
                for mid in list(ultima_alerta.keys()):
                    if mid not in ids_activos:
                        ultima_alerta.pop(mid, None)

        except Exception as e:
            app.logger.error(f"Error en verificación automática: {e}")

        time.sleep(60)


# -----------------------------------------------------------
# Ejecución local
# -----------------------------------------------------------
if __name__ == "__main__":
    app = create_app()

    # 🔹 Iniciar hilo en segundo plano
    verificador = threading.Thread(
        target=verificar_movimientos_periodicamente,
        args=(app,),
        daemon=True,
    )
    verificador.start()

    app.run(host="0.0.0.0", port=5000, debug=False)
