const CACHE_NAME = 'yamtrack-v2';
const OFFLINE_URL = '/offline';

// App shell assets that are safe to serve from cache first.
const PRECACHE_URLS = [
  '/static/css/main.css',
  '/static/favicon/android-chrome-192x192.png',
  '/static/favicon/android-chrome-512x512.png',
  '/static/fonts/roboto-flex.woff2',
  OFFLINE_URL,
];

// Install: pre-cache the app shell. Don't fail the whole install if a single
// optional asset is missing (e.g. the offline page on older deployments).
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) =>
      Promise.allSettled(PRECACHE_URLS.map((url) => cache.add(url)))
    )
  );
  self.skipWaiting();
});

// Activate: drop old caches and take control of open clients immediately.
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) =>
      Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      )
    ).then(() => self.clients.claim())
  );
});

function isStaticAsset(url) {
  return url.pathname.startsWith('/static/');
}

self.addEventListener('fetch', (event) => {
  const { request } = event;

  // Only deal with GET; let the browser handle POST/PUT/etc. directly so we
  // never interfere with tracking updates, logins or CSRF-protected actions.
  if (request.method !== 'GET') {
    return;
  }

  const url = new URL(request.url);

  // Ignore cross-origin requests (TMDB images, provider logos, CDN screenshots).
  if (url.origin !== self.location.origin) {
    return;
  }

  // Static assets: cache-first with background revalidation (stale-while-revalidate).
  if (isStaticAsset(url)) {
    event.respondWith(
      caches.open(CACHE_NAME).then((cache) =>
        cache.match(request).then((cached) => {
          const network = fetch(request)
            .then((response) => {
              if (response && response.ok) {
                cache.put(request, response.clone());
              }
              return response;
            })
            .catch(() => cached);
          return cached || network;
        })
      )
    );
    return;
  }

  // Navigations / HTML: network-first so tracked data is always fresh, with a
  // cached fallback (and finally the offline page) when the network is down.
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
          return response;
        })
        .catch(() =>
          caches.match(request).then((cached) => cached || caches.match(OFFLINE_URL))
        )
    );
    return;
  }

  // Everything else same-origin (JSON partials, etc.): network-first, fall back
  // to cache only if we happen to have it.
  event.respondWith(
    fetch(request).catch(() => caches.match(request))
  );
});
