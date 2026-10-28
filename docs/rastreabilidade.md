# Rastreabilidade, validação e lacunas

Baseline documental: 28/10/2026. Relaciona [SDD](sdd.md), código atual e testes existentes. IDs T identificam testes efetivamente encontrados em [tests/test_benchmark.py](../tests/test_benchmark.py); IDs E identificam evidências/resumos de execução. Não equivalem a novos testes executados nesta edição documental.

## 1. Catálogo da suíte automatizada

Execução: `python3 -W error::ResourceWarning -m unittest discover -s tests -v`. A suíte refatorada contém **25 métodos** (24 preservados e um novo smoke da composição CLI), usa somente Python stdlib e HTTP simulado em loopback. Um método pode conter vários subcasos; A quantidade de métodos não representa porcentagem de cobertura.

| ID | Nome exato | O que demonstra |
| --- | --- | --- |
| T01 | `CalculationTests.test_metrics_and_units` | Conversão de unidades, velocidade e TTFT preservado |
| T02 | `CalculationTests.test_zero_and_missing_durations_are_not_infinite` | Duração zero/ausente não gera divisão infinita |
| T03 | `CalculationTests.test_missing_tokens_rejected` | Contagem de saída ausente é erro |
| T04 | `CalculationTests.test_validation_and_deduplication` | Tipos/limites selecionados e deduplicação ordenada |
| T05 | `CalculationTests.test_destination_restrictions` | Destinos Ollama permitidos/rejeitados selecionados |
| T06 | `CalculationTests.test_summary_excludes_initial_and_failed_rows` | Mediana das repetições, sem primeira/falhas |
| T07 | `CalculationTests.test_csv_handles_quotes_newlines_and_formulas` | CSV, caracteres especiais e neutralização de fórmula |
| T08 | `ClientTests.test_fragmented_utf8_stream_and_thinking` | NDJSON/UTF-8 fragmentado e diferença conteúdo/texto |
| T09 | `ClientTests.test_stream_error` | Erro declarado dentro do stream |
| T10 | `ClientTests.test_incomplete_stream` | Stream sem fragmento final é rejeitado |
| T11 | `ClientTests.test_cancel_unblocks_current_request` | Fechamento da conexão em leitura bloqueada |
| T12 | `ClientTests.test_timeout` | Timeout em resposta parada |
| T13 | `ClientTests.test_continuous_fragments_obey_total_deadline` | Deadline global mesmo com bytes contínuos |
| T14 | `ClientTests.test_terminal_state_published_with_current_cleared` | Estado terminal publicado com current limpo |
| T15 | `ClientTests.test_manager_sequential_execution_and_busy_rejection` | Duas execuções ordenadas e rejeição de novo início ativo |
| T16 | `ClientTests.test_missing_model_fails_without_download` | Modelo ausente não inicia geração/download |
| T17 | `ClientTests.test_cancel_prevents_remaining_executions` | Cancelamento impede repetições restantes |
| T18 | `ClientTests.test_completed_results_survive_later_error` | Resultado concluído permanece após falha posterior |
| T19 | `AppTests.test_page_assets_and_token` | Assets, token, CSP e markup do tema/script antes do CSS |
| T20 | `AppTests.test_host_and_origin_rejected` | Host, Origin e Fetch-Site inválidos são rejeitados |
| T21 | `AppTests.test_post_requires_token` | POST com token incorreto é rejeitado |
| T22 | `AppTests.test_invalid_input_and_body_size` | Casos de entrada inválida, mídia incorreta e corpo grande |
| T23 | `AppTests.test_ollama_offline_returns_clear_error` | Indisponibilidade do Ollama vira erro 502 claro |
| T24 | `AppTests.test_end_to_end_job_and_exports` | Fluxo HTTP start/state e exportações CSV/JSON |
| T25 | `CliTests.test_cli_starts_composition_root_without_ollama` | Subprocesso pela entrada app.py, porta efêmera, health e asset sem Ollama disponível |

## 2. Evidências executadas e disponibilidade

Os arquivos `TEST_RESULTS.md`, `test-results/` e relatórios locais de auditoria são **evidências locais não distribuídas no Git público**. Não existem links relativos para esses arquivos neste pacote. Operador que possui o checkout original pode consultá-los; um clone público contém o resumo abaixo e pode reproduzir os testes.

| ID | Evidência e resultado registrado | Alcance e limite |
| --- | --- | --- |
| E01 | Suíte final anterior à documentação: 24 testes aprovados no host; QA independente 11,169 s. Imagem Docker final da mesma entrega: 24 testes em 11,209 s | Linux/Python 3.12.10; HTTP simulado. A rodada de tema repetiu a suíte no host: 24 testes em 11,163 s, conforme validação do agente raiz |
| E02 | Integração nativa real `qwen3:4b`, 2×128 tokens, contexto 4.096, raciocínio desligado. Repetição: 9,024 tokens/s, primeiro texto 0,125 s, total 14,310 s | Medição pontual, não meta/SLA. Exportações locais `native-ollama.json` e `.csv` conferidas |
| E03 | Integração Docker Linux real `qwen3:4b`, 2×32 tokens: 9,844 e 9,411 tokens/s; cancelamento em geração longa terminou em cancelled e permitiu novo teste | Modelo já carregado. Quantidades diferem de E02: não comparar desempenho entre modos. `docker-cancel.json` local é um envelope de ensaio com `elapsed_s` e `state`, não o formato bruto de `/api/state` |
| E04 | Navegador gstack: seleção, início, progresso, conclusão e exportações; layouts 375×812, 768×1024 e 1280×720, sem overflow da página ou erros de console registrados | Automação externa de desenvolvimento, não dependência do app nem regressão visual permanente |
| E05 | Rodada de tema: agente raiz verificou claro/escuro, persistência após reload, fallback do sistema escuro e escrita de storage negada sem impedir troca; capturas locais dos dois temas em três viewports | Cenários de navegador executados no Linux. Cálculo complementar de 14 pares de cores CSS mostrou contraste mínimo 5,72:1; não certifica acessibilidade integral |
| E06 | Arquivos Compose passaram `config`; build e serviço Linux com rede host executados | Não comprova integração do Compose padrão no Docker Desktop |
| E07 | Refatoração SDD-001: 25 testes aprovados no host em 11,230 s e dentro da imagem Docker em 11,492 s. Agente QA independente: 25 testes em 11,226 s, sem ResourceWarning; revisão final independente aprovada | Preservados os corpos e asserções dos 24 testes anteriores; adicionado teste CLI. A integração real pós-refatoração concluiu duas gerações de 32 tokens, cancelamento e exportações CSV/JSON. Navegador confirmou conexão, resultados, claro/escuro persistentes e console sem erros |

A edição puramente documental não reinicia app/Ollama nem gera novas medições. A refatoração SDD-001 e a inclusão de tema são alterações de código autorizadas nesta rodada e têm validação própria; não devem ser confundidas com uma execução de benchmark motivada apenas por edição de Markdown. Publicação GitHub, auditoria de segredos e aprovação de segurança são uma etapa separada coordenada pelo responsável da entrega; este pacote não presume esse gate aprovado.

## 3. Requisitos funcionais

| Requisito | Implementação concreta | Testes e evidências | Lacuna / interpretação |
| --- | --- | --- | --- |
| RF-01 | [Handler.do_GET](../backend/http.py), rota models; [OllamaClient.get](../backend/ollama.py); `models()` em [JS](../web/app.js) | T19, T23, T24; E02/E03 | Catálogo vazio sem teste dedicado; descoberta não filtra capacidade de geração |
| RF-02 | `validate_settings`; formulário e coleta dos campos no JS | T04, T22; E04 | Subconjunto de limites testado, não todas as bordas |
| RF-03 | `BenchmarkManager.start/_run`; `OllamaClient.generate` | T08, T15; E02/E03 | Não isola outros clientes do Ollama |
| RF-04 | `seconds`, `metrics`, relógio/stream em `generate` | T01–T03, T08, T10; E02/E03 | Não mede GPU; TTFT é do cliente Python |
| RF-05 | `snapshot`; `render`, `poll` no JS; tabelas HTML | T24; E04 | Teste Python não executa JavaScript; UI atualiza linhas completas, sem tokens parciais |
| RF-06 | `summarize`; tabela de resumo | T06; E02/E04 | Repetida não garante carregamento/cache quente; valores null podem reduzir amostra por métrica |
| RF-07 | `BenchmarkManager.cancel`; `OllamaClient.cancel`; botão/POST | T11, T17; E03 | Não garante liberação imediata de GPU ou cancelamento global de metadados |
| RF-08 | Tratamento por linha e tratamento fatal em `_run` | T09, T10, T16, T18, T23; E03 | Caso todas as linhas falham sem teste dedicado; global completed ainda pode ocorrer |
| RF-09 | `csv_export`; GET export; links de download | T07, T24; E02/E03 | Não há importação/histórico; CSV omite response/warning |
| RF-10 | `main`, `AppServer`; Dockerfile e ambos Compose | T19/T24; E04/E06 | Windows/Desktop não executados; health somente app |
| RF-11 | GET ps antes/depois de `generate`, campos loaded_before/size_* | T15; E02/E03 | Warning posterior e falha de metadados sem teste próprio |
| RF-12 | `validate_settings`, payload think e campos HTML/JS | T04/T08; E02 | Raciocínio simulado; integração com think=true e modelo compatível não executada |
| RF-13 | IIFE do tema e listeners em `web/app.js`; seletor HTML; variáveis em CSS | T19; E05 | Comportamento do navegador não é coberto pela suíte Python; sem opção Sistema/reset |

## 4. Requisitos não funcionais

| Requisito | Implementação concreta | Testes/evidências | Situação |
| --- | --- | --- | --- |
| RNF-01 | Imports stdlib; recursos web locais; ausência de instalação de dependências | T01–T25, inspeção imports; E01 | Implementado; navegador/Ollama continuam requisitos operacionais |
| RNF-02 | `local_request`, token no POST, CSP, allowlist `OllamaClient.__init__`, Compose loopback | T05, T19–T22; E06 | Proteção local, não autenticação de usuário ou exposição pública |
| RNF-03 | `validate_settings`, limite corpo/stream/metadados/texto | T04/T22 | Cobertura parcial das bordas; sem cota global de memória/conexões |
| RNF-04 | Watchdog Timer, shutdown e deadline monotônico em `generate` | T12/T13 | Implementado para geração, não para o job inteiro/GETs de metadados |
| RNF-05 | Manager lock/event, start rejeitado, finalização atômica, snapshot por deepcopy | T14/T15/T17/T18 | Implementado; estado único compartilhado, sem transações persistidas |
| RNF-06 | Labels, estados/alertas, foco, rolagem em tabela, tema | T19; E04/E05 | Validação localizada; sem auditoria completa WCAG, leitores de tela ou matriz de navegadores |
| RNF-07 | Pathlib/stdlib, recursos locais, comandos Windows/Linux, Compose separado | E01/E06; inspeção | Linux executado; Windows e Docker Desktop continuam não verificados |

## 5. Regras de negócio

| Regra | Código/documento que a aplica | Testes/evidências |
| --- | --- | --- |
| RN-01 | Configuração única em `start`, payload comum em `generate` | T08/T15; E02/E03 |
| RN-02 | `metrics` usa contador final e duração de geração | T01–T03/T08; E02 |
| RN-03 | Phase calculada pelo número da execução; initial separado | T06/T15; E02 |
| RN-04 | `summarize` filtra completed e run>1, mediana por campo | T06 |
| RN-05 | Verificação sob lock em `start`; estado global em AppServer | T14/T15 |
| RN-06 | Event, shutdown/close e finalização cancelada | T11/T17; E03 |
| RN-07 | Somente GET tags/ps e POST generate; nenhum pull/unload/reconfiguração | T16; inspeção do cliente |
| RN-08 | Campos size_* em JSON, notas na UI e especificação | E02/E03; inspeção; sem medidor de utilização |
| RN-09 | Estado substituído em `start`, sem banco/arquivo automático | T24 exporta snapshot; inspeção; sem teste dedicado de reinício |
| RN-10 | Um worker interno não controla servidor externo; notas UI | Documentado/inspeção; não existe teste de isolamento, pois isolamento não é oferecido |

## 6. Histórias e evidências

| História | Requisitos | Evidência principal |
| --- | --- | --- |
| US-01 | RF-01 | T19/T23, E02 |
| US-02 | RF-02/RF-03 | T04/T15/T22, E04 |
| US-03 | RF-03/RF-04/RF-05/RF-11/RF-12 | T01/T08/T24, E02/E03/E04 |
| US-04 | RF-06 | T06, E02 |
| US-05 | RF-07 | T11/T17/T14, E03 |
| US-06 | RF-08 | T09/T10/T16/T18/T23 |
| US-07 | RF-09 | T07/T24, E02/E03 |
| US-08 | RF-10 e RNF-01/RNF-02/RNF-07 | T05/T19–T22, E04/E06; gaps de plataformas permanecem |
| US-09 | RF-13 e RNF-06 | T19, E05 |

## 7. Lacunas explícitas e critérios para ampliar a validação

Não há porcentagem de cobertura, teste de carga ou certificação de plataforma. Antes de ampliar suporte ou modificar as áreas abaixo, acrescentar cenários orientados pelo requisito:

- Windows nativo: iniciar, parar, medir, cancelar, exportar e validar paths/browser.
- Docker Desktop: conectividade efetiva ao Ollama host e publicação loopback da UI.
- Python 3.11 e outras versões além da 3.12 executada: rodar suíte e fluxo mínimo.
- Mais navegadores: tema, APIs de media query/storage, teclado e layout.
- Contrato HTTP: corpo truncado/UTF-8 inválido, Content-Length ausente/não inteiro, headers variantes, método não implementado, export format desconhecido e cancel com JSON escalar.
- Limites do cliente: metadados >4 MiB, linha >1 MiB, resposta >64 mil caracteres, dados de duração não finitos/negativos e metadados malformados.
- Negócio: todos os resultados falhando com global completed, warning de ps posterior, dois modelos reais e opção think=true.
- Privacidade/segurança: revisão antes de cada publicação; scanners e ignore não são prova universal de ausência de segredo.

Os cenários acima são propostas de manutenção, não funcionalidade pendente silenciosamente incluída no MVP. Para a versão local atual, lacunas são declaradas; novos requisitos de garantia precisam atualizar SDD e contrato antes de alterar código.

## 8. Rastreabilidade da refatoração SDD-001

A [especificação da mudança](changes/001-separacao-responsabilidades.md) foi criada antes das edições. Os critérios abaixo tratam separação estrutural, não uma alteração de API.

| Critério | Código / verificação | Evidência e estado |
| --- | --- | --- |
| AC-SRP-01 | Imports em app.py/tests e pacote backend; monólito removido | Inspeção e busca de callers, sem wrapper vazio |
| AC-SRP-02 | T01–T24 com imports/composição adaptados | E07: suíte final de 25 testes aprovada; comparação AST confirmou preservação dos 24 cenários anteriores |
| AC-SRP-03 | T25 | CLI real em subprocesso, porta efêmera e Ollama indisponível |
| AC-SRP-04 | `backend.http.AppServer(address, manager)` e `app.main` | Composição concreta centralizada, HTTP sem construir cliente/manager |
| AC-SRP-05 | Dockerfile copia backend e web | E07: build, suíte dentro da imagem e integração real Linux/Ollama aprovados |
| AC-SRP-06 | Documentos e links deste pacote | Links locais, referências OpenAPI e os 25 nomes de testes conferidos contra os arquivos atuais |
| AC-SRP-07 | Gates independentes QA → review e segurança separado | E07: QA e revisão aprovados; segurança e publicação possuem auditoria própria do pacote versionado |

O responsável da entrega comparou AST do snapshot anterior com os módulos refatorados: nove símbolos foram preservados sem alteração de lógica; os dois alterados foram `main` e `AppServer`, nos pontos previstos de composição/injeção. Essa inspeção é evidência estrutural complementar, não substitui a execução da suíte ou integração real.
