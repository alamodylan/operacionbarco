// static/js/main.js

document.addEventListener("DOMContentLoaded", () => {
  console.log("🚢 Aplicación Operación Barco iniciada correctamente.");

  // Ejemplo: alerta pasiva si pasan 15 minutos sin actividad
  let startTime = Date.now();

  // Resetea el temporizador si hay interacción del usuario
  const resetTimer = () => (startTime = Date.now());
  ["click", "keydown", "mousemove"].forEach(evt =>
    document.addEventListener(evt, resetTimer)
  );

  // Revisión cada minuto
  setInterval(() => {
    const diffMinutes = Math.floor((Date.now() - startTime) / 60000);
    if (diffMinutes === 15) {
      mostrarAviso(
        "⚠️ Han pasado 15 minutos sin actividad. Verifica tus operaciones en curso."
      );
    }
  }, 60000);
});

// === Función auxiliar ===
function mostrarAviso(mensaje) {
  // Prefiere una notificación no intrusiva en vez de alert()
  const alerta = document.createElement("div");
  alerta.className =
    "alert alert-warning position-fixed bottom-0 end-0 m-3 shadow";
  alerta.style.zIndex = "2000";
  alerta.textContent = mensaje;
  document.body.appendChild(alerta);
  setTimeout(() => alerta.remove(), 10000);
}
