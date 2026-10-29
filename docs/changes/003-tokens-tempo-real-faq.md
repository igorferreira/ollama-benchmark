# SDD-003 — Acompanhamento ao vivo, uso de tokens e FAQ

Data: 29/10/2026. Registro inicial: **especificado antes da implementação** desta mudança, sob demanda explícita. Implementação concluída; resultados conhecidos e limites estão registrados ao fim. A execução continua local com Python stdlib e frontend sem dependências. A publicação Git não integra esta tarefa.

## Problema e resultado esperado

Durante uma geração, a versão anterior só mostra qual execução está em andamento. A pessoa quer acompanhar a saída e entender tokens, entrada/saída, cache, tempo e cobrança. Confundir fragmentos de streaming com tokens produziria uma medição falsa.

O contrato padrão do Ollama entrega `response`/`thinking` em fragmentos e estatísticas completas no objeto final. Pesquisa complementar da entrega confirmou `logprobs=true` e `top_logprobs=0`: metadados opcionais trazem uma lista com uma entrada por token gerado. Em duas requisições reais de 16 tokens no Ollama 0.32.15, a soma dessas entradas coincidiu com o contador final. Essa evidência fundamenta uma opção instrumentada, não uma garantia para todos os modelos/versões.

O padrão continua sem instrumentação, mostrando texto parcial, caracteres, fragmentos, cronômetro e primeiros tempos, com tokens aguardando estatística final. A opção explícita **Contar tokens de saída ao vivo (instrumentado)**, desligada por padrão, conta somente entradas válidas de metadados por token e reconcilia com `eval_count` no final. Não haverá estimador `caracteres/4`, contagem de chunks como tokens, tokenizer adicional ou coleta global do Ollama.

Metadados opcionais: [tipos oficiais de GenerateRequest/Logprob](https://github.com/ollama/ollama/blob/main/api/types.go). Fontes verificadas pela pesquisa da entrega: [API oficial](https://github.com/ollama/ollama/blob/main/docs/api.md) e [uso da API](https://docs.ollama.com/api/usage). Campos/documentação upstream podem evoluir; o comportamento garantido deste app permanece explícito.

## Escopo e requisitos novos

- **RF-15:** acompanhar a execução do próprio app em tempo real por snapshots, com texto limitado, caracteres, fragmentos, tempo e TTFT conteúdo/texto; tokens finais indisponíveis devem aparecer como aguardando medição, nunca como contagem inferida. A opção instrumentada conta tokens de saída observados em metadados válidos, com rótulo provisório e conferência final.
- **RF-16:** apresentar entrada, saída, cache e soma entrada+saída quando os contadores finais forem válidos, além do acumulado somente das execuções concluídas. Cache é mostrado separadamente e não somado novamente ao total.
- **RF-17:** disponibilizar FAQ estática, ligada na interface e consultável offline depois de armazenada como recurso público, com glossário, cobrança, interpretação e limites.
- **RF-18:** fornecer ajuda curta acessível por mouse, foco de teclado e toque, sem depender apenas de atributo title ou liberar scripts inline no CSP.

Os IDs seguem os requisitos anteriores: RF-14 pertence à instalação PWA. As correspondências finais e testes serão registradas na SDD/matriz sem reutilizar IDs.

### Fora do escopo

Monitorar todos os clientes Ollama; interceptar outras aplicações; tokenizer local; calcular fatura real; configurar tarifas/provedores; exibir raciocínio integral; histórico persistente; mudar serviço/configuração Ollama; instalar dependências; commit ou push.

## Contrato aditivo de estado

`GET /api/state` e exportação JSON preservam campos atuais e acrescentam:

- `live`: null antes de uma execução ou objeto da tentativa mais recente.
- `usage`: resumo de contadores finais somente das linhas `completed`, com quantidade de concluídas e excluídas. Sem concluídas ou contador ausente/inválido, a quantidade correspondente é null, não uma fatura zero presumida.

Objeto `live`:

| Campo | Semântica |
| --- | --- |
| `model`, `run` | Identificam a tentativa |
| `status` | waiting, streaming, completed, failed ou cancelled |
| `elapsed_s` | Duração local; início de geração alinhado ao relógio usado para TTFT, sem confundir com tempo do job inteiro |
| `response` | Prévia de texto de resposta, até 64.000 caracteres, renderizada por textContent |
| `output_characters` | Caracteres de resposta recebidos, inclusive além do limite de prévia |
| `thinking_characters` | Quantidade de caracteres de raciocínio recebidos, sem guardar/exibir seu conteúdo integral |
| `fragments` | Quantidade de fragmentos não vazios de conteúdo/raciocínio, explicitamente não tokens |
| `first_content_s`, `first_text_s` | Tempos medidos pelo cliente, null antes de ocorrerem |
| `tokens`, `prompt_tokens`, `prompt_cached_tokens`, `total_tokens` | null até resultado final; valores válidos de saída, entrada, cache e entrada+saída |
| `output_tokens_observed` | Contador provisório de entradas válidas em logprobs quando instrumentação ligada; null se desligada/indisponível/incompleta |
| `token_observation_status` | Estado da instrumentação: disabled, pending, matched, mismatch ou unavailable conforme a fase |
| `count_status` | pending enquanto aguarda estatística, final quando recebida, unavailable em tentativa sem conclusão válida |

`total_tokens` só existe numericamente quando entrada e saída forem inteiros não negativos. Cache não é adicionado novamente. Os contadores são os informados pelo Ollama, não uma promessa de equivalência à classificação de cobrança de um provedor remoto. Modelos com raciocínio podem incluir raciocínio na contagem de saída; a UI deve explicar isso.

Configuração ganha `live_token_count:boolean`, default false. Se true, somente então enviar `logprobs:true` e `top_logprobs:0` ao Ollama. Isso pode aumentar payload/custo de processamento e alterar o benchmark; comparar apenas modos equivalentes. Não há retry automático se incompatível.

Contar entradas de uma lista válida não equivale a contar fragmentos; um fragmento pode conter vários metadados. Se faltar metadata em conteúdo gerado ou se vier malformada, a tentativa deixa de afirmar contagem observada completa e marca indisponível. Não guardar logprobs, probabilidades ou conteúdo dos tokens de metadata no estado/exportação. Ao final, eval_count sempre determina os tokens da linha; diferença fica explícita, não é escondida nem altera o contador autoritativo.

Resultado final `Row` ganha `total_tokens`, `output_tokens_observed` e `token_observation_status` aditivos. CSV ganha a coluna correspondente sem remover campos existentes. Cumulativo inclui somente linhas concluídas, nunca trata geração falha/cancelada como custo zero conhecido. O acumulado não deve somar total e cache para cobrar duas vezes.

## Fluxo e limites

1. Manager prepara `live` para a execução. Cliente publica progresso por callback opcional sem alterar a configuração de geração.
2. Publicações normais são limitadas a aproximadamente uma por 250 ms; primeira e última atualização relevante são garantidas. O polling da UI continua próximo de 700 ms.
3. Snapshot e alteração de estado usam lock; callback não chama snapshot sob o mesmo lock. Não fazer cópia de 64 mil caracteres em cada fragmento só para atualização visual.
4. Durante espera sem fragmentos, cronômetro deriva do relógio monotônico da tentativa; campos de texto/contadores permanecem no último snapshot conhecido.
5. Ao concluir, estatísticas finais substituem os placeholders, linha e acumulado são atualizados.
6. Cancelamento/erro preserva a prévia disponível somente no estado volátil `live`, marcada como incompleta, com tokens finais indisponíveis. Nova tentativa substitui a prévia; novo job/reinício descarta estado anterior.

A exportação JSON passa a incluir prévia `live` do snapshot; CSV continua contendo apenas linhas registradas e métricas, sem prévia. Política de privacidade e documentação devem declarar essa mudança. Não armazenar APIs, HTML com token, prompts, respostas, prévias ou exportações no service worker.

## FAQ e acessibilidade

Página `/faq.html` sem token ou leitura de API, com CSS/JS locais e link visível para voltar ao app. Conteúdo: token versus palavra/caractere/fragmento; entrada/saída/cache/raciocínio; contadores finais e parciais; janela de contexto/limite de saída; TTFT versus tempo total/tokens/s; custo por milhão com categorias sem sobreposição; uso local versus fatura de serviço remoto; desempenho aceitável dependente do caso; modelos, hardware, cache, concorrência e privacidade.

Qualquer meta numérica de latência deve ser uma heurística contextual e não um SLA universal. Não publicar tarifas como preços atuais. O app não cobra API local; custos de energia/hardware e serviços externos não são calculados.

Tooltips devem abrir por hover/focus e permitir toque/teclado, com descrição associada, fechamento por Escape e sem esconder rótulos dos campos. O tema e contraste devem ser mantidos. FAQ pode usar elementos details/summary para respostas extensas; tooltips são resumos, não o único acesso à informação.

PWA recebe bump da versão de cache ao modificar CSS/recursos públicos. Somente FAQ e seus assets estritamente públicos podem ser acrescentados à allowlist. Página principal e API continuam fora do cache.

## Ownership e critérios de aceite

Backend: `backend/ollama.py`, `manager.py`, `metrics.py`, `exports.py`, `validation.py` e novo `tests/test_live.py`. Frontend/FAQ: `web/`, adição da rota pública em `backend/http.py` e novo `tests/test_faq.py`. Lead mantém este registro, contratos e documentação. Nenhum agente deve sobrescrever arquivos do outro sem coordenação.

- **AC-RT-01:** stream simulado lento produz snapshot parcial antes de done; texto/fragmentos/caracteres não são rotulados tokens.
- **AC-RT-02:** tokens finais corretos e total apenas com entrada+saída válidas; zero é válido, ausente/inválido é null. Com opção instrumentada, dois fragmentos contendo cinco metadados válidos produzem cinco tokens observados, nunca dois; ausência/má formação fica indisponível e divergência final é reconciliada usando o contador final.
- **AC-RT-03:** acumulado exclui falhas/cancelamentos e declara limites; cache sem dupla contagem.
- **AC-RT-04:** espera, erro, cancelamento, timeout e próxima execução deixam estado consistente; nenhuma corrida nova na finalização.
- **AC-RT-05:** prévia limitada, raciocínio sem texto armazenado, atualizações limitadas e última prévia publicada.
- **AC-RT-06:** FAQ acessível pelo app e offline depois de cache público; nenhum token/API/dado de teste entra no Cache Storage.
- **AC-RT-07:** ajuda usável com mouse, teclado e toque, sem violar CSP ou temas; FAQ não exige Ollama ligado.
- **AC-RT-08:** suíte stdlib preservada/ampliada, QA independente e review posteriores; auditoria de segurança coordenada pelo responsável da entrega.

## BDD

**Dado** um stream com vários fragmentos antes do objeto final, **quando** consulto o estado durante a geração, **então** vejo progresso e a prévia enquanto os contadores finais indicam espera; se eu habilitar a instrumentação compatível, tokens de saída observados serão contados pelas entradas de metadata e conferidos no fim.

**Dado** uma tentativa cancelada após receber texto, **quando** ela encerra, **então** a prévia fica marcada como incompleta e não se converte em tokens ou custo conhecido.

**Dado** um resultado com entrada válida e saída válida, **quando** a estatística final chega, **então** a soma exibida é entrada+saída e o cache é exibido separadamente.

**Dado** a FAQ pública já armazenada pelo PWA, **quando** o servidor fica indisponível, **então** posso consultar a ajuda sem recuperar uma página principal antiga com token ou dados de benchmark.

## Resultados

- Implementados progresso `live`, acumulado `usage`, contadores finais normalizados e opção `live_token_count=false` por padrão. Observação usa apenas metadata válida; faltas/má formação invalidam a tentativa e divergência é explícita.
- Suíte final: **50 testes aprovados em 19,866 s** pelo agente QA independente, sem ResourceWarning. São 27 testes preservados, 18 novos para backend/live e 5 para FAQ/cache/HTTP.
- Review independente posterior ao QA: **APROVADO**, sem bloqueadores concretos e sem alterar arquivos.
- Integração real da entrega, no Docker Linux com `qwen3:4b`: duas gerações de 128 tokens com instrumentação. Houve snapshots antes de done com contador observado positivo e tokens/entrada finais ainda null; ambos resultados terminaram observados 128=eval_count 128 e matched.
- Cada resultado real informou entrada 34 e total 162; acumulado das duas concluídas: entrada 68, saída 256, total 324. Cache permaneceu null quando não informado. Esses números são evidência pontual de contagem, não desempenho garantido ou cobrança.
- No navegador, a raiz confirmou prévia antes da linha final, observação 79 durante a geração, hover/foco/Escape e toque com tooltip íntegro em 375×812 sem overflow; FAQ 16perguntas sem token/campo de prompt e layouts em três viewports/dois temas.
- Política PWA validada por testes e navegador: cache v2 com dez recursos públicos e nenhuma raiz/API/token/dado de benchmark. Com o container do app parado, a FAQ controlada pelo service worker carregou suas 16 perguntas em tema escuro usando somente três GETs públicos (faq/help.js/style.css), sem API ou token. Após restaurar o container, health e formulário do app voltaram. Auditoria final de segurança/snapshot é coordenada separadamente pela raiz.
- Documentação, contratos e matriz atualizados; nenhuma dependência, configuração Ollama, script Windows, commit ou push foi criado nesta tarefa. TASK-WIN-01 e TASK-PS-01 permanecem planejadas.

Os artefatos de ensaio são locais e ignorados; não foram copiados como dados pessoais, prompts, texto bruto ou tokens da página. Windows e Docker Desktop continuam sem execução real nesta entrega.
