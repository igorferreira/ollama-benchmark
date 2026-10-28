# Mudança SDD-001 — Separação de responsabilidades no backend

Estado: **especificada antes da alteração de código desta refatoração**. Data: 28/10/2026. Autorização: demanda explícita para refatorar a separação de responsabilidades, com gate independente de QA ao final. Este registro é prospectivo para esta mudança; a baseline inicial descrita nos demais documentos permanece retrospectiva.

## Problema

O backend original distribui responsabilidades em dois arquivos principais: `app.py` reúne composição, HTTP, assets e CSV; `benchmark.py` reúne validação, cálculo, transporte e orquestração. Embora as funções e classes já permitam testes, mudanças nessas áreas têm motivos distintos e navegação/manutenção pouco localizadas.

O objetivo é tornar as fronteiras concretas sem alterar comportamento, introduzir frameworks ou criar interfaces/plugins sem consumidores reais. O frontend já está separado em `web/` e permanece no mesmo local.

## Design escolhido e escopo

| Destino | Responsabilidade e símbolos |
| --- | --- |
| `app.py` | Composition root: `main`, CLI/ambiente, instanciação de cliente/manager/servidor, abertura do navegador e encerramento |
| `backend/__init__.py` | Identificação do pacote, sem reexportações de conveniência |
| `backend/validation.py` | `validate_settings`: defaults, tipos, limites e normalização |
| `backend/metrics.py` | `seconds`, `metrics`, `summarize`: cálculo/transformação sem transporte ou estado de execução |
| `backend/ollama.py` | `Cancelled`, `OllamaClient`: protocolo HTTP externo, stream, deadline e socket |
| `backend/manager.py` | `BenchmarkManager`: um job, fila, estado, snapshots e cancelamento coordenado |
| `backend/exports.py` | `CSV_FIELDS`, `csv_export`: representação CSV e proteção contra fórmulas |
| `backend/http.py` | `AppServer`, `Handler`, mapa dos assets: borda HTTP, proteções e adaptação de endpoints |
| `web/` | Frontend existente, incluindo tema; nenhum cálculo de benchmark migra para o navegador |
| `tests/test_benchmark.py` | Imports e composição da fixture atualizados, 24 cenários existentes preservados |
| `Dockerfile` | Copiar `app.py`, pacote `backend/` e `web/` |

`AppServer` receberá um manager já construído. `main` será o único ponto de composição concreta para produção. O manager continua recebendo um cliente por injeção e duck typing; não haverá ABC, factory ou protocolo novo só para rotular SOLID.

O arquivo monolítico `benchmark.py` será removido após mover suas unidades e atualizar todos os consumidores internos. Como não houve publicação anterior do produto com consumidores externos contratados desses módulos, não será mantido um wrapper de compatibilidade vazio. A entrada `python app.py` continua existindo.

## Contratos preservados

- Mesmos caminhos HTTP, schemas, headers, status, mensagens e defaults; OpenAPI não recebe endpoints novos.
- CLI `--no-browser`, `--port` e variáveis `APP_PORT`, `APP_BIND`, `OLLAMA_URL`.
- Nomes/unidades das métricas, contador real de tokens, TTFT conteúdo/texto e resumo.
- Estado global único, preservação de linhas, cancelamento best-effort e deadline global de geração.
- Tema claro/escuro e preferência local do navegador.
- Ambos os arquivos Compose independentes; Ollama continua no host.
- Runtime e suíte automatizada somente Python stdlib, frontend sem build/CDN.

## Invariantes de segurança

Preservar sem enfraquecimento: validação Host/Origin/Fetch-Site, token aleatório por instância nos POSTs, CSP sem inline liberado, renderização por textContent, mapa explícito dos três assets, allowlist de destino Ollama, limites 64 KiB/4 MiB/1 MiB/64 mil caracteres, deadline/cancelamento/finalização atômica, proteção de fórmulas CSV e ausência de logs de acesso com prompts/resultados.

Não modificar bind/firewall/serviço Ollama ou containers de outros projetos. Publicação GitHub depende dos gates finais de QA, review e segurança coordenados pela entrega.

## Critérios de aceite

- **AC-SRP-01:** todos os consumidores internos usam os novos módulos e não importam `benchmark.py` removido.
- **AC-SRP-02:** os 24 testes existentes continuam passando sem alterar o que verificam; adaptações de import/composição são esperadas.
- **AC-SRP-03:** teste adicional relevante verifica composition root e inicialização por CLI, sem criar abstrações apenas para satisfazer teste.
- **AC-SRP-04:** `AppServer` recebe manager; transporte HTTP não instancia `OllamaClient` nem `BenchmarkManager` concretos.
- **AC-SRP-05:** Docker constrói com o pacote backend; integração Linux/Ollama e exportação/cancelamento continuam válidos nos cenários executados pela equipe.
- **AC-SRP-06:** docs, matriz e revisão SOLID passam a apontar para responsabilidades/caminhos reais, mantendo limites e plataformas não verificadas.
- **AC-SRP-07:** QA independente executa a suíte final; review ocorre após QA; auditoria de segurança/publicação é um gate separado.

## BDD da refatoração

**Dado** um cliente HTTP que já usa os endpoints locais, **quando** a separação de arquivos for entregue, **então** requests, schemas, métricas e erros esperados continuam iguais, sem campo ou rota nova.

**Dado** o comando `python app.py --no-browser --port <porta_livre>`, **quando** o processo iniciar, **então** a raiz de composição conecta as unidades e `/api/health` confirma o servidor sem exigir o Ollama disponível.

**Dado** que os testes usam um Ollama HTTP simulado, **quando** injetarem o manager no servidor refatorado, **então** fila, cancelamento, timeout e exportação mantêm seus contratos sem dependência externa.

## Verificação e rastreabilidade da mudança

Implementação concluída conforme o mapeamento especificado. A evidência E07 da [matriz](../rastreabilidade.md) registra:

- 25 testes aprovados no host e dentro da imagem Docker, incluindo o novo cenário CLI.
- QA independente aprovado: 25 testes em 11,226 segundos, sem ResourceWarning.
- Revisão final independente aprovada, sem bloqueador confirmado.
- Comparação AST dos testes: nenhum dos 24 cenários anteriores removido ou enfraquecido.
- Build e integração real Linux/Ollama: geração, cancelamento, exportações e temas preservados.
- Contrato HTTP mantido; referências documentais atualizadas para os novos módulos.

Auditoria de segredos/dados pessoais e publicação do repositório são verificações separadas do pacote versionado. Windows e Docker Desktop continuam não executados; nenhum resultado acima certifica essas plataformas.
