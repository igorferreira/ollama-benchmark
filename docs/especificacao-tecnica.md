# Especificação técnica — baseline implementada

Data da baseline documental: **28/10/2026**. Este documento descreve o código existente, não um serviço futuro. Fonte primária: [composição CLI](../app.py), [HTTP](../backend/http.py), [orquestração](../backend/manager.py), [cliente Ollama](../backend/ollama.py), [métricas](../backend/metrics.py), [validação](../backend/validation.py), [exportação](../backend/exports.py) e [frontend](../web/app.js). A separação de responsabilidades foi especificada em [SDD-001](changes/001-separacao-responsabilidades.md); o contrato HTTP permanece o mesmo. Requisitos: [SDD](sdd.md). Decisões e diagramas: [arquitetura](arquitetura.md). Contrato para ferramentas: [OpenAPI 3.1](openapi.yaml).

## 1. Convenções e compatibilidade

- HTTP local, sem TLS, autenticação de usuário ou sessões individuais.
- API do app recebe e retorna JSON UTF-8; não confundir com a API do Ollama que o app consome internamente.
- Caminhos e nomes de campos são sensíveis a maiúsculas/minúsculas. Não existe prefixo `/v1`, identificador de job ou paginação.
- Campos desconhecidos em configurações são ignorados. Dados normais retornados pelo Ollama podem conter atributos adicionais.
- `null` significa valor indisponível; campo ausente pode significar que a execução não chegou a produzir aquela informação. Não converter ausência em zero.
- `openapi.yaml` contém JSON, que também é YAML válido. Pode ser lido por `json` da biblioteca padrão. O arquivo descreve a API; não é carregado nem usado para validação em runtime.
- Tipos inteiros de entrada são estritos no Python: `true` e `1.0` não substituem o inteiro `1`. JSON Schema considera alguns números decimais matematicamente inteiros; essa diferença está registrada na extensão `x-python-type` do contrato.

## 2. Endpoints do app

| Método e caminho | Resposta de sucesso | Comportamento |
| --- | --- | --- |
| `GET /` | 200 HTML | Página com token da instância inserido em `meta[name=benchmark-token]` |
| `GET /app.js` | 200 JavaScript | Interface local |
| `GET /style.css` | 200 CSS | Estilos locais |
| `GET /api/health` | 200 `{"status":"ok"}` | Apenas disponibilidade do app; não consulta Ollama |
| `GET /api/models` | 200 `ModelsResponse` | Consulta catálogo e modelos carregados no Ollama; 502 se uma consulta falhar |
| `GET /api/state` | 200 `State` | Snapshot do único estado global, com resumo calculado |
| `GET /api/export?format=csv` | 200 CSV, anexo | Snapshot exportado, inclusive durante execução |
| `GET /api/export` | 200 JSON, anexo | Mesmo formato lógico de `State`, indentado |
| `POST /api/start` | 202 `{"status":"running"}` | Aceita job e inicia worker; não espera validar existência no catálogo |
| `POST /api/cancel` | 200 `{"status":estado_atual}` | Sinaliza cancelamento; se não há job ativo não altera estado |

Qualquer valor de `format` diferente de `csv`, incluindo `json` ou um valor desconhecido, produz JSON. Se houver valores repetidos, usa o primeiro. GET usa o caminho sem query para roteamento; queries extras são ignoradas. POST compara `self.path` literalmente: `/api/start?x=1` não é `/api/start` e resulta em 404 depois das validações comuns.

Caminhos desconhecidos tratados por GET/POST retornam 404 JSON. Métodos não implementados, como PUT/DELETE/HEAD/OPTIONS, seguem o comportamento 501 HTML da classe base `BaseHTTPRequestHandler`; não há preflight CORS.

### 2.1 Proteções e ordem de validação

Todos os GET/POST passam por `Handler.local_request`:

1. `Host` deve ser exatamente `127.0.0.1:<porta_real>` ou `localhost:<porta_real>`. Host sem porta, outro domínio, IPv6 no Host da interface e outra porta recebem 403.
2. Se `Origin` estiver presente, deve coincidir exatamente com `http://` concatenado ao `Host` recebido. `Origin` ausente é aceito; `null` ou origem HTTPS não coincidem.
3. `Sec-Fetch-Site: cross-site` recebe 403. Outros valores não são bloqueados por essa condição.

POST executa, nessa ordem:

1. Comparação constante do header `X-Benchmark-Token` com token criado por `secrets.token_urlsafe(32)` na inicialização da instância. Token é comum a todas as abas; não identifica usuário. Header ausente ou diferente: 403.
2. `Content-Type` precisa ter tipo de mídia `application/json`; parâmetro de charset é permitido pelo parser. Qualquer `Transfer-Encoding` não vazio recebe 415.
3. `Content-Length` convertido para inteiro. Ausente, negativo ou maior que 65.536: 413; texto não numérico: 400.
4. Leitura do corpo com timeout de socket de cinco segundos. Corpo incompleto/malformado ou UTF-8 inválido pode resultar em 400; timeout tratado produz 408. Erros de transporte não tratados não têm garantia de resposta JSON.
5. Parse JSON e despacho. `/api/start` valida o objeto; `/api/cancel` ignora o valor parseado, aceitando qualquer JSON válido: `{}`, `[]`, `null`, string, número ou booleano.

O token fica no HTML local. Uma aplicação local capaz de ler a página pode obtê-lo; isso não é autenticação contra processos da própria máquina. Não há CORS permissivo, HTTPS, limite de conexões ou autenticação para implantação pública.

### 2.2 Headers de resposta

Respostas geradas por `send_data` incluem tamanho em bytes UTF-8 e:

```text
Cache-Control: no-store
X-Content-Type-Options: nosniff
Referrer-Policy: no-referrer
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'
```

Exportação usa `Content-Disposition: attachment` com nomes fixos `ollama-benchmark.csv` ou `ollama-benchmark.json`. Essas garantias não se estendem a erros gerados diretamente pela classe HTTP base.

### 2.3 Erros HTTP e falhas assíncronas

| Código | Caso implementado | Formato |
| --- | --- | --- |
| 400 | JSON inválido, tamanho textual inválido ou configuração inválida | `{"error":"mensagem"}` |
| 403 | Host, Origin, Fetch-Site ou token rejeitado | Mesmo formato |
| 404 | Caminho desconhecido GET/POST | Mesmo formato |
| 408 | Timeout tratado lendo corpo do POST | Mesmo formato |
| 409 | Início durante `running` ou `cancelling` | Mesmo formato |
| 413 | Corpo sem tamanho válido no intervalo 0–65.536 | Mesmo formato |
| 415 | Tipo de mídia ou Transfer-Encoding rejeitado | Mesmo formato |
| 502 | `/api/models` não consegue acessar/interpretar catálogo ou carregados | Mesmo formato |

As mensagens são texto para diagnóstico, sem códigos de erro estáveis. Um 202 não garante sucesso do benchmark: modelo ausente, Ollama indisponível e erros de inferência aparecem posteriormente em `State.error` ou em `rows[].error`.

## 3. Contratos de dados

### 3.1 Configuração de entrada e normalização

```json
{
  "models": ["qwen3:4b"],
  "prompt": "Explique como funciona uma API REST.",
  "num_predict": 128,
  "num_ctx": 4096,
  "repetitions": 3,
  "timeout": 180,
  "think": false
}
```

| Campo | Tipo | Obrigatório / default | Validação |
| --- | --- | --- | --- |
| `models` | array de strings | Sim | 1–20 itens antes de deduplicar; cada nome não vazio após `strip`, até 200 caracteres |
| `prompt` | string | Sim | Não vazio após `strip`; até 16.000 caracteres Python |
| `num_predict` | inteiro estrito | Não / 128 | 1–4.096 |
| `num_ctx` | inteiro estrito | Não / 4.096 | 512–131.072 |
| `repetitions` | inteiro estrito | Não / 3 | 2–10; inclui a primeira execução |
| `timeout` | inteiro estrito, segundos | Não / 180 | 10–1.800; deadline da chamada `generate`, não de todo o job |
| `think` | booleano estrito | Não / false | Encaminhado ao Ollama |
| `live_token_count` | booleano estrito | Não / false | Instrumenta logprobs para observar tokens de saída ao vivo, com custo de medição e compatibilidade próprios |

A configuração precisa ser objeto JSON. Deduplicação preserva ordem; espaços no prompt e nos nomes não são removidos, apenas usados para checar vazio. Valores `null` explícitos não acionam defaults: são inválidos para esses campos. A configuração armazenada contém todos os campos normalizados e não conserva propriedades desconhecidas.

O app não valida capacidades de geração de todos os modelos, suporte a `think`, capacidade real de contexto ou tamanho tokenizado do prompt antes de gerar. A lista pode incluir modelos de embeddings; a falha de geração será registrada. `num_ctx` não é garantia de que todo pedido será aceito pelo Ollama/modelo.

### 3.2 Estado global `State`

```json
{
  "status": "idle",
  "rows": [],
  "settings": null,
  "current": null,
  "started_at": null,
  "error": null,
  "summary": [],
  "live": null,
  "usage": {"completed_runs": 0, "excluded_runs": 0, "prompt_tokens": null, "tokens": null, "prompt_cached_tokens": null, "total_tokens": null}
}
```

| Campo | Tipo | Semântica |
| --- | --- | --- |
| `status` | enum string | `idle`, `running`, `cancelling`, `completed`, `cancelled`, `failed` |
| `settings` | objeto normalizado ou null | Configuração do último job aceito |
| `rows` | array `Row` | Resultados anexados depois de concluir/falhar/cancelar uma execução; não há métricas parciais publicadas |
| `current` | `{model:string,run:integer}` ou null | Execução em andamento; `run` começa em 1 |
| `started_at` | string ISO 8601 UTC ou null | Instante de aceitação, por `datetime.now(timezone.utc).isoformat()` |
| `error` | string ou null | Falha fatal do worker; falhas por execução ficam na linha |
| `summary` | array `Summary` | Derivado de snapshot das linhas, não persistido separadamente |

`completed` significa que o worker percorreu a fila, mesmo se todas as linhas estiverem `failed`. `failed` global corresponde a falha fora do bloco individual, por exemplo catálogo inacessível ou modelo selecionado ausente. Cancelamento antes de começar uma execução pode produzir `cancelled` com zero linhas.

Todas as abas compartilham esse estado. Novo `/api/start` aceito substitui configuração, linhas e resumo anteriores. Não existe histórico, importação, isolamento por sessão, jobId, retomada ou retenção após reinício.

### 3.3 Resultado `Row`

Campos-base sempre presentes: `model:string`, `run:integer>=1`, `phase:initial|repeated`, `status:completed|failed|cancelled`. `phase` depende apenas de `run==1`.

| Campo adicional | Tipo normal | Unidade / origem |
| --- | --- | --- |
| `loaded_before` | booleano; pode faltar | Modelo encontrado em `/api/ps` imediatamente antes da inferência |
| `tokens` | inteiro não negativo | `eval_count`, validado estritamente |
| `tokens_per_s` | número ou null | Tokens / segundo de geração; null sem tempo positivo ou com zero tokens |
| `first_content_s` | número ou null | Segundos até primeiro fragmento com `response` ou `thinking` não vazio |
| `first_text_s` | número ou null | Segundos até primeiro `response` não vazio |
| `wall_s` | número | Duração local de `generate` até o último fragmento, antes de buscar metadados posteriores |
| `total_s`, `load_s` | número ou null | `total_duration`, `load_duration` convertidos de ns |
| `prompt_s`, `generation_s` | número ou null | `prompt_eval_duration`, `eval_duration` convertidos de ns |
| `prompt_tokens` | inteiro não negativo ou null | `prompt_eval_count` final, normalizado; booleano/float/string/negativo/ausente vira null |
| `prompt_cached_tokens` | inteiro não negativo ou null | `prompt_eval_cached_count` normalizado; subconjunto separado, sem dupla contagem |
| `total_tokens` | inteiro não negativo ou null | Entrada+saída somente quando ambas válidas; não é total faturável |
| `output_tokens_observed` | inteiro não negativo ou null | Entradas válidas de logprobs, apenas na opção instrumentada e enquanto a observação for completa |
| `token_observation_status` | enum string | disabled, unavailable, matched ou mismatch no resultado; pending aparece somente no progresso |
| `done_reason` | normalmente string | Valor do Ollama; `unknown` se ausente, sem validação adicional |
| `response` | string, máximo 64.000 caracteres | Concatenação somente de `response`; não armazena o raciocínio |
| `size_vram`, `size_memory` | normalmente inteiro ou null | Bytes copiados de `/api/ps` depois da geração, sem validação adicional |
| `warning` | string; opcional | Falha ao obter memória após uma geração bem-sucedida; não invalida suas métricas |
| `error` | string; opcional | Erro da execução; em geral a linha não possui métricas |

A implementação valida e normaliza durações, `eval_count` e os contadores finais de entrada/cache. Os demais campos originados no Ollama dependem do formato desse serviço; o OpenAPI deixa campos copiados sem revalidação abertos para refletir esse comportamento. Não se deve inferir que `size_vram/size_memory` equivale a utilização percentual ou backend GPU.

Geração cancelada ou com timeout não transforma texto parcial em métricas finais da linha. A SDD-003 preserva a última prévia incompleta no campo volátil `live` e, portanto, na exportação JSON do snapshot; CSV não contém esse texto. Os resultados de outras execuções permanecem. Na conclusão normal, existe uma linha por combinação modelo/execução. Falha global ou cancelamento pode deixar a fila incompleta.

### 3.4 Resumo `Summary`

Um item por modelo que já tem pelo menos uma linha, na ordem de aparição:

- `model`: nome.
- `initial`: primeira linha `completed` com `run==1`, ou null; inclui a linha inteira.
- `repeated_count`: quantidade de linhas `completed` com `run>1`.
- `tokens_per_s`, `first_text_s`, `wall_s`: mediana dos valores numéricos disponíveis dessas linhas repetidas; null se não houver valor elegível.

Cada métrica pode usar uma quantidade diferente de valores. Por exemplo, `repeated_count` inclui uma linha concluída cuja velocidade é null. Não há p95, média, desvio, intervalos de confiança ou descarte automático de outliers. `loaded_before` não filtra o resumo; o título correto é execuções repetidas, sem garantia de modelo aquecido.

### 3.5 Descoberta `ModelsResponse`

Objeto com `models`, `loaded` e `ollama_url`. `models` vem de `/api/tags`; `loaded` vem de `/api/ps`. Itens são repassados, não convertidos a um DTO fechado. A UI usa `name`, `size` e `details.quantization_level`, e considera carregado quando o nome aparece em `loaded`.

## 4. Integração com Ollama

O único destino é configurado no processo Python. O navegador não fornece URL nem chama diretamente o Ollama.

| Operação | Contrato consumido | Tratamento |
| --- | --- | --- |
| Catálogo | `GET /api/tags`, objeto `models` | Lista de instalados; checagem novamente antes de executar fila |
| Carregados | `GET /api/ps`, objeto `models` | Antes e depois de cada inferência |
| Inferência | `POST /api/generate` | NDJSON em stream; uma linha JSON por fragmento |

Payload de geração efetivo:

```json
{
  "model": "qwen3:4b",
  "prompt": "Explique como funciona uma API REST.",
  "stream": true,
  "think": false,
  "keep_alive": "2m",
  "options": {
    "num_ctx": 4096,
    "num_predict": 128,
    "temperature": 0,
    "seed": 42
  }
}
```

Não usa SDK Python, shell, CLI `ollama`, rota `/api/chat`, histórico `context`, ferramentas, imagem ou endpoint de download. `keep_alive=2m` pode alterar retenção em memória conforme política do servidor; o app não chama unload. Ollama pode expulsar outros modelos ao acomodar a inferência.

Em HTTP diferente de 200, lê até 2.000 bytes do diagnóstico. JSON com campo `error` não vazio interrompe a execução. Linha inválida, UTF-8 inválido, ausência de fragmento final `done` e `eval_count` inválido falham a linha. O cliente processa JSON completo por linha: fragmentação TCP e UTF-8 parcial são reagrupados pela leitura binária antes de decodificar JSON.

Fonte externa consultada via Context7 nesta documentação: [API oficial do Ollama](https://github.com/ollama/ollama/blob/main/docs/api.md). O comportamento específico deste app é definido pelo código, inclusive quando a documentação upstream evoluir.

## 5. Semântica de medição

`started = time.perf_counter()` ocorre ao entrar em `generate`, antes da conexão HTTP e serialização/envio. TTFT mede percepção desse cliente Python, não timestamp exato de execução da GPU e nem pintura no navegador.

```text
segundos = duração_em_nanossegundos / 1.000.000.000
tokens_por_segundo = eval_count / (eval_duration / 1.000.000.000)
```

`seconds` aceita apenas números finitos não negativos e rejeita booleanos. Duração inválida/ausente vira null; duração zero é preservada como zero, mas velocidade não divide por zero. `eval_count` precisa ser inteiro não negativo, caso contrário falha a execução.

`first_content_s` inclui raciocínio (`thinking`) e resposta; `first_text_s` inclui apenas resposta. O contador de saída do Ollama pode incluir raciocínio; portanto tokens/s não necessariamente equivale à velocidade só do texto visível. O app não tokeniza o prompt e não soma fragmentos para contar tokens.

`wall_s` inclui conexão, espera, carga, processamento do prompt, geração e transporte do stream; exclui consultas `/api/ps` anteriores/posteriores e polling/renderização. `total_s` é tempo declarado pelo Ollama e pode diferir de `wall_s`. Nenhum deles constitui SLA ou promessa de velocidade futura.

## 6. Concorrência, cancelamento e deadline

- `ThreadingHTTPServer` cria handlers concorrentes. Um `BenchmarkManager` controla um worker daemon sequencial por instância.
- `start` valida configuração e, sob `manager.lock`, rejeita `running/cancelling`, troca todo estado/evento e inicia worker.
- Worker consulta catálogo, percorre modelos na ordem normalizada e repetições de 1 até N. Uma geração ativa por vez no app, sem impedir outros clientes Ollama.
- Snapshot usa `deepcopy` sob lock; resumo é calculado depois. Estado terminal, erro e `current=None` são publicados juntos sob lock, impedindo limpeza do job anterior sobre o seguinte.
- Cancelamento troca estado para `cancelling`, sinaliza `Event` e tenta shutdown/close da conexão ativa sob lock do cliente. Worker observa o evento e publica `cancelled` ao finalizar. O valor devolvido pelo POST pode já ser `cancelled` devido à concorrência.
- Um `threading.Timer` daemon por geração sinaliza expiração e faz shutdown do socket ativo. Relógio monotônico e checagens antes/depois das leituras rejeitam fragmento final tardio, inclusive com bytes chegando continuamente.
- Timer é cancelado no `finally`; resposta e conexão são fechadas. Cancelamento tem precedência na classificação quando também houve erro/timeout.

O watchdog cobre a chamada `generate`. GETs de metadados usam timeout de socket/inatividade de cinco segundos, sem watchdog global equivalente. Não prometer que um job inteiro ou cancelamento termine exatamente dentro de `timeout`, sobretudo sob servidor de metadados malcomportado. Encerramento da conexão não comprova liberação imediata de GPU ou término interno da inferência no Ollama.

## 7. Limites e recursos

| Limite | Valor implementado |
| --- | --- |
| POST app | 65.536 bytes de corpo; leitura socket cinco segundos |
| Modelos | Até 20 itens antes de deduplicar |
| Execuções por modelo | 2–10; máximo 200 combinações por job |
| Prompt | 16.000 caracteres, sem contagem prévia de tokens |
| Linha JSON de geração | Até 1.048.576 bytes; leitura detecta excedente |
| Resposta de metadados Ollama | Até 4.194.304 bytes |
| Texto guardado por execução | Até 64.000 caracteres de resposta, sem raciocínio |
| Contexto solicitado | 512–131.072 tokens |
| Saída solicitada | 1–4.096 tokens |
| Deadline solicitado | 10–1.800 segundos por geração |
| Polling | Próxima consulta 700 ms depois de terminar a anterior, não uma taxa exata |

Não há cota global de memória ou limite de conexões HTTP. Snapshot e resumo copiam referências/conteúdos de resultados; exportação JSON também repete a linha inicial dentro do resumo. Os limites são de entrada/armazenamento, não garantias de memória ou duração máxima do lote.

## 8. CSV e JSON exportados

JSON exporta o snapshot completo do estado, sem envelope adicional, com `ensure_ascii=False`, indentação 2 e números não finitos proibidos. Pode conter prompt e texto gerado; trate-o como dado local do usuário.

CSV UTF-8 com BOM, cabeçalho e finais de linha do writer padrão. Ordem exata:

```text
model,run,phase,status,loaded_before,tokens,tokens_per_s,first_content_s,first_text_s,wall_s,total_s,load_s,prompt_tokens,prompt_cached_tokens,total_tokens,output_tokens_observed,token_observation_status,prompt_s,generation_s,done_reason,size_vram,size_memory,error,started_at,prompt,num_predict,num_ctx,repetitions,timeout,think,live_token_count
```

Uma linha por execução registrada, inclusive falhas/cancelamento. Campos ausentes e null viram célula vazia; booleanos são escritos como `True`/`False`, números com ponto decimal. O texto gerado e `warning` não entram no CSV. Campos string começando por `=`, `+`, `-`, `@`, tab, CR ou LF recebem apóstrofo inicial para reduzir interpretação como fórmula; não é exportação textual byte a byte do original. Vírgulas, aspas e quebras são escapadas pelo módulo `csv`.

## 9. CLI e variáveis de ambiente

| Configuração | Default | Regra |
| --- | --- | --- |
| `--no-browser` | Ausente | Impede tentativa automática de abrir navegador |
| `--port` | `APP_PORT` ou 8765 | Inteiro via argparse; flag prevalece; disponibilidade da porta cabe ao sistema |
| `APP_PORT` | `8765` | Convertida a inteiro ao construir parser; valor inválido pode falhar antes de processar flags |
| `APP_BIND` | `127.0.0.1` | Apenas `127.0.0.1` ou `0.0.0.0`; segundo valor é documentado para container, mas não bloqueado no modo nativo |
| `OLLAMA_URL` | `http://127.0.0.1:11434` | HTTP; host permitido `127.0.0.1`, `localhost`, `::1`, `host.docker.internal`; sem credenciais, query, fragmento ou caminho além de `/` |

Porta de Ollama omitida usa 11434; a implementação usa `url.port or 11434`. Não resolve URL livre enviada pela UI. A lista de nomes permitidos não elimina condições de DNS/rede do host. O servidor da interface usa IPv4; aceitar `::1` no destino Ollama não torna a interface IPv6.

## 10. Lacunas conhecidas e evolução

A baseline não contém OpenAPI em runtime, versionamento de API, persistência, autenticação de usuário, histórico, importação ou servidor público. Contratos e efeitos observados acima devem orientar mudanças [spec-first](desenvolvimento.md).

Sem testes dedicados atuais para todos os limites de byte/caractere, valores de CLI/env, todas as variantes de POST inválido, falha de metadados posterior à geração, lotes com todos os resultados falhos ou regressão visual automatizada. Lacunas e evidências por requisito estão em [rastreabilidade](rastreabilidade.md). Windows e Docker Desktop são alvos documentados, não plataformas já executadas nesta entrega.

## PWA e recursos estáticos adicionais

A SDD-002 adiciona `GET /pwa.js`, `/sw.js`, `/offline.html`, `/manifest.webmanifest` e os cinco arquivos em `/icons/` listados no contrato OpenAPI. O manifesto usa `application/manifest+json`; PNG usa `image/png`; SVG usa `image/svg+xml`; scripts usam `text/javascript`. Todos preservam Host/Origin e headers de segurança/no-store. Apenas a página `/` recebe substituição do token. A SDD-003 atualiza o service worker para o cache `ollama-benchmark-static-v3` com dez recursos públicos, incluindo FAQ e script de ajuda/tema, sem HTML principal, API, POST, exportação ou dados de teste. A página offline não contém token. Assets com query não são interceptados para cache; atualizações do worker removem somente versões antigas do cache com prefixo próprio.

O botão de instalação depende de `beforeinstallprompt`; sua ausência não é falha do benchmark. O endereço loopback fornece contexto seguro. A instalação não cria serviço de sistema e não fornece inferência offline.

## 12. SDD-003: progresso, contagem observada e FAQ

`GET /api/state` e JSON exportado acrescentam `live` (null ou objeto da tentativa mais recente) e `usage` (acumulado somente das linhas completed). Schema completo: `LiveProgress` e `Usage` em [OpenAPI](openapi.yaml). `current` continua identificando a tentativa; `live` pode permanecer depois de sua conclusão para mostrar o resultado ou a prévia incompleta.

`live` contém `model`, `run`, `status` (waiting/streaming/completed/failed/cancelled), `elapsed_s`, `response` limitado a 64 mil caracteres, `output_characters`, `thinking_characters`, `fragments`, `first_content_s`, `first_text_s`, os quatro contadores finais (`tokens`, `prompt_tokens`, `prompt_cached_tokens`, `total_tokens`), `count_status` (pending/final/unavailable), `output_tokens_observed` e `token_observation_status`.

O cliente publica callback inicial, primeiro conteúdo, atualizações com intervalo mínimo aproximado de 250 ms e último snapshot relevante. Manager combina publicação sob lock e cronômetro monotônico derivado no snapshot. Enquanto aguarda GET ps antes de iniciar generate, o relógio da inferência ainda não começou. A UI consulta aproximadamente a cada 700 ms; não há SLA de atualização ou SSE/WebSocket.

Sem instrumentação, os contadores finais ficam null durante o stream. `live_token_count=true` acrescenta ao payload Ollama `logprobs:true` e `top_logprobs:0`. Cada entrada válida de metadata precisa ser um objeto com token string e logprob numérico finito, sem booleanos. A aplicação soma entradas, não fragmentos, e não guarda seus tokens/probabilidades/bytes. Metadata ausente ou malformada em conteúdo invalida a observação completa daquela tentativa; o progresso textual continua, sem retry.

`output_tokens_observed` é provisório. No final, `eval_count` sempre determina `tokens`; o estado da observação fica matched, mismatch, unavailable ou disabled. Comparar resultados exige usar a mesma configuração de instrumentação, pois payload e processamento adicionais podem alterar a própria medição. Input/cache/total não são inferidos de caracteres ou da metadata de saída.

`usage` contém completed_runs, excluded_runs e soma por contador de prompt_tokens/tokens/prompt_cached_tokens/total_tokens. Não há concluídas ou uma concluída carece daquele contador: null para essa soma. Zero numérico válido é preservado. Linhas failed/cancelled são excluídas e não representam uso faturável zero. Cache permanece separado, já faz parte da visão de entrada; nunca adicionar como um terceiro termo ao total informado.

`GET /faq.html` e `/help.js` são recursos públicos estáticos, submetidos às mesmas proteções Host/Origin/CSP do mapa de assets. Não recebem token e não consultam API. Help JS inicializa tema e tooltips compartilhados; a lógica do benchmark continua em app.js. FAQ/help entram na allowlist pública do SW v3. HTML principal, APIs, app.js/pwa.js, prompts, prévias, respostas e exportações continuam fora dela.

A FAQ traz definições e fórmulas educativas com fontes; não calcula faturamento ou impõe SLA universal. O acompanhamento limita-se aos testes desta instância. Casos de aceite e ownership constam da [SDD-003](changes/003-tokens-tempo-real-faq.md).

## 13. SDD-004: inventário mínimo do ambiente

Novo `GET /api/system` responde `SystemSnapshot`, separado de `/api/state`, `usage`, linhas e exportações do benchmark. `GET /system.js` serve a apresentação genérica. Ambos passam por Host/Origin/Fetch-Site/CSP/no-store comuns; a API não aceita caminhos/comandos nem tem opção de burlar o intervalo. Sem coletor injetado ou em erro inesperado da borda, responde 503 JSON genérico, sem str da exceção/caminho privado.

`app.main` constrói `SystemCollector` e injeta como terceiro argumento opcional em `AppServer(address, manager, system_info=None)`. Fixtures antigas sem coletor não inspecionam incidentalmente o ambiente por visitar a nova API; recebem 503. `BenchmarkManager.is_active()` consulta running/cancelling sob lock breve, e o transporte chama snapshot fora desse lock.

Schema exato e unidades no OpenAPI: collected_at UTC ou null; environment(kind/scope/note); os(name/kernel/architecture); cpu(model/physical_cores/logical_cpus/scope); gpu(models/scope/note); memory(total_bytes/used_bytes/available_bytes/scope); disk(total_bytes/used_bytes/scope); uptime_seconds/uptime_scope; refresh(min_interval_s=10/paused/stale). Bytes e contagens são inteiros não negativos ou null. Nomes são strings imprimíveis limitadas a 256 caracteres; GPU até 16 modelos. Não existem campos de usuário, host, IP/MAC, serial, UUID, mount, caminho privado, arquivo ou lista de pacotes.

Fatos estáticos são normalizados por allowlist uma vez por instância. Dados dinâmicos têm no mínimo dez segundos entre tentativas, mesmo após falha. Snapshot é cópia em memória. Durante coleta concorrente, outros pedidos recebem o snapshot anterior marcado stale; I/O não segura lock do coletor ou manager. Durante benchmark ativo, nenhuma nova coleta dinâmica inicia e o retorno fica paused/stale; sem snapshot anterior, valores dinâmicos são desconhecidos e collected_at é null. O timestamp permanece o da última coleta dinâmica bem-sucedida.

Fontes Linux: os-release, release do kernel, arquitetura pontual de uname.machine, campos de CPU e topologia/afinidade visíveis, DRM/sysfs/base PCI local opcional, meminfo, cgroups v1/v2 conhecidos e uptime do kernel. Base PCI ausente não é dependência faltante: o modelo GPU pode permanecer desconhecido. A busca de cgroup é limitada e usa o menor limite finito conhecido entre candidato/ancestrais; used/available pertencem ao escopo desse limite, não são necessariamente consumo exclusivo do processo do app.

Fontes Windows: rótulo Windows com kernel/build conhecido, CPU por campo de registro restrito, modelos de display por EnumDisplayDevicesW e arquitetura por IsWow64Process2/fallback explícito. GlobalMemoryStatusEx usa estrutura de 64 bytes com DWORD de 32 bits e contadores de 64 bits e dwLength inicializado; GetTickCount64 tem restype uint64. Fixtures Linux simulam essas APIs, sem equivaler a homologação Windows.

Escopos de API são identificadores técnicos e são traduzidos pela interface: cpu process_visible_not_exclusive/process_visible_shared_kernel; gpu process_visible/container_visible; memory system_memory/cgroup_limit/container_limit_unknown; disk app_filesystem; uptime kernel/shared_kernel; unknown quando indisponível. O campo environment.scope é backend_process. No Docker, capacidade de host não comprovável fica null, não é inferida de memória física visível. Kernel/CPU podem ser compartilhados; GPU não exposta não prova ausência física nem indica o backend usado pelo Ollama. O alvo Ollama é um sistema externo e não é inventariado.

O frontend faz fetch no-store a cada dez segundos quando o app está ocioso, limitado pelo servidor também no botão Atualizar. Evento benchmark-status informa apenas active; pausa timer e aborta fetch de inventário durante teste, retomando com throttle. O painel não prende foco e oferece hover/foco/toque/clique/Escape. Barra de RAM exige valores conhecidos e capacidade positiva; desconhecido nunca vira barra de 0%. Inventário não persiste em localStorage, Cache Storage ou arquivos, nem aparece nas exportações do benchmark. SW v3 continua guardando dez recursos públicos anteriores; system.js e api/system ficam fora da allowlist.

Detalhes e critérios: [SDD-004](changes/004-resumo-ambiente-dinamico.md). Há teste sintético de Windows e execução real deve ser explicitamente diferenciada na matriz; não afirmar suporte validado apenas pela existência do código.

## Biblioteca de pedidos e hostname

`GET /prompts.js` e `GET /prompts.css` são assets estáticos da whitelist, com as mesmas proteções HTTP/CSP e no-store; ficam fora da allowlist SW v3. Não há endpoint novo de inferência. O catálogo local tem 18 IDs únicos e as seis células tipo × complexidade. O dialog fica fora do formulário; controles não submetem benchmark. Substituir edição exige confirmação, revalidada no clique; evento benchmark-status e textarea.disabled bloqueiam abrir/aplicar.

`SystemSnapshot.hostname` é string limitada a 256 caracteres imprimíveis ou null, obtida por socket.gethostname uma vez por instância, sem DNS/FQDN. A origem acompanha environment.kind: container não significa hostname físico. Não participa do estado/exports do benchmark, logs nem cache. A exposição local é exceção autorizada documentada na SDD-006.
