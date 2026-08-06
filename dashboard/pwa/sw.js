const CACHE_NAME = "noorbrain-production-v16-1";

const CORE = [
  "/mobile",
  "/studio",
  "/dashboard-static/js/electronic-voice-off.js?v=20260802-16",
  "/dashboard-static/js/unified-product-ui.js?v=20260802-16",
  "/dashboard-static/js/dashboard-camera-controls-v16.js?v=20260802-162",
  "/dashboard-static/css/production-mobile-v16.css?v=20260802-162"
];

self.addEventListener("install", event => {
  self.skipWaiting();

  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(CORE))
      .catch(() => undefined)
  );
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys()
      .then(keys =>
        Promise.all(
          keys
            .filter(key => key !== CACHE_NAME)
            .map(key => caches.delete(key))
        )
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", event => {
  const request = event.request;
  const url = new URL(request.url);

  if (request.method !== "GET") {
    return;
  }

  if (
    url.pathname.startsWith("/api/")
    || url.pathname === "/halo"
  ) {
    event.respondWith(fetch(request));
    return;
  }

  if (
    url.pathname.endsWith(".js")
    || url.pathname.endsWith(".css")
    || url.pathname === "/studio"
    || url.pathname === "/mobile"
  ) {
    event.respondWith(
      fetch(request, { cache: "no-store" })
        .then(response => {
          const copy = response.clone();
          caches.open(CACHE_NAME)
            .then(cache => cache.put(request, copy));
          return response;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  event.respondWith(
    caches.match(request)
      .then(cached => cached || fetch(request))
  );
});
