# Operação e diagnóstico

Este runbook é público e usa somente caminhos relativos. Nenhum comando abaixo foi executado por causa da documentação. As evidências da implementação anterior são locais e não acompanham o repositório público. Consulte [validação e lacunas](rastreabilidade.md) antes de tratar uma plataforma como homologada.

## 1. Pré-requisitos e início nativo

Python 3.11+, navegador e Ollama local com modelo de geração instalado. Não é necessário `pip`, `venv`, Node, Docker ou acesso à internet para o app nativo. O app não instala nem inicia o Ollama.

Na pasta do checkout:

| Ação | Linux | Windows / PowerShell |
| --- | --- | --- |
| Conferir Python | `python3 --version` | `py -3 --version` |
| Iniciar | `python3 app.py` | `py -3 app.py` |
| Sem abrir navegador | `python3 app.py --no-browser` | `py -3 app.py --no-browser` |
| Outra porta | `python3 app.py --port 8766` | `py -3 app.py --port 8766` |
| Encerrar | Ctrl+C no terminal do app | Ctrl+C no terminal do app |

Acesse `http://127.0.0.1:8765` ou a porta impressa. O terminal precisa continuar aberto. A abertura automática do navegador é tentativa, não pré-condição. Trocar porta muda a origem no navegador e também o espaço de armazenamento da preferência de tema.

Se houver erro de bind, escolha outra porta livre; não encerre processos desconhecidos para liberá-la. Use sempre a porta na URL e no Host; o serviço rejeita hosts diferentes de `127.0.0.1:<porta>` e `localhost:<porta>`.

Configuração por ambiente existe para processos avançados e containers; veja os defaults/restrições na [especificação técnica](especificacao-tecnica.md). Não use `APP_BIND=0.0.0.0` fora do container para expor o app na rede.

## 2. Uso normal e interpretação

1. Clique em **Atualizar modelos** e confirme a conexão. `/api/health` sozinho só confirma o app.
2. Selecione modelo(s) de geração já instalados; catálogo pode incluir modelos de embeddings que não geram texto.
3. Configure prompt, saída máxima, contexto, repetições e timeout. Comece com os valores padrão para não solicitar um contexto desproporcional à memória da máquina.
4. Evite outros clientes Ollama e carga pesada durante a medição. O app não consegue impedir concorrência externa.
5. Inicie e aguarde os resultados individuais. A primeira chamada aparece separada; resumo usa mediana das concluídas a partir da segunda.
6. Examine estado de cada linha. `Teste concluído` não significa que todas as gerações tiveram sucesso.
7. Exporte CSV ou JSON antes de iniciar outra comparação, reiniciar processo ou recriar container.

Compare modelos sob o mesmo prompt, limites e política de raciocínio. Mesmo com temperatura zero/seed42, não assuma determinismo entre plataformas. Repetições idênticas podem usar cache. O valor de tokens/s mede o estágio de geração informado pelo Ollama; TTFT inclui espera e carregamento vistos pelo cliente.

### Tema da interface

O seletor **Tema** no topo tem **Claro** e **Escuro**. Sem preferência válida salva, a página acompanha `prefers-color-scheme` do sistema. Depois da escolha explícita, essa escolha prevalece e é salva em `localStorage` na origem atual, quando permitido pelo navegador.

Storage bloqueado não impede a troca visual; a preferência permanece apenas na página atual e pode ser perdida no reload. Não existe opção Sistema/reset na interface nem sincronização instantânea entre abas. `localhost` e `127.0.0.1`, assim como portas diferentes, são origens distintas; podem ter preferências diferentes. A preferência de tema não é enviada ao Python e não faz parte das exportações.

## 3. Cancelamento e descarte de resultados

**Cancelar teste** sinaliza o worker e tenta fechar o socket da geração atual. Não é garantia de liberação imediata da GPU pelo Ollama. Cancelamento durante consultas de metadados não possui watchdog global equivalente ao da inferência.

Depois que o estado deixar `running/cancelling`, outro teste pode começar. Texto parcial da execução cancelada não é exportado. Resultados concluídos antes do cancelamento continuam disponíveis até novo job/reinício.

Não há recuperação após fechar o processo. Os arquivos de exportação são o mecanismo de preservação manual; não existe importação desses arquivos pelo app.

## 4. Execução com Docker

Ollama permanece no host. O container não recebe GPU e não contém modelos; apenas faz HTTP ao Ollama existente. Não precisa de modo privilegiado ou montagem de dispositivos.

### Linux com Docker Engine nativo e Ollama em loopback

```bash
docker compose -f compose.linux.yaml config
docker compose -f compose.linux.yaml up --build -d
```

O arquivo Linux é **independente**, não override para mesclar com `compose.yaml`. Usa `network_mode: host`, app em `127.0.0.1:8765` e destino `http://127.0.0.1:11434`. Não contém publicação de portas.

```bash
docker compose -f compose.linux.yaml ps
docker compose -f compose.linux.yaml logs --tail 50
docker compose -f compose.linux.yaml down
```

Execute na pasta deste projeto para operar somente este serviço. Não pare containers de outros projetos. `down` e recriação descartam resultados que estavam na memória; exporte antes.

### Docker Desktop ou host alcançável pelo gateway

```bash
docker compose config
docker compose up --build -d
```

Esse modo publica `127.0.0.1:8765:8765`. App escuta `0.0.0.0` apenas dentro do container e usa `host.docker.internal:11434`, provisionado por `host-gateway` no Compose.

A resolução do nome não garante acesso a um Ollama vinculado somente ao loopback do host. A integração dessa configuração não foi executada no ambiente da baseline; o arquivo passou validação de configuração. Se a conexão falhar, use execução Python nativa; em Linux nativo use o arquivo Linux. Não altere bind do Ollama ou firewall sem avaliar separadamente o efeito de exposição.

Não inicie ambos os modos juntos, pois usam a mesma porta. O primeiro build pode precisar baixar `python:3.12-slim`; isso é requisito do Docker, não do funcionamento nativo offline. O Compose não define healthcheck, restart automático, volume de persistência ou serviço Ollama.

## 5. Diagnóstico por sintoma

| Sintoma | Verificação e ação dentro do escopo |
| --- | --- |
| Página não abre | Confirme processo/serviço deste app e porta impressa; tente URL manual e outra porta livre |
| Health OK, Ollama indisponível | `/api/health` não testa o Ollama; atualize modelos e confira destino/servidor local |
| Falha somente no Docker | Confira qual Compose iniciou; bridge/gateway não equivale a loopback do host |
| Catálogo vazio | Instale um modelo de geração no Ollama por procedimento próprio; o app não faz downloads |
| Modelo ausente após 202 | Catálogo é validado assincronamente; atualize lista e selecione modelo disponível |
| Modelo de embeddings falha | Selecione um modelo de geração; a UI não filtra capacidades |
| 403 Host ou origem | Use URL local com porta correta; não use proxy/domínio externo; atualize a página |
| 403 token | Recarregue a página após reiniciar o app; token é recriado por processo |
| 409 em novo teste | Aguarde conclusão/cancelamento do job existente; todas as abas compartilham a instância |
| 400/413/415 ao usar cliente próprio | Confira JSON, tipos estritos, limites e headers; consulte OpenAPI/especificação |
| Timeout de geração | Reduza saída/contexto ou aumente timeout dentro dos limites; examine a linha falha |
| Cancelamento ainda em andamento | Aguarde o worker finalizar; metadados e servidor externo têm limitações descritas |
| Primeiro texto demora | Verifique carga do modelo, prompt/contexto e raciocínio; TTFT difere de tokens/s |
| Resumo com `—` | Não há valor numérico elegível nas repetições concluídas; primeira/falhas não entram |
| GPU não identificada | App só registra memória informada; não mede utilização nem descobre Vulkan/ROCm |
| Preferência do tema some | Confira storage permitido e mesma origem; reload sem storage pode voltar ao sistema |
| CSV começa com apóstrofo | Proteção contra fórmulas em strings que começam com caracteres especiais |
| Resultados sumiram | Novo teste/reinício substitui memória; procure exportação manual anterior |

## 6. Logs, privacidade e suporte

Logs de acesso do `BaseHTTPRequestHandler` são suprimidos. O processo imprime URL e encerramento; não há arquivo de log ou métricas operacionais persistidas. Falhas previstas são apresentadas na UI/estado; exceções inesperadas podem aparecer no stderr do processo/container. Não há endpoint de diagnóstico de sistema.

Para relatar bug, inclua versão do Python/SO/Ollama/Docker quando pertinente, modo nativo/container, parâmetros reduzidos e mensagem de erro. Substitua dados pessoais de prompts/respostas e nomes privados por exemplos sintéticos. Não publique token da página, cookies, ambiente completo, exportações ou capturas sem revisão.

`test-results/`, `TEST_RESULTS.md` e relatórios de auditoria locais não fazem parte do repositório público. O histórico de validação descrito nesta documentação é um resumo retrospectivo, não evidência distribuída. Política pública: [SECURITY.md](../SECURITY.md).

## 7. Checklist antes de atualizar

- Exporte o que precisa conservar.
- Pare somente a instância deste projeto.
- Consulte mudanças de contrato e plataforma na [SDD](sdd.md) e [especificação](especificacao-tecnica.md).
- Atualize código/arquivos e valide suíte; no Docker, reconstrua imagem.
- Abra a UI, confirme conexão/modelos e teste primeiro com saída curta.
- Mantenha mudanças de Ollama, firewall e drivers fora de uma atualização rotineira deste app.
