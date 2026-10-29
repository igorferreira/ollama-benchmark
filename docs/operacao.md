# Operação e diagnóstico

Este runbook é público e usa somente caminhos relativos. Nenhum comando abaixo foi executado por causa da documentação. As evidências da implementação anterior são locais e não acompanham o repositório público. Consulte [validação e lacunas](rastreabilidade.md) antes de tratar uma plataforma como homologada.

## Instalação PWA

Abra o endereço local no Chrome/Edge. Use o botão **Instalar aplicativo** quando oferecido ou a opção de instalar no menu do navegador. Mantenha a mesma origem e porta após instalar. A instalação não inicia o Python, o Docker ou o Ollama automaticamente. Com o servidor parado, a tela offline explica a inicialização. Para remover recursos persistentes, limpe os dados do site no navegador; para desinstalar, use as opções dele. Dados de benchmark e tokens não entram no cache da PWA.

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

Depois que o estado deixar `running/cancelling`, outro teste pode começar. A última prévia incompleta pode permanecer no estado ao vivo e na exportação JSON; a linha cancelada não recebe contagem final inventada. O CSV não contém a prévia. Resultados concluídos antes do cancelamento continuam disponíveis até novo job/reinício.

Comparações terminais são salvas em ~/.ollama_benchmark e a última válida é recuperada ao iniciar. A tabela Resultados apresenta data/modelo de registros locais; Detalhes carrega uma comparação com confirmação; não há importação de arquivos arbitrários. Em crash durante teste, o progresso ativo não é recuperado.

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

Execute na pasta deste projeto para operar somente este serviço. Não pare containers de outros projetos. `down` e recriação descartam progresso ainda ativo em memória, mas o volume nomeado mantém comparações terminais. Não use --volumes se pretende conservar o histórico.

### Docker Desktop ou host alcançável pelo gateway

```bash
docker compose config
docker compose up --build -d
```

Esse modo publica `127.0.0.1:8765:8765`. App escuta `0.0.0.0` apenas dentro do container e usa `host.docker.internal:11434`, provisionado por `host-gateway` no Compose.

A resolução do nome não garante acesso a um Ollama vinculado somente ao loopback do host. A integração dessa configuração não foi executada no ambiente da baseline; o arquivo passou validação de configuração. Se a conexão falhar, use execução Python nativa; em Linux nativo use o arquivo Linux. Não altere bind do Ollama ou firewall sem avaliar separadamente o efeito de exposição.

Não inicie ambos os modos juntos, pois usam a mesma porta. O primeiro build pode precisar baixar `python:3.12-slim`; isso é requisito do Docker, não do funcionamento nativo offline. O Compose não define healthcheck, restart automático, serviço Ollama; a SDD-007 adiciona volume nomeado somente para o histórico.

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
| Resultados sumiram | Verifique a tabela Resultados e avisos de armazenamento; progresso interrompido pode não ter sido salvo |

## 6. Logs, privacidade e suporte

Logs de acesso do `BaseHTTPRequestHandler` são suprimidos. O processo imprime URL e encerramento; não há arquivo de log operacional mantido pelo app. Comparações terminais são persistidas no histórico local conforme a seção 10; ferramentas externas podem redirecionar stdout/stderr para arquivos próprios. Falhas previstas aparecem na UI/estado, e exceções inesperadas podem aparecer no stderr. O endpoint `/api/system` apresenta somente o resumo mínimo e volátil do ambiente, separado do histórico e das exportações.

Para relatar bug, inclua versão do Python/SO/Ollama/Docker quando pertinente, modo nativo/container, parâmetros reduzidos e mensagem de erro. Substitua dados pessoais de prompts/respostas e nomes privados por exemplos sintéticos. Não publique token da página, cookies, ambiente completo, exportações ou capturas sem revisão.

`test-results/`, `TEST_RESULTS.md` e relatórios de auditoria locais não fazem parte do repositório público. O histórico de validação descrito nesta documentação é um resumo retrospectivo, não evidência distribuída. Política pública: [SECURITY.md](../SECURITY.md).

## 7. Checklist antes de atualizar

- Exporte o que precisa conservar.
- Pare somente a instância deste projeto.
- Consulte mudanças de contrato e plataforma na [SDD](sdd.md) e [especificação](especificacao-tecnica.md).
- Atualize código/arquivos e valide suíte; no Docker, reconstrua imagem.
- Abra a UI, confirme conexão/modelos e teste primeiro com saída curta.
- Mantenha mudanças de Ollama, firewall e drivers fora de uma atualização rotineira deste app.

## 8. Acompanhamento ao vivo e conceitos

O painel ao vivo mostra apenas testes iniciados neste app. Prévia, caracteres, fragmentos e cronômetro indicam atividade; fragmentos não equivalem a tokens. Tokens finais de entrada/saída/cache/total aguardam a estatística do Ollama. O acumulado soma somente execuções completed e não representa cobrança de terceiros.

A opção **Contar tokens de saída ao vivo (instrumentado)** começa desligada. Ao ligar, o app solicita metadata logprobs por token; se compatível, mostra contagem observada provisória. Metadata ausente/malformada deixa esse contador indisponível, sem estimativa ou retry. Ao fim, a conferência compara com eval_count e o contador final prevalece. A opção pode alterar throughput/latência; compare sempre modos equivalentes.

Use o link de FAQ no cabeçalho para explicações e exemplos educativos de cobrança/latência. Passe o mouse, use foco/Enter ou toque nos botões de ajuda; Escape fecha a explicação. A FAQ não depende do Ollama ligado e fica disponível offline depois de instalada no cache público da PWA. A página principal continua exigindo servidor e token novo; não é guardada offline.

Se a opção instrumentada for rejeitada, a linha registra o erro e as anteriores permanecem; desative a opção para outro teste somente por decisão explícita. Não há reenvio silencioso que duplique a inferência.

## 9. Resumo do ambiente e detalhes

A faixa no topo é dinâmica para o backend atual. Use Ver detalhes por mouse, foco ou toque; Escape e Fechar recolhem o painel sem prender a navegação. Clique mantém o painel aberto; sair com o ponteiro fecha quando não estiver fixado e não houver foco dentro. Nomes completos permanecem nos detalhes, mesmo quando o resumo abrevia prefixos redundantes para caber melhor.

Atualizar respeita intervalo mínimo de dez segundos. Durante benchmark, o botão/polling são pausados e o backend devolve o snapshot anterior como pausado; não interpretar o timestamp antigo como leitura instantânea. Fonte indisponível mantém Não informado. Não há inventário nas exportações do benchmark ou no cache PWA.

No Docker, capacidade total de RAM pode ser desconhecida se o limite não estiver comprovável; GPU sem dispositivo/nome exposto não significa ausência de GPU física. CPU/kernel podem ser compartilhados, disco é o agregado do sistema de arquivos do app e o ambiente não identifica automaticamente o alvo Ollama. Não habilite privilégios/mounts sensíveis/Docker socket apenas para preencher campos.

Se a rota responder 503, confirme execução pela entrada app.py com coletor composto; fixtures/servidores personalizados sem coletor não fazem descoberta automaticamente. Erros são genéricos para não expor caminhos privados. Não publique capturas reais sem avaliar fingerprint; use exemplos sintéticos para relatar problemas.

## Histórico no perfil e recuperação

A pasta ~/.ollama_benchmark pertence ao usuário que executa o processo. Guarda JSON por comparação terminal; abrir outro checkout pelo mesmo perfil pode compartilhar essa pasta. Pare o app antes de gerir arquivos manualmente. Não publique histórico em issues ou Git: pedidos/respostas podem ser privados.

No Docker, HOME aponta para o perfil do usuário não privilegiado do container. Volume nomeado montado só na pasta do histórico mantém dados entre recriações com o mesmo projeto Compose. Não há montagem do perfil nativo do host. Trocar o nome do projeto Compose pode selecionar outro volume; remover volumes remove seus dados. Windows/Docker Desktop continuam sem homologação real neste ambiente.

Se aparecer aviso de histórico indisponível, exporte os resultados em memória e verifique espaço/permissões no perfil do processo. Não publique caminhos pessoais nem conteúdo dos arquivos em logs públicos. Arquivos inválidos são ignorados com aviso e não apagados automaticamente. Falha do processo antes da conclusão não retoma geração na próxima abertura.


## 11. Scripts de início e parada

Os quatro wrappers ficam na raiz: start.sh/stop.sh para Bash e start.ps1/stop.ps1 para PowerShell 5.1/7. Eles resolvem a pasta do próprio script, inclusive com espaços, e chamam scripts/service.py com Python 3.11+. Não instalam pacotes nem alteram políticas do computador.

Modo nativo: `./start.sh` / `./stop.sh`, ou `.\start.ps1` / `.\stop.ps1`. Outra porta no start: `--port 8766` / `-Port 8766`. O processo roda em segundo plano com bind em 127.0.0.1; o estado operacional registra a porta e a identidade do próprio app. Arquivos service.local.json/log/lock são ignorados e não são histórico de benchmarks. Logs podem conter erros de inicialização; não os publique sem revisão.

Estado ausente em stop informa que não há instância gerenciada; estado corrompido ou identidade divergente causa recusa segura. Não mate por nome ou porta. Linux valida criação/boot, executável e argv via /proc e sinaliza por pidfd; kernel sem pidfd recusa parada automática. Windows valida CreationDate/ExecutablePath/CommandLine do Win32_Process e usa handle de processo, sem pedir administrador. Identidade indisponível é uma falha fechada. A parada Windows termina o processo; comparações ativas não têm garantia de salvamento, portanto conclua/cancele antes.

Modo Docker: `--docker` / `-Docker`. Linux usa compose.linux.yaml independente; Windows usa compose.yaml para Docker Desktop. O start verifica porta, serviço do próprio projeto, prontidão HTTP e hostname do container; não confunde saúde de outra instância com sucesso. A propriedade dos containers existentes, inclusive parados, é validada pelos labels de diretório/configuração do checkout. Stop usa somente docker compose stop benchmark, sem down/prune/remoção de volumes. Troque de modo somente após parar o anterior. Scripts não assumem controle de app iniciado manualmente sem seu estado operacional.

A equipe não altera ExecutionPolicy global nem instala Python/Docker. PowerShell pode seguir restrições do computador; a política de execução deve ser administrada pela pessoa responsável pelo ambiente. Testes com pwsh no Linux cobrem sintaxe e fluxo disponível nesse host, não homologam Windows PowerShell 5.1 no Windows.
