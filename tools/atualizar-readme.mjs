import { readFile, writeFile } from 'node:fs/promises';

const root = new URL('../', import.meta.url);
const readme = new URL('README.md', root);
const current = (await readFile(readme, 'utf8')).replaceAll('\r\n', '\n');
const news = JSON.parse(await readFile(new URL('docs/atualizacoes.json', root), 'utf8'));
const begin = '<!-- inicio-atualizacao-pwa -->';
const end = '<!-- fim-atualizacao-pwa -->';

function plain(text, max) {
  if (typeof text !== 'string' || !text.trim() || text.length > max || /[\r\n]/.test(text)) {
    throw new Error('A atualização deve ter título e resumo em texto simples.');
  }
  return text.trim().replace(/[\\`*_{}[\]<>()#+.!|>~-]/g, '\\$&');
}

const generated = [
  begin,
  '## Última atualização do PWA',
  '',
  '**' + plain(news.titulo, 120) + '**',
  '',
  plain(news.resumo, 300),
  '',
  '[Ver atualizações no site](https://dueuler.github.io/Sage-duEuler/#atualizacoes)',
  end,
].join('\n');

const start = current.indexOf(begin);
const finish = current.indexOf(end);
if (start < 0 || finish < start || current.indexOf(begin, start + begin.length) !== -1 ||
    current.indexOf(end, finish + end.length) !== -1) throw new Error('Bloco de atualização ausente ou duplicado.');
const updated = current.slice(0, start) + generated + current.slice(finish + end.length);
if (process.argv.includes('--check')) {
  if (current !== updated) throw new Error('Atualize o README com node tools/atualizar-readme.mjs.');
} else if (current !== updated) {
  await writeFile(readme, updated);
}
