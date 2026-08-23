/* sw.js — Daily panel service worker.
   Tek işi var: Actions'tan gelen web push mesajını bildirime çevirmek ve
   bildirime dokununca paneli açmak. Önbellek/offline işi YOK — panel her
   açılışta güncel JSON okumalı, eski veriyi göstermemeli.

   Kapsam: GitHub Pages'te /panel/ altında yayınlandığı için bu dosya
   /panel/sw.js olarak sunulur ve kapsamı /panel/ olur. */

self.addEventListener('install', e => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));

self.addEventListener('push', event => {
  let d = {};
  try { d = event.data ? event.data.json() : {}; } catch (e) { d = {}; }
  const baslik = d.title || 'Yoklama';
  const secenek = {
    body: d.body || 'Sıra sende.',
    tag: d.tag || 'yoklama',
    renotify: true,
    requireInteraction: !!d.sticky,
    data: { url: d.url || './index.html' }
  };
  event.waitUntil(self.registration.showNotification(baslik, secenek));
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  const hedef = (event.notification.data && event.notification.data.url) || './index.html';
  event.waitUntil((async () => {
    const tam = new URL(hedef, self.registration.scope).href;
    const acik = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    /* Panel zaten açıksa yeni sekme açma, olanı öne getir. */
    for (const c of acik) {
      if (c.url.startsWith(self.registration.scope) && 'focus' in c) return c.focus();
    }
    if (self.clients.openWindow) return self.clients.openWindow(tam);
  })());
});
