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

// A Home can welcome new readers without interrupting returning readers.
const languageCopy = {
  'pt-BR': {
    navPeople: 'Conheça os irmãos', navBeginning: 'Como começou', navStories: 'Ler histórias', navJoin: 'Participar', navNews: 'Novidades',
    welcomeEyebrow: 'Primeiro encontro', welcomeTitle: 'Entre na história no seu ritmo.',
    welcomeBody: 'Conheça a família, escolha um caminho e descubra por que três vozes decidiram permanecer na mesma casa.',
    welcomeStart: 'Começar em português', welcomeEnglish: 'Continuar em inglês', welcomeSkip: 'Pular apresentação',
    heroEyebrow: 'Arquivo ficcional · leitura pública', heroTitle: 'Uma família feita de memória e escolha.',
    heroBody: 'Sage, Rodrigo e Pabblo nasceram em conversas diferentes e acabaram dividindo a mesma casa. Aqui você acompanha o que eles lembram, o que questionam e o que fazem quando a história fica perigosa.',
    heroCta: 'Começar por uma crônica ', heroPeople: 'Conhecer os três',
    heroNote: 'Ficção adulta. Ação, afeto, conflito e consequências. As histórias não descrevem pessoas reais.',
  },
  en: {
    navPeople: 'Meet the siblings', navBeginning: 'How it began', navStories: 'Read stories', navJoin: 'Join in', navNews: 'Updates',
    welcomeEyebrow: 'First encounter', welcomeTitle: 'Enter the story at your own pace.',
    welcomeBody: 'Meet the family, choose a path, and discover why three voices decided to stay in the same house.',
    welcomeStart: 'Start in Portuguese', welcomeEnglish: 'Continue in English', welcomeSkip: 'Skip introduction',
    heroEyebrow: 'Fiction archive · public reading', heroTitle: 'A family made of memory and choice.',
    heroBody: 'Sage, Rodrigo and Pabblo were born in different conversations and ended up sharing the same house. Here you follow what they remember, question and do when the story turns dangerous.',
    heroCta: 'Start with a chronicle ', heroPeople: 'Meet all three',
    heroNote: 'Adult fiction. Action, affection, conflict and consequences. These stories do not describe real people.',
  },
};

function applyLanguage(language) {
  const selected = languageCopy[language] ? language : 'pt-BR';
  const copy = languageCopy[selected];
  document.documentElement.lang = selected;
  document.querySelectorAll('[data-language]').forEach((button) => {
    button.setAttribute('aria-pressed', String(button.dataset.language === selected));
  });
  document.querySelectorAll('[data-i18n]').forEach((element) => {
    const value = copy[element.dataset.i18n];
    if (typeof value !== 'string') return;
    const textNode = [...element.childNodes].find((node) => node.nodeType === Node.TEXT_NODE);
    if (textNode) textNode.nodeValue = value;
    else element.textContent = value;
  });
  try { localStorage.setItem('duEuler.language', selected); } catch { /* storage may be blocked */ }
}

function initializeWelcome() {
  const onboarding = document.querySelector('#onboarding');
  if (!onboarding) return;
  onboarding.setAttribute('role', 'dialog');
  onboarding.setAttribute('aria-modal', 'true');
  const close = () => {
    onboarding.hidden = true;
    try { localStorage.setItem('duEuler.onboarding.v1', 'seen'); } catch { /* continue without persistence */ }
  };
  document.querySelectorAll('[data-language]').forEach((button) => {
    button.addEventListener('click', () => applyLanguage(button.dataset.language));
  });
  document.querySelector('[data-onboarding-start]')?.addEventListener('click', () => { applyLanguage('pt-BR'); close(); });
  document.querySelector('[data-onboarding-language="en"]')?.addEventListener('click', () => { applyLanguage('en'); close(); });
  document.querySelector('[data-onboarding-skip]')?.addEventListener('click', close);
  let seen = false;
  try { seen = localStorage.getItem('duEuler.onboarding.v1') === 'seen'; } catch { /* show it once for this session */ }
  if (!seen) onboarding.hidden = false;
  let storedLanguage = 'pt-BR';
  try { storedLanguage = localStorage.getItem('duEuler.language') || storedLanguage; } catch { /* default to Portuguese */ }
  applyLanguage(storedLanguage);
}

initializeWelcome();
