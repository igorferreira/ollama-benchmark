# Documentação do Ollama Benchmark Local

Pacote SDD da baseline de **28/10/2026**, escrito a partir do código já implementado. É uma especificação retrospectiva verificável; o fluxo spec-first para mudanças futuras é definido explicitamente. A extensão de tema claro/escuro integra esta rodada de documentação e manutenção.

## Ordem de leitura

| Documento | Finalidade |
| --- | --- |
| [SDD: produto, requisitos e BDD](sdd.md) | Visão, escopo, atores, 13 RF, 7 RNF, 10 regras, 9 histórias e estados |
| [Arquitetura](arquitetura.md) | C4, componentes, threads, confiança, dados, sequências e deploy |
| [Especificação técnica](especificacao-tecnica.md) | Endpoints, schemas, unidades, erros, limites, concorrência, CLI/env e exportações |
| [OpenAPI 3.1](openapi.yaml) | Contrato legível por ferramentas, com sintaxe JSON válida como YAML |
| [Rastreabilidade e validação](rastreabilidade.md) | Requisito → código → testes nomeados → evidência e lacunas |
| [Operação](operacao.md) | Início, Docker, tema, exportação, diagnóstico e privacidade |
| [Desenvolvimento spec-first](desenvolvimento.md) | Processo de mudança, estratégia de testes, checks e gates |
| [Camadas e revisão SOLID](revisao-solid.md) | Avaliação por princípio com símbolos concretos e melhorias somente propostas |
| [Segurança e privacidade](../SECURITY.md) | Limites de uso local, tratamento de dados e relato responsável |
| [Dados e critérios técnicos de privacidade/LGPD](../PRIVACY.md) | Fluxos, retenção, exportação, minimização e limites da avaliação técnica |

## Mudanças orientadas por especificação

- [SDD-001 — Separação de responsabilidades](changes/001-separacao-responsabilidades.md): registro prospectivo escrito antes da refatoração, com mapeamento e critérios verificáveis.

## Decisões arquiteturais

- [ADR-001 — Python stdlib e interface web local](adr/001-python-stdlib-web-local.md).
- [ADR-002 — Execução sequencial e estado transitório](adr/002-execucao-sequencial-estado-transitorio.md).
- [ADR-003 — Fronteira local e proteções HTTP](adr/003-fronteira-local-e-protecao-http.md).
- [ADR-004 — Docker opcional e redes distintas](adr/004-docker-opcional-redes.md).
- [ADR-005 — Separação de responsabilidades no backend](adr/005-separacao-responsabilidades-backend.md).

ADRs 001–004 registram retrospectivamente decisões presentes na implementação inicial; não inventam aprovação formal anterior ao desenvolvimento. ADR-005 e SDD-001 acompanham a demanda explícita de refatoração desta rodada.

## O que este pacote afirma

Código nativo e Docker Linux, suíte Python e fluxo de navegador foram executados na entrega descrita pela matriz. Windows e Docker Desktop têm instruções, mas não foram executados. Cache frio, isolamento do Ollama, utilização GPU e garantia de performance não são recursos oferecidos.

Publicar o código no GitHub não significa disponibilizar um servidor web público. A aplicação continua destinada a uso pessoal local. Auditoria e publicação do repositório são gates próprios da entrega; esta documentação não substitui aprovação de segurança.

As evidências `test-results/`, `TEST_RESULTS.md` e relatórios de auditoria são arquivos locais ignorados, não distribuídos no repositório público. A matriz contém um resumo honesto e os comandos de reprodução; não depende de links para arquivos ausentes num clone público.

## Manter consistente

Altere primeiro os requisitos/BDD e contratos afetados, implemente, valide e atualize a matriz. Se houver divergência, identifique-a como desvio e corrija documento ou código segundo a intenção autorizada; não declare como implementado algo que só aparece no plano. Referências cruzadas e limites concretos devem ser conferidos contra os símbolos atuais, não contra memória de conversas.
