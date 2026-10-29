# ADR-006 — Histórico JSON terminal no perfil do processo

Estado: aceito para implementação por solicitação explícita da SDD-007. Data: 29/10/2026.

## Contexto

O estado exclusivamente transitório da baseline perdia comparações ao fechar o processo. A pessoa usuária solicitou salvar e recuperar resultados no perfil local, mantendo Python stdlib e funcionamento nativo/Docker. A decisão substitui a parte de retenção transitória da ADR-002; execução sequencial e estado compartilhado continuam iguais.

## Decisão

Usar um envelope JSON version:1 por comparação terminal em Path.home()/.ollama_benchmark, com ID UUID hex, arquivo limitado64MiB, escrita temporária restrita+fsync+replace. Injetar HistoryRepository na composição e manter persistência fora do transporte/cliente Ollama e lock do manager. Preparar pasta no startup, recuperar último terminal válido e revalidar atividade/geração antes de carga explícita. Token/hostname/inventário ficam fora do envelope; summary/usage são recalculados.

Docker usa volume nomeado apenas para essa pasta no perfil do UID65534, com root filesystem read-only. Não montar perfil do host nem adicionar serviço de banco. A pessoa gerencia retenção/backup e conteúdo privado; não há exclusão/pruning automático.

## Consequências

- Preserva comparações sem dependência externa ou gravação por fragmento; uma falha de armazenamento não perde os resultados em memória.
- Crash durante inferência não produz checkpoint nem retomada. Arquivos inválidos são ignorados com aviso e não apagados.
- JSON legível facilita inspeção/backup, mas contém prompts/respostas e não tem criptografia pelo app. Permissões Linux não equivalem a uma garantia de ACL Windows.
- A listagem/recuperação varre arquivos: IO cresce com o histórico, embora não retenha todos os textos na memória. Não há índice, paginação ou limite de retenção global.
- Alternativas banco/SQLite e journal contínuo foram rejeitadas neste escopo por adicionarem gestão sem necessidade; podem ser avaliadas se tamanho/uso real justificar.
