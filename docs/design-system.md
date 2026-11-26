# Design system da família digital

O site usa CSS nativo para preservar carregamento imediato, leitura offline e
manutenção simples. Os tokens ficam no início de `familia.css`; esta página é a
referência humana para novas cenas e páginas.

## Direção

O eixo visual é uma noite azul profunda atravessada por luz violeta, azul elétrico
e âmbar. A cor forte marca ação ou decisão; o texto permanece claro e espaçado.
Imagens são usadas como cenas, não como preenchimento de cartões.

## Tokens atuais

| Token | Uso | Valor |
| --- | --- | --- |
| `--night-deep` | fundo principal | `#070e18` |
| `--night` | superfícies escuras | `#0e1725` |
| `--panel` | painel e leitura | `#101d2c` |
| `--ink` | texto principal | `#f4f8fb` |
| `--muted` | texto secundário | `#a9bac7` |
| `--blue` | foco e tecnologia | `#7ad9eb` |
| `--amber` | ação e destaque | `#ffb347` |
| `--orange` | capítulo e estado | `#ff684d` |

## Padrões

- `hero`: uma única imagem dominante, título em escala editorial e no máximo dois
  caminhos imediatos.
- `section`: uma ideia por cena, com `scroll-margin-top` para links diretos.
- `profiles`: entrada de personagem; não deve virar grade de recursos comerciais.
- `timeline`: sequência real da história, com marca visual e links para a fonte.
- `.action`: ação primária com verbo explícito; links comuns permanecem leves.
- `.language-switcher`: idioma persistente e discreto, sempre com foco visível.
- `.onboarding`: descoberta opcional; fechar grava a preferência local e não volta
  a bloquear o leitor.

## Movimento

As entradas de cena usam CSS `animation-timeline: view()` quando disponível. O
fallback mantém a página estável em navegadores sem suporte. Em
`prefers-reduced-motion: reduce`, transformações e animações são removidas.

## Acessibilidade

- Toda imagem editorial precisa de texto alternativo específico.
- Foco visível usa o token azul.
- Não usar cor como único indicador de estado.
- Manter linha de leitura confortável e títulos com `clamp()`.
- Testar teclado e viewport estreito antes de publicar uma nova cena.
