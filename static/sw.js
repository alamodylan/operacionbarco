self.addEventListener("push", (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch (e) {
    data = {};
  }

  const title = data.title || "Operación Barco";
  const body = data.body || "Nueva alerta";
  const url = data.url || "/notificaciones/alerta";

  const options = {
    body,
    data: { url },

    // ✅ Android-friendly: icono/badge ayudan a que se vea más “serio”
    icon: "/static/icons/icon-192.png",
    badge: "/static/icons/badge-72.png",

    // ✅ Vibra (si el dispositivo lo permite y el canal lo deja)
    vibrate: [200, 100, 200],

    // ✅ Cada push separada (NO tag fijo)
    // requireInteraction: true // en Android suele ignorarse, lo dejo comentado
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();

  const url = event.notification?.data?.url || "/notificaciones/alerta";

  event.waitUntil((async () => {
    const allClients = await clients.matchAll({ type: "window", includeUncontrolled: true });

    for (const client of allClients) {
      if (client.url.startsWith(self.location.origin)) {
        await client.focus();
        try { await client.navigate(url); } catch (e) {}
        return;
      }
    }

    await clients.openWindow(url);
  })());
});