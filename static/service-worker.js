const CACHE_NAME = "hospital-celular-pwa-v5";
const STATIC_ASSETS = [
  "/",
  "/app/static/manifest.json",
  "/app/static/manifest.json?v=tx-icon-v5",
  "/app/static/favicon.png",
  "/app/static/favicon.png?v=tx-icon-v5",
  "/app/static/apple-touch-icon.png",
  "/app/static/apple-touch-icon.png?v=tx-icon-v5",
  "/app/static/apple-touch-icon-precomposed.png",
  "/app/static/apple-touch-icon-precomposed.png?v=tx-icon-v5",
  "/app/static/icon-192.png",
  "/app/static/icon-192.png?v=tx-icon-v5",
  "/app/static/icon-512.png",
  "/app/static/icon-512.png?v=tx-icon-v5"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS).catch(() => null))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") {
    return;
  }

  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
});
