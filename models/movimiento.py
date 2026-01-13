from datetime import datetime
import pytz
from models.base import db
from models.notificacion import enviar_notificacion

# ✅ NUEVO (necesario para push + guardar alerta)
import os
import json
from flask import current_app
from pywebpush import webpush, WebPushException

CR_TZ = pytz.timezone("America/Costa_Rica")

class MovimientoBarco(db.Model):
    __tablename__ = "movimientos_barco"
    __table_args__ = {"schema": "operacionbarco"}

    id = db.Column(db.Integer, primary_key=True)

    operacion_id = db.Column(
        db.Integer,
        db.ForeignKey("operacionbarco.operaciones_barco.id"),
        nullable=False
    )

    placa_id = db.Column(
        db.Integer,
        db.ForeignKey("operacionbarco.placas.id"),
        nullable=False
    )

    contenedor = db.Column(db.String(50), nullable=False)
    hora_salida = db.Column(
        db.DateTime,
        default=lambda: datetime.now(CR_TZ).replace(tzinfo=None)
    )
    hora_llegada = db.Column(db.DateTime, nullable=True)

    estado = db.Column(db.String(20), default="en_ruta")

    ultima_notificacion = db.Column(db.DateTime, nullable=True)

    alerta_orden_enviada = db.Column(db.Boolean, default=False)

    placa = db.relationship("Placa", backref="movimientos")

    # ======================================================
    # 🔥 URGENCIA
    # ======================================================

    def _ahora(self):
        """Devuelve el tiempo actual con la misma zona horaria usada en BD."""
        return datetime.now(CR_TZ).replace(tzinfo=None)

    def es_urgente(self):
        if self.estado != "en_ruta":
            return False

        ahora = self._ahora()
        minutos = (ahora - self.hora_salida).total_seconds() / 60
        return minutos >= 15

    def debe_notificar(self):
        if not self.es_urgente():
            return False

        ahora = self._ahora()

        # primera notificación
        if self.ultima_notificacion is None:
            return True

        minutos = (ahora - self.ultima_notificacion).total_seconds() / 60
        return minutos >= 3

    def marcar_notificado(self):
        self.ultima_notificacion = self._ahora()

    # ======================================================
    # ✅ NUEVO: Helpers mínimos para Push (solo para ALERTA RESUELTA)
    # ======================================================

    def _push_text(self, texto: str, max_len: int = 180) -> str:
        # Push suele fallar si el payload es muy largo → mandamos resumen
        t = (texto or "").replace("*", "")
        t = " ".join(t.split())
        return (t[:max_len - 1] + "…") if len(t) > max_len else t

    def _guardar_ultima_alerta(self, titulo: str, mensaje: str):
        # Guarda lo completo para ver “en grande” en /notificaciones/alerta
        try:
            ruta = os.path.join(current_app.root_path, "last_alert.json")
            data = {
                "titulo": titulo,
                "mensaje": mensaje,
                "fecha": datetime.now(CR_TZ).strftime("%d/%m/%Y %H:%M:%S")
            }
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            # Cero riesgo: si esto falla, no afecta WhatsApp ni el cierre
            pass

    def _enviar_push(self, titulo: str, mensaje: str, url: str = "/notificaciones/alerta"):
        # Envía push a dispositivos suscritos (push_subs.json)
        try:
            ruta = os.path.join(current_app.root_path, "push_subs.json")
            if not os.path.exists(ruta):
                return

            with open(ruta, "r", encoding="utf-8") as f:
                subs = json.load(f) or []

            vapid_private = os.getenv("VAPID_PRIVATE_KEY", "")
            vapid_subject = os.getenv("VAPID_SUBJECT", "mailto:ti@alamo.com")
            if not vapid_private or not subs:
                return

            payload = json.dumps({
                "title": titulo,
                "body": self._push_text(mensaje),
                "url": url
            })

            vivos = []
            for s in subs:
                sub_info = {
                    "endpoint": s["endpoint"],
                    "keys": {"p256dh": s["p256dh"], "auth": s["auth"]}
                }
                try:
                    webpush(
                        subscription_info=sub_info,
                        data=payload,
                        vapid_private_key=vapid_private,
                        vapid_claims={"sub": vapid_subject}
                    )
                    vivos.append(s)
                except WebPushException:
                    # endpoint muerto → no lo guardamos
                    pass

            # Limpieza de endpoints muertos
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(vivos, f, ensure_ascii=False, indent=2)

        except Exception:
            # Cero riesgo: si push falla, no afecta WhatsApp ni el cierre
            pass

    # ======================================================
    # 🟩 FINALIZAR
    # ======================================================

    def finalizar(self):
        """Finaliza un movimiento y, si estaba en emergencia, envía aviso especial."""

        ahora = datetime.now(CR_TZ).replace(tzinfo=None)

        # Detectar si el viaje estaba en emergencia antes de cerrar
        estaba_en_emergencia = False

        # Condición 1: más de 15 minutos en ruta
        if self.estado == "en_ruta" and self.hora_salida:
            minutos = (ahora - self.hora_salida).total_seconds() / 60
            if minutos >= 20:
                estaba_en_emergencia = True

        # Condición 2: tenía alertas enviadas
        if self.ultima_notificacion:
            estaba_en_emergencia = True

        # Finalizar
        self.hora_llegada = ahora
        self.estado = "finalizado"

        # Limpiar controles
        self.ultima_notificacion = None
        self.alerta_orden_enviada = True

        # Enviar notificación solo si estaba en emergencia
        if estaba_en_emergencia:
            duracion_min = int((self.hora_llegada - self.hora_salida).total_seconds() / 60)

            mensaje = (
                f"🟢 *ALERTA RESUELTA*\n"
                f"El viaje que estaba en *EMERGENCIA* ha sido finalizado.\n\n"
                f"📦 Identificador: {self.contenedor}\n"
                f"🚛 Placa: {self.placa.numero_placa}\n"
                f"🎨 Color cabezal: {self.placa.color_cabezal or 'No registrado'}\n"
                f"👤 Chofer: {self.placa.propietario or 'No registrado'}\n"
                f"🕒 Salida: {self.hora_salida.strftime('%d/%m/%Y %H:%M')}\n"
                f"🏁 Llegada: {self.hora_llegada.strftime('%d/%m/%Y %H:%M')}\n"
                f"⏱️ Duración total: {duracion_min} minutos\n\n"
                f"✔ Emergencia cerrada correctamente."
            )

            try:
                # ✅ WhatsApp (igual que siempre)
                enviar_notificacion(mensaje)

                # ✅ NUEVO: Web Push + ver en grande
                self._guardar_ultima_alerta("🟢 Alerta resuelta", mensaje)
                self._enviar_push("🟢 Alerta resuelta", mensaje, url="/notificaciones/alerta")

            except Exception as e:
                print(f"⚠️ Error al enviar notificación de cierre de emergencia: {e}")

    def tiempo_total(self, formato=False):
        if self.hora_llegada:
            total_min = int((self.hora_llegada - self.hora_salida).total_seconds() / 60)
            if formato:
                h, m = divmod(total_min, 60)
                return f"{h}h {m}m"
            return total_min
        return None

    def __repr__(self):
        return f"<Movimiento {self.contenedor} - {self.estado}>"