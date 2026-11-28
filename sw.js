/* ==============================================================================
   GUARDIAN ANGEL™ — NETWORK-FIRST PWA SERVICE WORKER (v3.2.1)
   Always serves fresh online HTML/CSS/JS while keeping full offline fallback.
   ============================================================================== */

const CACHE_NAME = 'guardian-angel-v3.2.3';
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/guardian.html',
  '/guardian_mobile.html',
  '/guardian_angel_app.html',
  '/app.css?v=3.2.3',
  '/config.js?v=3.2.3',
  '/manifest.webmanifest'
];

// 1. Install & Pre-cache Fresh App Shell
self.addEventListener('install', event => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS)).catch(() => {})
  );
});

// 2. Activate & Purge All Legacy Cache-First Caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

// 3. Fetch Strategy: Network-First for All GET Requests, Cache Fallback Offline
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;

  event.respondWith(
    fetch(event.request)
      .then(networkResp => {
        if (networkResp && networkResp.status === 200 && networkResp.type === 'basic') {
          const respToCache = networkResp.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, respToCache));
        }
        return networkResp;
      })
      .catch(() => caches.match(event.request))
  );
});

// 4. Web Push Notification Listener (Family Alerts)
self.addEventListener('push', event => {
  let data = { title: 'Guardian Angel Alert', body: 'Suspicious activity blocked.' };
  try {
    data = event.data.json();
  } catch (e) {
    data.body = event.data ? event.data.text() : data.body;
  }

  const options = {
    body: data.body,
    icon: '/manifest.webmanifest',
    badge: '/manifest.webmanifest',
    vibrate: [200, 100, 200, 100, 200],
    data: { url: '/guardian_mobile.html' }
  };

  event.waitUntil(self.registration.showNotification(data.title, options));
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil(
    clients.matchAll({ type: 'window' }).then(clientList => {
      for (const client of clientList) {
        if (client.url.includes('guardian_mobile.html') && 'focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) return clients.openWindow('/guardian_mobile.html');
    })
  );
});
