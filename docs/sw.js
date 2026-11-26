const prefix = `sage-familia:${self.registration.scope}:`;
const cacheName = prefix + 'v4';
const files = ['./', 'index.html', 'familia.css', 'manifest.webmanifest', 'app.js', 'push-config.js', 'push-firebase.js',
  'icone-192.png', 'icone-512.png', 'acolhimento.md', 'acolhimento.json', 'editorial.md', 'perfis.json', 'atualizacoes.json',
  'caderno-duhuman.html', 'biblioteca.html', 'biblioteca.json', 'retratos/sage.webp', 'retratos/rodrigo.webp', 'retratos/pabblo.webp'];
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
  const page = new URL(request.url);
  page.hash = '';
  if (request.method !== 'GET' || !cachedUrls.has(page.href)) return;
  event.respondWith((async () => {
    const cache = await caches.open(cacheName);
    try {
      const response = await fetch(request);
      if (response.ok) await cache.put(page.href, response.clone());
      return response;
    } catch {
      return (await cache.match(page.href)) || Response.error();
    }
  })());
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil(self.clients.openWindow(new URL('./#atualizacoes', self.registration.scope).href));
});

self.addEventListener('push', event => {
  let data;
  try { data = event.data?.json()?.data; } catch { return; }
  if (data?.tipo !== 'sage-atualizacao' || typeof data.id !== 'string' ||
      typeof data.titulo !== 'string' || typeof data.resumo !== 'string') return;
  event.waitUntil(self.registration.showNotification(data.titulo, {
    body: data.resumo,
    icon: new URL('icone-192.png', self.registration.scope).href,
    tag: data.id,
  }));
});
