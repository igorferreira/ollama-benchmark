# ADR-004 — Docker opcional e dois arquivos de rede independentes

- **Data da baseline:** 28/10/2026.
- **Status:** decisão observada na implementação; registro retrospectivo.

## Contexto

O aplicativo deve funcionar apenas com Python no host, mas também recebeu uma opção Docker. O objeto do teste é o Ollama instalado no computador, não um Ollama novo dentro do projeto. No container, `127.0.0.1` normalmente identifica o próprio namespace do container. Um nome resolvido para o host não garante acesso ao serviço se o Ollama estiver vinculado somente ao loopback.

## Decisão

Empacotar somente o app na imagem. Manter dois arquivos Compose **independentes**:

- [compose.yaml](../../compose.yaml): app em `0.0.0.0` dentro do container, publicação `127.0.0.1:8765:8765` e Ollama em `host.docker.internal:11434`, com mapeamento `host-gateway`.
- [compose.linux.yaml](../../compose.linux.yaml): `network_mode: host`, app em `127.0.0.1:8765` e Ollama em `127.0.0.1:11434`, sem publicar portas.

Não mesclar os dois arquivos. Não passar GPU ao container do benchmark, criar serviço Ollama, baixar modelos ou reconfigurar o bind/firewall do host. Executar como usuário 65534:65534, com filesystem read-only, capabilities removidas e `no-new-privileges` no Compose.

## Alternativas e consequências

| Alternativa | Avaliação retrospectiva |
| --- | --- |
| Incluir Ollama no Compose | Mudaria o sistema medido, exigiria modelos, armazenamento e integração GPU fora do pedido |
| Um Compose único com alterações manuais | Menos arquivos, porém aumenta chance de configuração incompatível ou exposição acidental |
| Override com limpeza de campos herdados | Viável, mas exige atenção à mesclagem de `ports` e `network_mode` e a sintaxe/versionamento adicionais |
| Dois arquivos completos pequenos | Duplica poucas linhas de proteção, porém deixa as redes explícitas e evita combinação inválida |

O modo Linux host-network foi validado com Ollama real; o arquivo padrão teve sua configuração validada, sem teste real no Docker Desktop. A evidência local `TEST_RESULTS.md` (não versionada) distingue essas condições. No Desktop, se o gateway não alcançar o Ollama local, o fallback documentado é executar Python no host. Não há garantia de que `host.docker.internal` alcance qualquer serviço loopback.

## Evidências e revisão futura

A imagem usa `python:3.12-slim` sem digest fixado: primeiro build pode exigir internet e rebuild futuro pode mudar a revisão da imagem. Não há volume para reter resultados. A documentação de [rede do Docker Compose](https://github.com/docker/compose/blob/main/internal/relay/relay.go), consultada via Context7, confirma os mecanismos de resolução Desktop/host-gateway; a topologia efetiva está nos arquivos do projeto e na [arquitetura](../arquitetura.md).

Reavaliar somente se existir requisito de outro ambiente de rede, destino remoto ou reprodução integral do stack de inferência. Para comandos de operação, usar o [runbook](../operacao.md).
