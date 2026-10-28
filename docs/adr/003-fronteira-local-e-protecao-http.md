# ADR-003 — Fronteira HTTP local e proteção das operações

- **Data da baseline:** 28/10/2026.
- **Status:** decisão observada na implementação; registro retrospectivo.

## Contexto

Mesmo uma ferramenta local pode receber requisições originadas por outra página aberta no navegador. A aplicação também aceita prompts, nomes de modelos e respostas que não devem virar HTML executável ou fórmulas ao exportar. O produto não exige contas, destinos remotos ou compartilhamento na rede.

## Decisão

Vincular o app nativo ao loopback por padrão. Validar `Host` com porta exata; quando `Origin` existir, exigir correspondência com `http://` mais o Host permitido; rejeitar `Sec-Fetch-Site: cross-site`. Para POST, exigir token aleatório do processo, JSON, ausência de `Transfer-Encoding` e limite de corpo. Não habilitar CORS.

O navegador acessa somente o servidor Python. O destino Ollama vem do ambiente e é restrito a HTTP e hostnames locais permitidos. A UI usa `textContent`, recursos locais e CSP. CSV neutraliza strings cujo início pode ser interpretado como fórmula. Os valores exatos e a ordem de validação estão na [especificação técnica](../especificacao-tecnica.md).

## Alternativas e consequências

| Alternativa | Avaliação retrospectiva |
| --- | --- |
| Navegador chamando Ollama diretamente | Exigiria gerir CORS e exporia ao frontend a integração e configuração de destino |
| Endpoint arbitrário digitado na página | Amplia a fronteira de rede sem necessidade do requisito local |
| Login e usuários | Adiciona gestão de credenciais e sessões sem requisito de compartilhamento |
| Loopback, mesma origem e token de processo | Proteção proporcional ao serviço pessoal local, mantendo o fluxo pequeno |

**Benefícios:** nenhuma alteração de CORS no Ollama; redução de comandos web cruzados e de destinos inesperados; sem credenciais para armazenar. **Limites:** token não é autenticação de pessoa; GETs não o exigem; ausência de `Origin` é aceita; processos locais autorizados a alcançar o serviço podem lê-lo. Não há isolamento entre abas ou usuário local hostil. `APP_BIND=0.0.0.0` é suportado para encaminhamento interno Docker, mas seu uso nativo ampliaria a exposição e não faz parte da operação recomendada.

## Evidências e revisão futura

Ver `Handler.local_request` e `Handler.do_POST` em [http](../../backend/http.py), `OllamaClient.__init__` em [ollama](../../backend/ollama.py), `csv_export` em [exports](../../backend/exports.py) e testes em [tests/test_benchmark.py](../../tests/test_benchmark.py). Os caminhos foram atualizados pela [SDD-001](../changes/001-separacao-responsabilidades.md), preservando as proteções da baseline original. Mudanças para acesso remoto ou rede pública exigem especificação própria de autenticação, autorização, TLS, retenção e limites de capacidade; esta baseline não aprova essa expansão.
