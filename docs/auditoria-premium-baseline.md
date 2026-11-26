# Baseline da reformulação premium

Data do baseline: 26/11/2026  
Branch de origem: `main`  
SHA de origem: `0d067bc85b81dfbe940b79117eb782bc0663a8fc`  
Branch de trabalho: `codex/reformulacao-premium`

## O que existe de fato

- O website público é um PWA estático servido pelo diretório `docs/` e publicado por
  `.github/workflows/publicar-pwa.yml`.
- A Home é `docs/index.html`; a biblioteca é gerada por
  `tools/gerar-biblioteca.mjs` a partir dos Markdown em `irmaos/`.
- `docs/app.js` registra o Service Worker, verifica atualizações e prepara o push
  Firebase. O push depende de `docs/push-config.js` e de configuração externa; a
  chave VAPID está vazia no baseline.
- `docs/sw.js` cobre leitura offline e cache dos assets públicos. Não há backend de
  contratação, CRM, autenticação de visitante, formulário comercial ou API de
  serviços no website público.
- `sage_rodrigo_runtime/` é um runtime Python separado, com SQLite local e
  relatórios; não é carregado pelo PWA e não deve ser misturado à camada visual.
- Não há `package.json`, bundler, TypeScript, suíte de testes de frontend ou
  configuração de Playwright no repositório. A validação disponível é estática,
  por `node --check`, scripts de geração e o workflow de publicação.

## Inventário de páginas e contratos

| Página/arquivo | Papel | Estado preservado |
| --- | --- | --- |
| `docs/index.html` | Home narrativa e pontos de entrada | URLs com hash, links da biblioteca, controles de avisos/push |
| `docs/biblioteca.html` + JSON | Leitura dos manifestos, cartas e contos | Geração determinística e leitura offline |
| `docs/caderno-duhuman.html` | Caderno editorial | Página pública independente |
| `docs/acolhimento.*` | Guia para participação | Markdown e JSON públicos |
| `docs/perfis.json` | Dados estruturados dos três irmãos | Consumido por documentação e biblioteca |
| `docs/manifest.webmanifest` | Instalação PWA | `start_url`, escopo e ícones |
| `docs/sw.js` | Cache e atualização offline | Versão de cache e fallback existentes |
| `firebase/*` | Envio de push e regras | Integração opcional; sem segredo no repositório |

## Diagnóstico visual do baseline

1. A identidade azul-noturna/laranja já existe, mas a Home ainda organiza grande
   parte do conteúdo como seções equivalentes e cartões.
2. A tipografia principal é adequada para leitura, porém a escala narrativa e a
   sinalização de capítulo ainda são discretas em telas grandes.
3. A nova imagem `guardiao.webp` estava fora da lista de assets do workflow; essa
   dependência foi corrigida no commit `0d067bc`.
4. A experiência não tinha onboarding nem seletor persistente de idioma.
5. O site não possui métricas Lighthouse registradas neste checkout; portanto,
   metas de 95/95/95/95 e Core Web Vitals continuam não medidas.

## Limites da missão nesta arquitetura

- Não inventar contratação, clientes, depoimentos, números, autenticação ou
  resultados comerciais que não existam.
- Não instalar um framework ou biblioteca de animação pesada para uma Home que
  já funciona como HTML/CSS/JS offline. CSS nativo, Web Animations e um pequeno
  controlador de estado são suficientes para a primeira versão.
- Internacionalização será introduzida como camada de conteúdo do PWA, com
  português brasileiro padrão e inglês selecionável; conteúdos editoriais
  autorais permanecem identificados como textos em português até receberem uma
  tradução revisada, em vez de serem traduzidos automaticamente sem revisão.

## Princípios adotados

- A narrativa deve ser percebida em uma tela grande sem esconder a navegação.
- Movimento acompanha descoberta e entrada de cena; `prefers-reduced-motion`
  remove transformações e autoplay.
- Imagens têm função editorial, não são decoração repetida.
- Cada CTA descreve uma ação real disponível hoje: ler, conhecer, participar ou
  ativar avisos.
- Toda alteração fica em branch própria até validação e revisão do responsável.

## Referências de princípios, não de cópia

- [Vercel Web Interface Guidelines](https://vercel.com/design/guidelines):
  hierarquia, previsibilidade e detalhes de interface.
- [Vercel Design](https://vercel.com/design): tipografia e composição de produto
  com sistema consistente.
- [Linear](https://linear.app/): narrativa de produto, densidade controlada e
  estados claros.
- [Apple Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/):
  movimento com propósito, legibilidade e redução de complexidade.

## Próximas verificações

- Validar a Home em 360, 390, 768, 1024, 1280, 1440, 1920 e 2560 px.
- Executar `node --check` nos scripts públicos e os checks determinísticos dos
  geradores.
- Inspecionar teclado, foco, contraste, reduced motion e o fluxo de onboarding.
- Medir performance e acessibilidade em navegador quando houver executor visual
  disponível; sem essa medição, não declarar as metas Lighthouse como atingidas.
