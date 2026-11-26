const button = document.querySelector('#avisos');
const status = document.querySelector('#estado-avisos');
const storageKey = 'sage-familia-ultima-atualizacao';
let watching = false;
let pushEnabled = false;

if ('serviceWorker' in navigator && /^https?:$/.test(location.protocol)) {
  navigator.serviceWorker.register('sw.js').then(() => {
    if (!('Notification' in window)) return;
    button.hidden = false;
    void configurePush().catch(() => {});
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
  if (pushEnabled) return;
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

async function configurePush() {
  const { vapidKey } = await import('./push-config.js');
  if (!vapidKey || !('PushManager' in window)) return;
  const key = 'sage-familia-push-inscrito';
  const toggle = document.querySelector('#push');
  const feedback = document.querySelector('#estado-push');
  let subscribed = localStorage.getItem(key) === 'sim';
  const render = () => {
    toggle.hidden = false;
    toggle.textContent = subscribed ? 'Desativar notificações push' : 'Ativar notificações push';
    if (subscribed) button.hidden = true;
  };
  pushEnabled = subscribed;
  render();
  toggle.addEventListener('click', async () => {
    toggle.disabled = true;
    try {
      if (!subscribed && await Notification.requestPermission() !== 'granted') {
        feedback.textContent = 'Libere as notificações nas permissões do navegador para ativar o push.';
        return;
      }
      const push = await import('./push-firebase.js');
      if (subscribed) {
        await push.unsubscribe();
        localStorage.removeItem(key);
        feedback.textContent = 'Notificações push desativadas.';
      } else {
        await push.subscribe();
        localStorage.setItem(key, 'sim');
        feedback.textContent = 'Inscrição concluída. Novidades podem chegar com a página fechada.';
      }
      subscribed = !subscribed;
      pushEnabled = subscribed;
      button.hidden = subscribed;
      render();
    } catch {
      feedback.textContent = 'Não foi possível alterar a inscrição. Tente novamente com internet.';
    } finally {
      toggle.disabled = false;
    }
  });
  if (subscribed) {
    const push = await import('./push-firebase.js');
    if (Notification.permission === 'granted') await push.subscribe();
    else {
      await push.unsubscribe();
      localStorage.removeItem(key);
      pushEnabled = subscribed = false;
      button.hidden = false;
      render();
    }
  }
}
