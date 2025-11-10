from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from datetime import datetime
from models.base import db
from models.operacion import Operacion
from models.movimiento import MovimientoBarco
from models.placa import Placa
from models.notificacion import enviar_notificacion
import pytz

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
        return render_template("operaciones.html", operaciones=operaciones)
    except Exception as e:
        current_app.logger.exception(f"Error al listar operaciones: {e}")
        flash("Ocurrió un error al cargar las operaciones activas.", "danger")
        return render_template("operaciones.html", operaciones=[])

# ------------------------------------------------------------
# ➕ 2️⃣ Crear nueva operación de barco
# ------------------------------------------------------------
@operacion_bp.route("/nueva", methods=["POST"])
@login_required
def nueva_operacion():
    try:
        nombre = request.form.get("nombre")

        if not nombre:
            flash("Debe ingresar el nombre de la operación (barco).", "warning")
            return redirect(url_for("operacion_bp.listar_operaciones"))

        nueva = Operacion(
            nombre=nombre.strip(),
            fecha_creacion=datetime.now(CR_TZ).replace(tzinfo=None)
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

        # ✅ Cargar solo placas activas
        placas_disponibles = (
            Placa.query
            .filter(Placa.estado.ilike("activa"))
            .order_by(Placa.numero_placa.asc())
            .all()
        )

        # ✅ Cargar movimientos asociados a esta operación
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
            movimientos=movimientos
        )

    except Exception as e:
        current_app.logger.exception(f"Error al cargar detalles de operación: {e}")
        flash("No se pudo cargar la operación.", "danger")
        return redirect(url_for("operacion_bp.listar_operaciones"))

# ------------------------------------------------------------
# 🚛 4️⃣ Agregar movimiento
# ------------------------------------------------------------
@operacion_bp.route("/agregar_movimiento/<int:operacion_id>", methods=["POST"])
@login_required
def agregar_movimiento(operacion_id):
    try:
        placa_id = request.form.get("placa_id")
        contenedor = request.form.get("contenedor")

        if not placa_id or not contenedor:
            flash("Debe seleccionar una placa activa y escribir el número de contenedor.", "warning")
            return redirect(url_for("operacion_bp.detalle_operacion", operacion_id=operacion_id))

        nuevo_mov = MovimientoBarco(
            operacion_id=operacion_id,
            placa_id=placa_id,
            contenedor=contenedor.strip().upper(),
            hora_salida=datetime.now(CR_TZ).replace(tzinfo=None),
            estado="en_ruta"
        )

        db.session.add(nuevo_mov)
        db.session.commit()

        # 🔔 Notificación
        placa = Placa.query.get(placa_id)
        mensaje = (
            f"🚛 Nueva salida registrada:\n"
            f"Placa: {placa.numero_placa}\n"
            f"Contenedor: {nuevo_mov.contenedor}\n"
            f"Hora: {nuevo_mov.hora_salida.strftime('%H:%M %d/%m/%Y')}"
        )
        enviar_notificacion(mensaje)

        flash(f"Movimiento agregado correctamente para el contenedor {contenedor}.", "success")
        return redirect(url_for("operacion_bp.detalle_operacion", operacion_id=operacion_id))

    except Exception as e:
        current_app.logger.exception(f"Error al agregar movimiento: {e}")
        flash("Error al agregar movimiento.", "danger")
        return redirect(url_for("operacion_bp.detalle_operacion", operacion_id=operacion_id))

# ------------------------------------------------------------
# 🏁 5️⃣ Finalizar un movimiento
# ------------------------------------------------------------
@operacion_bp.route("/finalizar_movimiento/<int:movimiento_id>", methods=["POST"])
@login_required
def finalizar_movimiento(movimiento_id):
    try:
        mov = MovimientoBarco.query.get_or_404(movimiento_id)
        mov.finalizar()
        db.session.commit()

        flash(f"Movimiento {mov.contenedor} finalizado correctamente.", "success")
        return redirect(url_for("operacion_bp.detalle_operacion", operacion_id=mov.operacion_id))

    except Exception as e:
        current_app.logger.exception(f"Error al finalizar movimiento: {e}")
        flash("Error al finalizar movimiento.", "danger")
        return redirect(url_for("operacion_bp.listar_operaciones"))

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
