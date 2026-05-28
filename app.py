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

from models.tiempo import ConfigTiempos
from models.operacion import Operacion

from routes.notificacion_routes import (
    guardar_ultima_alerta,
    enviar_push_mismo_mensaje,
)

# Blueprints
from routes.auth_routes import auth_bp
from routes.placa_routes import placa_bp
from routes.operacion_routes import operacion_bp
from routes.movimiento_routes import movimiento_bp
from routes.notificacion_routes import notificacion_bp
from routes.usuario_routes import usuario_bp
from routes.tiempos import tiempos_bp


load_dotenv()

CR_TZ = pytz.timezone("America/Costa_Rica")


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    app.config["SESSION_PERMANENT"] = True
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=1)

    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = True

    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
        "pool_timeout": 30,
    }

    db.init_app(app)
    bcrypt.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = "auth_bp.login"
    login_manager.login_message = "Por favor, inicia sesión para continuar."
    login_manager.refresh_view = "auth_bp.login"
    login_manager.needs_refresh_message = "Tu sesión ha expirado. Vuelve a iniciar sesión."
    login_manager.needs_refresh_message_category = "info"
    login_manager.session_protection = "basic"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return Usuario.query.get(int(user_id))
        except Exception as e:
            try:
                db.session.rollback()
            except Exception:
                pass

            app.logger.error(
                f"Error cargando usuario de sesión {user_id}: {e}"
            )
            return None

    @app.before_request
    def mantener_sesion():
        session.permanent = True

    app.register_blueprint(auth_bp)
    app.register_blueprint(placa_bp)
    app.register_blueprint(operacion_bp)
    app.register_blueprint(movimiento_bp)
    app.register_blueprint(notificacion_bp)
    app.register_blueprint(usuario_bp)
    app.register_blueprint(tiempos_bp)

    @app.route("/sw.js")
    def sw():
        return send_from_directory("static", "sw.js")

    @app.route("/")
    @login_required
    def dashboard():
        return render_template("dashboard.html", user=current_user)

    @app.errorhandler(404)
    def page_not_found(e):
        try:
            db.session.rollback()
        except Exception:
            pass

        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_error(e):
        try:
            db.session.rollback()
        except Exception:
            pass

        return render_template("500.html"), 500

    with app.app_context():
        try:
            db.create_all()

            admin_existente = Usuario.query.filter_by(
                email="italamo@alamoterminales.com"
            ).first()

            if not admin_existente:
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

        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error creando tablas o usuario admin: {e}")

    return app


def verificar_movimientos_periodicamente(app):
    """
    Revisa cada minuto los movimientos en ruta.

    - Importación usa min_import.
    - Exportación usa min_export.
    - Luego de la primera alerta, reenvía cada 4 minutos.
    - Si el movimiento se cierra, deja de notificar.
    """

    ultima_alerta = {}

    while True:
        try:
            with app.app_context():
                ahora = datetime.now(CR_TZ).replace(tzinfo=None)

                print(
                    "⏱️ Verificando movimientos activos...",
                    ahora.strftime("%H:%M:%S %d/%m/%Y"),
                )

                cfg = (
                    ConfigTiempos.query
                    .order_by(ConfigTiempos.id.desc())
                    .first()
                )

                min_import = cfg.min_import if cfg else 20
                min_export = cfg.min_export if cfg else 30

                movimientos = (
                    MovimientoBarco.query
                    .filter_by(estado="en_ruta")
                    .all()
                )

                if not movimientos:
                    ultima_alerta.clear()
                    db.session.remove()
                    time.sleep(60)
                    continue

                operacion_ids = {
                    mov.operacion_id
                    for mov in movimientos
                    if mov.operacion_id
                }

                operaciones = (
                    Operacion.query
                    .filter(Operacion.id.in_(operacion_ids))
                    .all()
                    if operacion_ids
                    else []
                )

                operaciones_map = {
                    op.id: op
                    for op in operaciones
                }

                for mov in movimientos:
                    if not mov.hora_salida:
                        continue

                    minutos = (
                        ahora - mov.hora_salida
                    ).total_seconds() / 60

                    oper = operaciones_map.get(mov.operacion_id)

                    tipo = (
                        getattr(oper, "tipo_operacion", "") or ""
                    ).strip().lower()

                    if tipo == "importacion":
                        umbral = min_import
                        tipo_label = "IMPORTACIÓN"
                    else:
                        umbral = min_export
                        tipo_label = "EXPORTACIÓN"

                    if minutos < umbral:
                        continue

                    ultimo_envio = ultima_alerta.get(mov.id)

                    if (
                        not ultimo_envio
                        or (ahora - ultimo_envio).total_seconds() >= 240
                    ):
                        mensaje = (
                            "🚨 *ALERTA DE RETRASO EN RUTA!*\n"
                            f"📌 Tipo: {tipo_label}\n"
                            f"🎯 Umbral: {umbral} min\n"
                            f"🧱 Contenedor: {mov.contenedor}\n"
                            f"🚛 Placa: {mov.placa.numero_placa}\n"
                            f"👨‍🔧 Chofer: {mov.placa.propietario or 'Desconocido'}\n"
                            f"🕒 Inicio: {mov.hora_salida.strftime('%H:%M %d/%m/%Y')}\n"
                            f"⏱️ Tiempo transcurrido: {int(minutos)} minutos"
                        )

                        try:
                            alerta_id = guardar_ultima_alerta(
                                f"🚨 Retraso: {tipo_label}",
                                mensaje,
                                tipo="emergencia",
                                operacion_id=mov.operacion_id,
                                movimiento_id=mov.id,
                            )

                            url_alerta = (
                                f"/notificaciones/alerta/{alerta_id}"
                                if alerta_id
                                else "/notificaciones/alerta"
                            )

                            enviar_push_mismo_mensaje(
                                mensaje,
                                f"🚨 Retraso: {tipo_label}",
                                url=url_alerta
                            )

                            ultima_alerta[mov.id] = ahora

                        except Exception as e:
                            try:
                                db.session.rollback()
                            except Exception:
                                pass

                            app.logger.error(
                                f"Error enviando push del movimiento "
                                f"{mov.id}: {e}"
                            )

                ids_activos = {
                    mov.id
                    for mov in movimientos
                }

                for mid in list(ultima_alerta.keys()):
                    if mid not in ids_activos:
                        ultima_alerta.pop(mid, None)

                db.session.remove()

        except Exception as e:
            try:
                db.session.rollback()
            except Exception:
                pass

            try:
                db.session.remove()
            except Exception:
                pass

            app.logger.error(
                f"Error en verificación automática: {e}"
            )

        time.sleep(60)


if __name__ == "__main__":
    app = create_app()

    verificador = threading.Thread(
        target=verificar_movimientos_periodicamente,
        args=(app,),
        daemon=True,
    )

    verificador.start()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
