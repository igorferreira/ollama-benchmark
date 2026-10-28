# Privacidade e uso de dados

Este app mede o desempenho do Ollama com prompts fornecidos pela pessoa usuária. O funcionamento não exige nome, email, documento, senha, chave de API ou qualquer outro dado pessoal. Use exemplos sintéticos ou anonimizados nos testes. Não insira credenciais, dados pessoais ou dados sensíveis nos prompts.

## Fluxo e permanência dos dados

| Dado | Finalidade e destino | Permanência e controle |
| --- | --- | --- |
| Prompt e parâmetros | Navegador → backend Python → Ollama configurado; usados para gerar a resposta e medir o teste | Formulário do navegador e estado em memória do processo. Iniciar outra comparação substitui o estado ativo do backend; encerrar o processo libera seu estado operacional |
| Texto gerado, métricas, modelo e mensagens de erro | Ollama → backend → navegador; apresentação e comparação dos resultados | Estado em memória do backend; a resposta preservada tem limite de 64 mil caracteres por execução. Outras abas da mesma instância acessam o mesmo estado |
| Exportação CSV/JSON | Download solicitado pela pessoa usuária | Arquivo em texto legível, sob controle do navegador/sistema operacional. Pode conter prompt, resposta e erros. Não é apagado quando o app reinicia |
| Preferência de tema | Armazenamento local do navegador, chave `ollama-benchmark-theme` | Somente `light` ou `dark`. Persiste por origem até limpar os dados do site; não armazena prompt, credencial ou identificador de usuário |
| Token de proteção da página | Memória do backend e página entregue ao navegador; protege operações POST | Gerado por inicialização, sem armazenamento persistente implementado. Não é uma senha nem uma chave de API do Ollama |

O backend não implementa histórico em banco, gravação automática de prompts/resultados, analytics ou telemetria. As mensagens de acesso HTTP estão desabilitadas. O código não implementa logs intencionais de payloads; configurações do sistema, ferramentas de diagnóstico e serviços externos continuam fora desse controle.

## Limites da execução local

O navegador conversa com a API do app na mesma origem. O backend aceita somente os destinos locais previstos para o Ollama, incluindo o gateway do host no Docker. O servidor Ollama é outro processo, com configuração, modelos, eventuais integrações e política de retenção próprios. Um endpoint local não comprova que o modelo execute sem serviços externos. Confirme o uso de modelos efetivamente locais e a configuração do Ollama antes de tratar informações confidenciais.

A interface deve permanecer no loopback. Ela não possui autenticação de usuários nem isolamento entre abas ou pessoas com acesso à mesma instância. As proteções de origem e token não substituem controle de acesso do computador. Consulte [SECURITY.md](SECURITY.md).

## Critérios técnicos relacionados à LGPD

A revisão técnica utiliza como referências os princípios de finalidade, adequação, necessidade, transparência, segurança e prevenção do art. 6º e a proteção desde a concepção prevista no art. 46 da [Lei Geral de Proteção de Dados Pessoais — texto oficial](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm).

| Critério examinado | Medida presente e limite |
| --- | --- |
| Finalidade e necessidade | O teste funciona com conteúdo sintético; não há cadastro nem campo obrigatório de identificação pessoal. Texto livre ainda permite que uma pessoa insira dados sensíveis por engano |
| Transparência | Este documento descreve fluxos, armazenamento, exportações e fronteiras do Ollama. O app não escolhe uma base legal para o tratamento realizado por quem o utiliza |
| Minimização da retenção | Um estado ativo em memória, sem histórico persistente implementado. Downloads, dados do navegador, Ollama, arquivos de diagnóstico, backups e mecanismos do sistema operacional exigem gestão separada |
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
