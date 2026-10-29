'use strict';
const CACHE_PREFIX = 'ollama-benchmark-static-';
const CACHE_NAME = CACHE_PREFIX + 'v1';
// Only public resources belong here: never add /, /api/* or benchmark data.
const PUBLIC_ASSETS = [
  '/offline.html', '/style.css', '/manifest.webmanifest',
  '/icons/icon.svg', '/icons/icon-192.png', '/icons/icon-512.png',
  '/icons/maskable-512.png', '/icons/apple-touch-icon.png'
];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(PUBLIC_ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(
    keys.filter(key => key.startsWith(CACHE_PREFIX) && key !== CACHE_NAME).map(key => caches.delete(key))
  )).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin) return;
  if (request.mode === 'navigate' && url.pathname === '/') {
    // Main HTML contains the session token. Fetch it without persisting it.
    event.respondWith(fetch(request).catch(() => caches.match('/offline.html')));
    return;
  }
  if (url.search || !PUBLIC_ASSETS.includes(url.pathname)) return;
  event.respondWith(fetch(request).catch(() => caches.match(url.pathname)));
});
