async function activarNotificaciones() {
  try {
    if (!("serviceWorker" in navigator)) {
      alert("Este navegador no soporta notificaciones");
      return;
    }

    const permiso = await Notification.requestPermission();
    if (permiso !== "granted") {
      alert("No se permitieron las notificaciones");
      return;
    }

    const registro = await navigator.serviceWorker.register("/static/sw.js");

    if (!window.VAPID_PUBLIC_KEY || window.VAPID_PUBLIC_KEY.length < 20) {
      alert("Falta configurar la clave VAPID pública (siguiente paso).");
      return;
    }

    const sub = await registro.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(window.VAPID_PUBLIC_KEY)
    });

    const res = await fetch("/notificaciones/api/push/subscribe", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(sub)
    });

    if (res.ok) alert("✅ Notificaciones activadas");
    else alert("❌ No se pudo guardar la suscripción");
  } catch (e) {
    console.error(e);
    alert("Error activando notificaciones");
  }
}

// Solo para probar que el botón funciona (por ahora NO manda push real, eso viene después)
async function probarNotificacion() {
  alert("🧪 Botón OK. La prueba real viene cuando configuremos VAPID + backend.");
}

function urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) outputArray[i] = rawData.charCodeAt(i);
  return outputArray;
}