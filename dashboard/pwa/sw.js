const CACHE_NAME = "noorbrain-halo-mic-final-v3";

const CORE = [
  "/mobile",
  "/studio",
  "/dashboard-static/js/halo-mic-final-fix.js?v=20260729-4",
  "/dashboard-static/css/halo-mic-final-fix.css?v=20260729-4"
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

self.addEventListener("install", event => {
  event.waitUntil(caches.open("noorbrain-sprint8c2-startup-silence-v1")
    .then(cache => cache.add("/dashboard-static/js/sprint8c-voice-repeat-guard.js?v=20260801-2")));
});
