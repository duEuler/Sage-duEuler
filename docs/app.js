const button = document.querySelector('#avisos');
const status = document.querySelector('#estado-avisos');
const storageKey = 'sage-familia-ultima-atualizacao';
let watching = false;

if ('serviceWorker' in navigator && /^https?:$/.test(location.protocol)) {
  navigator.serviceWorker.register('sw.js').then(() => {
    if (!('Notification' in window)) return;
    button.hidden = false;
    button.addEventListener('click', async () => {
      const permission = await Notification.requestPermission();
      if (permission === 'granted') {
        await checkUpdates({ initialize: true });
        watchUpdates();
        status.textContent = 'Avisos ativados. O app verifica novidades enquanto está aberto.';
      } else {
        status.textContent = 'Os avisos podem ser liberados nas permissões do navegador.';
      }
    });

    if (Notification.permission === 'granted') {
      void checkUpdates();
      watchUpdates();
    }
  }).catch(() => {
    status.textContent = 'A leitura offline não pôde ser ativada neste navegador.';
  });
}

function watchUpdates() {
  if (watching) return;
  watching = true;
  window.addEventListener('focus', () => void checkUpdates());
  setInterval(() => {
    if (document.visibilityState === 'visible') void checkUpdates();
  }, 5 * 60 * 1000);
}

async function checkUpdates({ initialize = false } = {}) {
  try {
    const response = await fetch('atualizacoes.json', { cache: 'no-cache' });
    if (!response.ok) return;
    const news = await response.json();
    if (typeof news.id !== 'string' || typeof news.titulo !== 'string' || typeof news.resumo !== 'string') return;
    const previous = localStorage.getItem(storageKey);
    if (!initialize && previous && previous !== news.id) {
      const registration = await navigator.serviceWorker.ready;
      await registration.showNotification(news.titulo, {
        body: news.resumo,
        icon: 'icone-192.png',
        tag: news.id,
      });
    }
    localStorage.setItem(storageKey, news.id);
  } catch {
    // A próxima abertura tenta de novo se a rede ou o armazenamento estiver indisponível.
  }
}
