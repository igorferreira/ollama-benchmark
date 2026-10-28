# ADR-001 — Python padrão com interface web local

- **Data da baseline:** 28/10/2026.
- **Status:** decisão observada na implementação; registro retrospectivo.
- **Escopo:** app próprio, sem substituir o Ollama.

## Contexto

O produto deve executar localmente em Windows e Linux, depender somente de Python para seu backend e permitir que a pessoa repita medições do Ollama já instalado. Navegador e Ollama são dependências operacionais explícitas. A implementação atual usa `http.server`, `http.client`, `threading`, `json`, `csv` e arquivos web locais.

Este registro documenta a decisão materializada no código. A comparação de alternativas abaixo é uma análise retrospectiva, não uma ata de deliberação anterior ao desenvolvimento.

## Decisão

Manter um processo Python com servidor HTTP local e frontend HTML/CSS/JavaScript nativo do navegador. Manter [app.py](../../app.py) como raiz de composição; separar transporte HTTP, integração Ollama, orquestração, validação, cálculo e exportação no pacote [backend](../../backend/), conforme a evolução [SDD-001](../changes/001-separacao-responsabilidades.md). A baseline original reunia essas responsabilidades em dois arquivos. Consumir a API HTTP do Ollama diretamente pela biblioteca padrão, sem SDK Python, `pip`, Node, CDN ou banco.

## Alternativas e consequências

| Alternativa | Avaliação para este escopo |
| --- | --- |
| Flask/FastAPI e cliente HTTP externo | Reduzem algumas tarefas HTTP, mas adicionam pacotes e instalação contrários à restrição |
| Interface desktop com toolkit | Muda distribuição e comportamento entre sistemas; navegador já satisfaz o fluxo |
| CLI somente | Menos interface, mas não atende a experiência de seleção/comparação visual planejada |
| Aplicação web local com biblioteca padrão | Satisfaz dependência mínima; transfere ao projeto validação HTTP e ciclo de execução |

**Benefícios:** distribuição por arquivos, ausência de build frontend e funcionamento offline após requisitos locais atendidos. **Custos:** rotas, erros e proteção HTTP são responsabilidade explícita do projeto; não existe framework fornecendo contratos ou validação automática. `http.server` é usado para serviço pessoal local, sem alegação de aptidão para publicação pública.

## Evidências e revisão futura

A estrutura e imports atuais materializam esta decisão. A [arquitetura](../arquitetura.md) mostra componentes; a [especificação técnica](../especificacao-tecnica.md) define contratos e limites. `TEST_RESULTS.md` (evidência local não versionada) registra validação Linux e lacuna Windows. Reavaliar caso surja requisito real de servidor público, autenticação multiusuário ou distribuição instalada; qualquer pacote novo deve alterar formalmente a restrição de dependência.
