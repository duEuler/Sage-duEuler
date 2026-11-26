import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';

const project = 'lutandopelahumanidade';
const firestore = `https://firestore.googleapis.com/v1/projects/${project}/databases/(default)/documents`;
const fcm = `https://fcm.googleapis.com/v1/projects/${project}/messages:send`;
const strings = fields => Object.fromEntries(Object.entries(fields).map(([key, value]) => [key, { stringValue: value }]));
const digest = value => createHash('sha256').update(value).digest('hex');

export async function publish(news, credential, request = fetch) {
  if (!/^[a-z0-9-]{1,80}$/.test(news?.id ?? '') || typeof news.titulo !== 'string' ||
      !news.titulo.trim() || news.titulo.length > 120 || typeof news.resumo !== 'string' || news.resumo.length > 300)
    throw new Error('EDICAO_INVALIDA');
  if (!credential) throw new Error('CREDENCIAL_DO_EMISSOR_AUSENTE');
  const headers = { Authorization: `Bearer ${credential}`, 'Content-Type': 'application/json' };
  const call = async (url, method = 'GET', body) => {
    const response = await request(url, { method, headers, body: body === undefined ? undefined : JSON.stringify(body),
      redirect: 'error', signal: AbortSignal.timeout(15000) });
    return { status: response.status, body: await response.json().catch(() => ({})) };
  };
  const read = async url => {
    const result = await call(url);
    if (result.status === 404) return null;
    if (result.status !== 200) throw new Error(`FIRESTORE_LEITURA_${result.status}`);
    return result.body;
  };
  const write = async (url, fields) => {
    const result = await call(url, 'PATCH', { fields: strings(fields) });
    if (result.status !== 200) throw new Error(`FIRESTORE_GRAVACAO_${result.status}`);
  };
  const edition = `${firestore}/sagePushCampaigns/${news.id}`;
  if (await read(edition)) return { status: 'already-sent' };
  let pageToken = '';
  const result = { status: 'sent', accepted: 0, expired: 0, skipped: 0, failed: 0 };
  do {
    const query = new URLSearchParams({ pageSize: '100' });
    if (pageToken) query.set('pageToken', pageToken);
    const list = await read(`${firestore}/sagePushSubscriptions?${query}`);
    for (const subscription of list?.documents ?? []) {
      const id = subscription.name.split('/').at(-1);
      const token = subscription.fields?.token?.stringValue;
      if (!token) { result.skipped++; continue; }
      const receipt = `${firestore}/sagePushReceipts/${digest(`${news.id}:${id}:${token}`)}`;
      if (await read(receipt)) { result.skipped++; continue; }
      const send = await call(fcm, 'POST', { message: { token, data: {
        tipo: 'sage-atualizacao', id: news.id, titulo: news.titulo, resumo: news.resumo,
      }, webpush: { headers: { TTL: '86400' } } } });
      if (send.status === 200) {
        await write(receipt, { edition: news.id, outcome: 'accepted' });
        result.accepted++;
      } else if (send.body.error?.details?.some(detail => detail.errorCode === 'UNREGISTERED')) {
        if (subscription.updateTime) {
          const condition = new URLSearchParams({ 'currentDocument.updateTime': subscription.updateTime });
          const removal = await call(`${firestore}/sagePushSubscriptions/${encodeURIComponent(id)}?${condition}`, 'DELETE');
          if (![200, 404, 409, 412].includes(removal.status)) { result.failed++; continue; }
        }
        result.expired++;
      } else {
        result.failed++;
      }
    }
    pageToken = list?.nextPageToken ?? '';
  } while (pageToken);
  if (result.failed) throw new Error(`FCM_ENTREGAS_PENDENTES_${result.failed}`);
  await write(edition, { id: news.id, outcome: 'completed' });
  return result;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  try {
    const news = JSON.parse(await readFile(new URL('../docs/atualizacoes.json', import.meta.url), 'utf8'));
    console.log(JSON.stringify(await publish(news, process.env.FIREBASE_PUSH_ACCESS_TOKEN)));
  } catch (error) {
    console.error(error instanceof Error && /^[A-Z0-9_]+$/.test(error.message) ? error.message : 'ENVIO_PUSH_FALHOU');
    process.exitCode = 1;
  }
}
