const prefix = `sage-familia:${self.registration.scope}:`;
const cacheName = prefix + 'v1';
const files = ['./', 'index.html', 'familia.css', 'manifest.webmanifest', 'app.js',
  'icone-192.png', 'icone-512.png', 'acolhimento.md', 'acolhimento.json', 'editorial.md', 'perfis.json', 'atualizacoes.json'];
const cachedUrls = new Set(files.map(file => new URL(file, self.registration.scope).href));

self.addEventListener('install', event => {
  event.waitUntil(caches.open(cacheName).then(cache => cache.addAll(files)));
});

self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    await Promise.all((await caches.keys()).filter(key => key.startsWith(prefix) && key !== cacheName)
      .map(key => caches.delete(key)));
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', event => {
  const { request } = event;
  if (request.method !== 'GET' || !cachedUrls.has(request.url)) return;
  event.respondWith((async () => {
    const cache = await caches.open(cacheName);
    try {
      const response = await fetch(request);
      if (response.ok) await cache.put(request, response.clone());
      return response;
    } catch {
      return (await cache.match(request)) || Response.error();
    }
  })());
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil(self.clients.openWindow(new URL('./#atualizacoes', self.registration.scope).href));
});
