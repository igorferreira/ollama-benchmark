# Revisão de camadas e princípios SOLID

## 1. Escopo e condição da revisão

Revisão por inspeção do desenho e dos módulos da mudança de **28/10/2026**. A baseline inicial era retrospectiva; a [SDD-001](changes/001-separacao-responsabilidades.md) foi escrita antes da refatoração autorizada para separar responsabilidades. Esta revisão explica o que melhorou e o que permanece limitado. Não é uma certificação binária “100% SOLID”, nem substitui o gate de QA e review de código.

O [ADR-005](adr/005-separacao-responsabilidades-backend.md) registra a decisão da separação. O comportamento externo, a restrição de biblioteca padrão e o frontend existente são preservados.

## 2. Backend e frontend

| Área | Código | Responsabilidade | Fronteira |
| --- | --- | --- | --- |
| Frontend | [index.html](../web/index.html), [style.css](../web/style.css), [app.js](../web/app.js) | Controles, tema, polling, apresentação e downloads | API da mesma origem; não chama Ollama nem calcula tokens/s |
| Raiz de composição | [app.py](../app.py) | CLI/ambiente, construção de cliente/manager/servidor, abertura do navegador e encerramento | Único ponto de composição concreta em produção |
| Borda HTTP | [backend/http.py](../backend/http.py) | Rotas, validação de requisição, headers, assets e adaptação de respostas | `AppServer(address, manager)` recebe aplicação pronta |
| Aplicação / orquestração | [backend/manager.py](../backend/manager.py) | Um job, worker sequencial, estados, cancelamento e snapshots | `BenchmarkManager(client)` recebe cliente; não renderiza HTML |
| Integração externa | [backend/ollama.py](../backend/ollama.py) | `OllamaClient`, HTTP/NDJSON, socket ativo e deadline | Não usa SDK, CLI ou configurações do navegador |
| Validação | [backend/validation.py](../backend/validation.py) | `validate_settings`: defaults, tipos, limites e normalização | Sem transporte ou estado de execução |
| Cálculo | [backend/metrics.py](../backend/metrics.py) | `seconds`, `metrics`, `summarize`: unidades, velocidade e resumo | Sem HTTP, apresentação ou criação de worker |
| Exportação | [backend/exports.py](../backend/exports.py) | `CSV_FIELDS`, `csv_export`: serialização CSV e neutralização de fórmulas | Recebe snapshot; não consulta Ollama nem inicia inferência |

Direção principal: navegador → HTTP → manager → cliente Ollama. A rota de descoberta continua acessando `manager.client` diretamente. Exportações consultam snapshot e funções de representação. `app.py` importa as classes concretas para montar o processo; `backend/http.py` não instancia cliente ou manager.

A extração altera a localização das responsabilidades e a composição, não o contrato HTTP. Não cria microsserviços, uma arquitetura hexagonal formal, plugins ou uma camada nova de persistência. O antigo `benchmark.py` é removido e os consumidores internos são atualizados; não há wrapper vazio de compatibilidade. Os diagramas atuais estão na [arquitetura](arquitetura.md).

## 3. Avaliação por princípio

| Princípio | Avaliação atual | Evidência | Limite e trade-off |
| --- | --- | --- | --- |
| **S — Single Responsibility** | Melhoria concreta na organização do backend | Validação, métricas, integração, manager, exportação e HTTP possuem módulos próprios; `app.main` concentra composição/ciclo de vida | `Handler` ainda reúne roteamento, assets e headers na mesma borda. `OllamaClient.generate` ainda mantém protocolo, socket e temporização juntos para medir junto da leitura. Arquivo por responsabilidade não prova responsabilidade única absoluta |
| **O — Open/Closed** | Parcial e deliberadamente simples | Rotas GET/POST continuam em `if/elif`; assets/destinos usam allowlists; métricas e campos CSV são explícitos | Novo endpoint, provedor ou métrica exige editar pontos existentes. Extrair arquivos não torna o código fechado à modificação. Não existe demanda que justifique registry, strategy ou plugin |
| **L — Liskov Substitution** | Sem hierarquia de domínio suficiente para conclusão ampla | `AppServer`/`Handler` especializam classes stdlib; o domínio não define famílias de subclasses intercambiáveis | Herança stdlib e mocks de cliente não demonstram LSP completo. Não há violação demonstrada somente por não existir classe abstrata |
| **I — Interface Segregation** | Contrato de cliente pequeno e implícito | Manager usa `get(path)`, `generate(model, settings, event)` e `cancel()` | Catálogo, geração e cancelamento pertencem ao mesmo cliente. Consumidores futuros podem pedir segregação; adicionar interfaces sem esse consumidor aumentaria manutenção |
| **D — Dependency Inversion** | Injeção e composição mais claras; independência de protocolo continua parcial | `BenchmarkManager(client)` recebe cliente; `AppServer(address, manager)` recebe manager; `app.main` monta dependências concretas | Manager conhece caminhos e formato Ollama; HTTP usa `manager.client` para descoberta. Não há abstração independente de provedor. Duck typing fornece substituição útil sem framework de DI |

A intenção de SRP é separar motivos de mudança. O ganho foi localizar essas áreas em módulos com dependências explícitas, não criar uma classe por função ou acrescentar nomes de camadas sem comportamento.

## 4. Testabilidade e limites de evidência

- `CalculationTests` verifica cálculos e exportação sem Ollama ou navegador.
- `ClientTests` configura o cliente com um servidor HTTP simulado e exercita stream, deadline, cancelamento e falhas.
- `test_completed_results_survive_later_error` substitui `generate` para produzir uma falha controlada. Demonstra um ponto de substituição útil, sem provar todas as propriedades LSP.
- `AppTests` constrói cliente e manager na fixture e injeta o manager em `AppServer`. A borda HTTP não precisa montar o restante da aplicação para o teste.
- `CliTests.test_cli_starts_composition_root_without_ollama`, em [tests/test_benchmark.py](../tests/test_benchmark.py), inicia `app.py` por subprocesso com porta livre e Ollama indisponível; confere `/api/health` e `/app.js`. Esse cenário corresponde ao critério adicional da SDD-001. A inspeção confirma sua presença; o resultado final da execução pertence à [rastreabilidade](rastreabilidade.md).
- O frontend apenas formata números recebidos. Restrições HTML auxiliam uso; a validação efetiva de configuração fica em `backend.validation`.

Os testes demonstram cenários especificados; não adesão universal a princípios. A aprovação antiga dos 24 testes da baseline não aprova automaticamente o código reorganizado. A entrega da refatoração precisa de execução final e gates independentes conforme [desenvolvimento](desenvolvimento.md). Windows e Docker Desktop continuam não verificados sem execução nesses ambientes.

## 5. Evoluções condicionadas a requisitos futuros

As opções seguintes não integram esta refatoração sem nova demanda:

1. Separar adaptação de endpoints e assets se a borda HTTP crescer com funcionalidades independentes, preservando as proteções comuns.
2. Definir um contrato de inferência independente e mover os caminhos/formato Ollama para um adaptador se houver um segundo provedor real. Um `typing.Protocol` pode documentar duck typing, mas não deve existir somente para contar interfaces.
3. Revisar representação compartilhada de métricas/CSV/UI/OpenAPI se a frequência de mudança justificar essa coordenação, sem registro dinâmico prematuro.
4. Especificar retenção, segurança e ciclo de vida antes de introduzir persistência, múltiplos usuários ou jobs paralelos.

A conclusão é específica: SRP e composição receberam melhorias reais. OCP continua limitado, DIP não elimina acoplamento ao protocolo, e LSP não pode ser certificado sem contexto de substituição de domínio.
