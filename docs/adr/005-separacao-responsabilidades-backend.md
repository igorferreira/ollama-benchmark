# ADR-005 — Separação de responsabilidades no backend

- **Data:** 28/10/2026.
- **Status da decisão:** adotada para a mudança SDD-001 sob demanda explícita de refatoração.
- **Origem:** [SDD-001 — Separação de responsabilidades](../changes/001-separacao-responsabilidades.md), especificada antes da alteração de código desta mudança.
- **Gate de entrega:** execução dos testes, QA independente e review posteriores à implementação; decisão de design não substitui esses resultados.

## Contexto

Na baseline inicial, `app.py` reunia composição, CLI, HTTP, assets e CSV; `benchmark.py` reunia validação, métricas, transporte Ollama e orquestração. As funções e classes já tinham fronteiras testáveis, mas os arquivos concentravam diferentes motivos de mudança. A [revisão SOLID](../revisao-solid.md) apontou essa limitação. A demanda seguinte autorizou separar responsabilidades mantendo a dependência exclusiva da biblioteca padrão e o comportamento externo.

Este ADR pertence à refatoração especificada antes do código, diferentemente dos ADRs 001–004, que registraram retrospectivamente decisões da baseline inicial. Não se atribui ao desenho original uma aprovação prévia que não ocorreu.

## Decisão

Usar um pacote `backend/` com módulos coesos:

| Módulo | Motivo de mudança |
| --- | --- |
| `validation.py` | Tipos, defaults, limites e normalização de configuração |
| `metrics.py` | Conversões, cálculo de velocidade e resumo estatístico |
| `ollama.py` | Protocolo HTTP Ollama, NDJSON, temporização do stream e socket |
| `manager.py` | Coordenação da fila, estado, snapshots e cancelamento |
| `exports.py` | Representação CSV e proteção de fórmulas |
| `http.py` | Contrato HTTP local, proteção de entrada, assets e respostas |
| `__init__.py` | Identificação do pacote, sem reexportar todos os símbolos |

`app.py` permanece como raiz de composição e ponto de entrada operacional. Ele constrói `OllamaClient`, injeta esse cliente em `BenchmarkManager` e injeta o manager em `AppServer(address, manager)`. A borda HTTP deixa de construir as dependências de aplicação concretas. A injeção usa objetos e duck typing existentes, sem ABC, `Protocol`, factory, container de DI ou registry sem necessidade atual.

Remover o arquivo monolítico `benchmark.py` depois de atualizar imports, testes, Dockerfile e documentação. Não manter wrapper vazio de compatibilidade: não existe consumidor externo contratado desses imports na baseline. O comando `python app.py`, a API HTTP e as exportações continuam sendo as interfaces operacionais preservadas.

## Alternativas

| Alternativa | Consequência |
| --- | --- |
| Manter os dois arquivos e apenas documentar | Preserva menor quantidade de arquivos, mas não atende à demanda explícita de separar responsabilidades |
| Criar uma classe ou camada para cada operação | Multiplica indireções sem novos consumidores e pode esconder os fluxos simples de benchmark |
| Introduzir framework, interfaces formais e container de DI | Amplia dependências e manutenção sem resolver um requisito adicional |
| Extrair módulos por responsabilidade e centralizar composição | Localiza motivos de mudança, preservando funções, contratos e forma de execução |

## Consequências

**Melhoria concreta de SRP:** regras, cálculos, exportação, protocolo e coordenação podem ser encontrados e alterados em módulos distintos. Alterar CSV não exige navegar no servidor; alterar validação não exige navegar no leitor de stream. A raiz de composição também fica distinguível da adaptação HTTP.

**Melhoria concreta de composição/DIP:** `BenchmarkManager(client)` já recebia seu cliente; `AppServer(address, manager)` passa a receber a aplicação pronta. Ainda assim, o manager conhece caminhos `/api/tags` e `/api/ps` e formato do Ollama. A extração não torna o domínio independente de qualquer provedor de inferência.

**Limites preservados:** roteamento continua em `if/elif`, campos de métricas/CSV continuam explícitos, e extensões exigem editar esses pontos. Não há novo mecanismo OCP de plugins. Não existe hierarquia de domínio que permita afirmar conformidade LSP ampla; a ausência de classe abstrata também não demonstra violação. O client mantém protocolo, socket e marcação de tempo próximos para não deslocar a medição para o frontend.

A separação cria mais arquivos e imports. Esse custo é aceito em troca de navegação e motivos de mudança localizados; não justifica novas camadas automaticamente.

## Invariantes e verificação

Preservar API, schemas, mensagens, defaults, Host/Origin/token/CSP, destino Ollama restrito, limites de corpo/linha/texto, deadline, cancelamento, finalização atômica e exportação CSV/JSON. Frontend e preferência de tema permanecem nos mesmos arquivos. Docker passa a copiar o pacote `backend/`; Compose e Ollama do host não mudam.

Os critérios `AC-SRP-01` a `AC-SRP-07` e BDD estão na [mudança SDD-001](../changes/001-separacao-responsabilidades.md). Os 24 cenários anteriores devem ser preservados e um cenário adicional deve cobrir a composição por CLI. A [matriz de rastreabilidade](../rastreabilidade.md) deve apontar para os símbolos reais e para o resultado atual dos gates, sem reutilizar a aprovação da baseline antiga como aprovação automática da refatoração.

Mudanças futuras de provedor, persistência ou multiusuário precisam de requisitos próprios e revisão das fronteiras; não são consequência aprovada deste ADR.
