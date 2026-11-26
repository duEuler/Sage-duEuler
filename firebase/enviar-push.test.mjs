import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { runInNewContext } from 'node:vm';
import { publish } from './enviar-push.mjs';

const news = { id: 'conto-2', titulo: 'Crônica nova', resumo: 'Uma nova história.' };

test('retenta apenas quem falhou e não reenvia uma edição concluída', async () => {
  const tokenFields = token => ({ fields: { token: { stringValue: token } } });
  const recipients = [
    { name: 'subscriptions/a', ...tokenFields('a') },
    { name: 'subscriptions/b', ...tokenFields('b') },
    { name: 'subscriptions/c', ...tokenFields('c'), updateTime: '2026-11-26T00:00:00Z' },
  ];
  const saved = new Map();
  const sent = [];
  let fail = true;
  const request = async (url, { method, body }) => {
    if (url.includes('messages:send')) {
      const message = JSON.parse(body).message;
      assert.equal(message.data.id, news.id);
      assert.equal(message.notification, undefined);
      sent.push(message.token);
      if (message.token === 'c') return Response.json({ error: { details: [{ errorCode: 'UNREGISTERED' }] } }, { status: 404 });
      if (message.token === 'b' && fail) return Response.json({}, { status: 503 });
      return Response.json({ name: 'mock-delivery' });
    }
    if (method === 'DELETE') {
      assert(new URL(url).searchParams.has('currentDocument.updateTime'));
      recipients.splice(2, 1);
      return Response.json({});
    }
    if (url.includes('sagePushSubscriptions?')) return Response.json({ documents: recipients });
    if (method === 'PATCH') {
      saved.set(url, JSON.parse(body));
      return Response.json({});
    }
    return saved.has(url) ? Response.json(saved.get(url)) : Response.json({}, { status: 404 });
  };
  await assert.rejects(publish(news, 'mock', request), /FCM_ENTREGAS_PENDENTES_1/);
  fail = false;
  assert.deepEqual(await publish(news, 'mock', request), { status: 'sent', accepted: 1, expired: 0, skipped: 1, failed: 0 });
  assert.deepEqual(await publish(news, 'mock', request), { status: 'already-sent' });
  assert.deepEqual(sent, ['a', 'b', 'c', 'b']);
  await assert.rejects(publish({ ...news, id: '../fora' }, 'mock'), /EDICAO_INVALIDA/);
});

test('o worker recebe dados em segundo plano sem depender de uma página', async () => {
  const script = await readFile(new URL('../docs/sw.js', import.meta.url), 'utf8');
  const handlers = {};
  const notices = [];
  runInNewContext(script, {
    URL,
    self: {
      registration: {
        scope: 'https://dueuler.github.io/Sage-duEuler/',
        showNotification(title, options) { notices.push({ title, tag: options.tag }); return Promise.resolve(); },
      },
      addEventListener(name, handler) { handlers[name] = handler; },
    },
  });
  const payload = data => ({ data: { json: () => ({ data }) }, waitUntil: promise => promise });
  await handlers.push(payload({ tipo: 'outro' }));
  await handlers.push(payload({ ...news, tipo: 'sage-atualizacao' }));
  assert.deepEqual(notices, [{ title: 'Crônica nova', tag: 'conto-2' }]);
});
