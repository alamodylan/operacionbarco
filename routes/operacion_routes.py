from datetime import datetime

import pytz
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user

from models.base import db
from models.operacion import Operacion
from models.movimiento import MovimientoBarco
from models.placa import Placa


CR_TZ = pytz.timezone("America/Costa_Rica")

# ============================================================
# 🟦 BLUEPRINT DE OPERACIONES DE BARCO
# ============================================================
operacion_bp = Blueprint("operacion_bp", __name__, url_prefix="/operaciones")


# ------------------------------------------------------------
# 📄 1️⃣ Listar operaciones en proceso
# ------------------------------------------------------------
@operacion_bp.route("/", methods=["GET"])
@login_required
def listar_operaciones():
    try:
        operaciones = (
            Operacion.query
            .filter_by(estado="en_proceso")
            .order_by(Operacion.fecha_creacion.desc())
            .all()
        )
        return render_template(
            "operaciones.html",
            operaciones=operaciones,
            rol=current_user.rol
        )

    except Exception as e:
        current_app.logger.exception(f"Error al listar operaciones: {e}")
        flash("Ocurrió un error al cargar las operaciones activas.", "danger")
        return render_template(
            "operaciones.html",
            operaciones=[],
            rol=current_user.rol
        )


# ------------------------------------------------------------
# ➕ 2️⃣ Crear nueva operación de barco
# ------------------------------------------------------------
@operacion_bp.route("/nueva", methods=["POST"])
@login_required
def nueva_operacion():
    try:
        nombre = request.form.get("nombre")
        tipo_operacion = request.form.get("tipo_operacion")

        if not nombre or not tipo_operacion:
            flash("Debe ingresar nombre y tipo de operación.", "warning")
            return redirect(url_for("operacion_bp.listar_operaciones"))

        nueva = Operacion(
            nombre=nombre.strip(),
            tipo_operacion=tipo_operacion,
            fecha_creacion=datetime.now(CR_TZ).replace(tzinfo=None),
        )

        db.session.add(nueva)
        db.session.commit()

        flash(f"Operación '{nombre}' creada exitosamente.", "success")
        return redirect(url_for("operacion_bp.detalle_operacion", operacion_id=nueva.id))

    except Exception as e:
        current_app.logger.exception(f"Error al crear operación: {e}")
        flash("Error al crear la operación.", "danger")
        return redirect(url_for("operacion_bp.listar_operaciones"))


# ------------------------------------------------------------
# 🔍 3️⃣ Ver detalles de una operación
# ------------------------------------------------------------
@operacion_bp.route("/detalle/<int:operacion_id>", methods=["GET"])
@login_required
def detalle_operacion(operacion_id):
    try:
        operacion = Operacion.query.get_or_404(operacion_id)

        placas_disponibles = (
            Placa.query
            .filter(Placa.estado.ilike("activa"))
            .order_by(Placa.numero_placa.asc())
            .all()
        )

        movimientos = (
            MovimientoBarco.query
            .filter_by(operacion_id=operacion.id)
            .order_by(MovimientoBarco.id.desc())
            .all()
        )

        return render_template(
            "operacion_detalle.html",
            operacion=operacion,
            placas=placas_disponibles,
            movimientos=movimientos,
            rol=current_user.rol,
        )

    except Exception as e:
        current_app.logger.exception(f"Error al cargar detalles de operación: {e}")
        flash("No se pudo cargar la operación.", "danger")
        return redirect(url_for("operacion_bp.listar_operaciones"))


# ------------------------------------------------------------
# 🚛 4️⃣ Agregar movimiento (SALIDA) — SIN NOTIFICACIÓN
#     ✅ AHORA: solo con IDENTIFICADOR FIJO (sin escribir contenedor)
# ------------------------------------------------------------
@operacion_bp.route("/agregar_movimiento/<int:operacion_id>", methods=["POST"])
@login_required
def agregar_movimiento(operacion_id):
    try:
        placa_id = request.form.get("placa_id")

        if not placa_id:
            flash("Debe seleccionar un identificador fijo.", "warning")
            return redirect(url_for("operacion_bp.detalle_operacion", operacion_id=operacion_id))

        placa = Placa.query.get(int(placa_id))
        if not placa:
            flash("La placa seleccionada no existe.", "danger")
            return redirect(url_for("operacion_bp.detalle_operacion", operacion_id=operacion_id))

        # ✅ Usamos el identificador fijo como el "contenedor" del movimiento
        identificador = (placa.identificador_fijo or "").strip()

        if not identificador:
            flash("Esa placa no tiene identificador fijo asignado.", "warning")
            return redirect(url_for("operacion_bp.detalle_operacion", operacion_id=operacion_id))

        # ✅ Opcional: evitar doble movimiento EN RUTA con el mismo identificador en la misma operación
        existente = (
            MovimientoBarco.query
            .filter_by(operacion_id=operacion_id, contenedor=identificador, estado="en_ruta")
            .first()
        )
        if existente:
            flash(f"El identificador {identificador} ya está en ruta en esta operación.", "warning")
            return redirect(url_for("operacion_bp.detalle_operacion", operacion_id=operacion_id))

        nuevo_mov = MovimientoBarco(
            operacion_id=operacion_id,
            placa_id=placa.id,
            contenedor=identificador,  # 👈 aquí va el identificador fijo
            hora_salida=datetime.now(CR_TZ).replace(tzinfo=None),
            estado="en_ruta",
            ultima_notificacion=None,
        )

        db.session.add(nuevo_mov)
        db.session.commit()

        flash(f"Movimiento agregado correctamente para el identificador {identificador}.", "success")
        return redirect(url_for("operacion_bp.detalle_operacion", operacion_id=operacion_id))

    except Exception as e:
        current_app.logger.exception(f"Error al agregar movimiento: {e}")
        db.session.rollback()
        flash("Error al agregar movimiento.", "danger")
        return redirect(url_for("operacion_bp.detalle_operacion", operacion_id=operacion_id))


# ------------------------------------------------------------
# 🏁 5️⃣ Finalizar un movimiento (ENTRADA)
# ------------------------------------------------------------
@operacion_bp.route("/finalizar_movimiento/<int:movimiento_id>", methods=["POST"])
@login_required
def finalizar_movimiento(movimiento_id):

    try:

        mov = MovimientoBarco.query.get_or_404(movimiento_id)

        if mov.estado == "finalizado":
            flash(
                "Ese movimiento ya fue finalizado.",
                "warning"
            )

            return redirect(
                url_for(
                    "operacion_bp.detalle_operacion",
                    operacion_id=mov.operacion_id
                )
            )

        if not mov.hora_salida:

            flash(
                "El movimiento no tiene hora de salida.",
                "danger"
            )

            return redirect(
                url_for(
                    "operacion_bp.detalle_operacion",
                    operacion_id=mov.operacion_id
                )
            )

        # ====================================================
        # ⏱️ VALIDAR TIEMPO MÍNIMO
        # ====================================================

        hora_llegada = datetime.now(CR_TZ).replace(tzinfo=None)

        minutos = (
            hora_llegada - mov.hora_salida
        ).total_seconds() / 60

        if minutos < 8:

            flash(
                (
                    "No se puede finalizar un viaje "
                    "menor a 8 minutos."
                ),
                "warning"
            )

            return redirect(
                url_for(
                    "operacion_bp.detalle_operacion",
                    operacion_id=mov.operacion_id
                )
            )

        # ====================================================
        # ✅ FINALIZAR MOVIMIENTO
        # ====================================================

        mov.hora_llegada = hora_llegada
        mov.estado = "finalizado"
        mov.cerrado_por_user_id = current_user.id

        db.session.commit()

        flash(
            (
                f"Movimiento {mov.contenedor} "
                f"finalizado correctamente."
            ),
            "success"
        )

        return redirect(
            url_for(
                "operacion_bp.detalle_operacion",
                operacion_id=mov.operacion_id
            )
        )

    except Exception as e:

        try:
            db.session.rollback()
        except Exception:
            pass

        current_app.logger.exception(
            f"Error al finalizar movimiento: {e}"
        )

        flash(
            "Error al finalizar movimiento.",
            "danger"
        )

        return redirect(
            url_for("operacion_bp.listar_operaciones")
        )


# ------------------------------------------------------------
# ⛔ 6️⃣ Finalizar toda la operación
# ------------------------------------------------------------
@operacion_bp.route("/finalizar_operacion/<int:operacion_id>", methods=["POST"])
@login_required
def finalizar_operacion(operacion_id):
    try:
        operacion = Operacion.query.get_or_404(operacion_id)

        if operacion.finalizar():
            db.session.commit()
            flash(f"La operación '{operacion.nombre}' fue finalizada correctamente.", "success")
        else:
            flash("No se puede finalizar. Hay movimientos aún en tránsito.", "warning")

        return redirect(url_for("operacion_bp.listar_operaciones"))

    except Exception as e:
        current_app.logger.exception(f"Error al finalizar operación: {e}")
        flash("Error al finalizar la operación.", "danger")
        return redirect(url_for("operacion_bp.listar_operaciones"))


# ------------------------------------------------------------
# 🧪 DEBUG: Ver valores reales de WhatsApp cargados desde Render
# ------------------------------------------------------------
@operacion_bp.route("/debug-noti", methods=["GET"])
def debug_noti():
    return {
        "WHATSAPP_PHONE": repr(current_app.config.get("WHATSAPP_PHONE")),
        "CALLMEBOT_API_KEY": repr(current_app.config.get("CALLMEBOT_API_KEY")),
        "WHATSAPP_PHONE_1": repr(current_app.config.get("WHATSAPP_PHONE_1")),
        "CALLMEBOT_API_KEY_1": repr(current_app.config.get("CALLMEBOT_API_KEY_1")),
    }


@operacion_bp.route("/noti-test")
def noti_test():
    from models.notificacion import enviar_notificacion

    ok = enviar_notificacion("🔥 Notificación de prueba Operación Barco")
    return {"resultado": ok}
