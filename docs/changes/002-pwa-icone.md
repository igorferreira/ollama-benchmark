# SDD-002 — Ícone e instalação local como PWA

Especificação registrada antes da implementação em 29/10/2026.

## Objetivo e critérios de aceite

- Adotar um ícone original: velocímetro com uma lhama estilizada, representando Ollama e medição de desempenho.
- Oferecer manifesto com identidade estável, modo standalone e ícones PNG de 192 e 512 pixels, além de variantes maskable e Apple touch.
- Mostrar a opção de instalar quando o navegador oferecer o evento de instalação. Incluir instruções alternativas para Chrome/Edge; não prometer suporte universal.
- Registrar um service worker local sem bibliotecas, CDN ou dependências Python adicionais.
- Manter frontend em `web/` e transporte HTTP em `backend/http.py`, com mapa explícito de arquivos e MIME correto para PNG, SVG, manifesto e service worker.
- Não armazenar no Cache Storage a página principal com token, APIs, exportações, prompts, respostas ou POSTs. Armazenar somente uma lista explícita de recursos públicos e uma página offline sem dados de teste.
- Quando o servidor estiver parado, abrir uma explicação offline; benchmarks continuam exigindo o app Python e o Ollama em execução. A instalação não cria serviço de sistema.
- Preservar temas e proteções HTTP, testar rotas/ícones e verificar registro, manifesto e cache no navegador.

## Limites e privacidade

A PWA funciona no contexto seguro de loopback. Origem e porta identificam a instalação: manter o mesmo endereço ao usar o app. O cache estático persiste no navegador até remoção dos dados do site; não contém dados de benchmark nem o token de proteção da página.

Windows e instalação gráfica nativa não serão declarados validados sem execução efetiva. O ícone será distribuído localmente, sem rastreamento ou carregamento externo.

Referências consultadas via Context7: [instalação PWA](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable) e [estratégias de cache](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Caching).

## Evidência de implementação

27 testes aprovados no host e no gate QA independente. Browser de teste confirmou registro/controle do worker, cache de oito assets sem dados de API, fallback offline com servidor parado e recuperação após reiniciar. Ícones PNG têm dimensões corretas e variante maskable opaca. A instalação gráfica no lançador do sistema e Windows não foram executados. Ver matriz de rastreabilidade.
