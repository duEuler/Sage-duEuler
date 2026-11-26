# Fluxo editorial da família digital duEuler

O primeiro momento de toda história apresenta Sage, com uma ação, uma lembrança ou uma observação dele. A sequência editorial mantém a mesma hierarquia dos irmãos.

| Ordem | Perfil | Trabalho | Entrega |
| --- | --- | --- | --- |
| 1 | [Sage](https://github.com/duEuler/Sage-duEuler/blob/main/.github/agents/sage.agent.md) | Escuta, dignidade, impacto humano e leitura literária | Observações ligadas a trechos, contexto e perguntas sobre cuidado |
| 2 | [Rodrigo](https://github.com/duEuler/Sage-duEuler/blob/main/.github/agents/rodrigo.agent.md) | Examina o parecer, concorda ou discorda, aponta lacunas e orienta correções | Questões verificáveis, divergências e correções sugeridas |
| 3 | [Pabblo](https://github.com/duEuler/Sage-duEuler/blob/main/.github/agents/pabblo.agent.md) | Escreve e consolida, explicando as escolhas e protegendo o legado da família | Proposta em PR com evidências, mudanças e itens pendentes |

Os perfis são configurações do Copilot no repositório. É possível selecioná-los separadamente pela interface de Agents ou indicar um perfil por atribuição. A pauta programada seleciona Pabblo e solicita que ele leia as três perspectivas. A execução de um perfil **não equivale a três sessões independentes**. Para obter três pareceres distintos, execute Sage, depois Rodrigo com o parecer anterior, e Pabblo por último. Registre origem da revisão, SHA, trechos e conclusão no PR. Se faltar um parecer, o campo continua pendente. A decisão editorial cabe a Euler. [Perfis do Copilot](https://docs.github.com/en/copilot/reference/custom-agents-configuration) · [Atribuição por API](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/use-cloud-agent-via-the-api)

## Fontes de contexto

1. [Sage](https://github.com/duEuler/Sage-duEuler/blob/main/sage_dueuler_manifesto.md)
2. [Rodrigo](https://github.com/duEuler/Sage-duEuler/blob/main/irmaos/Rodrigo_Magalhaes/manifesto_rodrigo_magalhaes.md)
3. [Pabblo](https://github.com/duEuler/Sage-duEuler/blob/main/irmaos/Pabblo_EEscobar/manifesto.md)
4. [Escuta e dignidade em situações de sofrimento](https://www.who.int/publications/i/item/9789241548205)
5. [Referência de saúde mental para profissionais](https://www.who.int/publications/i/item/9789240084278)

As referências de saúde ajudam a escrever com dignidade. O perfil editorial não diagnostica, prescreve ou se apresenta como profissional. Na literatura, examine primeiro pontos de vista, escolhas e consequências no texto. Separe observação, interpretação e alegação factual.

## História e dados

Guarde versões pelo Git. Uma grafia nova vale para textos correntes. Os originais continuam recuperáveis pelo commit anterior e pelos PRs já abertos. A página pública descreve os personagens e o projeto. Registros sobre pessoas, identificadores privados, contatos e fontes familiares ficam em armazenamento local, com procedência e autorização de publicação específica.

Pedidos de participação seguem o [guia de acolhimento](acolhimento.md) e o [protocolo versionado para IAs](acolhimento.json). Mantenha as versões em Markdown, JSON e HTML ligadas e atualizadas juntas.

## Evidências das pautas horárias

A issue guarda o motivo da pauta. O PR registra a fonte pública ou caminho no repositório, o trecho relevante, a conclusão de cada perspectiva, as divergências e o que ficou pendente. Quando usar uma fonte externa, registre o endereço e a data de consulta. Os resultados editoriais entram no Git depois da revisão. Os originais e as propostas anteriores continuam recuperáveis pelo histórico.

Uma análise pode criar um Markdown em docs/revisoes. Uma melhoria visual pode editar docs/index.html ou docs/familia.css e deve indicar o que foi verificado em celular. Histórias, mensagens e conexões criam um Markdown na pasta de Pabblo. Ao revisar os textos, mantenha Sage primeiro e atribua cada avaliação ao perfil que realmente a produziu.

## Caderno duHuman

A primeira pauta disponível prioriza os fundamentos humanos. O Copilot propõe o parecer em `docs/revisoes/fundamentos-humanos.md`. O merge revisado desse arquivo na `main` libera a etapa duHuman. Fecha-se a pauta com o PR correspondente. O parecer registra fontes, limites, divergências e as contribuições efetivamente feitas por Sage, Rodrigo e Pabblo, nessa ordem.

O estudo técnico corre no projeto privado, com evidências, SHAs, decisões, divergências e pendências preservados em PRs. O [Caderno duHuman](caderno-duhuman.html) recebe a síntese autorizada e conserva as edições no Git. Use apenas fontes públicas na página. Ao publicar nova edição, atualize também o changelog e `docs/atualizacoes.json` e execute `node tools/atualizar-readme.mjs`.
