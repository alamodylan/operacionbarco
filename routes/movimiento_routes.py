from datetime import datetime

import pytz

from flask import (
    Blueprint,
    render_template,
    request,
    flash,
    jsonify,
    current_app,
)

from flask_login import login_required, current_user

from sqlalchemy.orm import joinedload
from sqlalchemy import text

from models.base import db
from models.movimiento import MovimientoBarco
from models.operacion import Operacion


CR_TZ = pytz.timezone("America/Costa_Rica")

movimiento_bp = Blueprint(
    "movimiento_bp",
    __name__,
    url_prefix="/movimientos"
)


# ============================================================
# 📋 LISTAR MOVIMIENTOS FINALIZADOS (PAGINADO)
# ============================================================
@movimiento_bp.route("/", methods=["GET"])
@login_required
def listar_movimientos():

    try:
        page = request.args.get("page", 1, type=int)
        per_page = 5

        operaciones_paginadas = (
            Operacion.query
            .options(
                joinedload(Operacion.movimientos)
                .joinedload(MovimientoBarco.placa)
            )
            .filter(Operacion.estado == "finalizada")
            .order_by(Operacion.fecha_creacion.desc())
            .paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )
        )

        datos = []

        for op in operaciones_paginadas.items:
            movimientos_finalizados = [
                m for m in op.movimientos
                if m.estado == "finalizado"
            ]

            if movimientos_finalizados:
                datos.append({
                    "operacion": op,
                    "movimientos": movimientos_finalizados,
                })

        return render_template(
            "movimientos.html",
            datos=datos,
            pagination=operaciones_paginadas
        )

    except Exception as e:
        current_app.logger.exception(
            f"Error al listar movimientos: {e}"
        )

        flash(
            "Ocurrió un error al cargar los movimientos.",
            "danger"
        )

        return render_template(
            "movimientos.html",
            datos=[],
            pagination=None
        )


# ============================================================
# 🏁 REGISTRAR LLEGADA / FINALIZAR MOVIMIENTO
# ============================================================
@movimiento_bp.route("/llegada/<int:id>", methods=["POST"])
@login_required
def registrar_llegada_movimiento(id):

    try:
        movimiento = MovimientoBarco.query.get(id)

        if not movimiento:
            return jsonify({
                "error": "Movimiento no encontrado"
            }), 404

        if movimiento.estado == "finalizado":
            return jsonify({
                "mensaje": "El movimiento ya fue finalizado"
            }), 200

        hora_llegada = datetime.now(CR_TZ).replace(tzinfo=None)

        if not movimiento.hora_salida:
            return jsonify({
                "error": "El movimiento no tiene hora de salida registrada."
            }), 400

        minutos = (
            hora_llegada - movimiento.hora_salida
        ).total_seconds() / 60

        # =====================================================
        # 🚫 BLOQUEO: NO PERMITIR CIERRES MENORES A 8 MINUTOS
        # =====================================================
        if minutos < 8:
            return jsonify({
                "error": (
                    "No se puede finalizar este viaje porque "
                    "tiene menos de 8 minutos en tránsito."
                ),
                "duracion_minutos": round(minutos, 2)
            }), 400

        movimiento.hora_llegada = hora_llegada
        movimiento.estado = "finalizado"
        movimiento.cerrado_por_user_id = current_user.id

        db.session.commit()

        return jsonify({
            "mensaje":
                f"Movimiento {movimiento.contenedor} "
                f"finalizado correctamente"
        }), 200

    except Exception as e:
        db.session.rollback()

        current_app.logger.exception(
            f"Error al registrar llegada del movimiento: {e}"
        )

        return jsonify({
            "error": "Error interno al registrar llegada"
        }), 500


# ============================================================
# 📊 REPORTE: CHOFERES QUE MÁS DURAN EN TRÁNSITO
# ============================================================
@movimiento_bp.route("/reportes/choferes-transito", methods=["GET"])
@login_required
def reporte_choferes_transito():

    try:
        page = request.args.get("page", 1, type=int)
        per_page = 25
        offset = (page - 1) * per_page

        total_query = text("""
            SELECT COUNT(*) AS total
            FROM (
                SELECT p.propietario
                FROM operacionbarco.movimientos_barco m
                JOIN operacionbarco.placas p
                    ON p.id = m.placa_id
                WHERE m.estado = 'finalizado'
                  AND m.hora_llegada IS NOT NULL
                  AND m.hora_salida IS NOT NULL
                GROUP BY p.propietario
            ) x
        """)

        data_query = text("""
            SELECT
                COALESCE(p.propietario, 'No registrado') AS chofer,
                COUNT(m.id) AS total_viajes,
                ROUND(
                    AVG(EXTRACT(EPOCH FROM (m.hora_llegada - m.hora_salida)) / 60),
                    2
                ) AS promedio_minutos,
                ROUND(
                    MAX(EXTRACT(EPOCH FROM (m.hora_llegada - m.hora_salida)) / 60),
                    2
                ) AS mayor_duracion_minutos,
                ROUND(
                    MIN(EXTRACT(EPOCH FROM (m.hora_llegada - m.hora_salida)) / 60),
                    2
                ) AS menor_duracion_minutos
            FROM operacionbarco.movimientos_barco m
            JOIN operacionbarco.placas p
                ON p.id = m.placa_id
            WHERE m.estado = 'finalizado'
              AND m.hora_llegada IS NOT NULL
              AND m.hora_salida IS NOT NULL
            GROUP BY p.propietario
            ORDER BY promedio_minutos DESC
            LIMIT :limit OFFSET :offset
        """)

        total = db.session.execute(total_query).scalar() or 0

        registros = db.session.execute(
            data_query,
            {
                "limit": per_page,
                "offset": offset
            }
        ).mappings().all()

        pages = (total + per_page - 1) // per_page

        return render_template(
            "reporte_choferes_transito.html",
            registros=registros,
            page=page,
            pages=pages
        )

    except Exception as e:
        current_app.logger.exception(
            f"Error en reporte de choferes en tránsito: {e}"
        )

        flash(
            "Ocurrió un error al cargar el reporte de choferes.",
            "danger"
        )

        return render_template(
            "reporte_choferes_transito.html",
            registros=[],
            page=1,
            pages=0
        )


# ============================================================
# 🚨 REPORTE: VIAJES MENORES A 10 MINUTOS
# ============================================================
@movimiento_bp.route("/reportes/viajes-menores-10", methods=["GET"])
@login_required
def reporte_viajes_menores_10():

    try:
        page = request.args.get("page", 1, type=int)
        per_page = 50
        offset = (page - 1) * per_page

        total_query = text("""
            SELECT COUNT(*) AS total
            FROM operacionbarco.movimientos_barco m
            WHERE m.estado = 'finalizado'
              AND m.hora_llegada IS NOT NULL
              AND m.hora_salida IS NOT NULL
              AND EXTRACT(EPOCH FROM (m.hora_llegada - m.hora_salida)) / 60 < 10
        """)

        data_query = text("""
            SELECT
                m.id,
                p.numero_placa,
                COALESCE(p.propietario, 'No registrado') AS chofer,
                m.contenedor,
                m.hora_salida,
                m.hora_llegada,
                ROUND(
                    EXTRACT(EPOCH FROM (m.hora_llegada - m.hora_salida)) / 60,
                    2
                ) AS duracion_minutos,
                COALESCE(u.nombre, u.email, 'No registrado') AS cerrado_por
            FROM operacionbarco.movimientos_barco m
            JOIN operacionbarco.placas p
                ON p.id = m.placa_id
            LEFT JOIN operacionbarco.usuarios u
                ON u.id = m.cerrado_por_user_id
            WHERE m.estado = 'finalizado'
              AND m.hora_llegada IS NOT NULL
              AND m.hora_salida IS NOT NULL
              AND EXTRACT(EPOCH FROM (m.hora_llegada - m.hora_salida)) / 60 < 10
            ORDER BY m.hora_llegada DESC
            LIMIT :limit OFFSET :offset
        """)

        total = db.session.execute(total_query).scalar() or 0

        registros = db.session.execute(
            data_query,
            {
                "limit": per_page,
                "offset": offset
            }
        ).mappings().all()

        pages = (total + per_page - 1) // per_page

        return render_template(
            "reporte_viajes_menores_10.html",
            registros=registros,
            page=page,
            pages=pages
        )

    except Exception as e:
        current_app.logger.exception(
            f"Error en reporte de viajes menores a 10 minutos: {e}"
        )

        flash(
            "Ocurrió un error al cargar el reporte de viajes menores a 10 minutos.",
            "danger"
        )

        return render_template(
            "reporte_viajes_menores_10.html",
            registros=[],
            page=1,
            pages=0
        )
