# Ollama Benchmark Local

Aplicação web local para medir o desempenho do Ollama em Windows e Linux. Usa somente a biblioteca padrão do Python e arquivos HTML/CSS/JavaScript locais. Não precisa de `pip`, Node, banco de dados ou internet durante os testes.

## Documentação de manutenção

A [documentação SDD completa](docs/README.md) reúne requisitos e BDD, arquitetura C4 e ADRs, especificação técnica/OpenAPI, rastreabilidade, operação, desenvolvimento e revisão SOLID. O [backlog](docs/backlog.md) registra a validação Windows/Docker Desktop ainda pendente (TASK-WIN-01).

O seletor **Tema** no topo permite **Claro** ou **Escuro**. Sem preferência salva, acompanha o sistema. A escolha é persistida no navegador quando o armazenamento está disponível; storage bloqueado não impede a troca visual.

## Instalar como aplicativo (PWA)

O ícone original combina um velocímetro e uma lhama estilizada. Abra **http://127.0.0.1:8765** no Chrome ou Edge e use **Instalar aplicativo**, quando o navegador disponibilizar o botão, ou a opção de instalação no menu do navegador. A aplicação instalada abre em janela própria, conforme o suporte do navegador.

Mantenha o mesmo endereço e porta: `localhost` e `127.0.0.1` são origens distintas. A PWA não instala Python/Ollama nem inicia os servidores automaticamente. Com o servidor parado, mostra uma página explicativa offline; medições exigem o app e o Ollama em execução.

O service worker guarda somente recursos públicos de uma lista explícita: página offline, FAQ, script de ajuda/tema, CSS, manifesto e ícones. **Não guarda a página principal com token, APIs, prompts, respostas ou exportações.** Limpar os dados do site remove o cache e a preferência de tema. Não há dependências Python adicionais.

## Requisitos

- Python 3.11 ou superior.
- Navegador.
- Ollama instalado, iniciado e com pelo menos um modelo de geração instalado na mesma máquina.

O app não instala, baixa ou modifica modelos. Docker e Compose são opções de execução; não são dependências do modo Python.

## Iniciar e parar pelos scripts da raiz

Depois de instalar Python 3.11+, abra um terminal na pasta do projeto:

| Modo | Linux / Bash | Windows / PowerShell |
| --- | --- | --- |
| Iniciar nativo | `./start.sh` | `.\start.ps1` |
| Parar nativo | `./stop.sh` | `.\stop.ps1` |
| Iniciar com Docker | `./start.sh --docker` | `.\start.ps1 -Docker` |
| Parar com Docker | `./stop.sh --docker` | `.\stop.ps1 -Docker` |

Acesse **http://127.0.0.1:8765**. O modo nativo inicia `app.py` em segundo plano. Para outra porta nativa: `./start.sh --port 8766` ou `.\start.ps1 -Port 8766`. O stop usa a porta registrada; não encerra processos apenas por ocuparem a porta.

Iniciar/parar novamente é seguro: os scripts verificam a identidade da instância deste checkout. `service.local.json`, `service.local.log` e `service.local.lock` são arquivos operacionais locais ignorados pelo Git. Não altere o estado manualmente enquanto o app estiver ativo. Uma instância iniciada diretamente com `python3 app.py` não é adotada automaticamente pelos wrappers; encerre-a no terminal original antes de usar start.

Pare o modo atual antes de trocar entre nativo e Docker. O modo Docker usa o Compose do projeto e preserva volumes no stop; precisa de Docker/Compose e Python. Não muda Ollama, firewall ou ExecutionPolicy. Conclua ou cancele a comparação antes de parar o servidor: progresso ainda ativo pode não ter sido salvo. Scripts e instruções Windows estão implementados; homologação Windows real continua pendente.

## Rodar com Python

Abra um terminal na pasta deste projeto.

Windows:

```powershell
py -3 app.py
```

Linux:

```bash
python3 app.py
```

Acesse **http://127.0.0.1:8765**. O app tenta abrir essa página automaticamente. Para iniciar sem abrir o navegador:

```bash
python3 app.py --no-browser
```

No Windows, substitua `python3` por `py -3`. Para outra porta: `python3 app.py --port 8766`.

O processo precisa continuar aberto. Para encerrar, pressione **Ctrl+C**. Comparações encerradas são salvas em JSON no perfil de quem executa o app, em `~/.ollama_benchmark`. A última comparação válida reaparece ao iniciar; a tabela Resultados inclui comparações anteriores, com data e ação Detalhes para carregar outra com confirmação. CSV/JSON continuam disponíveis para compartilhar.

## Como usar

1. Confira a conexão e selecione um ou vários modelos instalados.
2. Edite o prompt ou abra **Biblioteca de pedidos** para escolher entre 18 exemplos de código/não código, filtrados por complexidade. A prévia só troca o texto ao clicar **Usar pedido**; edições exigem confirmação. Selecionar não inicia teste nem muda limites/modelos. Use o mesmo pedido para todos os modelos.
3. Defina o limite de saída, contexto, execuções e timeout. O padrão é 128 tokens, contexto 4.096, três execuções e 180 segundos por execução.
4. Clique em **Iniciar comparação**. O app executa os modelos e repetições sequencialmente.
5. Veja o progresso, resultados individuais e resumo. Exporte CSV ou JSON para guardar.

A primeira chamada aparece separada das demais. O resumo usa a mediana das execuções 2 em diante. O app registra se o modelo já estava carregado antes de cada chamada, sem forçar descarregamento. O Ollama pode descarregar modelos para acomodar outros, conforme sua própria configuração.

**Cancelar teste** impede próximas execuções e tenta interromper a conexão atual. Isso não garante que o Ollama libere a GPU imediatamente. Consultas de metadados podem levar até cinco segundos para expirar.

Se o modelo não suportar geração ou rejeitar a opção de raciocínio, a execução registra o erro retornado. Uma falha não apaga os resultados anteriores. Nenhum download automático será iniciado.

## Resumo dinâmico do ambiente

O topo apresenta uma faixa compacta de SO, CPU, GPU e RAM com **Ver detalhes**, timestamp e atualização. Os dados vêm do ambiente atual do backend, nunca de um inventário de exemplo; valores indisponíveis aparecem como **Não informado**. O painel funciona com mouse, teclado e toque, nos temas claro/escuro.

No Docker, o rótulo distingue o container: CPU/kernel podem ser compartilhados, memória respeita o escopo conhecido e GPU não exposta não significa ausência física. O resumo não identifica automaticamente o host nem a GPU usada pelo Ollama. Disco significa o sistema de arquivos do app, não todos os discos físicos.

O snapshot fica somente em memória e fora das exportações/cache PWA. Atualização dinâmica limitada a dez segundos, pausada durante benchmarks. O app não exige neofetch/fastfetch, administrador ou pacotes Python adicionais.

## Acompanhamento ao vivo e FAQ

Durante cada teste do app, acompanhe a prévia da resposta, tempo decorrido, primeiro conteúdo/texto e quantidade de caracteres/fragmentos recebidos. **Fragmentos não são tokens.** O Ollama normalmente entrega as estatísticas completas no fim; até lá, os tokens exatos aparecem como aguardando medição final. A opção **Contar tokens de saída ao vivo (instrumentado)** usa metadados opcionais `logprobs` quando o Ollama/modelo os fornece, com conferência pelo contador final. Ela começa desligada e pode alterar o desempenho do teste; compare modos equivalentes. Sem metadata válida, a contagem observada fica indisponível. Não há estimativa por caracteres nem monitoramento de outros aplicativos Ollama.

Ao terminar, a interface mostra entrada, saída, cache e total informado (entrada + saída, sem somar cache novamente), além do acumulado somente das execuções concluídas. Falhas/cancelamentos ou contadores ausentes não representam uso faturável zero. O app não calcula fatura ou tarifa de provedor.

O link **Conceitos e FAQ** abre uma página estática com definições, exemplos de custo, interpretação de latência e limites. Ajuda breve nos controles funciona por mouse, teclado e toque. A FAQ fica disponível offline depois de armazenada pela PWA; o benchmark continua exigindo os servidores locais.

## Métricas

| Campo | Significado |
| --- | --- |
| Tokens/s | `eval_count / eval_duration × 1.000.000.000` |
| Primeiro conteúdo | Tempo do envio até o primeiro fragmento com texto ou raciocínio |
| Primeiro texto | Tempo do envio até o primeiro fragmento da resposta visível |
| Total medido | Tempo no cliente Python até concluir o stream |
| Total Ollama | `total_duration` retornado pelo servidor |
| Carga | Tempo informado pelo Ollama para carregar o modelo |
| Prompt | Tempo informado para processar o prompt |
| Geração | Tempo informado para gerar a saída |
| Tokens | Contagem real retornada pelo Ollama, não número de fragmentos do stream |

Os tempos informados pelo Ollama são convertidos de nanossegundos para segundos. Durações ausentes ou nulas não produzem velocidades inventadas. O limite de saída é um máximo: um modelo pode terminar antes dele. O JSON registra o motivo de término e preserva o texto gerado, limitado a 64.000 caracteres por execução. O CSV inclui parâmetros, prompt, data e métricas; o JSON inclui também texto, resumo e mensagens de aviso.

Temperatura 0 e seed 42 são fixos para reduzir variação, sem garantir resultados idênticos entre plataformas. Raciocínio começa desativado e pode ser habilitado para modelos compatíveis. Quando há raciocínio, o primeiro texto pode chegar depois do primeiro conteúdo; os tokens de saída informados pelo Ollama podem incluir raciocínio.

Pedidos idênticos repetidos podem aproveitar cache de prompt. A primeira chamada não representa necessariamente cache frio do sistema operacional. Outros aplicativos usando Ollama, carga do computador, contexto, quantização e tamanho da resposta alteram os tempos. O app não oferece isolamento entre clientes.

O JSON inclui memória do modelo e `size_vram` quando disponível em `/api/ps`. Isso representa alocação informada pelo Ollama; não mede uso percentual da GPU e não identifica o backend Vulkan/ROCm.

## Docker e Docker Compose

O container executa somente este app. **O Ollama continua no host**, fora do container. Não é necessário passar dispositivos GPU para o container do benchmark.

### Docker Desktop ou host acessível pelo gateway

```bash
docker compose up --build -d
```

Abra **http://127.0.0.1:8765**. Esse arquivo publica a interface somente no loopback do host. Dentro do container, o app escuta em `0.0.0.0` para permitir o encaminhamento da porta. O destino do Ollama é `http://host.docker.internal:11434`.

**Atenção à rede:** resolver `host.docker.internal` não garante acesso a um Ollama que escuta somente em `127.0.0.1`. O comportamento depende do Docker Desktop e da rede do host. Em Docker Engine nativo no Linux, o gateway normalmente não acessa serviços vinculados somente ao loopback. O app mostrará o erro de conexão. Este projeto não altera `OLLAMA_HOST`, firewall ou serviços do computador.

Se o Docker Desktop não alcançar o seu Ollama local, use o modo Python, que acessa diretamente o loopback. Não exponha o Ollama para toda a rede apenas para rodar o benchmark.

### Linux com Docker Engine nativo e Ollama em loopback

Use o arquivo Linux **sozinho**, sem combinar com `compose.yaml`:

```bash
docker compose -f compose.linux.yaml up --build -d
```

Esse modo usa a rede do host, app vinculado a `127.0.0.1:8765` e Ollama em `127.0.0.1:11434`. Não publica portas. É a opção para este PC Linux com o Ollama vinculado somente ao loopback. Não inicie os dois modos ao mesmo tempo, porque usam a mesma porta.

O arquivo é separado para evitar a mesclagem acidental de `ports` com `network_mode: host`. Não precisa de tags YAML especiais nem versões recentes de Compose para limpar campos herdados.

Comandos úteis:

```bash
docker compose config
docker compose logs --tail 50
docker compose down
```

No modo Linux, inclua `-f compose.linux.yaml` em todos esses comandos. `down` encerra somente este projeto. Não execute comandos para parar containers de outros projetos.

O Dockerfile usa a imagem oficial `python:3.12-slim`, usuário sem privilégios, filesystem somente leitura no Compose, capabilities removidas e `no-new-privileges`. O primeiro build precisa baixar a imagem se ela não existir localmente. O volume nomeado do histórico preserva comparações terminais ao recriar o container com o mesmo projeto; progresso ativo ainda não salvo pode ser perdido.

## Testes

Não exigem Ollama, pois incluem um servidor HTTP simulado da biblioteca padrão:

```bash
python3 -m unittest discover -s tests -v
```

No Windows:

```powershell
py -3 -m unittest discover -s tests -v
```

Cobertura: cálculo de métricas, duração zero, validação, stream fragmentado/UTF-8, raciocínio, erro no stream, stream incompleto, timeout, cancelamento, fila sequencial, resultados preservados, proteção de origem/Host/token e exportação CSV/JSON.

Validação real deve conferir um modelo instalado pelo navegador, verificar os tempos e baixar as exportações. Testes automatizados não comprovam execução em Windows sem uma execução real nesse sistema.

## Configuração e segurança local

O padrão nativo é `127.0.0.1:8765` com Ollama em `127.0.0.1:11434`. Configurações avançadas são variáveis de ambiente do processo, nunca campos livres da página:

- `APP_PORT`: porta da interface, padrão `8765`.
- `APP_BIND`: `127.0.0.1`; `0.0.0.0` existe somente para a rede interna do container. Não use esse valor para expor a execução nativa.
- `OLLAMA_URL`: HTTP com destino restrito a `127.0.0.1`, `localhost`, `::1` ou `host.docker.internal`.

A interface valida `Host` e `Origin`, exige JSON e token de sessão para operações, limita o corpo recebido e não habilita CORS. O navegador acessa apenas o app Python; esse app chama o Ollama. O serviço foi feito para uso pessoal local, não como servidor público.

## Estrutura

- `app.py`: composition root, CLI e inicialização.
- `backend/http.py`: HTTP local e interface.
- `backend/ollama.py`: cliente Ollama e stream.
- `backend/manager.py`: fila, estado e cancelamento.
- `backend/metrics.py`, `backend/validation.py`, `backend/exports.py`: cálculos, validação e exportação.
- `web/`: interface sem dependências externas.
- `tests/`: testes unitários e HTTP simulado.
- `Dockerfile`, `compose.yaml`, `compose.linux.yaml`: execução opcional em container.

Documentação de referência consultada via Context7: [API do Ollama](https://github.com/ollama/ollama/blob/main/docs/api.md) e [Docker Compose](https://github.com/docker/compose).

A complexidade dos exemplos é editorial, não prevê tokens/custo/tempo. Exemplos longos podem exigir maior limite de saída, ajustado manualmente. O guia de tokens, tempos e custos está logo abaixo do nome do app. Na faixa de hardware e nos detalhes do ambiente, hostname identifica apenas a máquina/container onde este backend executa: nome local volátil, sem consulta DNS, separado das exportações e do cache. Evite compartilhar capturas com identificadores locais.

## Histórico local

O app cria `~/.ollama_benchmark` no perfil de execução. Guarda uma comparação por JSON depois de completed, failed ou cancelled, incluindo pedido/respostas e métricas; não grava cada fragmento nem recupera uma inferência interrompida por crash. Não apaga comparações antigas automaticamente. Falhas de disco/permissão ou arquivo corrompido geram aviso sem derrubar o app. Proteja esses arquivos e seus backups; consulte [privacidade](PRIVACY.md).

Ao abrir, a última comparação válida restaura resultados e formulário se você ainda não o editou. Na tabela Resultados, use Detalhes e confirme a carga para substituir o formulário/detalhes atuais; a ação não executa teste e fica bloqueada enquanto outro estiver ativo. Modelos ausentes são sinalizados. No Docker, o histórico pertence ao perfil dentro do container e é mantido em volume nomeado do projeto: não é a pasta do perfil nativo do host.

Na seção Resultados, **s = segundos** e **tokens/s = tokens de saída por segundo**. O comparativo aparece antes dos detalhes, e Como ler as métricas explica as unidades; mais conceitos ficam no guia.

A tabela Resultados reúne as comparações do perfil e a comparação atual, com **Data/hora da execução**. As métricas de datas/jobs diferentes permanecem separadas. Abrir Detalhes de uma comparação antiga não remove as demais linhas; CSV/JSON exportam somente a comparação exibida nos detalhes, identificada por data. A instalação como aplicativo fica na ajuda opcional do rodapé.
