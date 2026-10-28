# Desenvolvimento orientado por especificação

## 1. Baseline e responsabilidade

A versão inicial foi implementada e validada antes deste pacote SDD. A refatoração de responsabilidades desta rodada tem registro prospectivo próprio: [SDD-001](changes/001-separacao-responsabilidades.md), escrito antes das alterações de código. Estes documentos são uma **baseline retrospectiva de 28/10/2026**: não representam aprovação prévia de requisitos, nem uma execução histórica de spec-first. A partir desta baseline, o processo abaixo orienta manutenção e evolução.

O produto usa Python 3.11+ e biblioteca padrão, frontend local e Ollama existente. Não adicionar framework, pacote, build frontend ou serviço de persistência como conveniência técnica sem requisito explícito e revisão arquitetural.

Referências: [SDD](sdd.md), [arquitetura](arquitetura.md), [contrato humano](especificacao-tecnica.md), [contrato para ferramentas](openapi.yaml), [rastreabilidade](rastreabilidade.md) e [operação](operacao.md).

## 2. Fluxo spec-first para uma mudança

1. **Demanda:** registre problema e resultado observável. Identifique usuários afetados, dados tratados e compatibilidade esperada.
2. **Especificação:** altere ou acrescente IDs RF/RNF/RN e história/BDD na SDD antes de mudar comportamento. Reutilize IDs existentes quando a intenção do requisito permanecer a mesma; não recicle IDs removidos.
3. **Contrato:** descreva requests, defaults, limites, respostas, estados e erro novos/alterados. Atualize OpenAPI quando a API mudar. Alterações somente de tema podem não afetar o contrato HTTP.
4. **Arquitetura:** avalie threads, estado global, medição, segurança local, memória e redes Docker. Crie ADR somente para decisão com trade-off duradouro; não registrar cada edição trivial como ADR.
5. **Teste que distingue comportamento:** planeje cenário que falharia antes da correção. Preferir fixture sintética/HTTP simulado para lógica; navegador real para interação/layout/tema; Ollama real para integração.
6. **Implementação mínima completa:** preserve erros, proteção de origem, medição correta e restrição de dependências. Não introduza opções ou abstrações sem demanda.
7. **Verificação e QA:** rode checks pertinentes; atualize matriz requisito→código→testes→evidência e registre plataformas realmente executadas. Nunca transformar alvo Windows/Desktop em homologação sem execução nesses ambientes.
8. **Review:** outra leitura confronta código, especificação, contrato e testes. Reprovação volta para implementação; correção de comportamento exige revalidar testes afetados antes de novo review.
9. **Entrega:** descreva comportamento final, testes, lacunas e riscos. Antes de publicação pública, revise segredos/dados pessoais e política de arquivos locais; publicação exige autorização da tarefa e gate de segurança aplicável.

Mudanças urgentes podem primeiro impedir dano/erro, mas devem completar a especificação e rastreabilidade antes de serem tratadas como entrega encerrada. Não falsificar uma cronologia spec-first após o fato.

## 3. Organização e pontos de mudança

| Área | Arquivos e contratos a revisar juntos |
| --- | --- |
| Validação/defaults | `backend.validation.validate_settings`, formulário HTML, coleta JS, schemas `StartRequest/Settings`, BDD e testes de limites |
| Métricas | `seconds`, `metrics`, captura de stream, resumo, UI, CSV, OpenAPI e testes de unidades/ausência |
| Fila/estado | `BenchmarkManager`, polling/UI, schema `State/Row/Summary`, casos de concorrência/cancelamento |
| Transporte Ollama | `OllamaClient`, limite de resposta, timeout/deadline, fixtures HTTP e troubleshooting |
| HTTP local | `Handler`, origem/Host/token/Content-Length/CSP, testes app e schemas de erro |
| Tema/UI | HTML, `web/app.js`, variáveis CSS, inicialização antes do CSS, storage bloqueado, teclado, ambos os temas |
| Deploy | Dockerfile, ambos os Compose independentes, variáveis/CLI e documentação de rede/portas |
| Exportação | `CSV_FIELDS`, `csv_export`, snapshots JSON, proteção contra fórmulas, schemas e testes |

## 4. Ambiente e checks

Nenhum pacote Python externo é necessário para executar os testes automatizados. Eles sobem servidores HTTP somente em loopback e portas efêmeras. Um ambiente sandbox que bloqueia sockets impede esses testes e não comprova falha do app.

Linux:

```bash
python3 -W error::ResourceWarning -m unittest discover -s tests -v
python3 -m compileall -q app.py backend tests
```

Windows:

```powershell
py -3 -W error::ResourceWarning -m unittest discover -s tests -v
py -3 -m compileall -q app.py backend tests
```

Validação de Compose, quando Docker estiver disponível:

```bash
docker compose config
docker compose -f compose.linux.yaml config
```

O repositório não instala tooling de navegador, renderizador Mermaid, validador OpenAPI, scanner ou pipeline CI. Ferramentas de desenvolvimento locais podem complementar a validação, sem se tornarem dependências do runtime. A suíte formal do projeto permanece Python stdlib.

### Verificar contrato sem dependências

O contrato usa sintaxe JSON dentro de `openapi.yaml`. Leitura básica:

```bash
python3 -m json.tool docs/openapi.yaml
```

Isso valida JSON, não toda a especificação OpenAPI. Para verificar referências locais com biblioteca padrão:

```python
import json
from pathlib import Path

contract = json.loads(Path("docs/openapi.yaml").read_text(encoding="utf-8"))

def check(value):
    if isinstance(value, dict):
        if "$ref" in value:
            reference = value["$ref"]
            assert reference.startswith("#/"), reference
            target = contract
            for part in reference[2:].split("/"):
                target = target[part.replace("~1", "/").replace("~0", "~")]
        for child in value.values():
            check(child)
    elif isinstance(value, list):
        for child in value:
            check(child)

assert contract["openapi"] == "3.1.0"
check(contract)
```

Para validar exemplos contra um validador completo OpenAPI/JSON Schema, use ferramenta de desenvolvimento aprovada fora do runtime. Não afirmar que apenas `json.tool` certifica conformidade OpenAPI.

## 5. Estratégia de testes

A [matriz](rastreabilidade.md) relaciona todos os nomes atuais da suíte e as lacunas. Níveis:

1. **Unidade:** validação, métricas, mediana, CSV e URLs de destino.
2. **Cliente HTTP simulado:** NDJSON fragmentado, UTF-8, conteúdo/raciocínio, erro, término incompleto, timeout e cancelamento.
3. **Gerenciador:** fila sequencial, rejeição de início concorrente, cancelamento e finalização atômica.
4. **App HTTP:** assets, token, Host/Origin, início, estado e exportação.
5. **Navegador manual/automação externa:** fluxo e layout em desktop/tablet/celular; teclado; tema claro/escuro, persistência, sistema e storage indisponível.
6. **Integração real:** modelo instalado no Ollama e exportações; modo nativo e Docker Linux. Não comparar desempenho entre modos usando quantidades diferentes de saída.
7. **Portabilidade futura:** execução Windows nativa e Docker Desktop, explicitamente ainda sem homologação na baseline.

O tema não recebe um motor JavaScript como dependência da suíte Python. Seu comportamento precisa ser validado no navegador, além do teste HTTP de markup/ordem do script. Não usar testes estáticos como substituto para essa validação.

## 6. Gates de conclusão de uma mudança

Uma mudança só deve ser apresentada como concluída quando:

- Requisito, BDD e comportamento final concordam.
- Contratos/defaults/limites e exemplos refletem código real.
- Testes pertinentes passam e cenários não executados são declarados.
- QA e review previstos foram aprovados após os últimos patches.
- Links e IDs da documentação existem; nenhum dado privado foi copiado de evidências locais.
- Nenhum token/segredo está em exemplos; caminhos de usuário são substituídos por caminhos relativos/placeholders.
- Resultados locais e relatórios de auditoria continuam fora do pacote público conforme ignore/política.

Não exigir uma nova rodada de benchmark real para edição puramente documental. Não reiniciar serviço para corrigir Markdown. Reexecutar verificação funcional quando houver alteração real, como a inclusão de tema nesta rodada.

## 7. Registro de alterações e compatibilidade

Ainda não existe versionamento semântico formal ou migração de dados, pois resultados não persistem no processo. `info.version` do OpenAPI identifica a baseline documental e não substitui versionamento de release. Se a API mudar, registrar alteração no contrato e explicar o efeito em clientes próprios que consomem `/api/*`.

Arquivos de exportação não têm versão de schema no envelope atual. Preservar nomes/unidades ou introduzir mudança explícita e documentada; não reinterpretar silenciosamente resultados antigos. Não há promessa de importação ou compatibilidade de escrita entre futuras versões.
