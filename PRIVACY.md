# Privacidade e uso de dados

Este app mede o desempenho do Ollama com prompts fornecidos pela pessoa usuária. O funcionamento não exige nome, email, documento, senha, chave de API ou qualquer outro dado pessoal. Use exemplos sintéticos ou anonimizados nos testes. Não insira credenciais, dados pessoais ou dados sensíveis nos prompts.

## Fluxo e permanência dos dados

| Dado | Finalidade e destino | Permanência e controle |
| --- | --- | --- |
| Prompt e parâmetros | Navegador → backend Python → Ollama configurado; usados para gerar a resposta e medir o teste | Formulário e estado em memória; comparações terminais são salvas automaticamente em JSON no perfil local ~/.ollama_benchmark (SDD-007). Iniciar outra comparação substitui o estado ativo, mas não apaga arquivos históricos |
| Texto gerado, prévia ao vivo, métricas, modelo e mensagens de erro | Ollama → backend → navegador; apresentação e comparação dos resultados | Estado em memória do backend; a resposta preservada tem limite de 64 mil caracteres por execução. Outras abas da mesma instância acessam o mesmo estado. A prévia da tentativa mais recente pode permanecer após erro/cancelamento até a próxima tentativa/job ou encerramento; comparações terminais passam a ser gravadas automaticamente no histórico local, incluindo pedido/resposta e métricas; fragmentos ativos não são salvos |
| Exportação CSV/JSON | Download solicitado pela pessoa usuária | Arquivo em texto legível, sob controle do navegador/sistema operacional. Pode conter prompt, resposta e erros; o JSON inclui também o snapshot de prévia ao vivo, inclusive uma tentativa incompleta. O CSV não inclui texto da prévia. Não é apagado quando o app reinicia |
| Preferência de tema | Armazenamento local do navegador, chave `ollama-benchmark-theme` | Somente `light` ou `dark`. Persiste por origem até limpar os dados do site; não armazena prompt, credencial ou identificador de usuário |
| Token de proteção da página | Memória do backend e página entregue ao navegador; protege operações POST | Gerado por inicialização, sem armazenamento persistente implementado. Não é uma senha nem uma chave de API do Ollama |
| Resumo do ambiente do backend | SO/kernel/arquitetura, modelo de CPU/GPU, memória, agregado do sistema de arquivos do app e uptime, quando disponíveis; apresentação local em endpoint separado | Fatos estáticos em memória por instância e snapshot dinâmico limitado a dez segundos. Pausa durante benchmark. Não integra estado/exportações do teste, Cache Storage, localStorage ou gravação automática em disco |

O backend grava automaticamente comparações terminais em arquivos JSON no perfil local, incluindo prompts, respostas e métricas. Não usa banco de dados, analytics ou telemetria. As mensagens de acesso HTTP estão desabilitadas. O código não implementa logs intencionais de payloads; configurações do sistema, ferramentas de diagnóstico e serviços externos continuam fora desse controle.

A instalação PWA adiciona registro de service worker, manifesto e Cache Storage no navegador. O cache guarda somente a página offline, FAQ, script público de ajuda/tema, CSS, manifesto e ícones de uma lista explícita. Nunca guarda a página principal com token, APIs, prompts, respostas, prévias ao vivo ou exportações. A FAQ não consulta a API nem recebe dados de teste; links de referência externos só abrem por ação da pessoa usuária. Os recursos públicos persistem até limpar os dados do site.

## Limites da execução local

O navegador conversa com a API do app na mesma origem. O backend aceita somente os destinos locais previstos para o Ollama, incluindo o gateway do host no Docker. O servidor Ollama é outro processo, com configuração, modelos, eventuais integrações e política de retenção próprios. Um endpoint local não comprova que o modelo execute sem serviços externos. Confirme o uso de modelos efetivamente locais e a configuração do Ollama antes de tratar informações confidenciais.

A interface deve permanecer no loopback. Ela não possui autenticação de usuários nem isolamento entre abas ou pessoas com acesso à mesma instância. As proteções de origem e token não substituem controle de acesso do computador. Consulte [SECURITY.md](SECURITY.md).

## Critérios técnicos relacionados à LGPD

A revisão técnica utiliza como referências os princípios de finalidade, adequação, necessidade, transparência, segurança e prevenção do art. 6º e a proteção desde a concepção prevista no art. 46 da [Lei Geral de Proteção de Dados Pessoais — texto oficial](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm).

| Critério examinado | Medida presente e limite |
| --- | --- |
| Finalidade e necessidade | O teste funciona com conteúdo sintético; não há cadastro nem campo obrigatório de identificação pessoal. Texto livre ainda permite que uma pessoa insira dados sensíveis por engano |
| Transparência | Este documento descreve fluxos, armazenamento, exportações e fronteiras do Ollama. O app não escolhe uma base legal para o tratamento realizado por quem o utiliza |
| Minimização da retenção | Um estado ativo em memória e arquivos de comparações terminais no perfil local, sem exclusão automática. Downloads, dados do navegador, Ollama, arquivos de diagnóstico, backups e mecanismos do sistema operacional exigem gestão separada |
| Segurança e prevenção | Bind local, validação de Host/Origin, token em POST, limites de entrada, CSP, apresentação por `textContent` e neutralização de fórmulas CSV. São controles específicos, não uma garantia universal contra vazamento |
| Publicação responsável | Revisão do índice Git, scanner de segredos sem verificação remota e exclusão de relatórios/exportações locais antes da publicação do código |

Esta avaliação documenta medidas técnicas e limitações. Publicar o código não certifica conformidade integral com a LGPD, não define papéis jurídicos ou base legal de cada uso e não autoriza tratar dados pessoais de terceiros. A aplicabilidade e as obrigações dependem do contexto real de tratamento.

## Limpeza e compartilhamento

1. Prefira prompts inteiramente fictícios. Substituir nomes isolados não comprova anonimização de um conjunto de dados.
2. Exporte somente se precisar guardar a medição. Inspecione o conteúdo antes de compartilhar.
3. Para substituir o estado ativo do backend, inicie outra comparação; para encerrar a sessão operacional, pare o app. Essas ações não garantem apagamento seguro de memória física, swap, dumps ou cópias externas.
4. Apague exportações e cópias desnecessárias no sistema operacional e confira a retenção do Ollama separadamente.
5. Limpe os dados do site no navegador se quiser remover a preferência de tema e outros dados mantidos pelo próprio navegador.
6. Não anexe prompts privados, senhas, chaves ou exportações pessoais a issues, commits ou relatórios públicos.

Os arquivos `test-results/`, `TEST_RESULTS.md` e relatórios `*.local.*` são evidências privadas do ambiente de desenvolvimento, excluídas do Git. Regras de ignore e scanners ajudam a prevenir publicação acidental, mas cada novo arquivo precisa de revisão.

## Resumo dinâmico e fingerprint

A SDD-004 acrescenta um inventário mínimo do ambiente onde o processo Python executa. Combinar hardware/software pode criar fingerprint; esses campos não devem ser tratados como dados universalmente anônimos. A finalidade é contextualizar a medição local, não identificar pessoas ou monitorar todo o computador.

O coletor não consulta ou apresenta username, IP/MAC, serial, UUID, nomes de discos/volumes, caminhos de montagem, diretório pessoal, nomes de arquivos ou lista de pacotes. Retorna somente campos técnicos previstos, com limites e indisponibilidade explícita. Leituras e uso de APIs do sistema são locais, sem telemetria, comandos arbitrários ou inventário remoto.

Por solicitação explícita (SDD-006), a exceção é o hostname: nome técnico local obtido uma vez por instância por `socket.gethostname()`, sem DNS. Aparece somente na faixa de hardware e nos detalhes locais; pode identificar a máquina e merece cuidado ao compartilhar capturas. Em container é o nome do container/namespace, não do host físico. Não entra em logs, exportações, cache ou localStorage.

No Docker, o resumo pertence ao processo/container: SO pode vir da imagem e CPU/kernel podem ser compartilhados. Memória é apresentada no escopo comprovável; host inacessível ou dispositivo não exposto não vira hardware inventado. O alvo Ollama pode ser outro ambiente, e modelo de GPU não comprova uso pelo Ollama.

O endpoint `/api/system` é separado, com `no-store` e proteções locais. Inventário fica fora dos snapshots/exportações do benchmark e da allowlist PWA. Valores dinâmicos têm timestamp; durante teste ativo, usa-se o snapshot anterior marcado como pausado em vez de coletar novamente. O resumo permanece somente na memória do processo e no DOM da página; encerramento não é promessa de apagamento seguro de RAM/swap/dumps.

Fixtures, documentação e capturas públicas não devem conter inventário pessoal real. A implementação não habilita DE/WM/tema do desktop/fontes/shell/pacotes por conveniência: são informações dispensáveis ao objetivo mínimo desta entrega.

## Biblioteca de pedidos

A biblioteca contém apenas 18 exemplos genéricos públicos, incluídos no JavaScript local. Não consulta Ollama, não guarda escolhas e só preenche o textarea por ação explícita, com confirmação antes de substituir edição. Ao executar uma comparação, o pedido escolhido segue o fluxo normal de benchmark e exportação descrito acima.

## Histórico autorizado no perfil local

A SDD-007 autoriza armazenar pedidos, parâmetros, respostas, métricas e mensagens de comparações encerradas em `~/.ollama_benchmark`. Cada comparação gera um JSON versionado. Essa pasta pode conter informações confidenciais mesmo quando os exemplos do catálogo são públicos: a pessoa controla o conteúdo enviado aos modelos. Não há telemetria, sincronização remota ou exclusão automática pelo app. Backups do perfil podem copiar esses dados. A exclusão, quando desejada, é feita pela pessoa no sistema operacional, com o app parado; não se promete apagamento seguro.

Token da página, credenciais, hostname e inventário não são incluídos no histórico. Arquivos temporários restritos e substituição atômica reduzem falhas de gravação; no Linux o diretório usa 0700 e arquivos 0600. Não se afirma garantia equivalente de ACL no Windows. Falhas de armazenamento geram aviso genérico e preservam os resultados em memória. Arquivos corrompidos são ignorados com aviso.

No Docker, o perfil do usuário do container e um volume nomeado do projeto guardam o histórico, separados do perfil real do host. Recriar o container preserva o volume; excluir o volume elimina sua cópia. Limpar dados do navegador não apaga o histórico do backend. A API continua local/no-store e o service worker não armazena dados históricos.

Ao iniciar, a última comparação terminal válida pode ser recuperada sem inferência; formulário é restaurado apenas se ainda não editado. Na tabela unificada de Resultados, abrir Detalhes de outra comparação exige confirmação explícita e é recusado durante teste ativo. Interrupção abrupta antes do fim não gera checkpoint recuperável daquela execução; não existe retomada automática de geração.
