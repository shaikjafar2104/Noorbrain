const CACHE_NAME = "noorbrain-v126-product-finish-1";

const CORE = [
  "/mobile?v126=1",
  "/studio",
  "/dashboard-static/css/noorbrain-mobile-shell-v126.css?v=20260813-product-finish",
  "/dashboard-static/css/halo-mic-final-fix.css?v=20260813-product-finish",
  "/dashboard-static/css/automation-center-v12.css?v=20260813-full-product",
  "/dashboard-static/js/mobile-rules-v12.js?v=20260813-full-product",
  "/dashboard-static/js/automation-center-v12.js?v=20260813-full-product",
  "/dashboard-static/js/noorbrain-mobile-shell-v126.js?v=20260813-product-finish",
  "/dashboard-static/js/noorbrain-mobile-mount-v126.js?v=20260813-1",
  "/dashboard-static/js/halo-mic-final-fix.js?v=20260813-product-finish"
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
