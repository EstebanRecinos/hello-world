/* ORBITA-LINK service worker.
   Estrategia honesta:
   - Shell y assets estáticos: cache-first con actualización en segundo plano
     (la app abre sin conexión).
   - API: siempre red. El estado offline del tracking lo maneja la propia app
     (guarda el último estado conocido y lo muestra con un aviso con hora);
     las escrituras requieren conexión y lo dicen — sin colas engañosas. */

const CACHE = "orbita-shell-v1";
const SHELL = [
  "/",
  "/index.html",
  "/tokens.css",
  "/styles.css",
  "/app.js",
  "/manifest.json",
  "/img/logo.svg",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  if (url.pathname.startsWith("/api/")) return; // la API nunca se sirve de cache

  e.respondWith(
    caches.match(e.request, { ignoreSearch: url.pathname === "/" }).then((cached) => {
      const fresh = fetch(e.request)
        .then((resp) => {
          if (resp.ok) {
            const copy = resp.clone();
            caches.open(CACHE).then((c) => c.put(e.request, copy));
          }
          return resp;
        })
        .catch(() => cached);
      return cached || fresh;
    })
  );
});
