# ADR-002 — Execução sequencial e estado transitório único

- **Data da baseline:** 28/10/2026.
- **Status:** decisão observada na implementação; registro retrospectivo.

## Contexto

Benchmarks simultâneos competem pelos mesmos recursos do Ollama e dificultam interpretar os números. O escopo inicial é pessoal e local: não exige histórico consultável, contas ou recuperação após falha. O código atual mantém um manager por processo e um worker por comparação.

## Decisão

Executar modelos na ordem selecionada e suas repetições em sequência. Rejeitar novo início enquanto o estado estiver `running` ou `cancelling`. Manter somente a comparação atual em memória e permitir exportação explícita CSV/JSON. Proteger publicações com lock; copiar profundamente o estado para leitura. Publicar status terminal, erro fatal e `current=null` em uma única seção crítica.

A primeira execução é separada no resumo. As posteriores concluídas formam medianas por métrica. Não forçar descarregamento para tentar produzir cache frio: registrar `loaded_before` e a condição inicial observada.

## Alternativas e consequências

| Alternativa | Avaliação retrospectiva |
| --- | --- |
| Fila paralela | Menor tempo total de fila, mas competição entre as próprias medições; exigiria outro desenho de interpretação |
| Histórico em SQLite ou arquivos automáticos | Biblioteca padrão permitiria SQLite, mas adicionaria retenção, migração, limpeza e recuperação não exigidas |
| Estado por aba/job | Exigiria identificação, gestão de ciclo e contratos adicionais sem requisito multiusuário |
| Estado único em memória e download | Menor implementação que cobre o uso pessoal; a pessoa assume salvar o que deseja reter |

**Benefícios:** resultados da própria fila não concorrem entre si; leitura consistente; exportação simples. **Custos:** todas as abas compartilham o mesmo teste; iniciar outra comparação substitui resultados; reiniciar perde estado. Outra instância do app ou outro cliente Ollama ainda pode interferir, portanto sequencial não significa isolamento global.

Cancelamento é cooperativo, com tentativa de interromper o transporte atual. Deadline de geração utiliza relógio monotônico e watchdog do socket, sem matar o Ollama. Falha por linha preserva resultados anteriores. Finalização `completed` informa término da fila, inclusive quando existem linhas com falha; ver a [SDD](../sdd.md).

## Evidências e revisão futura

`BenchmarkManager`, `summarize` e `OllamaClient.generate` estão respectivamente em [manager](../../backend/manager.py), [metrics](../../backend/metrics.py) e [ollama](../../backend/ollama.py), após a [SDD-001](../changes/001-separacao-responsabilidades.md). Os testes de concorrência, finalização atômica, stream contínuo e cancelamento estão em [tests/test_benchmark.py](../../tests/test_benchmark.py). A [rastreabilidade](../rastreabilidade.md) identifica os nomes completos dos testes. Reavaliar persistência ou múltiplos jobs somente após especificar retenção, privacidade, concorrência e critérios de limpeza.

## Atualização de retenção

A [ADR-006](006-historico-json-terminal-perfil.md) e SDD-007 substituem a retenção exclusivamente transitória por histórico JSON de comparações terminais no perfil. Execução sequencial, um estado ativo compartilhado e limites de isolamento permanecem.
