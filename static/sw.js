self.addEventListener("push", (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch (e) {
    data = { title: "Operación Barco", body: event.data ? event.data.text() : "" };
  }

  const title = data.title || "Operación Barco";
  const body = data.body || "";
  const url = data.url || "/dashboard";

  event.waitUntil(
    self.registration.showNotification(title, {
      body,
      data: { url },
      requireInteraction: true
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();

  const url = event.notification?.data?.url || "/dashboard";

  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if ("focus" in client) return client.focus();
      }
      if (clients.openWindow) return clients.openWindow(url);
    })
  );
});