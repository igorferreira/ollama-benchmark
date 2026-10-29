# SDD-004 — Resumo dinâmico do ambiente de execução

Data: 29/10/2026. Registro criado **antes da implementação**, após autorização explícita para executar TASK-SYS-01. O trabalho anterior de tokens ao vivo/FAQ permanece preservado; tarefas Windows/PowerShell do backlog não são implementadas por esta mudança. Sem commit/push ou alteração do Ollama.

## Objetivo e direção visual

Apresentar no topo um resumo real e compacto do ambiente onde o backend executa, acompanhado de detalhes acessíveis. Nunca copiar valores de uma máquina de exemplo para o produto, fixtures ou documentação pública. Mudar de máquina/instância deve mudar os dados naturalmente.

Manter identidade do app (ícone, azul e fontes locais), sem transformar a interface em um dashboard genérico de cartões repetidos. Uma faixa unificada após o título reúne badge de origem/SO e CPU, GPU e RAM, com separadores e números tabulares. RAM só terá barra se capacidade e uso forem conhecidos e compatíveis; ausência não será uma barra vazia que sugere zero. Detalhes em painel elegante, adaptado inline no celular, com hierarquia visual, timestamp e atualização explícita, sem animação piscante e respeitando preferência de movimento reduzido. FAQ/PWA e benchmark continuam legíveis.

A implementação de frontend segue o brief e a skill frontend-design aplicada pela liderança; usa somente fonte system-ui e recursos locais. Temas claro/escuro, foco e contraste permanecem obrigatórios.

## Requisitos e contrato aditivo

- **RF-19:** visualizar resumo dinâmico de SO, CPU, GPU e RAM do ambiente atual do backend, com origem inequívoca e campos indisponíveis como Não informado.
- **RF-20:** abrir detalhes por hover, foco, toque e botão Ver detalhes; Escape fecha sem prender foco. Dados mutáveis têm timestamp, refresh limitado e pausa durante benchmark.
- **RNF-08:** inventário mínimo e volátil, sem identificadores pessoais, persistência, exportação de benchmark ou cache PWA; coleta não pode distorcer o sistema medido.

Novo `GET /api/system`, sujeito às proteções comuns Host/Origin/Fetch-Site e `Cache-Control: no-store`. Não recebe parâmetros de comandos/caminhos. O contrato permanece separado de `/api/state` e dos arquivos CSV/JSON de benchmark.

```text
collected_at: timestamp UTC ou null
 environment: {kind: native|container|unknown, scope: string, note: string}
 os: {name: string|null, kernel: string|null, architecture: string|null}
 cpu: {model: string|null, physical_cores: int|null, logical_cpus: int|null, scope: string}
 gpu: {models: string[], scope: string, note: string}
 memory: {total_bytes: int|null, used_bytes: int|null, available_bytes: int|null, scope: string}
 disk: {total_bytes: int|null, used_bytes: int|null, scope: app_filesystem}
 uptime_seconds: number|null
 uptime_scope: string
 refresh: {min_interval_s: 10, paused: boolean, stale: boolean}
```

Valores desconhecidos são null ou lista vazia, jamais hardware inventado. Lista vazia de GPU significa modelo não identificado/exposto, não ausência física. Capacidade/uso em bytes e uptime em segundos, com escopo explícito. `collected_at` é o instante do snapshot dinâmico, não uma garantia de dados instantâneos.

## Componentes e ownership

- `backend/system_info.py`: novo coletor stdlib independente, com fontes injetáveis para fixtures. Fatos estáticos por instância; snapshot dinâmico cacheado por pelo menos dez segundos.
- `app.py`: composição injeta SystemCollector em AppServer. Terceiro argumento opcional preserva fixtures existentes; sem coletor injetado, a rota informa indisponibilidade em vez de coletar dados reais de testes incidentalmente.
- `backend/http.py`: endpoint separado; consulta estado ativo de forma breve e chama coletor fora do lock do manager.
- `backend/manager.py`: pequena consulta `is_active` sob lock, sem subprocesso/coleta nesse lock.
- `web/`: faixa, detalhes, JS próprio e estilos; atualizações limitadas, pausa durante inferência e viewport somente como dado do navegador.
- `tests/test_system.py`: backend e HTTP com fontes/fixtures inteiramente sintéticas.
- `tests/test_system_ui.py`: estrutura pública, fronteira de cache e acessibilidade estática.
- Liderança: docs, contrato OpenAPI, privacidade e rastreabilidade.

Os dois workers não devem editar os arquivos do outro nem sobrescrever as mudanças anteriores. Não adicionar SDK/framework, registros de extensão ou classe por campo sem necessidade.

## Fontes e fronteiras

Linux usa leituras limitadas e conhecidas de os-release, /proc, sysfs, disponibilidade do processo e cgroups quando acessíveis. GPU pode usar nomes expostos pelo sistema ou base PCI local opcional, sem depender de neofetch/fastfetch/lspci. Não retornar caminhos físicos ou identificadores de localização do dispositivo.

Windows usa stdlib, ctypes e winreg para campos mínimos quando disponíveis; falhas produzem null, sem exigir administrador ou ferramentas instaladas. Se algum comando fixo for necessário, deve ter timeout/limite de saída, sem shell ou interpolação de entrada. Não inspecionar ambiente de credenciais.

No container, SO pode ser da imagem, kernel/CPU podem ser compartilhados e RAM deve respeitar o escopo conhecido de cgroup. Se não houver limite/capacidade comprovável, não fingir que memória física visível é uma alocação exclusiva do container. Sem dispositivo GPU exposto, informar desconhecido. Não buscar host por Docker socket, modo privilegiado, volumes sensíveis ou inventário remoto. O ambiente do processo não equivale automaticamente ao alvo Ollama.

Disco é o agregado do sistema de arquivos do app, não inventário de discos físicos. Uptime de kernel compartilhado deve ser rotulado como tal. Resolução opcional vem do navegador e significa viewport, sem atribuição automática ao monitor/host.

## Privacidade e proteção do benchmark

Não coletar/retornar username, hostname, identificador usuário@máquina, IP/MAC, serial, UUID, nomes de discos/volumes, mounts, diretório pessoal, nomes de arquivos, lista de pacotes ou telemetria. Não guardar inventário em logs, snapshots de benchmark, CSV/JSON exportado, Cache Storage ou localStorage. Fatos de hardware combinados podem criar fingerprint; a finalidade é somente contextualizar o teste local.

Atualização de RAM/disco/uptime ocorre sob demanda e com throttle de dez segundos. Durante `running/cancelling`, devolver snapshot anterior como pausado; se não existir, campos dinâmicos ficam desconhecidos, sem coletar para completar o painel. Pausar polling de inventário no frontend durante o teste. Static facts só são lidos na inicialização da instância, sem trabalho repetitivo durante a geração.

O service worker recebe bump de cache ao mudar assets públicos; somente script/estilo genéricos podem entrar na allowlist. `/api/system` permanece sempre fora do cache. Sem alteração de rede/firewall/Ollama ou serviços de sistema.

## Critérios de aceite

- **AC-SYS-01:** fixtures diferentes em novas instâncias produzem SO/CPU/GPU/RAM diferentes, sem valores de exemplo hardcoded.
- **AC-SYS-02:** dados Linux/Windows são parseados/obtidos com fallback seguro; zero válido se distingue de desconhecido e capacidade de uso.
- **AC-SYS-03:** container possui rótulo e escopos honestos; host/GPU não expostos ficam desconhecidos sem inferir ausência física ou uso pelo Ollama.
- **AC-SYS-04:** snapshots têm timestamp/throttle; durante benchmark não há coleta dinâmica nova, I/O sob managerlock ou polling de inventário desnecessário.
- **AC-SYS-05:** endpoint/API/HTML/exportações/cache/logs não incluem identificadores proibidos; inventário não entra no estado/exportação de benchmark ou cache PWA.
- **AC-SYS-06:** faixa e painel são legíveis e equilibrados em 375 px, tablet e desktop, nos dois temas; hover/foco/toque/botão/Escape funcionam e o foco não fica preso.
- **AC-SYS-07:** suíte anterior preservada e novos testes sintéticos aprovados; QA independente, review posterior e segurança separados. Fixtures Windows não equivalem a execução real no Windows.

## BDD

**Dado** outro ambiente de execução, **quando** uma nova instância iniciar, **então** os campos refletirão esse ambiente sem recompilação ou edição manual de inventário.

**Dado** benchmark ativo, **quando** a interface solicitar atualização, **então** verá o snapshot anterior marcado como pausado, sem nova coleta dinâmica.

**Dado** container sem GPU exposta ou capacidade de host acessível, **quando** eu abrir os detalhes, **então** verei origem e indisponibilidade explícitas, sem dados fictícios de host.

**Dado** teclado ou toque em tela pequena, **quando** eu abrir Ver detalhes, **então** os dados ficarão dentro da viewport e Escape permitirá fechar mantendo navegação utilizável.

## Resultados

Implementação concluída com SystemCollector, endpoint separado e faixa/painel acessíveis. Suíte atual: 77 testes (50 preservados e 27 novos), executados com aprovação pelo agente QA independente. Workers validaram 23 testes de backend e quatro de UI, além de compilação/sintaxe. Auditoria separada de segurança não encontrou bloqueadores na coleta/privacidade; a revisão final de código segue o fluxo posterior ao QA.

A raiz verificou Docker versus execução nativa, no-store, intervalo, exportações sem inventário, Origin 403 e pausa durante benchmark real preservando timestamp/RAM. A origem Docker e valores desconhecidos ficaram explícitos. Foram verificadas seis combinações de 375/768/1280 px e temas claro/escuro, sem overflow, com hover/foco/Escape/clique mobile/Fechar.

Os valores e capturas reais permanecem locais/ignorados; este registro não contém inventário pessoal. Windows foi coberto por fixtures sintéticas, sem homologação de sistema real. Não foram implementados scripts PowerShell, Compose Windows, coletor remoto ou novos serviços. Sem commit/push nesta tarefa.

Exceção posterior autorizada pela [SDD-006](006-hostname-e-cabecalho.md): o hostname passa a ser exibido localmente nos detalhes, sem DNS, persistência, logs, exportação ou cache. A proibição original acima descreve a baseline SDD-004; os demais identificadores continuam excluídos.
