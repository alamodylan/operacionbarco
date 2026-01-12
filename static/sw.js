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
    tag: "operacionbarco-alert",
    renotify: true
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

// ✅ Esto hace que al tocar ABRA la alerta grande
self.addEventListener("notificationclick", (event) => {
  event.notification.close();

  const url = event.notification?.data?.url || "/notificaciones/alerta";

  event.waitUntil((async () => {
    const allClients = await clients.matchAll({ type: "window", includeUncontrolled: true });

    // Si ya hay una pestaña abierta del sistema, la enfocamos y navegamos
    for (const client of allClients) {
      if (client.url.startsWith(self.location.origin)) {
        await client.focus();
        try { await client.navigate(url); } catch (e) {}
        return;
      }
    }

    // Si no hay pestaña, abrimos una nueva
    await clients.openWindow(url);
  })());
});