# SDD-008 — Refinamento visual e de interação

Registro prospectivo de 29/10/2026, anterior ao código, com execução explícita das sugestões da auditoria Impeccable autorizada pela pessoa usuária. Preservar identidade azul, temas, botão da biblioteca alinhado ao h2, guia sob a marca e hostname dinâmico no resumo atual.

## Escopo e aceites

- **RF-26 / AC-UX-01:** resumo comparativo primeiro dentro de Resultados. Instrumentação ao vivo fica nessa seção, aberta durante teste; ao terminar recolher instrumentação/última prévia e tabela de execuções individuais. Priorizar Modelo/tokens por segundo/primeiro texto/total na visão comparativa, sem declarar vencedor de qualidade. Coluna de modelo fixa durante scroll horizontal e aviso textual no mobile; metodologia continua acessível.
- **AC-UX-02:** borda dos inputs no tema claro com contraste de pelo menos 3:1 contra branco. Preservar foco visível e estados desabilitados legíveis; esta melhoria não certifica WCAG integral.
- **AC-UX-03:** lista de modelos com altura limitada (~250–300 px), rolagem local e contador de selecionados sempre visível. Manter labels e seleção múltipla. Notas metodológicas repetidas podem ficar em details, sem wizard.
- **AC-UX-04:** ao selecionar um exemplo no dialog mobile, prévia aparece na área visível, com navegação Voltar à lista ou fluxo de rolagem coerente. Texto integral, filtros, consentimento, bloqueios e Escape/foco continuam funcionando.
- **AC-UX-05:** ajuda com área de toque próxima de 44 px e ícone discreto. Desktop ancorado ao gatilho com limite da viewport; mobile expansão próxima ao campo ou sheet coerente. Preservar teclado, Escape e prioridade de dialog aberto.
- **AC-UX-06:** polling de estado pausa em documento oculto, retorna imediatamente ao ficar visível, usa intervalo maior no idle e backoff simples de falha. Streaming ativo continua responsivo, sem duplicar timers ou requisições.
- **AC-UX-07:** página offline com ação Tentar novamente visualmente primária e comandos separados/legíveis. Não adicionar botão de copiar sem necessidade.

Integração SDD-007: histórico compacto em Resultados. Ao restaurar automaticamente a última comparação, restaurar também pedido/parâmetros/modelos se a pessoa ainda não editou o formulário, protegendo digitação e seleção enquanto chamadas assíncronas carregam. Carregamento explícito exige confirmação e backend recusa durante teste.

## Responsabilidades e limites

Mesmo worker frontend da SDD-007 edita layout/scripts/estilos para evitar conflito. Nenhuma dependência, framework ou fonte remota. Backend de inferência, contadores e metodologia permanecem iguais. Testes atualizam contratos relevantes em vez de duplicar checks superficiais. QA/revisão e browser final são obrigatórios; sem reiniciar serviços ou fazer commit/push pela equipe.

## Resultados

Implementação concluída e validada pela raiz nos dois temas e em seis combinações de viewport/tema. QA independente, segurança e revisão final independente aprovados; a [E12](../rastreabilidade.md#e12--validação-sdd-007008) registra runtime, navegador, testes e limites. O fechamento não atribui nova nota Impeccable nem certificação integral de acessibilidade.

## Complemento solicitado: legenda das métricas

**AC-UX-08:** mostrar junto de Resultados/histórico uma linha sempre visível “s = segundos · tokens/s = tokens de saída por segundo”. Complemento expansível Como ler as métricas explica primeiro texto/TTFT visível, primeiro conteúdo (pode incluir raciocínio), entrada/saída/cache (sem somar cache novamente), total medido versus total Ollama, carga, processamento do prompt e geração, usando os rótulos reais das tabelas. Link para FAQ aprofunda sem duplicar todo o guia. Tabelas podem apontar a legenda por aria-describedby. Funciona tanto durante teste quanto após recuperar histórico; não depende de hover. Siglas adicionais só são explicadas onde efetivamente aparecem.

## Decisão intermediária retirada: hierarquia após o primeiro checkpoint

**AC-UX-09 — RETIRADO pela solicitação AC-UX-10 abaixo:** histórico deve parecer parte de um único fluxo de Resultados, e não outra seção autônoma. Usar details compacto “Comparações salvas”, inicialmente fechado, dentro de Resultados; remover h2 independente e card com borda pesada/duplicada. Preservar IDs/controles/lista/confirmação. Contextualizar estado atual/salvo por rótulo/data, com exportações pertencendo à comparação exibida. Em erro, pode expandir para tornar aviso acessível. A posição no DOM sozinha não satisfaz o critério: o grupo precisa ser visualmente subordinado ao painel de resultados.

## Substituição explícita da solução de histórico

Após o checkpoint, a pessoa usuária substituiu a solução AC-UX-09: **não haverá accordion, seletor ou seção separada Comparações salvas**. O registro acima preserva a decisão intermediária retirada; o contrato atual é **AC-UX-10**:

Uma única tabela Resultados mostra comparações atuais e históricas, uma linha por comparação/modelo, com coluna Data/hora da execução explícita. Usar started_at original; saved_at só como fallback rotulado quando início não estiver disponível. Cada comparação conserva suas próprias medianas e parâmetros: não agregar jobs/datas. Depois de salvar, deduplicar a comparação corrente pelo ID. Abrir outra comparação não remove as demais linhas da tabela. Ação Detalhes por linha pode carregar o job com confirmação inline e bloqueio durante teste; exportação continua somente da comparação exibida nos detalhes, identificada por data/status.

GET /api/history passa a incluir summary numérico por modelo, sem prompts/respostas/initial row completa. Renderer combina esses itens com o estado atual sem misturar métricas. Não altera o armazenamento, inferência ou privacidade do histórico.

**AC-UX-11:** mover a orientação de instalação e os controles existentes install-app/install-status para details opcional Instalar como aplicativo no rodapé/ajuda. Preservar IDs, prompt nativo e aviso de servidor necessário; não competir com o início de comparação nem deixar a explicação solta no cabeçalho.
