# SDD-007 — Histórico local de comparações

Registro prospectivo de 29/10/2026, criado antes da implementação. A solicitação autoriza persistir pedidos, respostas e métricas no perfil local do usuário que executa o backend. Preservar os dados ativos antes de qualquer reinício; a raiz coordena checkpoint, runtime e Docker.

## Escopo e contrato

- **RF-24:** persistir uma comparação terminal (completed, failed ou cancelled) por arquivo JSON em `Path.home() / '.ollama_benchmark'`, sem salvar fragmentos ou estados running/cancelling. Ao iniciar, recuperar a comparação terminal válida mais recente, sem fazer inferência, e restaurar formulário/modelos se ainda intocados, protegendo edições durante as chamadas assíncronas.
- **RF-25:** consultar comparações anteriores e carregar uma explicitamente, restaurando pedido, parâmetros e seleção de modelos sem iniciar teste. Carregar é recusado durante teste ativo; a interface pede confirmação antes de substituir o trabalho atual.

Repositório separado `backend/history.py`, injetado no manager pela composição. Arquivo versionado pelo campo version:1, ID UUID hex de 32 caracteres, timestamps UTC e snapshot terminal com settings/rows e informações necessárias à exportação; summary/usage são recalculados ao carregar. Não serializar token de sessão, credenciais, hostname ou inventário do sistema. O carregamento revalida o envelope e a configuração; nunca recebe caminho fornecido pelo navegador.

`GET /api/history` lista IDs/data/modelos/status e warning genérico. `POST /api/history/load` recebe objeto `{ "id": "<uuidhex>" }`, protegido por token/Host/Origin, e retorna o snapshot restaurado. ID inválido: 400; ausente/corrompido: 404; teste ativo: 409; armazenamento indisponível: erro/aviso genérico sem caminho pessoal. API e dados permanecem no-store e fora do cache PWA. Campo aditivo de estado identifica comparação/histórico e informa falha de persistência sem confundi-la com erro de inferência.

A pasta é preparada ao iniciar a instância, mesmo antes do primeiro teste; falha gera warning genérico e não impede o servidor.

## Escrita e recuperação

Diretório Linux 0700, arquivo temporário 0600, JSON UTF-8 com allow_nan=False, flush/fsync e replace atômico no mesmo diretório. Não apagar/prunar arquivos anteriores. Arquivos corrompidos são ignorados na recuperação/listagem com aviso genérico; falha de disco/permissão não derruba o app nem apaga a medição em memória. Windows usa APIs stdlib, sem afirmar garantia equivalente de ACL. Testes usam TemporaryDirectory injetado, nunca o perfil real.

Somente estados terminais são salvos. Se o processo encerrar abruptamente durante uma comparação, o andamento não será recuperado ou retomado. A última comparação salva válida continua disponível. Ao carregar histórico, nenhum comando é executado e Ollama/modelos não são instalados; modelos históricos ausentes da lista atual são sinalizados e não substituídos silenciosamente.

## Docker e privacidade

O perfil dentro do container precisa ser gravável pelo usuário 65534, com volume nomeado dedicado montado apenas na pasta do histórico; root filesystem continua read-only, sem Docker socket/privileged/mount do perfil real. Ambos Compose usam o volume do projeto. Explicar que o perfil do container não é o perfil do host e que remover volumes perde o histórico.

Prompts e respostas passam a ficar em disco local, até a pessoa gerenciar esses arquivos. Não há exclusão automática nem botão de exclusão nesta entrega. O diretório não deve entrar no Git, cache da PWA, telemetria ou relatórios públicos. A captura de tela/listagem pode revelar nomes de modelos ou pedidos; considerar ao compartilhar. Configuração do Ollama e retenção dele permanecem independentes.

## UI e aceites

Uma tabela Resultados reúne comparações atuais e anteriores por job/modelo, com data/hora original e ação Detalhes. Navegar na tabela não altera o formulário; somente confirmação de carregar substitui os detalhes/formulário. API revalida atividade para fechar corrida; abertura e carga não iniciam inferência. Manter temas/layout e não reorganizar cabeçalho ou revisão visual em andamento.

- **AC-HIST-01:** múltiplos arquivos terminais, IDs seguros, dados UTF-8 e persistência atômica; sem gravação a cada stream.
- **AC-HIST-02:** iniciar com último terminal válido, ignorando corrompidos e falhas de IO sem crash; não retomar geração interrompida.
- **AC-HIST-03:** lista/carga protegidas, validação de IDs e token, nenhuma navegação por caminhos e 409 durante running/cancelling.
- **AC-HIST-04:** formulário/pedido/modelos restaurados explicitamente, confirmação preserva trabalho em cancelamento e nenhum início automático.
- **AC-HIST-05:** dados excluem token/credenciais/inventário; erro genérico sem prompt ou caminho; cache nunca contém histórico.
- **AC-HIST-06:** volume Docker persistente/usuário sem privilégios e instruções nativas Windows/Linux, sem alegar teste Windows real.
- **AC-HIST-07:** testes de tempfile, corrupção/falha/atomicidade, restauração startup, API e UI; QA, segurança e revisão independentes.

## Responsabilidades

Worker backend: history.py, manager.py/http.py, composição app.py, Dockerfile/ambos Compose e tests/test_history.py. Worker frontend: web/history.js/history.css, integração mínima app.js/index.html e tests/test_history_ui.py. Liderança: documentação, OpenAPI e matriz. Todos preservam alterações alheias, especialmente hostname/cabeçalho/fontes/auditoria visual.

## Resultados

Implementação concluída. QA independente, auditoria de segurança e revisão final independente aprovados. A raiz validou persistência e recuperação nativa, migração da comparação existente, gravação automática de outra comparação e volume Docker com fixture isolada. A tabela unificada, confirmação, exportação do job exibido e ausência de inferência ao abrir detalhes foram verificadas no navegador. Evidências e limites estão na [E12](../rastreabilidade.md#e12--validação-sdd-007008).

Contrato final de disco: `{version:1,id,saved_at,state:{status,settings,rows,current:null,started_at,error,live:null}}`. Estado público inclui `history:{enabled,id,saved_at,saved,warning}`; saved=false pode aparecer brevemente após estado terminal enquanto a escrita termina. Limite por arquivo64MiB; lista lê arquivos sequencialmente, retendo só metadados, e latest retém apenas o melhor envelope. Sem índice ou limite global de quantidade: IO cresce com o histórico.

Refinamento explícito posterior na SDD-008: não há seção, accordion ou seletor de histórico separado. GETlist inclui summary numérico por modelo (model,repeated_count,tokens_per_s,first_text_s,wall_s,initial_wall_s), sem corpo initial completo. A tabela unificada preserva jobs/datas separados e deduplica a comparação atual pelo ID após salvar. CSV/JSON seguem o job exibido nos detalhes, não todos os arquivos.

Limite conhecido não bloqueante: uma atualização manual na pequena janela entre finalizar a geração e publicar o ID de persistência pode mostrar temporariamente duas linhas da mesma comparação. O próximo polling reconcilia o ID; não há arquivo duplicado, perda de dados ou agregação entre jobs.
