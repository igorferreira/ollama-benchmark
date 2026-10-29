# Rastreabilidade, validação e lacunas

Baseline documental: 28/10/2026. Relaciona [SDD](sdd.md), código atual e testes existentes. IDs T identificam testes efetivamente encontrados em [tests/test_benchmark.py](../tests/test_benchmark.py); IDs E identificam evidências/resumos de execução. Não equivalem a novos testes executados nesta edição documental.

## 1. Catálogo da suíte automatizada

Execução: `python3 -W error::ResourceWarning -m unittest discover -s tests -v`. A suíte atual contém **119 métodos**: 82 preservados até SDD-006, 14 de persistência, quatro de histórico/UI refinada e 19 de ciclo de vida (SDD-009). Um método pode conter vários subcasos; a quantidade de métodos não representa porcentagem de cobertura.

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
| T26 | `AppTests.test_pwa_manifest_and_binary_icons` | Manifesto instalável e dimensões/assinatura MIME dos ícones PNG |
| T27 | `AppTests.test_pwa_assets_preserve_origin_and_token_boundaries` | Assets PWA sem token, origem/CSP preservadas e caminhos não autorizados rejeitados |
| T28 | `TokenUsageTests.test_live_count_option_is_strict_and_disabled_by_default` | Opção booleana estrita e desligada por padrão |
| T29 | `TokenUsageTests.test_cache_is_separate_from_input_plus_output` | Cache separado da soma entrada+saída |
| T30 | `TokenUsageTests.test_missing_invalid_and_zero_counters` | Ausência, valores inválidos e zero preservam semântica |
| T31 | `TokenUsageTests.test_accumulated_usage_excludes_failed_and_cancelled` | Acumulado exclui linhas falhas e canceladas |
| T32 | `TokenUsageTests.test_missing_counter_does_not_silently_become_zero` | Contador ausente não vira zero silenciosamente |
| T33 | `TokenUsageTests.test_csv_contains_total_without_changing_old_columns` | CSV inclui total, opção e conferência sem remover colunas antigas |
| T34 | `LiveClientTests.test_logprob_entries_not_chunks_count_observed_tokens` | Cinco entradas em dois fragmentos produzem cinco tokens observados |
| T35 | `LiveClientTests.test_logprob_mismatch_keeps_final_authoritative` | Divergência preserva autoridade do contador final |
| T36 | `LiveClientTests.test_missing_or_malformed_logprobs_invalidates_attempt` | Metadata ausente, vazia ou malformada invalida observação completa |
| T37 | `LiveClientTests.test_unsupported_logprobs_fails_without_retry` | API incompatível falha sem repetir inferência |
| T38 | `LiveClientTests.test_cancelled_observation_is_not_presented_as_a_final_count` | Cancelamento não apresenta observação provisória como total final |
| T39 | `LiveClientTests.test_disabled_observation_does_not_change_payload` | Opção desligada mantém payload sem logprobs |
| T40 | `LiveClientTests.test_progress_stays_pending_until_authoritative_final` | Progresso permanece sem contadores finais até done |
| T41 | `LiveClientTests.test_fast_chunks_throttled_but_last_preview_published` | Publicações limitadas com última prévia garantida |
| T42 | `LiveClientTests.test_preview_bounded_and_reasoning_only_counted` | Prévia limitada e raciocínio contado sem preservar seu texto |
| T43 | `LiveClientTests.test_error_publishes_last_incomplete_preview_without_tokens` | Erro publica última prévia incompleta sem tokens finais |
| T44 | `LiveClientTests.test_manager_partial_snapshot_precedes_done_and_clock_advances` | Snapshot parcial antes de done e cronômetro avançando |
| T45 | `LiveClientTests.test_cancel_retains_incomplete_preview_and_new_job_resets` | Cancelamento preserva prévia incompleta; novo teste limpa estado |
| T46 | `FaqTests.test_faq_public_without_ollama_token_or_api_script` | FAQ pública sem Ollama, token ou script de API |
| T47 | `FaqTests.test_faq_anchors_assets_and_shared_theme` | Âncoras, assets e tema compartilhado |
| T48 | `FaqTests.test_faq_and_help_keep_local_http_boundary` | FAQ/helper preservam Host/Origin/CSP locais |
| T49 | `FaqTests.test_cache_contains_only_explicit_public_resources` | Cache contém somente recursos públicos explicitamente permitidos |
| T50 | `FaqTests.test_help_labels_and_preview_do_not_remove_form_accessibility` | Ajuda e prévia preservam rótulos e acessibilidade do formulário |
| T51 | `SystemFixtureTests.test_distinct_instances_use_their_own_static_facts` | Instâncias distintas usam seus próprios fatos, sem inventário fixo |
| T52 | `SystemFixtureTests.test_malformed_static_sources_fall_back_to_unknown` | Fonte estática/seções/modelos malformados resultam em desconhecido |
| T53 | `SystemFixtureTests.test_static_source_read_once_and_dynamic_throttled` | Fatos estáticos uma vez e dados dinâmicos com throttle |
| T54 | `SystemFixtureTests.test_busy_without_previous_snapshot_does_not_collect` | Teste ativo sem snapshot não inicia coleta |
| T55 | `SystemFixtureTests.test_busy_preserves_previous_snapshot_and_refreshes_afterward` | Pausa preserva snapshot e retomada atualiza depois do intervalo |
| T56 | `SystemFixtureTests.test_dynamic_collection_does_not_hold_collector_lock` | I/O dinâmico não segura lock do coletor |
| T57 | `SystemFixtureTests.test_failures_keep_unknown_distinct_from_zero_and_throttle_retries` | Falha/zero/ausência distintos e novas tentativas limitadas |
| T58 | `SystemFixtureTests.test_extra_identifiers_are_not_serialized_or_persisted` | Campos extras de identificação não são serializados/persistidos |
| T59 | `LinuxSourceTests.test_linux_static_uses_whitelisted_model_and_optional_pci_names` | Linux usa campos de modelo permitidos e base PCI opcional |
| T60 | `LinuxSourceTests.test_native_memory_and_uptime_units` | Unidades de RAM e uptime Linux |
| T61 | `LinuxSourceTests.test_container_without_limit_or_device_does_not_invent_host_capacity` | Container sem limite/dispositivo não inventa capacidade de host |
| T62 | `LinuxSourceTests.test_cgroup_v2_uses_lowest_known_ancestor_limit` | Cgroup v2 respeita menor limite ancestral conhecido |
| T63 | `LinuxSourceTests.test_cgroup_v1_and_unlimited_sentinel` | Cgroup v1 e sentinela de limite não definido |
| T64 | `LinuxSourceTests.test_inconsistent_memory_and_missing_sources_stay_unknown` | Memória inconsistente/fontes ausentes permanecem desconhecidas |
| T65 | `WindowsSourceTests.test_memory_structure_and_uptime_use_64_bit_api` | Windows estrutura/API de memória e uptime em 64 bits |
| T66 | `WindowsSourceTests.test_windows_registry_and_display_sources_return_only_model_labels` | Registro/display Windows retornam somente rótulos de modelo |
| T67 | `WindowsSourceTests.test_windows_architecture_from_native_machine_api` | Arquitetura Windows por API nativa simulada |
| T68 | `WindowsSourceTests.test_windows_static_fixture_and_safe_failures` | Fixtures Windows e falhas seguras |
| T69 | `SystemHttpTests.test_system_endpoint_no_store_and_outside_benchmark_exports` | Endpoint no-store e inventário separado de exportações |
| T70 | `SystemHttpTests.test_dynamic_source_runs_outside_manager_lock` | Coleta dinâmica fora do lock do manager |
| T71 | `SystemHttpTests.test_busy_route_uses_cached_data_without_io_under_manager_lock` | Endpoint pausado reutiliza snapshot sem I/O sob managerlock |
| T72 | `SystemHttpTests.test_unexpected_collector_exception_is_generic_and_private` | Exceção inesperada vira erro genérico sem detalhe privado |
| T73 | `SystemHttpTests.test_host_origin_and_absent_collector` | Host/Origin rejeitados e coletor ausente retorna 503 |
| T74 | `SystemUiTests.test_environment_strip_placeholders_and_accessible_details` | Faixa com placeholders e detalhes acessíveis |
| T75 | `SystemUiTests.test_system_script_is_separate_public_and_not_on_faq` | Script de sistema separado e ausente da FAQ |
| T76 | `SystemUiTests.test_inventory_is_never_added_to_public_cache_or_benchmark_export` | Inventário não entra no cache público ou exportação |
| T77 | `SystemUiTests.test_public_script_preserves_origin_and_payload_boundaries` | Asset público mantém origem e apresentação por textContent |
| T78 | `SystemFixtureTests.test_requested_hostname_is_sanitized_and_failure_is_unknown` | Hostname sintético sanitizado, limitado e nullable em falha |
| T79 | `PromptTests.test_catalog_has_eighteen_unique_synthetic_examples_in_six_cells` | Catálogo de 18 exemplos, cobertura de seis células e conteúdo público |
| T80 | `PromptTests.test_dialog_is_outside_benchmark_form_and_controls_are_labelled` | Dialog fora do formulário, labels, posição do botão e cabeçalho |
| T81 | `PromptTests.test_assets_keep_csp_host_origin_and_no_token_boundary` | Assets com CSP/Host/Origin/no-store, sem token |
| T82 | `PromptTests.test_catalog_never_uses_inference_persistence_or_offline_cache` | Sem inferência/persistência/cache do catálogo |
| T83 | `HistoryTests.test_multiple_snapshots_restore_latest_and_utf8` | Persistência/recuperação/API com dados sintéticos em diretório temporário |
| T84 | `HistoryTests.test_startup_creates_private_folder_and_io_failure_is_nonfatal` | Persistência/recuperação/API com dados sintéticos em diretório temporário |
| T85 | `HistoryTests.test_permissions_atomic_and_no_temporary_left` | Persistência/recuperação/API com dados sintéticos em diretório temporário |
| T86 | `HistoryTests.test_storage_failure_is_nonfatal_and_generic` | Persistência/recuperação/API com dados sintéticos em diretório temporário |
| T87 | `HistoryTests.test_projection_excludes_session_inventory_and_unknown_nested_fields` | Persistência/recuperação/API com dados sintéticos em diretório temporário |
| T88 | `HistoryTests.test_corrupt_invalid_nonterminal_and_nonfinite_are_ignored` | Persistência/recuperação/API com dados sintéticos em diretório temporário |
| T89 | `HistoryTests.test_ids_and_symlinks_do_not_escape_directory` | Persistência/recuperação/API com dados sintéticos em diretório temporário |
| T90 | `HistoryTests.test_oversize_file_is_rejected_before_json_parsing` | Persistência/recuperação/API com dados sintéticos em diretório temporário |
| T91 | `HistoryTests.test_manager_saves_once_outside_lock_and_restores_without_generation` | Persistência/recuperação/API com dados sintéticos em diretório temporário |
| T92 | `HistoryTests.test_failed_and_cancelled_jobs_are_saved_once_without_resume` | Persistência/recuperação/API com dados sintéticos em diretório temporário |
| T93 | `HistoryTests.test_load_revalidates_after_concurrent_start_without_lock_during_io` | Persistência/recuperação/API com dados sintéticos em diretório temporário |
| T94 | `HistoryTests.test_old_save_does_not_overwrite_new_comparison_metadata` | Persistência/recuperação/API com dados sintéticos em diretório temporário |
| T95 | `HistoryTests.test_http_protections_list_load_and_busy` | Persistência/recuperação/API com dados sintéticos em diretório temporário |
| T96 | `HistoryUiTests.test_history_requires_explicit_confirmation_and_is_outside_form` | Histórico e apresentação/refinamento responsivo sem executar inferência |
| T97 | `HistoryUiTests.test_history_assets_keep_token_and_local_http_boundary` | Histórico e apresentação/refinamento responsivo sem executar inferência |
| T98 | `HistoryUiTests.test_summary_first_units_legend_and_readable_detail_structure` | Histórico e apresentação/refinamento responsivo sem executar inferência |
| T99 | `HistoryUiTests.test_startup_and_polling_guards_and_light_input_contrast` | Histórico e apresentação/refinamento responsivo sem executar inferência |
| T100 | `HistoryTests.test_list_projects_separate_model_summaries_without_prompt_or_response` | Duas comparações/datas separadas, métricas numéricas por modelo e nenhum texto privado na lista |
| T101 | `ServiceTests.test_state_missing_corrupt_or_other_checkout_never_controls_a_process` | Ciclo de vida local, identidade segura e isolamento dos recursos do checkout |
| T102 | `ServiceTests.test_state_requires_creation_executable_and_this_exact_command` | Ciclo de vida local, identidade segura e isolamento dos recursos do checkout |
| T103 | `ServiceTests.test_atomic_state_is_private_and_keeps_previous_file_on_replace_failure` | Ciclo de vida local, identidade segura e isolamento dos recursos do checkout |
| T104 | `ServiceTests.test_start_is_idempotent_for_the_recorded_process` | Ciclo de vida local, identidade segura e isolamento dos recursos do checkout |
| T105 | `ServiceTests.test_reused_pid_refuses_start_and_stop_without_signalling` | Ciclo de vida local, identidade segura e isolamento dos recursos do checkout |
| T106 | `ServiceTests.test_port_collision_does_not_spawn_or_stop_other_servers` | Ciclo de vida local, identidade segura e isolamento dos recursos do checkout |
| T107 | `ServiceTests.test_stop_missing_or_dead_is_idempotent_without_any_signal` | Ciclo de vida local, identidade segura e isolamento dos recursos do checkout |
| T108 | `ServiceTests.test_stop_signals_only_the_validated_pidfd` | Ciclo de vida local, identidade segura e isolamento dos recursos do checkout |
| T109 | `ServiceTests.test_identity_change_after_opening_pidfd_preserves_state_and_sends_nothing` | Ciclo de vida local, identidade segura e isolamento dos recursos do checkout |
| T110 | `ServiceTests.test_lifecycle_lock_refuses_concurrent_controller_then_releases` | Ciclo de vida local, identidade segura e isolamento dos recursos do checkout |
| T111 | `ServiceTests.test_compose_is_scoped_to_checkout_and_does_not_remove_volumes` | Ciclo de vida local, identidade segura e isolamento dos recursos do checkout |
| T112 | `ServiceTests.test_docker_start_refuses_occupied_port_without_healthy_project_container` | Ciclo de vida local, identidade segura e isolamento dos recursos do checkout |
| T113 | `ServiceTests.test_docker_start_is_idempotent_only_for_healthy_project_container` | Ciclo de vida local, identidade segura e isolamento dos recursos do checkout |
| T114 | `ServiceTests.test_compose_success_without_confirmed_readiness_is_failure` | Ciclo de vida local, identidade segura e isolamento dos recursos do checkout |
| T115 | `ServiceTests.test_container_health_rejects_native_app_or_other_hostname` | Ciclo de vida local, identidade segura e isolamento dos recursos do checkout |
| T116 | `ServiceTests.test_compose_ownership_checks_stopped_containers_checkout_and_config` | Ciclo de vida local, identidade segura e isolamento dos recursos do checkout |
| T117 | `ServiceTests.test_compose_refuses_wrong_ownership_before_start_or_stop` | Ciclo de vida local, identidade segura e isolamento dos recursos do checkout |
| T118 | `ServiceTests.test_operational_symlinks_and_reparse_attributes_never_touch_the_target` | Ciclo de vida local, identidade segura e isolamento dos recursos do checkout |
| T119 | `PowerShellWrapperTests.test_multiple_python_commands_choose_one_without_running_the_app` | Múltiplos resultados Get-Command, caminhos Unicode/espaços e encaminhamento dos wrappers sem executar app real |

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

### PWA — evidência de 29/10/2026

A SDD-002 adicionou T26 e T27. Suíte no host: 27 testes em 12,760 s; agente QA independente: 27 testes em 13,241 s, sem ResourceWarning. No navegador Chromium de teste, o service worker foi registrado e assumiu controle; o cache continha exatamente oito recursos públicos, sem raiz ou URLs de API mesmo após GET de exportação e POST de cancelamento com conteúdo sintético. Com o container do app parado, a navegação abriu a página offline sem token ou resultados; após iniciar novamente, a página principal voltou com conexão ao Ollama. Layouts mobile/tablet/desktop e console verificados. Instalação gráfica no sistema operacional não foi executada.

## 3. Requisitos funcionais

| Requisito | Implementação concreta | Testes e evidências | Lacuna / interpretação |
| --- | --- | --- | --- |
| RF-01 | [Handler.do_GET](../backend/http.py), rota models; [OllamaClient.get](../backend/ollama.py); `models()` em [JS](../web/app.js) | T19, T23, T24; E02/E03 | Catálogo vazio sem teste dedicado; descoberta não filtra capacidade de geração |
| RF-02 | `validate_settings`; formulário e coleta dos campos no JS | T04, T22; E04 | Subconjunto de limites testado, não todas as bordas |
| RF-03 | `BenchmarkManager.start/_run`; `OllamaClient.generate` | T08, T15; E02/E03 | Não isola outros clientes do Ollama |
| RF-04 | `seconds`, `metrics`, relógio/stream em `generate` | T01–T03, T08, T10; E02/E03 | Não mede GPU; TTFT é do cliente Python |
| RF-05 | `snapshot`; `render`, `poll` no JS; tabelas HTML | T24; E04 | Teste Python não executa JavaScript; Linhas finais continuam completas; SDD-003 acrescenta prévia e observação opcional separadas |
| RF-06 | `summarize`; tabela de resumo | T06; E02/E04 | Repetida não garante carregamento/cache quente; valores null podem reduzir amostra por métrica |
| RF-07 | `BenchmarkManager.cancel`; `OllamaClient.cancel`; botão/POST | T11, T17; E03 | Não garante liberação imediata de GPU ou cancelamento global de metadados |
| RF-08 | Tratamento por linha e tratamento fatal em `_run` | T09, T10, T16, T18, T23; E03 | Caso todas as linhas falham sem teste dedicado; global completed ainda pode ocorrer |
| RF-09 | `csv_export`; GET export; links de download | T07, T24; E02/E03 | Não há importação/histórico; CSV omite response/warning |
| RF-10 | `main`, `AppServer`; Dockerfile e ambos Compose | T19/T24; E04/E06 | Windows/Desktop não executados; health somente app |
| RF-11 | GET ps antes/depois de `generate`, campos loaded_before/size_* | T15; E02/E03 | Warning posterior e falha de metadados sem teste próprio |
| RF-12 | `validate_settings`, payload think e campos HTML/JS | T04/T08; E02 | Raciocínio simulado; integração com think=true e modelo compatível não executada |
| RF-13 | IIFE do tema e listeners em `web/help.js`; seletor HTML; variáveis em CSS | T19; E05 | Comportamento do navegador não é coberto pela suíte Python; sem opção Sistema/reset |
| RF-14 | `web/pwa.js`, `web/sw.js`, manifesto, ícones e `STATIC_ASSETS` | T26/T27; SDD-002 | Instalação depende do navegador; requer servidores ligados; Cache Storage não inclui dados de benchmark |
| RF-15 | `OllamaClient.generate(progress=...)`, `BenchmarkManager.snapshot`, painel live | T34–T45; SDD-003 | Atualização por polling; tokens gerais somente finais; observado opcional via metadata |
| RF-16 | `token_count`, `metrics`, `usage`, CSV, painéis de contadores | T28–T33/T35/T36; SDD-003 | Acumulado só completed; não é fatura ou monitor global |
| RF-17 | `/faq.html`, `/help.js`, allowlist SWv2 | T46–T49 | FAQ pública sem API/token; consulta offline requer cache anterior |
| RF-18 | Tooltips compartilhados em help.js, labels e foco | T50; navegador a validar nesta entrega | Teste HTTP não substitui interação real com mouse/teclado/toque |
| RF-19 | `SystemCollector`, composição e `/api/system`; `web/system.js` | T51–T58/T59–T68/T69/T75 | Ambiente do backend; não inventário do host/Ollama; Windows real ainda não executado |
| RF-20 | `snapshot(busy=...)`, `manager.is_active`, faixa/painel e evento benchmark-status | T53–T57/T70/T71/T74; E10 | Snapshot timestamp/throttle; inspeção de browser cobre interação além do teste estático |

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
| RNF-08 | Allowlist de campos, fontes fixas/injetáveis, cópia volátil e API separada | T58/T69/T72/T73/T76/T77 | Não há inventário em cache/exportações; fatos combinados ainda podem formar fingerprint |

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

## 9. Mudança SDD-003 e cobertura específica

Os testes T28–T45 estão em `tests/test_live.py`; T46–T50 em `tests/test_faq.py`. Os nomes exatos acima foram extraídos dos métodos reais, sem alegar cobertura integral da UI pelo Python.

| Critério | Testes principais | Observação |
| --- | --- | --- |
| AC-RT-01 | T40/T44 | Snapshot parcial antes de done, sem converter fragmentos em tokens |
| AC-RT-02 | T29/T30/T34–T36 | Entrada/saída/cache/total, metadata por token e reconciliação final |
| AC-RT-03 | T31/T32 | Falhas/cancelamentos fora do acumulado; ausência não vira zero |
| AC-RT-04 | T37/T38/T43–T45 e suíte anterior de deadline/cancelamento | Sem retry em incompatibilidade; preservação/reset de prévia |
| AC-RT-05 | T41/T42 | Throttle e última publicação; limite de prévia e raciocínio sem texto persistido |
| AC-RT-06 | T46–T49 | Assets públicos e cache sem token/API/dados |
| AC-RT-07 | T50 e validação de navegador desta entrega | Interação real/contraste/layout não são certificados pelo parse de HTML |
| AC-RT-08 | Gate final desta entrega | QA independente, review posterior e segurança separado; sem commit/publicação nesta tarefa |

### E08 — SDD-003, validação de 29/10/2026

QA independente: **50 testes aprovados em 19,866 s**, exit 0, sem ResourceWarning. Review posterior independente: **APROVADO**, sem alteração de arquivos. Essa aprovação pertence ao código novo, não foi herdada da baseline.

A raiz executou integração real no Docker Linux com `qwen3:4b`, opção instrumentada ligada e duas saídas de 128 tokens. Capturou 202 snapshots: antes de done havia saída observada positiva com contadores finais ainda null; no fim ambos resultados tiveram observed 128=eval_count 128 e status matched. Entrada 34 / saída 128/total 162 por resultado; acumulado 68/256/324, cache null quando ausente. Uma observação visual durante o stream mostrou 79 tokens observados e prévia de 370 caracteres, sem copiar o texto gerado para esta documentação.

Navegador confirmou hover, foco de teclado, Escape e toque com tooltip dentro da viewport 375×812 sem overflow; FAQ com 16 perguntas sem token ou campo de prompt; layouts em três viewports e dois temas. Os cenários automatizados conferem dez assets públicos no cache e exclusão de raiz/API/token/dados; o snapshot de segurança é coordenado pela raiz.

Artefato de contadores/snapshots sem texto: `test-results/live-faq-real.json` (local, ignorado, não distribuído). Não há homologação Windows/Docker Desktop, monitoramento global de uso ou auditoria de cobrança de terceiros.

### E09 — FAQ offline e recuperação

Depois de preservar exportações locais e parar efetivamente o container do app, a raiz recarregou a FAQ controlada pelo service worker: 16 perguntas, tema escuro e ausência de token da sessão. A navegação fez somente três GETs públicos de FAQ, helper e CSS, sem chamadas de API. Cache v2 confirmado com dez recursos públicos e nenhuma raiz/API. Após restaurar o Compose, health e formulário do app voltaram. Esse ensaio não significa benchmark offline: gerar continua exigindo app e Ollama disponíveis.

## 10. Mudança SDD-004: inventário e visual

T51–T73 pertencem a `tests/test_system.py`; T74–T77 a `tests/test_system_ui.py`. Todas as fixtures de hardware usadas por esses testes são sintéticas, sem copiar a configuração pessoal de um exemplo.

| Critério | Testes principais / evidência |
| --- | --- |
| AC-SYS-01 | T51/T53, instâncias/fontes diferentes |
| AC-SYS-02 | T52/T57/T59/T60/T64–T68 |
| AC-SYS-03 | T61–T63; comparação real de modos da E10 |
| AC-SYS-04 | T53–T56/T70/T71; pausa real durante running na E10 |
| AC-SYS-05 | T58/T69/T72/T73/T76/T77 |
| AC-SYS-06 | T74 e verificação visual/interação real da E10 |
| AC-SYS-07 | Suíte completa de 77 testes, QA independente e fechamento da entrega; Windows somente fixtures |

### E10 — Resumo dinâmico do ambiente, 29/10/2026

QA independente executou 77 testes com ResourceWarning como erro: todos passaram. Os workers verificaram 23 testes de sistema em 2,526 s e quatro de UI em 0,519 s; estes checks não substituem o gate independente da suíte completa. Auditoria de segurança separada registrou 27 cenários SYS aprovados e scanner sem achados em 57 candidatos/53 textos; evidências detalhadas são locais/ignoradas, não dados pessoais distribuídos com o código.

A raiz comparou o app em Docker e uma instância nativa: rótulos/escopos distintos, API no-store, intervalo mínimo de dez segundos, inventário ausente das exportações e Origin inválida rejeitada. Docker apresentou RAM/GPU desconhecidas onde não comprováveis, sem inventar host; o modo nativo apresentou os campos conhecidos do ambiente real. Nenhum valor pessoal desse inventário é reproduzido nesta matriz.

Durante benchmark real em running, a raiz confirmou resposta com paused=true e timestamp/RAM anteriores preservados. A coleta não é monitor global nem prova que a GPU indicada executa o modelo.

Visual e interação foram conferidos em 375/768/1280 px nos temas claro/escuro: sem overflow, hover/foco/Escape, clique mobile e Fechar, com painel legível. Capturas são locais ignoradas. Windows/Docker Desktop não foram executados; fixtures de ctypes/registro não homologam uma instalação Windows real.

## SDD-005/006 — Biblioteca e identificação local

| Requisito/aceite | Código | Verificação e limite |
| --- | --- | --- |
| RF-21 / AC-PROMPT-01/02 | web/prompts.js catálogo, renderList e preview | T79/T80; filtros/seleção/empty state também exigem navegador |
| RF-22 / AC-PROMPT-03/04/05 | controls, needsConfirmation, handler apply e benchmark-status | T80/T82 verificam fronteiras estáticas; proteção de edição e bloqueio dinâmico exigem navegador |
| AC-PROMPT-06 | dialog nativo e prompts.css | T80; teclado, mobile e temas exigem navegador |
| AC-PROMPT-07 | STATIC_ASSETS e SW v3 | T81/T82, T26/T27/T49 |
| RF-23 / AC-HOST-01/02 | _hostname, SystemCollector, system.js | T78 e inspeção navegador; hostname fixture example-host, nunca inventário real versionado |
| AC-HOST-03 | header index.html | T80 e inspeção visual |
| AC-HOST-04 / AC-PROMPT-08 | isolamento manager/cache e gates | T58/T69/T72/T81/T82; QA automatizado e navegador aprovados; revisão final independente APROVADA |

Os testes novos não substituem testes comportamentais reais do dialog. Windows real continua não executado. A identificação técnica local da SDD-006 é exceção autorizada à baseline que excluía hostname; não autoriza demais identificadores, coleta remota ou publicação de inventário.

### E11 — Biblioteca de pedidos e hostname, 29/10/2026

Suíte de desenvolvimento: 82 testes aprovados em 23,480 s com ResourceWarning como erro. QA independente automatizado: 82 aprovados em 23,404 s; sintaxe JS e diff limpos, 42 referências OpenAPI resolvidas e 82 métodos na matriz. Auditoria de segurança separada: 62 candidatos/58 textos sem achados, testes de biblioteca/SYS aprovados.

A raiz validou em navegador os 18 pedidos e seis células, filtros, prévia, confirmação de substituição, invalidação da confirmação após edição, bloqueio durante teste e corrida local, Escape/restauração de foco, parâmetros preservados e nenhuma chamada de início de benchmark por navegação/aplicação. Em 375/768/1280 px nos dois temas, não houve overflow e as ações permaneceram visíveis. Botão alinhado ao h2 à direita, guia sob o título e eyebrow removido.

Hostname foi exibido nos detalhes com rótulo do container; a coleta nativa correspondeu à fonte local sem reproduzir o identificador em evidência pública. Continua fora de exportações/cache/logs. Relatórios e capturas são locais ignorados. Windows real e toque físico não executados. QA final independente **APROVADO** com as evidências automatizadas e de navegador acima; revisão posterior independente APROVADA.

A revisão identificou um conflito real de Escape: painéis/ajudas atrás do dialog podiam consumir a tecla antes do fechamento modal. Corrigidos os dois handlers globais de `system.js` e `help.js` para ceder a `dialog[open]`; revisão agrupada dos cinco módulos de UI não encontrou outro conflito. Revalidação independente: suíte 82/82 em 23,417 s após o ajuste SYS; após a última guarda de ajuda, FAQ cinco testes em 0,543 s e SYS UI quatro em 0,517 s, além de sintaxe de todos os scripts e diff limpos. A validação dirigida evita repetir toda a suíte por uma guarda isolada e não implica novos testes Windows.

No build final, a raiz abriu simultaneamente painel SYS fixado, tooltip por hover e biblioteca por Enter: o primeiro Escape fechou somente o dialog e devolveu foco ao botão; o segundo fechou painel/tooltip. Fluxo integral da biblioteca repetido sem inferência. QA final independente **APROVADO** após essas evidências e a revalidação dirigida.

Fechamento: **QA APROVADO**, **review independente posterior APROVADO** e auditoria de segurança **APROVADA**. Nenhum commit/push ou alteração de serviço/Ollama foi feito pela equipe de implementação. Windows real permanece não executado.

## SDD-007/008 — Histórico terminal e apresentação

| Requisito/critério | Código | Verificação |
| --- | --- | --- |
| RF-24 / AC-HIST-01/02 | backend/history.py, composição app.py e finally do manager | T83–T92; startup/criação/corrupção/IO/atômico/failed/cancelled; crash ativo é lacuna intencional sem retomada |
| RF-25 / AC-HIST-03 | history_list/load_history e HTTP | T93–T95, Host/Origin/token/IDs/409/geração concorrente |
| AC-HIST-04 | app.js restoreSettings/stateRevision e history.js | T96/T99; edição durante fetch e confirmação exigem navegador |
| AC-HIST-05 | terminal_state allowlist e SWv4 | T87/T97/T49/T76; sem inventário/token/cache no histórico |
| AC-HIST-06 | Dockerfile/Compose volume e HOME | Config/build/runtime pela raiz; Windows real pendente |
| RF-26 / AC-UX-01/02/03/08/10/11 | comparativo unificado com datas, unidades, modelos limitados, CSS | T96/T98/T99; hierarchy/mobile/contraste real complementam no browser |
| AC-UX-04/05 | catálogo mobile, help.js/style.css | T50/T80/T98; foco/hover/toque e prioridade Escape exigem browser |
| AC-UX-06/07 | app.js poll e offline.html | T99/T98, visibilidade/backoff/sem timers duplicados e offline visual no browser |
| AC-HIST-07 | Gates independentes | E12: QA, segurança e revisão final aprovados nesta entrega |

T83–T95 e T100 estão em tests/test_history.py; T96–T99 em tests/test_history_ui.py. CliTests agora isola HOME/USERPROFILE com diretório temporário para não ler o perfil real ao iniciar app.py.

### E12 — Validação SDD-007/008

Workers: suíte anterior ao último ajuste de startup, 98 testes em 24,423 s com ResourceWarning como erro; checks finais dirigidos 13 testes de histórico e quatro de UI aprovados. Esses checks não equivalem ao gate independente final de 100 testes. Browser, Docker/volume, QA, auditoria de segurança e revisão finais serão registrados após execução pela raiz.

A solução intermediária de accordion/seletor de histórico foi retirada antes do gate. O contrato final usa a tabela única Resultados, linhas job/modelo com data/hora original, metadata summary numérica (T100), detalhes com confirmação e exportação somente do job exibido. Instalação permanece no details opcional do rodapé.


A raiz validou o runtime nativo atualizado: preservou a comparação anterior de duas execuções, migrou-a para o histórico do perfil e confirmou a restauração após reinício. Duas novas execuções reais, com saída limitada a oito tokens, geraram outro JSON automaticamente sem apagar o anterior. Diretório Linux 0700 e arquivos 0600 foram verificados; a listagem retornou somente metadata/summary numérico previsto.

Em um perfil sintético isolado, o navegador validou múltiplas comparações/datas, métricas separadas por job, confirmação, exportação do job exibido e nenhuma inferência ao abrir detalhes. Seis combinações de viewport/tema passaram sem overflow global; ajuda ancorada de 44 px, foco da prévia e SW v4 sem dados privados foram conferidos. A confirmação final da tabela mantém aviso de rolagem visível também no desktop, cabeçalhos/Estado com quebra e horário com fonte mínima de 12 px.

O teste Docker usou somente fixture e volume temporários dedicados: UID 65534, root filesystem read-only, salvamento e recuperação após recriação aprovados; recursos de teste removidos pela raiz. A aplicação principal permanece nativa. Estas evidências não homologam Windows real, toque físico ou leitor de tela. QA automatizado e segurança separados foram informados pela raiz; o fechamento abaixo registra o gate final.


Fechamento independente: **QA APROVADO**, **auditoria de segurança APROVADA** e **review posterior APROVADO**. A suíte completa executou 100 métodos em 23,932 s: 99 passaram e um assert dependente de espaçamento foi corrigido sem alterar produção; os quatro testes UI passaram novamente em 0,521 s. Após o patch final HTML/CSS, quatro UI passaram em 0,517 s. Sintaxe JavaScript, diff, ambos Compose e contrato OpenAPI foram verificados: 100 métodos na matriz, 28 rotas e 61 referências resolvidas. A raiz confirmou visualmente a tabela após a última alteração.

A revisão registrou uma observação P2 não bloqueante: uma atualização manual na microjanela entre o estado terminal e a publicação do history.id pode duplicar temporariamente a linha corrente até o próximo polling. Não duplica o arquivo persistido, não perde dados e não mistura métricas entre jobs. Não se alega invariância visual absoluta nessa janela. Windows real, leitor de tela e toque físico continuam não homologados. Nenhum commit/push foi realizado nesta entrega.


## SDD-009 — Ciclo de vida na raiz

T101–T119 estão em tests/test_service.py e cobrem estado local inválido/ausente, identidade e PID reutilizado, atomicidade, idempotência, lock, porta ocupada, sinal por pidfd, argumentos Compose, prontidão do container e propriedade do checkout, além de symlink/reparse/arquivos especiais. A equipe de implementação executou os 18 com ResourceWarning como erro; Bash passou shellcheck e os scripts PowerShell passaram parsing via pwsh no Linux. A evidência E13 abaixo registra runtime e gates desta extensão. Não equivale a homologação Windows real.

A regressão de resolução PowerShell acrescentou T119: a fixture retorna dois executáveis para Get-Command e confirma que cada wrapper usa somente o primeiro, inclusive em caminhos com espaços/Unicode. Os 19 testes de lifecycle passaram no Linux; nenhum app real foi iniciado pela fixture.


### E13 — Validação SDD-009

QA independente **APROVADO**: suíte base 118/118 em 24,423 s; após os ajustes dirigidos, Service 19/19 em 1,132 s. A união contém 119 métodos, todos presentes na matriz. Shellcheck, bash -n, parser PowerShell via pwsh Linux, diff e links passaram; contrato preservado em 28 rotas/61 referências. Segurança do helper e revisão final independente desta extensão foram aprovadas separadamente.

A raiz validou ciclo real Bash e PowerShell 7 no Linux: start/stop, idempotência, recusa de porta ocupada e de instância não gerenciada, prontidão Docker do próprio checkout e preservação dos dois arquivos de comparações anteriores. Um checkout sintético com espaços/Unicode foi exercitado desde cwd externo, sem usar o perfil real nessa fixture. A aplicação final ficou nativa em 127.0.0.1:8765 pelo start.sh, com Docker parado e históricos preservados. Arquivos service-runtime.local.json e service-spaces.local.json são evidências ignoradas, não documentação pública de máquina.

Windows real com PowerShell 5.1/7 permanece pendente. Parada durante inferência pode interromper progresso não salvo; concluir/cancelar a comparação continua recomendado. Setup/instalação automática, serviços de sistema, autostart e mudanças globais de política não foram acrescentados.

Fechamento E13: **QA APROVADO**, **segurança APROVADA** e **review final independente APROVADO**. Nenhuma nova alteração de produção foi feita após os testes dirigidos e o ciclo real. Setup e validação Windows real permanecem no backlog; somente os quatro wrappers e o helper local foram implementados nesta extensão.
