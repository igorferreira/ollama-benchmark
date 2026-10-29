# SDD-006 — Nome local da máquina e acesso ao guia

Registro prospectivo de 29/10/2026, criado antes da alteração. Demanda explícita: exibir o hostname do ambiente de execução e tornar o guia mais visível logo abaixo do nome do aplicativo, removendo o eyebrow “Benchmark local”.

## Contrato e privacidade

Adicionar `hostname: string | null` a `/api/system`, coletado uma vez por instância por `socket.gethostname()`, sem lookup DNS/FQDN ou chamadas de rede. Remover caracteres não imprimíveis, limitar a 256 caracteres e usar null em falha/valor vazio. A UI mostra texto seguro nos detalhes com rótulo “Hostname da máquina” ou “Hostname do container”, conforme a origem já informada. O nome do container não representa o host físico ou alvo Ollama.

Esta é uma exceção autorizada à minimização da SDD-004: o hostname é um identificador técnico exibido apenas localmente e de forma volátil. Continuam proibidos username, IP/MAC, serial, UUID, caminhos pessoais e coleta remota. Não registrar valores reais em código, fixtures públicas, documentação, logs, exportações, cache PWA ou localStorage. Inventário pode identificar a máquina; evitar compartilhar capturas com dados locais.

## Aceite

- **RF-23 / AC-HOST-01:** origem dinâmica por ambiente; falha produz null; sanitização e limite são testados com valores sintéticos.
- **AC-HOST-02:** nome visível nos detalhes, textContent, com distinção máquina/container e sem alterar campos do benchmark.
- **AC-HOST-03:** guia único logo abaixo do logotipo/nome, alinhado à esquerda, antes da descrição/faixa; tema permanece à direita e instalação disponível.
- **AC-HOST-04:** no-store/proteções HTTP preservados; nome não entra nos resultados/exportações/cache; suíte anterior e QA/review finais aprovados.

Arquivos: `backend/system_info.py`, `web/system.js`, markup do cabeçalho/detalhes em `web/index.html`, testes sintéticos e documentação/OpenAPI. Sem dependências novas, lookup remoto ou mudança de configuração.

## Resultado

Hostname coberto por fixture sintética, sanitização/limite/null e suíte SYS de 28 testes aprovada. Suíte completa de 82 testes aprovada também por QA independente automatizado. Nome foi colocado somente nos detalhes para manter a faixa compacta. Navegador validado e QA final independente APROVADO; revisão final independente APROVADA. Windows real não é presumido por fixtures Linux.

Navegador validado pela raiz: 18 exemplos/seis células e fluxo seguro, seis combinações de viewport/tema sem overflow; hostname local rotulado por origem e guia/cabeçalho aprovados. Evidência resumida na [E11 da rastreabilidade](../rastreabilidade.md#e11--biblioteca-de-pedidos-e-hostname-29102026). Auditoria independente de segurança aprovada; gates QA/review formalizados no fechamento da matriz.

Fechamento: **QA APROVADO**, **review independente posterior APROVADO** e auditoria de segurança **APROVADA**. Nenhum commit/push ou alteração de serviço/Ollama foi feito pela equipe de implementação. Windows real permanece não executado.

## Ajuste posterior — hostname visível na faixa

Por solicitação posterior, o nome também aparece abaixo do SO na faixa de CPU/GPU/RAM, com rótulo Hostname e a origem nativa/container já indicada. Nomes longos são abreviados visualmente na faixa; o valor completo continua nos detalhes. A apresentação reutiliza o mesmo snapshot local, sem nova coleta, persistência ou alteração da API.
