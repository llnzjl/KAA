const CACHE = 'kaa-public-v8:' + self.registration.scope;
const FILES = ['./', 'app.js?v=8', 'styles.css?v=8', 'phone.css?v=8', 'logo.svg',
  'manifest.json', 'api/content', 'locales/en.json', 'locales/ko.json',
  'locales/fa.json', 'locales/ps.json', 'locales/ur.json', 'locales/hi.json',
  'locales/zh.json', 'locales/vi.json', 'locales/tl.json', 'locales/ja.json'];
const urls = FILES.map(path => new URL(path, self.registration.scope).href);
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(urls)));
  self.skipWaiting();
});
self.addEventListener('activate', event => event.waitUntil(
  caches.keys().then(keys => Promise.all(keys.filter(key =>
    key.startsWith('kaa-public-') && key !== CACHE &&
    (key.endsWith(':' + self.registration.scope) || /^kaa-public-v\d+$/.test(key))
  ).map(key => caches.delete(key)))).then(() => self.clients.claim())
));
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  url.hash = '';
  if (event.request.method !== 'GET' || !urls.includes(url.href)) return;
  event.respondWith(fetch(event.request).then(response => {
    if (response.ok) {
      const copy = response.clone();
      event.waitUntil(caches.open(CACHE).then(cache => cache.put(event.request, copy)));
    }
    return response;
  }).catch(() => caches.match(event.request)));
});
