# Segurança e privacidade

Este aplicativo foi projetado para uso pessoal local. Execute a interface em `127.0.0.1`; no Docker, use os arquivos Compose fornecidos, que limitam o acesso pelo host ao loopback.

## Credenciais

O app não exige chave de API, conta GitHub ou credencial para conversar com o Ollama local. O token incluído na página é gerado em memória a cada inicialização para proteger operações da interface. Ele não é uma credencial permanente e não deve ser copiado para exemplos ou arquivos versionados.

Arquivos `.env`, certificados, chaves privadas, configurações locais e relatórios pessoais estão excluídos do Git. Essa exclusão não substitui a inspeção do conteúdo antes de cada publicação.

## Dados dos testes

Prompts, textos gerados e parâmetros ficam na memória do servidor até encerrar o processo ou iniciar uma nova comparação. Os resultados são compartilhados pelas abas que acessam a mesma instância. Não há autenticação de usuários, isolamento entre usuários ou banco de dados.

Exportações CSV/JSON podem conter informações sensíveis fornecidas pelo usuário. Inspecione-as antes de compartilhar. A pasta `test-results/` e os relatórios locais de validação não fazem parte da distribuição pública.

O código do app não envia os resultados a serviços de telemetria. Ele chama o endereço local configurado para o Ollama. O comportamento do servidor Ollama e de seus modelos é externo ao app; prefira modelos instalados e execução local quando o prompt exigir privacidade.

## Privacidade e dados pessoais

Use prompts sintéticos ou anonimizados e não insira senhas, chaves, dados pessoais ou sensíveis. O app aceita texto livre e não possui um filtro que impeça toda inclusão acidental desse conteúdo. Iniciar outra comparação ou encerrar o processo substitui/libera o estado operacional do backend, sem remover exportações, dados do navegador ou cópias mantidas pelo Ollama/sistema operacional.

O mapa de dados, retenção, controles e limites da revisão técnica relacionada à LGPD está em [PRIVACY.md](PRIVACY.md). A avaliação técnica não representa certificação jurídica de conformidade nem define a base legal dos usos do app.

## Limites de proteção

A interface valida `Host`, verifica `Origin` quando presente, bloqueia requisições marcadas como entre sites e exige um token nas operações POST. Essas medidas não transformam o app em um serviço multiusuário nem protegem contra processos maliciosos que já executam no computador.

O endpoint do Ollama é configurado no processo, com nomes de host permitidos restritos. Não exponha o Ollama ou a interface à internet. A opção `APP_BIND=0.0.0.0` serve à rede interna do container; não deve ser usada para disponibilizar a execução Python na rede local.

## Comunicação de problemas

Não publique credenciais, prompts privados ou exportações pessoais em issues. Ao informar um problema, use um exemplo mínimo fictício e remova tokens, caminhos pessoais e identificadores da máquina. Se o repositório oferecer comunicação privada de vulnerabilidades, prefira esse canal para falhas sensíveis.
