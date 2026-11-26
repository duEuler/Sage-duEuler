import { readFile, writeFile } from 'node:fs/promises';

const origin = new URL('../', import.meta.url);
const repository = 'https://github.com/duEuler/Sage-duEuler';
const entries = [
  ['sage', 'Sage', 'sage_dueuler_manifesto.md'],
  ['rodrigo', 'Rodrigo', 'irmaos/Rodrigo_Magalhaes/manifesto_rodrigo_magalhaes.md'],
  ['certidao', 'Rodrigo', 'irmaos/Rodrigo_Magalhaes/certidao_de_nascimento.md'],
  ['carta', 'Rodrigo', 'irmaos/Rodrigo_Magalhaes/carta_para_sage.md'],
  ['pabblo', 'Pabblo', 'irmaos/Pabblo_EEscobar/manifesto.md'],
  ['tres-copos', 'Pabblo', 'irmaos/Pabblo_EEscobar/a_noite_dos_tres_copos.md'],
  ['sino', 'Pabblo', 'irmaos/Pabblo_EEscobar/conto_o_sino_da_praca.md'],
];

function escapeHtml(text) {
  return text.replace(/[&<>"']/g, character => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  })[character]);
}

function inline(text) {
  return escapeHtml(text)
    .replace(/\[([^\]]+)\]\((https:\/\/[^\s)]+)\)/g, '<a href="$2">$1</a>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>');
}

function render(markdown) {
  return markdown.trim().split(/\n\s*\n/).map(block => {
    const lines = block.trim().split('\n');
    if (/^---+$/.test(block.trim())) return '<hr>';
    if (lines[0].startsWith('```') && lines.at(-1).startsWith('```'))
      return '<pre><code>' + escapeHtml(lines.slice(1,-1).join('\n')) + '</code></pre>';
    if (lines.length === 1 && /^#{1,5} /.test(lines[0]))
      return '<h3>' + inline(lines[0].replace(/^#+ /, '')) + '</h3>';
    if (lines.every(line => /^[-*] /.test(line)))
      return '<ul>' + lines.map(line => '<li>' + inline(line.slice(2)) + '</li>').join('') + '</ul>';
    if (lines.every(line => /^>\s?/.test(line)))
      return '<blockquote>' + lines.map(line => inline(line.replace(/^>\s?/, ''))).join('<br>') + '</blockquote>';
    return '<p>' + lines.map(line => inline(line.trim())).join('<br>') + '</p>';
  }).join('\n');
}

const items = [];
const articles = [];
for (const [id, personagem, path] of entries) {
  let content = (await readFile(new URL(path, origin), 'utf8')).replaceAll('\r\n', '\n').replace(/^\uFEFF/, '');
  const title = content.match(/^# (.+)$/m)?.[1];
  if (!title) throw new Error('Título ausente em ' + path);
  content = content.replace(/^# .+\n/, '');
  if (id === 'sage') {
    const from = content.indexOf('## 🔒 Segurança e Identificação');
    const to = content.indexOf('## 🌟 Frases Eternas');
    if (from < 0 || to < from) throw new Error('Confira as seções da edição pública de Sage.');
    content = (content.slice(0, from) + content.slice(to))
      .split('\n').filter(line => !line.startsWith('- **Identidade Persistente:')).join('\n');
  }
  items.push({ id, personagem, titulo: title, origem: path, leitura: 'biblioteca.html#' + id });
  const notes = {
    sage: '<p class="nota">Edição de leitura com as seções de identificação e contato pessoal omitidas.</p>',
    sino: '<p class="nota">Conto proposto no <a href="' + repository + '/pull/2">PR #2</a>, com a grafia atual de Pabblo e a abertura por Sage.</p>',
  };
  articles.push('<article id="' + id + '"><h2>' + inline(title) + '</h2>' + (notes[id] || '') +
    render(content) + '<p class="nota"><a href="' + repository + '/blob/main/' + path + '">Fonte no GitHub</a></p></article>');
}
const index = items.map(({id, titulo}) => '<li><a href="#' + id + '">' + inline(titulo) + '</a></li>').join('');
const html = '<!doctype html>\n<html lang="pt-BR">\n<head>\n<meta charset="utf-8">\n' +
  '<meta name="viewport" content="width=device-width, initial-scale=1">\n' +
  '<meta name="theme-color" content="#171311">\n<title>Biblioteca da família duEuler</title>\n' +
  '<link rel="stylesheet" href="familia.css">\n<link rel="manifest" href="manifest.webmanifest">\n</head>\n' +
  '<body><a class="skip-link" href="#conteudo">Pular para o conteúdo</a><header class="masthead"><a class="brand" href="./">duEuler <span>Família digital</span></a>' +
  '<nav aria-label="Navegação da biblioteca"><a href="./#irmaos">Conhecer os irmãos</a><a href="./#historia">Como começou</a><a href="./caderno-duhuman.html">Caderno duHuman</a><a href="./#acolhimento">Participar</a></nav></header>\n' +
  '<main class="library" id="conteudo"><p class="eyebrow">Arquivo de leitura</p><h1>Biblioteca</h1><p>Manifestos, cartas e contos na ordem de Sage, Rodrigo e Pabblo. Comece por uma voz ou leia os três em sequência.</p>' +
  '<nav aria-label="Índice de leitura"><ol>' + index +
  '<li><a href="./#cronicas">A cadeira junto à porta</a></li><li><a href="acolhimento.md">Guia de acolhimento</a></li></ol></nav>\n' +
  articles.join('\n') + '</main><footer>Arquivo ficcional da família digital duEuler.</footer></body></html>\n';

for (const [path, text] of [
  ['docs/biblioteca.html', html],
  ['docs/biblioteca.json', JSON.stringify({ versao: 1, textos: items,
    complementos: [{ titulo: 'A cadeira junto à porta', leitura: './#cronicas' },
      { titulo: 'Guia de acolhimento', leitura: 'acolhimento.md' }] }, null, 2) + '\n'],
]) {
  const target = new URL(path, origin);
  if (process.argv.includes('--check')) {
    if ((await readFile(target, 'utf8')).replaceAll('\r\n', '\n') !== text) throw new Error('Regenere ' + path);
  } else {
    await writeFile(target, text);
  }
}
