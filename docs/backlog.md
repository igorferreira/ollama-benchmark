# Backlog de evolução e validação

Este backlog registra trabalho proposto. Não equivale a funcionalidade implementada ou plataforma já homologada. Alterações precisam de especificação, validação e revisão conforme [desenvolvimento](desenvolvimento.md).

## TASK-WIN-01 — Validar Docker Desktop no Windows e avaliar Compose específico

- **Estado:** planejada; validação Windows pendente.
- **Origem:** solicitação explícita para avaliar se é necessário um arquivo equivalente ao `compose.linux.yaml` para Windows.
- **Escopo inicial:** testar o `compose.yaml` existente, destinado a Docker Desktop/gateway, antes de criar uma duplicação. `compose.linux.yaml` é um modo independente com rede host para Docker Engine Linux; não deve ser copiado mecanicamente para Windows.
- **Decisão da avaliação documental:** não criar `compose.windows.yaml` agora, pois seria uma duplicação do arquivo padrão sem diferença comprovada. Criar arquivo específico somente se a validação Windows identificar uma configuração necessária distinta. A integração real continua pendente.

### Critérios de aceite

1. Registrar Windows, Docker Desktop, engine de containers Linux, WSL2 e modo de rede efetivamente utilizados, com versões.
2. Validar `docker compose config` no ambiente Windows e confirmar publicação da interface somente no loopback da máquina.
3. Verificar resolução e conectividade real a `host.docker.internal:11434`, inclusive o caso em que Ollama escuta somente no loopback. Documentar resultados e limitações, sem presumir equivalência com rede host do Linux.
4. Executar smoke do app com Ollama real: descoberta de modelo, geração, tokens e durações consistentes, cancelamento e exportações CSV/JSON.
5. Verificar assets/ícones/PWA e limites de cache no navegador Windows, sem guardar tokens, APIs ou dados de teste.
6. Confirmar caminhos de operação/portas e instruções PowerShell; comparar configurações antes de decidir por novo Compose.
7. Confirmar Python mínimo 3.11 e preservar alternativa nativa `py -3 app.py` caso Docker Desktop não alcance o Ollama local. Não orientar exposição pública do Ollama ou abertura irrestrita de firewall apenas para viabilizar o benchmark.
8. Atualizar runbook e matriz com evidências executadas; manter lacunas explícitas e não marcar como concluída por passar somente no Linux.

### Entregável esperado

Relato da validação real e decisão justificada: reutilizar o Compose padrão ou propor um arquivo Windows com diferença concreta. Nenhum arquivo Windows novo foi criado por esta tarefa planejada.

### Referências da avaliação documental

- [Rede do Docker Desktop](https://docs.docker.com/desktop/features/networking/networking-how-tos/): `host.docker.internal` identifica o host, mas resolver esse nome não comprova acesso a qualquer serviço vinculado somente ao loopback.
- [Driver de rede host](https://docs.docker.com/engine/network/drivers/host/): Docker Desktop 4.34+ oferece host networking como opção habilitada nas configurações, para containers Linux; não é suporte a Windows containers e não funciona com Enhanced Container Isolation.

Se necessário, a tarefa pode avaliar esse modo host opt-in do Desktop como alternativa de conectividade, sem presumir que já funciona neste projeto. Nenhuma configuração de Docker Desktop, Ollama ou firewall foi alterada nesta avaliação. Fontes consultadas pela pesquisa da entrega; Windows/Docker Desktop não foram executados no ambiente Linux utilizado.

## TASK-PS-01 — Automatizar preparação e ciclo de vida no PowerShell

- **Estado:** início/parada nativos e Docker implementados na SDD-009; setup e homologação Windows real permanecem pendentes.
- **Dependência:** TASK-WIN-01 para confirmar o modo Docker Desktop antes de automatizar sua operação.
- **Objetivo:** depois de Python 3.11+ já instalado, permitir preparar/verificar o checkout e iniciar/parar somente o site deste projeto, com alternativas nativa e Docker.
- **Artefatos implementados:** `start.sh`, `stop.sh`, `start.ps1` e `stop.ps1` na raiz, com flag de modo Docker e helper `scripts/service.py`. `scripts/setup.ps1` continua candidato futuro; não foi implementado.

### Subtarefas planejadas

1. **TASK-PS-01.1 — Preparação:** detectar `py -3` ou `python`, validar versão mínima 3.11, estrutura do checkout, disponibilidade do Ollama e portas. Não instalar dependências pip nem baixar Python/Docker automaticamente.
2. **TASK-PS-01.2 — Início nativo:** iniciar `app.py` em segundo plano de forma idempotente. Registrar apenas os dados operacionais mínimos em estado `*.local.json` ignorado pelo Git, sem prompts, tokens ou credenciais.
3. **TASK-PS-01.3 — Parada nativa segura:** conferir PID, instante de criação e identidade do executável/linha de comando associada ao checkout antes de parar. Não confiar apenas em PID ou porta: PID pode ser reutilizado. Nunca encerrar todos os processos Python, o Ollama ou processo de outro projeto.
4. **TASK-PS-01.4 — Docker:** iniciar/parar pelo Compose do projeto conforme TASK-WIN-01. Preservar outros containers e dados; não usar prune ou remoção de volumes. Detectar Docker ausente, engine parado e condições de VM/WSL2 com erro claro.
5. **TASK-PS-01.5 — Documentação e validação:** instruções para PowerShell 5.1 e 7 no Windows, caminhos com espaços, timeouts, saúde do site, PWA/FAQ e limpeza somente do estado próprio. Execução real Windows continua pendente.

### Critérios de aceite

- Preparação verifica os requisitos e informa correções sem exigir administrador nem instalar ferramentas por conta própria.
- Start repetido não cria processos duplicados; stop repetido informa que a instância já está parada.
- Site iniciado responde a `/api/health`, página principal, FAQ e assets PWA; teste do Ollama é distinto da saúde HTTP do app.
- Porta ocupada por outro processo gera diagnóstico, sem encerrar ou substituir esse processo.
- Parada verifica identidade completa do processo próprio, incluindo proteção contra PID reutilizado e checkout com espaços no caminho.
- Operação Docker limita-se ao projeto Compose correto e não afeta containers externos, volumes ou outros serviços.
- Não alterar `OLLAMA_HOST`, firewall, ExecutionPolicy global, serviço de sistema, autostart ou política do computador sem solicitação própria.
- Não armazenar chaves/tokens nos scripts, logs ou estado versionado; estado operacional local precisa de ignore e tratamento de arquivo ausente/corrompido.
- Início, parada, idempotência, erros e caminhos com espaços são testados no Windows real com PowerShell 5.1/7 antes de declarar homologação.

A SDD-009 implementa os quatro scripts de início/parada na raiz, com modos nativo e Docker. O script de preparação/setup continua planejado; nenhuma instalação automática foi acrescentada. Homologação Windows real permanece pendente.

## TASK-SYS-01 — Resumo da máquina e detalhes acessíveis no site

- **Estado:** implementada na [SDD-004](changes/004-resumo-ambiente-dinamico.md), com testes sintéticos e verificação real Linux nativo/Docker. Windows real continua pendente em TASK-WIN-01; resultados e limites estão na matriz.
- **Natureza dinâmica obrigatória:** o resumo será obtido do ambiente que executa o backend em cada instância, nunca de valores estáticos, fixtures ou do exemplo pessoal da solicitação. Instalar, iniciar ou reconstruir em outra máquina deve produzir o inventário daquele ambiente, sem recompilar para trocar valores nem editar configuração manualmente.
- **Objetivo:** mostrar no topo um resumo útil ao benchmark — sistema operacional, CPU/GPU e RAM — com detalhes por mouse, foco de teclado ou toque e ação explícita **Ver detalhes**. Escape deve fechar o popover; informações essenciais não podem depender somente de hover.
- **Dependências:** TASK-WIN-01 para validar Windows e a estratégia Docker; especificação de campos, origem e privacidade antes de implementar.
- **Escopo mínimo:** metadados técnicos necessários para contextualizar uma medição. Aparência inspirada em inventários de sistema não implica executar ou exigir neofetch/fastfetch.

### Campos e origem dos dados

- Resumo: SO, modelo da CPU, modelo da GPU quando disponível e capacidade total de RAM, descobertos no ambiente de execução atual do backend. Disco, quando incluído, segue a mesma origem. Separar claramente capacidade de uso medido.
- Detalhes úteis: versão do SO/kernel, arquitetura, núcleos/threads, RAM total/usada e uptime. Resolução somente quando inferível com origem explícita, distinguindo viewport do navegador de resolução do monitor.
- Ambiente desktop, DE/WM, tema, fonte, shell e quantidade de pacotes são opcionais de baixo valor para o benchmark; avaliar se justificam coleta. Não exigir todos os campos nem coletar lista de pacotes.
- RAM usada, disco usado e uptime são valores mutáveis: devem vir de snapshots medidos com timestamp e estratégia de atualização limitada, nunca valores fixos ou copiados de um exemplo. Disco é opcional, somente capacidade/uso agregado de origem claramente delimitada, sem nomes de volumes, caminhos de montagem ou arquivos.
- Campo indisponível: **Não informado**, sem presumir zero ou inventar valores. Identificar origem: processo/backend, container, navegador ou alvo Ollama, quando comprovável.
- O navegador apenas apresenta os dados do backend; não é a origem presumida de CPU/GPU/SO/RAM/disco. Resolução obtida no navegador deve ser rotulada como informação do navegador e não atribuída ao host.
- Em Docker, o backend observa o ambiente do container. Esses dados não representam automaticamente o host ou a máquina que executa o Ollama; a identidade entre ambientes nunca deve ser presumida. Se informações do host não forem acessíveis, mostrar **Não informado — host não acessível neste modo**, sem inventar ou reutilizar um snapshot pessoal.
- Dados do container não representam automaticamente o host. Ausência de dispositivo GPU no container não demonstra ausência de GPU física. Modelo/capacidade de GPU não comprova utilização pelo Ollama; não inferir isso a partir de um inventário.

### Implementação futura e limites

Usar Python stdlib e estratégias nativas limitadas para Linux/Windows, com fallback quando indisponíveis. Neofetch, fastfetch, pacotes pip e ferramentas novas não serão dependências obrigatórias. Caso um comando nativo seja necessário, usar executável e argumentos predefinidos, sem interpolação de entrada do usuário ou shell injection, com timeout e limite de saída; não exigir administrador.

No Docker, informar a fronteira observada. Não recorrer a container privilegiado, Docker socket ou volumes sensíveis do host para obter um inventário mais completo. Não criar coletor remoto, monitor global do computador ou serviço de sistema para satisfazer esta tarefa.

Coleta eventual por HTTP deve preservar Host/Origin/CSP e endpoint não cacheado. Preferir consulta sob demanda; se uso de RAM justificar atualização periódica, limitar a aproximadamente cinco a dez segundos, sem introduzir trabalho de inventário durante inferência ativa ou distorcer o benchmark. Não alterar rede, firewall ou configuração do Ollama.

### Privacidade e minimização

Dados combinados de hardware/software podem identificar uma máquina por fingerprint. Documentar finalidade, campos e timestamp; não tratar inventário como autorização para coletar tudo que estiver disponível.

Não coletar ou publicar username, hostname, identificador usuário@máquina, IP/MAC, serial, UUID, nomes de discos/volumes, caminhos de montagem, diretório pessoal, nomes de arquivos, lista de pacotes ou telemetria. Não copiar o exemplo pessoal da solicitação para fixtures, documentação, capturas ou arquivos versionados.

Manter dados somente pelo tempo necessário à visualização, sem persistência ou inclusão nas exportações do benchmark por padrão. Persistência exige solicitação explícita e revisão própria. Não guardar inventário no cache PWA, logs ou relatórios públicos; fixtures e capturas de validação devem ser inteiramente sintéticas.

### Critérios de aceite

1. Cada inicialização/instância consulta o ambiente atual do backend; fixtures sintéticas distintas demonstram que iniciar ou reconstruir em outra máquina muda os dados naturalmente, sem valores hardcoded, recompilação para trocar inventário ou edição manual. O topo apresenta resumo legível, com detalhes acessíveis por hover, foco, toque e ação explícita; Escape fecha e o foco permanece utilizável nos temas claro/escuro.
2. Capacidade, uso, timestamp e origem são distintos; indisponibilidade usa **Não informado**, sem afirmar que container é host ou que GPU está sendo usada pelo Ollama.
3. Linux/Windows têm testes com fixtures sintéticas de campos válidos, ausentes, malformados e comando indisponível, além de timeout/limite de saída quando aplicável.
4. Cenários de container demonstram fronteiras e fallback sem privilégios, montagem sensível ou Docker socket; resolução do navegador não é apresentada como monitor físico sem evidência.
5. API, HTML, exportações, logs e cache são verificados para ausência de PII e identificadores proibidos; endpoint futuro mantém proteções locais e não entra na allowlist do service worker.
6. RAM usada, disco usado e uptime carregam timestamp do snapshot e atualização limitada; a estratégia pausa ou evita consultas onerosas durante inferência, sem distorcer o benchmark. Coleta/refresh não cria monitoramento global; custos são avaliados antes de habilitar atualização automática.
7. Documentação declara minimização e campos opcionais, sem homologar Windows ou dados do host Docker apenas por testes executados no Linux.

O registro original era apenas planejamento. A solicitação posterior autorizou a implementação da SDD-004, com dados dinâmicos e validação da entrega em Linux/Docker. Não houve cópia de inventário pessoal para fixtures/documentação pública. TASK-WIN-01 e TASK-PS-01 continuam planejadas.

Exceção posterior autorizada pela [SDD-006](changes/006-hostname-e-cabecalho.md): o hostname passa a ser exibido localmente nos detalhes, sem DNS, persistência, logs, exportação ou cache. A proibição original acima descreve a baseline SDD-004; os demais identificadores continuam excluídos.
