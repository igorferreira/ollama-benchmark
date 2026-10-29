# SDD-005 — Biblioteca local de pedidos

Data: 29/10/2026. Registro criado **antes da implementação**, sob demanda explícita. Preservar integralmente as mudanças de tokens/FAQ/SYS ainda não commitadas. Não executar benchmark, alterar serviços/Ollama, instalar dependências ou fazer commit/push.

## Objetivo e escopo

Oferecer exemplos genéricos em português para preencher o pedido sem copiar manualmente. Biblioteca local com 18 exemplos: três em cada combinação de tipo código/não código e complexidade simples/intermediário/avançado. Cada item tem ID estável, título, descrição curta e pedido completo.

A complexidade é uma classificação heurística editorial, não contagem de tokens, preço, SLA ou qualidade garantida. Modelo, contexto e limite de saída influenciam resultado; exemplos longos podem exigir limite maior. Selecionar não altera modelo, contexto, saída, raciocínio ou instrumentação e nunca inicia teste ou executa código.

## Requisitos novos

- **RF-21:** abrir biblioteca no canto superior direito do cabeçalho da seção Configure o teste, filtrar por tipo/complexidade e selecionar um único exemplo com prévia integral.
- **RF-22:** aplicar somente após ação explícita Usar pedido, protegendo edição existente, preservando o texto em cancelamento/fechamento e bloqueando aplicação durante benchmark.

Fora do escopo: salvar exemplos pessoais, editar catálogo pela UI, gerar exemplos com Ollama, telemetria, busca remota, API nova de inferência, persistência, instalação de dependências ou ajuste automático dos parâmetros.

## Interação e proteção do texto

Dialog nativo `showModal`, com título/descrição associados, filtros rotulados, lista de seleção única, prévia de texto sem execução, botão Usar pedido e ações Fechar/Cancelar. O navegador fornece semântica modal e Escape; ao fechar, restaurar foco ao botão de abertura quando utilizável.

Abrir, filtrar, selecionar e fechar não mudam o textarea. Somente Usar pedido troca seu valor. Se o texto atual não estiver vazio e diferir tanto do default quanto do último exemplo aplicado, exibir aviso explícito e confirmação de substituição junto à prévia. Sem confirmação, aplicar fica indisponível. Mudança posterior do texto/seleção invalida confirmação anterior; o handler revalida a condição imediatamente antes de aplicar. Não há substituição silenciosa por selecionar um cartão.

O módulo acompanha o evento existente `benchmark-status`, verifica atividade/textarea desabilitado ao abrir e aplicar e mantém abertura/aplicação indisponíveis durante teste conhecido pela interface. Se o teste começa com dialog aberto, não modificar o pedido e mostrar o bloqueio; Fechar/Cancelar continuam disponíveis. Essa proteção não altera o servidor nem implementa monitoramento global do Ollama.

## Arquivos e contratos

- `web/prompts.js`: catálogo local e lógica do dialog, isolado do módulo de benchmark.
- `web/prompts.css`: layout responsivo, temas existentes e estados de seleção/foco.
- `web/index.html`: botão alinhado ao h2 da seção Configure o teste (acima do label do textarea) e markup do dialog, com scripts/estilos externos.
- `backend/http.py`: somente whitelist dos dois assets, mantendo Host/Origin/CSP/no-store.
- `tests/test_prompts.py`: catálogo/cobertura das seis células, segurança de assets/markup/cache e preservação dos limites.
- Liderança: SDD/contrato estático, rastreabilidade, README e documentos pertinentes.

Não há nova rota de dados ou alteração de schema/configuração do benchmark. Catálogo e escolhas ficam no JavaScript local. Conteúdo inserido é texto no textarea e não é interpretado como HTML/JavaScript/SQL. Dados dinâmicos são apresentados por textContent; não usar innerHTML, handlers/styles inline ou CDN.

## Visual e acessibilidade

Manter identidade azul, fonte local e temas do app. Dialog compacto e legível em 375 px, tablet e desktop; corpo rolável com ações sempre alcançáveis, seleção clara e prévia inteira com quebra de linha. Evitar poluir o topo ou multiplicar cartões decorativos. Filtros, resultado vazio, contagem de itens e aviso de substituição devem ser compreensíveis por teclado/leitor de tela. Respeitar foco visível e movimento reduzido.

Biblioteca tem somente textos sintéticos públicos, sem prompts pessoais, credenciais, inventário ou dados de execução. Assets novos ficam fora da allowlist PWA; manter SW v3 e os dez recursos públicos atuais. FAQ e tela offline não precisam carregar o módulo da biblioteca. Fechar não apaga formulário nem cria persistência. Exportações já existentes só conterão o pedido caso a pessoa decida executar um benchmark com ele.

## Critérios de aceite

- **AC-PROMPT-01:** 18 exemplos únicos, três por cada uma das seis células, com título/descrição/pedido completo em português.
- **AC-PROMPT-02:** filtros combinados e seleção única atualizam lista/prévia; resultado vazio não deixa aplicar uma seleção invisível anterior.
- **AC-PROMPT-03:** somente Usar pedido preenche textarea, sem modificar qualquer parâmetro ou iniciar geração.
- **AC-PROMPT-04:** texto editado exige confirmação explícita; mudar texto/seleção invalida confirmação; cancelar/Escape/Fechar preservam texto.
- **AC-PROMPT-05:** evento de benchmark ativo bloqueia abrir/aplicar, inclusive se dialog já aberto; guards do handler impedem aplicação por corrida entre eventos locais.
- **AC-PROMPT-06:** dialog responsivo nos dois temas, foco/Escape/restauração e controles acessíveis.
- **AC-PROMPT-07:** assets locais sem token, persistência ou API de inferência; CSP/Host/Origin preservados, SW v3 sem adicionar catálogo ou dados de teste ao cache.
- **AC-PROMPT-08:** suíte anterior preservada, novos testes e QA/review independentes após o freeze; sem homologar Windows real por testes Linux.

## BDD

**Dado** um pedido digitado pela pessoa, **quando** eu navegar/filtrar/selecionar ou fechar a biblioteca, **então** o pedido continuará intacto até confirmar Usar pedido e a substituição exigida.

**Dado** um filtro que não inclui o exemplo selecionado, **quando** a lista mudar, **então** a seleção anterior não poderá ser aplicada inadvertidamente.

**Dado** benchmark ativo ou iniciado enquanto o dialog está aberto, **quando** eu tentar aplicar, **então** o texto não será substituído e nenhum teste adicional será disparado.

## Resultados

Implementação disponível. Suíte de desenvolvimento: 82 testes aprovados em 23,480 s com ResourceWarning como erro; QA independente automatizado confirmou 82 em 23,404 s. Quatro testes de biblioteca verificam catálogo, markup, HTTP/segurança e exclusão de inferência/persistência/cache. Sintaxe JS e diff sem erros. Validação comportamental no navegador concluída pela raiz e QA final independente APROVADO; revisão final independente APROVADA. Os testes estáticos não substituem esses gates.

Refinamento visual explícito antes do freeze: abertura alinhada à direita do h2 “2. Configure o teste”, usando section-head com quebra responsiva; não junto ao label do textarea.

Navegador validado pela raiz: 18 exemplos/seis células e fluxo seguro, seis combinações de viewport/tema sem overflow; hostname local rotulado por origem e guia/cabeçalho aprovados. Evidência resumida na [E11 da rastreabilidade](../rastreabilidade.md#e11--biblioteca-de-pedidos-e-hostname-29102026). Auditoria independente de segurança aprovada; gates QA/review formalizados no fechamento da matriz.

Correção no gate de revisão: quando o painel do ambiente estiver fixado atrás de um dialog, seu handler de Escape cede ao modal aberto, para o primeiro Escape fechar a biblioteca nativamente. O painel não modal continua utilizável depois. A mesma prioridade é aplicada ao handler de Escape da ajuda flutuante, inclusive quando aberta por hover sem foco. Regressão dirigida de navegador e check do handler acompanham o fechamento.

Fechamento: **QA APROVADO**, **review independente posterior APROVADO** e auditoria de segurança **APROVADA**. Nenhum commit/push ou alteração de serviço/Ollama foi feito pela equipe de implementação. Windows real permanece não executado.
