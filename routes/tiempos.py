from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user

from models.base import db
from models.tiempo import ConfigTiempos

tiempos_bp = Blueprint("tiempos_bp", __name__, url_prefix="/tiempos")


def es_admin(user):
    return getattr(user, "rol", None) == "Admin"


def obtener_config():
    cfg = ConfigTiempos.query.order_by(ConfigTiempos.id.desc()).first()
    if not cfg:
        cfg = ConfigTiempos(
            min_import=20,
            min_export=30,
            updated_by=getattr(current_user, "id", None),
        )
        db.session.add(cfg)
        db.session.commit()
    return cfg


@tiempos_bp.route("/", methods=["GET"])
@login_required
def ver_tiempos():
    if not es_admin(current_user):
        flash("No tienes permisos para acceder a esta sección.", "danger")
        return redirect(url_for("operacion_bp.listar_operaciones"))

    cfg = obtener_config()
    return render_template("tiempos.html", cfg=cfg)


@tiempos_bp.route("/guardar", methods=["POST"])
@login_required
def guardar_tiempos():
    if not es_admin(current_user):
        flash("No tienes permisos para modificar esta configuración.", "danger")
        return redirect(url_for("operacion_bp.listar_operaciones"))

    try:
        min_import = int(request.form.get("min_import", 0))
        min_export = int(request.form.get("min_export", 0))

        if min_import < 1 or min_export < 1:
            flash("Los minutos deben ser mayores a 0.", "warning")
            return redirect(url_for("tiempos_bp.ver_tiempos"))

        cfg = obtener_config()
        cfg.min_import = min_import
        cfg.min_export = min_export
        cfg.updated_by = current_user.id

        db.session.commit()

        flash("✅ Tiempos de notificación actualizados.", "success")
        return redirect(url_for("tiempos_bp.ver_tiempos"))

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"Error guardando tiempos: {e}")
        flash("❌ Error al guardar los tiempos.", "danger")
        return redirect(url_for("tiempos_bp.ver_tiempos"))