self.addEventListener("push", function (event) {
  let data = {};
  try { data = event.data.json(); } catch(e) {}

  const title = data.title || "Operación Barco";
  const body = data.body || "Nueva notificación";

  event.waitUntil(
    self.registration.showNotification(title, {
      body,
      icon: "/static/LogoAlamo.jpg"
    })
  );
});