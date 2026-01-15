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

    // ✅ Android-friendly
    icon: "/static/icons/icon-192.png",
    badge: "/static/icons/badge-72.png",

    vibrate: [200, 100, 200],
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();

  const rawUrl = event.notification?.data?.url || "/notificaciones/alerta";
  const targetUrl = new URL(rawUrl, self.location.origin).toString(); // ✅ absoluta

  event.waitUntil(
    (async () => {
      const allClients = await clients.matchAll({
        type: "window",
        includeUncontrolled: true,
      });

      // Si ya hay una pestaña/ventana abierta del sitio, úsala
      for (const client of allClients) {
        if (client.url.startsWith(self.location.origin)) {
          await client.focus();

          // ✅ Si ya está en esa URL exacta, no navegues (evita "trabas")
          if (client.url !== targetUrl) {
            try {
              await client.navigate(targetUrl);
            } catch (e) {}
          }
          return;
        }
      }

      // Si no hay ninguna, abre una nueva
      await clients.openWindow(targetUrl);
    })()
  );
});