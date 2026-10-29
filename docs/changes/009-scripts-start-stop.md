# SDD-009 — Scripts de início e parada na raiz

Registro prospectivo de 29/10/2026, anterior ao código. A solicitação autoriza `start.sh`, `stop.sh`, `start.ps1` e `stop.ps1` na raiz, sem instalar dependências ou alterar políticas do sistema.

## Escopo e contrato

Os quatro scripts chamam um helper Python stdlib compartilhado em `scripts/service.py`. O modo padrão inicia somente `app.py`, em segundo plano, com Python 3.11+, bind loopback e porta 8765. `--port` no Bash e `-Port` no PowerShell permitem outra porta nativa. Início e parada repetidos são idempotentes. Não criar serviço de sistema, autostart, ambiente virtual ou script de instalação.

O estado operacional `service.local.json`, o log `service.local.log` e o lock `service.local.lock` ficam na raiz e são ignorados pelo Git. Não contêm prompts, respostas, tokens ou ambiente completo. O estado registra PID, criação, executável e comando do próprio checkout; não é arquivo de histórico. A escrita é atômica e restrita ao usuário no Linux. Um lock do sistema operacional impede inícios concorrentes; arquivo de lock remanescente não significa lock ativo.

Antes de parar, conferir identidade completa. Linux usa `/proc` (btime e startticks, sem guardar boot UUID) e pidfd para sinalizar somente o processo validado, mesmo diante de PID reutilizado. Em kernel sem pidfd, a parada automática recusa o sinal em vez de aceitar a corrida. Windows consulta Win32_Process via PowerShell/CIM com comando fixo, e usa handle de processo para a parada. Não inspecionar processos em massa nem encerrar por nome/porta. Estado corrompido ou identidade divergente produz erro sem matar ou substituir processo.

`--docker` no Bash e `-Docker` no PowerShell usam somente Compose do checkout: `compose.linux.yaml` em Linux e `compose.yaml` no Windows, com project-directory explícito. Iniciar usa up/build em segundo plano; parar usa stop. Não usar down, prune ou remover volumes. Porta customizada não é oferecida nesse modo. Docker e Compose são dependências opcionais deste modo; os wrappers também precisam do Python.

Wrappers resolvem a própria pasta, inclusive caminhos com espaços, e não mudam ExecutionPolicy, firewall, Ollama ou configurações globais. Scripts PowerShell aceitam Windows PowerShell 5.1 e PowerShell 7; validação Linux com pwsh não equivale a homologação Windows real.

## Critérios de aceite

- **AC-SVC-01:** quatro entradas na raiz e um helper stdlib, sem pacotes extras; versão Python é verificada.
- **AC-SVC-02:** início idempotente, lock e porta ocupada tratados sem substituir processo alheio; prontidão exige sinal do próprio filho e health HTTP.
- **AC-SVC-03:** parada idempotente; PID, criação, executável, comando e checkout validados antes de sinalizar; PID reutilizado não recebe sinal.
- **AC-SVC-04:** arquivos operacionais ignorados, sem dados de benchmark/credenciais; estado inválido não causa exclusão ou parada insegura.
- **AC-SVC-05:** Compose restrito ao projeto/arquivo correto e volumes preservados; não afetar outros containers ou Ollama.
- **AC-SVC-06:** testes isolados cobrem identidade, estado ausente/corrompido, colisão de porta e argumentos Compose; Bash/PS passam verificações disponíveis, com limites de plataforma explícitos.

## Limites

Parar o servidor durante uma comparação interrompe o progresso ainda não salvo; concluir ou cancelar o teste antes da parada é a operação recomendada. No Windows, a parada por handle termina o processo; não promete um encerramento Python equivalente a Ctrl+C. Scripts não assumem controle de uma instância iniciada manualmente sem seu estado operacional. A raiz coordena a migração da instância atualmente ativa, sem intervenção dos workers.

## Resultados

Implementação congelada e QA independente APROVADO. Foram validados 119 métodos: suíte base de 118 em 24,423 s e os 19 de lifecycle finais em 1,132 s, incluindo a nova regressão PowerShell. Bash passou shellcheck, PowerShell passou parsing via pwsh no Linux e a raiz executou o ciclo real descrito abaixo. Segurança do helper e revisão final independente foram aprovadas separadamente. Windows real permanece pendente. A equipe de implementação não reiniciou serviços.

Fontes primárias de plataforma: [Win32_Process](https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-process) documenta CreationDate, ExecutablePath e CommandLine; caminhos indisponíveis por permissão fazem o controle recusar a operação. A consulta PowerShell fixa usa saída UTF-8 para caminhos Unicode.

## Propriedade dos recursos locais

Antes de alterar containers existentes, a listagem inclui também os parados e verifica somente os labels Compose de diretório/configuração contra o checkout e arquivo esperado. Nome de projeto coincidente não basta. Início/parada apontam explicitamente para o serviço benchmark. Porta ocupada por modo nativo ou origem desconhecida impede início Docker; health deve corresponder ao hostname do próprio container.

Arquivos operacionais recusam symlinks, reparse points, hardlinks e arquivos especiais antes de escrita. O descriptor aberto é comparado com a entrada local por identidade de arquivo; arquivo novo usa criação exclusiva. Isso não transforma um checkout controlado por terceiros em ambiente confiável.

O preflight Linux usa SO_REUSEADDR como o HTTPServer do app, permitindo reinício rápido quando a conexão anterior está em TIME_WAIT; um listener ainda ativo continua sendo recusado. A configuração não é aplicada indiscriminadamente no Windows. O caso foi verificado com sockets efêmeros de teste, sem tocar a porta da aplicação ativa.

Correção de resolução PowerShell: Get-Command pode retornar mais de uma aplicação com o mesmo nome; os wrappers selecionam um único resultado antes de invocar o candidato. A regressão executa ambos com uma fixture de Python inofensiva e dois resultados, cobrindo caminhos com espaços/Unicode sem iniciar ou parar o app real.

## Evidência operacional final

A raiz executou start/stop e idempotência com Bash e PowerShell 7 no Linux, nos modos nativo e Docker. Verificou recusa de porta ocupada/instância não gerenciada, propriedade dos containers do checkout e preservação dos volumes. Testou também a resolução dos wrappers desde outro diretório e em checkout sintético com espaços/Unicode, sem acessar o perfil de benchmark real nessa fixture.

Ao final, a aplicação permaneceu nativa em 127.0.0.1:8765, iniciada por start.sh; o container do projeto ficou parado. As duas comparações locais anteriores foram preservadas. Evidências detalhadas ficam somente em test-results/service-runtime.local.json e service-spaces.local.json, ignoradas pelo Git. Não foi executado Windows real com PowerShell 5.1 ou 7; testes Linux e revisão da sintaxe não equivalem a essa homologação.

Fechamento: **QA APROVADO**, **segurança APROVADA** e **revisão final independente APROVADA**. Os scripts de início/parada estão implementados e foram exercitados no Linux. Setup/instalação automática e homologação Windows real continuam pendentes; não foram acrescentados serviços de sistema, autostart ou alterações globais de política.
