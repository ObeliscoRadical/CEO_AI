self.addEventListener('push', (event) => {
  let data = { title: 'CEO AI', body: '', url: '/' };
  try { data = event.data ? event.data.json() : data; } catch (e) {}
  event.waitUntil(
    self.registration.showNotification(data.title || 'CEO AI', {
      body: data.body || '',
      icon: '/logo192.png',
      badge: '/logo192.png',
      data: { url: data.url || '/' },
    })
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || '/';
  event.waitUntil(clients.openWindow(url));
});
