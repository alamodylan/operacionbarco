from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from models.base import db
from models.placa import Placa

placa_bp = Blueprint("placa_bp", __name__)

# ---- Listar placas ----
@placa_bp.route("/", methods=["GET"])
@login_required
def listar_placas():
    try:
        placas = Placa.query.order_by(Placa.fecha_registro.desc()).all()
        return render_template("placas.html", placas=placas)
    except Exception as e:
        current_app.logger.exception(f"Error al listar placas: {e}")
        flash("Ocurrió un error al cargar las placas.", "danger")
        return render_template("placas.html", placas=[])

# ---- Registrar nueva placa ----
@placa_bp.route("/nueva", methods=["POST"])
@login_required
def nueva_placa():
    try:
        numero_placa = (request.form.get("numero_placa") or "").strip().upper()
        propietario = (request.form.get("propietario") or "").strip() or None
        color_cabezal = (request.form.get("color_cabezal") or "").strip() or None

        # ✅ NUEVO: identificador fijo (opcional)
        identificador_fijo = (request.form.get("identificador_fijo") or "").strip().upper() or None

        if not numero_placa:
            flash("Debe ingresar un número de placa.", "warning")
            return redirect(url_for("placa_bp.listar_placas"))

        # Verificar duplicados de placa
        if Placa.query.filter_by(numero_placa=numero_placa).first():
            flash("Esta placa ya está registrada.", "danger")
            return redirect(url_for("placa_bp.listar_placas"))

        # ✅ Verificar duplicado de identificador (si viene)
        if identificador_fijo and Placa.query.filter_by(identificador_fijo=identificador_fijo).first():
            flash("Ese identificador ya está ligado a otra placa.", "danger")
            return redirect(url_for("placa_bp.listar_placas"))

        nueva = Placa(
            numero_placa=numero_placa,
            propietario=propietario,
            color_cabezal=color_cabezal,
            identificador_fijo=identificador_fijo,
            usuario_id=current_user.id if current_user else None
        )

        db.session.add(nueva)
        db.session.commit()

        flash(f"Placa {numero_placa} agregada exitosamente.", "success")
        return redirect(url_for("placa_bp.listar_placas"))

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"Error al agregar placa: {e}")
        flash(f"Error al registrar la placa: {str(e)}", "danger")
        return redirect(url_for("placa_bp.listar_placas"))

# ---- Actualizar datos de placa (propietario, color, identificador) ----
@placa_bp.route("/actualizar/<int:placa_id>", methods=["POST"])
@login_required
def actualizar_placa(placa_id):
    try:
        placa = Placa.query.get_or_404(placa_id)

        propietario = (request.form.get("propietario") or "").strip() or None
        color_cabezal = (request.form.get("color_cabezal") or "").strip() or None

        # ✅ NUEVO: identificador fijo (opcional)
        identificador_fijo = (request.form.get("identificador_fijo") or "").strip().upper() or None

        # ✅ Validación: identificador único (si viene)
        if identificador_fijo:
            dup = (Placa.query
                   .filter(Placa.identificador_fijo == identificador_fijo, Placa.id != placa.id)
                   .first())
            if dup:
                flash(f"❌ Ese identificador ya está ligado a la placa {dup.numero_placa}.", "danger")
                return redirect(url_for("placa_bp.listar_placas"))

        placa.propietario = propietario
        placa.color_cabezal = color_cabezal
        placa.identificador_fijo = identificador_fijo

        db.session.commit()
        flash(f"Placa {placa.numero_placa} actualizada correctamente.", "success")
        return redirect(url_for("placa_bp.listar_placas"))

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"Error al actualizar placa: {e}")
        flash(f"Error al actualizar la placa: {str(e)}", "danger")
        return redirect(url_for("placa_bp.listar_placas"))

# ---- Cambiar estado (Activa / Inactiva) ----
@placa_bp.route("/estado/<int:placa_id>", methods=["POST"])
@login_required
def cambiar_estado(placa_id):
    try:
        placa = Placa.query.get_or_404(placa_id)
        nuevo_estado = (request.form.get("estado") or "").strip()

        if nuevo_estado not in ["Activa", "Inactiva"]:
            flash("Estado inválido.", "warning")
            return redirect(url_for("placa_bp.listar_placas"))

        placa.estado = nuevo_estado
        db.session.commit()

        flash(f"Estado de la placa {placa.numero_placa} cambiado a {nuevo_estado}.", "info")
        return redirect(url_for("placa_bp.listar_placas"))

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"Error al cambiar estado de placa: {e}")
        flash(f"Error al actualizar el estado de la placa: {str(e)}", "danger")
        return redirect(url_for("placa_bp.listar_placas"))

# ---- ✅ Guardar cambios en lote ----
@placa_bp.route("/actualizar_batch", methods=["POST"])
@login_required
def actualizar_placas_batch():
    try:
        updates = {}

        for key, value in request.form.items():
            if key.startswith("propietario["):
                placa_id = int(key.split("[", 1)[1].split("]")[0])
                updates.setdefault(placa_id, {})["propietario"] = value.strip() or None

            elif key.startswith("color_cabezal["):
                placa_id = int(key.split("[", 1)[1].split("]")[0])
                updates.setdefault(placa_id, {})["color_cabezal"] = value.strip() or None

            elif key.startswith("estado["):
                placa_id = int(key.split("[", 1)[1].split("]")[0])
                estado = value.strip()
                if estado in ["Activa", "Inactiva"]:
                    updates.setdefault(placa_id, {})["estado"] = estado

            elif key.startswith("identificador_fijo["):
                placa_id = int(key.split("[", 1)[1].split("]")[0])
                ident = value.strip().upper()
                updates.setdefault(placa_id, {})["identificador_fijo"] = ident or None

        if not updates:
            flash("No hay cambios para guardar.", "info")
            return redirect(url_for("placa_bp.listar_placas"))

        ids = list(updates.keys())
        placas = Placa.query.filter(Placa.id.in_(ids)).all()
        placas_por_id = {p.id: p for p in placas}

        # Validación duplicados (form + DB)
        nuevos_ident_por_pid = {}
        for pid, data in updates.items():
            if "identificador_fijo" in data:
                nuevos_ident_por_pid[pid] = data["identificador_fijo"]

        # 1) duplicados dentro del mismo batch
        seen = {}
        for pid, ident in nuevos_ident_por_pid.items():
            if not ident:
                continue
            if ident in seen and seen[ident] != pid:
                flash(f"❌ Identificador repetido en el formulario: {ident}.", "danger")
                return redirect(url_for("placa_bp.listar_placas"))
            seen[ident] = pid

        # 2) duplicados contra DB
        idents = [i for i in nuevos_ident_por_pid.values() if i]
        if idents:
            existentes = Placa.query.filter(Placa.identificador_fijo.in_(idents)).all()
            for p in existentes:
                pid_form = seen.get(p.identificador_fijo)
                if pid_form is None:
                    continue
                if p.id != pid_form:
                    flash(f"❌ El identificador {p.identificador_fijo} ya está ligado a la placa {p.numero_placa}.", "danger")
                    return redirect(url_for("placa_bp.listar_placas"))

        # Aplicar cambios
        for pid, data in updates.items():
            p = placas_por_id.get(pid)
            if not p:
                continue

            if "propietario" in data:
                p.propietario = data["propietario"]

            if "color_cabezal" in data:
                p.color_cabezal = data["color_cabezal"]

            if "estado" in data:
                p.estado = data["estado"]

            if "identificador_fijo" in data:
                p.identificador_fijo = data["identificador_fijo"]

        db.session.commit()
        flash("✅ Cambios guardados correctamente.", "success")
        return redirect(url_for("placa_bp.listar_placas"))

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"Error en actualizar_placas_batch: {e}")
        flash(f"❌ Error al guardar cambios: {str(e)}", "danger")
        return redirect(url_for("placa_bp.listar_placas"))

# ---- ✅ NUEVO: Buscar identificadores (para Operación Barco) ----
@placa_bp.route("/buscar-identificador", methods=["GET"])
@login_required
def buscar_identificador():
    try:
        q = (request.args.get("q") or "").strip().upper()
        if not q:
            return jsonify([])

        rows = (Placa.query
                .filter(Placa.estado == "Activa")
                .filter(Placa.identificador_fijo.isnot(None))
                .filter(Placa.identificador_fijo.ilike(f"%{q}%"))
                .order_by(Placa.identificador_fijo.asc())
                .limit(20)
                .all())

        return jsonify([{
            "id": r.id,
            "identificador": r.identificador_fijo,
            "placa": r.numero_placa,
            "propietario": r.propietario
        } for r in rows])

    except Exception as e:
        current_app.logger.exception(f"Error en buscar_identificador: {e}")
        return jsonify([]), 200