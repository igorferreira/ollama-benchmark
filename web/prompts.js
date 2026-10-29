// Public synthetic examples. No personal prompts or runtime data are stored here.
const PROMPT_EXAMPLES = [
  {
    "id": "code-simple-01",
    "type": "code",
    "complexity": "simple",
    "title": "Somar números em Python",
    "description": "Função curta com exemplos de entrada e saída.",
    "prompt": "Escreva uma função Python chamada somar_pares que receba uma lista de inteiros e devolva a soma dos números pares. Use apenas a biblioteca padrão. Mostre a função, explique a condição usada e apresente três exemplos: lista vazia, valores negativos e lista com números misturados. Não leia arquivos nem execute comandos."
  },
  {
    "id": "code-simple-02",
    "type": "code",
    "complexity": "simple",
    "title": "Entender um trecho JavaScript",
    "description": "Explicação passo a passo de um filtro.",
    "prompt": "Explique em português o resultado deste JavaScript: const valores = [2, 5, 8, 11]; const resultado = valores.filter(numero => numero > 5).map(numero => numero * 2); Explique filter e map, mostre o valor de resultado e uma versão equivalente usando for. Não execute o código; raciocine sobre ele."
  },
  {
    "id": "code-simple-03",
    "type": "code",
    "complexity": "simple",
    "title": "Consultar uma tabela SQL",
    "description": "SELECT com filtro e ordenação em dados fictícios.",
    "prompt": "Considere uma tabela fictícia livros com colunas id, titulo, ano e disponivel, sendo disponivel um booleano. Escreva uma consulta SQL para selecionar titulo e ano dos livros disponíveis publicados a partir de 2020, ordenando do mais recente ao mais antigo e depois por título. Explique cada cláusula e mostre um pequeno exemplo de resultado fictício. Não altere dados."
  },
  {
    "id": "code-intermediate-01",
    "type": "code",
    "complexity": "intermediate",
    "title": "Validar um carrinho",
    "description": "Regras de negócio e testes sem pacotes externos.",
    "prompt": "Implemente em Python uma função total_carrinho(itens, desconto_percentual). Cada item contém nome, quantidade inteira positiva e preco_unitario decimal não negativo. Use Decimal, evite mutação dos dados recebidos e rejeite desconto fora de 0 a 100. Explique como receber valores monetários sem erro de ponto flutuante. Inclua testes unittest para carrinho vazio, desconto de 100%, quantidade inválida e soma de dois produtos. Apresente o código como texto; não acesse rede ou arquivos."
  },
  {
    "id": "code-intermediate-02",
    "type": "code",
    "complexity": "intermediate",
    "title": "Revisar uma função assíncrona",
    "description": "Análise de falhas e proposta de correção.",
    "prompt": "Revise este JavaScript fictício: async function carregar(ids) { const dados = []; ids.forEach(async id => { dados.push(await buscar(id)); }); return dados; } A função buscar é assíncrona e pode rejeitar. Explique por que o resultado pode estar vazio. Proponha uma versão que preserve a ordem com Promise.all e outra sequencial. Compare concorrência, falhas e custo para uma API com limite de requisições. Não faça chamadas reais."
  },
  {
    "id": "code-intermediate-03",
    "type": "code",
    "complexity": "intermediate",
    "title": "Projetar uma API de tarefas",
    "description": "Contrato REST e casos de erro consistentes.",
    "prompt": "Proponha um contrato REST para uma lista pessoal de tarefas, com criação, consulta paginada, atualização e exclusão. Cada tarefa tem id, titulo, concluida e criada_em. Mostre métodos, rotas, exemplos JSON e códigos HTTP. Defina validação de título, comportamento para id inexistente e limites de paginação. Explique a diferença entre PUT e PATCH neste contrato. Não inclua credenciais ou serviços externos."
  },
  {
    "id": "code-advanced-01",
    "type": "code",
    "complexity": "advanced",
    "title": "Projetar processamento idempotente",
    "description": "Concorrência, falhas e recuperação em uma fila.",
    "prompt": "Desenhe um processador de pedidos fictícios com uma fila que entrega mensagens pelo menos uma vez. O mesmo pedido pode chegar duplicado ou fora de ordem. Defina estados, chave de idempotência, transações e estratégia de repetição com limite. Mostre pseudocódigo, esquema mínimo de dados e uma sequência de falha entre gravação e confirmação da mensagem. Discuta consistência, observabilidade e testes de concorrência. Declare premissas e não prometa exactly-once sem justificar."
  },
  {
    "id": "code-advanced-02",
    "type": "code",
    "complexity": "advanced",
    "title": "Refatorar uma importação CSV",
    "description": "Separação de responsabilidades e limites de memória.",
    "prompt": "Proponha uma implementação Python com biblioteca padrão para importar CSV de produtos em fluxo, sem carregar o arquivo inteiro. Separe leitura, validação e destino com funções pequenas e dependências injetadas. Considere cabeçalho inválido, linhas grandes, preço decimal, duplicatas e erro do destino no meio da importação. Mostre código central, testes unittest com StringIO e uma política explícita de recuperação. Não grave arquivos reais nem execute comandos."
  },
  {
    "id": "code-advanced-03",
    "type": "code",
    "complexity": "advanced",
    "title": "Planejar migração de um banco",
    "description": "Compatibilidade entre versões durante a entrega.",
    "prompt": "Uma aplicação fictícia possui a coluna nome_completo e precisa migrar para nome_exibicao sem interromper versões antigas. Elabore uma estratégia expandir/migrar/contrair, incluindo compatibilidade de leitura e escrita, preenchimento retroativo em lotes, validação e rollback. Mostre SQL ilustrativo e descreva como lidar com atualizações concorrentes. Compare os riscos de renomear diretamente. Declare o banco assumido e as limitações do exemplo; não execute nada."
  },
  {
    "id": "non-code-simple-01",
    "type": "non-code",
    "complexity": "simple",
    "title": "Explicar cache com uma analogia",
    "description": "Conceito técnico em linguagem cotidiana.",
    "prompt": "Explique o que é cache para alguém sem experiência em informática. Use uma analogia com uma biblioteca, um exemplo de uso no computador e uma limitação quando os dados ficam antigos. Termine com três frases resumindo a ideia. Evite jargões e não afirme que cache sempre melhora qualquer tarefa."
  },
  {
    "id": "non-code-simple-02",
    "type": "non-code",
    "complexity": "simple",
    "title": "Escrever um convite",
    "description": "Mensagem curta para um encontro fictício.",
    "prompt": "Escreva um convite informal para um clube de leitura fictício, no sábado às 15h, na Biblioteca do Bairro. O encontro é gratuito e cada pessoa pode levar um livro de que goste. Use um tom acolhedor e limite a mensagem a 100 palavras. Não invente endereço, contatos ou links."
  },
  {
    "id": "non-code-simple-03",
    "type": "non-code",
    "complexity": "simple",
    "title": "Organizar uma lista",
    "description": "Agrupar itens e justificar a escolha.",
    "prompt": "Organize estes itens em categorias úteis para uma compra doméstica: arroz, sabonete, tomate, detergente, banana, feijão, papel higiênico e cenoura. Mostre uma lista por categoria e explique em duas frases como essa organização ajuda na compra. Não adicione produtos nem estime preços."
  },
  {
    "id": "non-code-intermediate-01",
    "type": "non-code",
    "complexity": "intermediate",
    "title": "Comparar alternativas de estudo",
    "description": "Tabela de critérios e escolha contextual.",
    "prompt": "Compare três formas de estudar um tema novo: livro, curso gravado e projeto prático. Use uma tabela com autonomia, feedback, custo de tempo e profundidade. Depois proponha uma sequência de duas semanas para uma pessoa com 30 minutos diários. Declare as premissas, explique os compromissos de cada opção e não recomende marcas ou cursos pagos."
  },
  {
    "id": "non-code-intermediate-02",
    "type": "non-code",
    "complexity": "intermediate",
    "title": "Resumir uma decisão de equipe",
    "description": "Separar fatos, proposta e dúvidas.",
    "prompt": "Transforme estas anotações fictícias em uma ata objetiva: a equipe avaliou estender o atendimento; duas pessoas preferem testar primeiro; ainda não há orçamento aprovado; foi proposto um piloto de duas semanas; Marina vai levantar a demanda até sexta; a data de início não foi decidida. Separe fatos, proposta, ação com responsável e pendências. Não apresente proposta como decisão já aprovada e não invente datas."
  },
  {
    "id": "non-code-intermediate-03",
    "type": "non-code",
    "complexity": "intermediate",
    "title": "Planejar uma oficina",
    "description": "Agenda prática com objetivos verificáveis.",
    "prompt": "Planeje uma oficina de 90 minutos sobre organização pessoal para 12 participantes adultos. Disponibilize apenas papel e caneta. Apresente objetivo, agenda com tempos que somem 90 minutos, uma atividade em duplas e uma forma simples de avaliar aprendizado. Inclua adaptação para alguém que prefira não compartilhar informações pessoais. Não peça dados sensíveis."
  },
  {
    "id": "non-code-advanced-01",
    "type": "non-code",
    "complexity": "advanced",
    "title": "Avaliar uma proposta fictícia",
    "description": "Análise de premissas, riscos e sensibilidade.",
    "prompt": "Uma biblioteca comunitária fictícia recebe 200 visitas por semana e considera ampliar o horário em duas noites. O piloto duraria quatro semanas, com capacidade adicional de 40 visitas semanais e custo adicional total de 800 unidades monetárias. Analise benefícios possíveis, custo por visita adicional em cenários de 25%, 50% e 100% de ocupação dessa capacidade e limitações dos dados. Proponha métricas e critérios para continuar ou encerrar o piloto. Mostre cálculos, separe hipótese de fato e não trate a decisão como investimento garantido."
  },
  {
    "id": "non-code-advanced-02",
    "type": "non-code",
    "complexity": "advanced",
    "title": "Confrontar argumentos",
    "description": "Avaliação equilibrada sem falsa certeza.",
    "prompt": "Produza uma análise sobre a proposta fictícia de tornar reuniões semanais opcionais em uma equipe distribuída. Formule o argumento mais forte a favor e contra, explicite pressupostos e identifique quais evidências poderiam mudar a conclusão. Proponha um experimento de seis semanas com métricas, riscos de viés e critérios de interrupção. Considere fusos horários e acessibilidade. Termine com uma recomendação condicional, sem inventar pesquisas ou estatísticas."
  },
  {
    "id": "non-code-advanced-03",
    "type": "non-code",
    "complexity": "advanced",
    "title": "Criar um plano de contingência",
    "description": "Prioridades, responsáveis e comunicação.",
    "prompt": "Elabore um plano de contingência para um evento comunitário fictício de 80 pessoas em espaço aberto, sujeito a chuva. Há um salão coberto com capacidade para 50 pessoas e orçamento limitado, ainda sem valor definido. Defina premissas, alternativas, gatilhos de decisão, responsabilidades por função e mensagens ao público. Inclua uma matriz simples de riscos e uma lista de verificação para o dia anterior. Não invente normas legais nem prometa segurança; sinalize dados que precisam ser confirmados com a organização."
  }
];

(() => {
  'use strict';
  document.addEventListener('DOMContentLoaded', () => {
    const byId = id => document.getElementById(id);
    const dialog = byId('prompts-dialog');
    const textarea = byId('prompt');
    const opener = byId('prompts-open');
    if (!dialog || !textarea || !opener) return;
    const type = byId('prompts-type');
    const complexity = byId('prompts-complexity');
    const list = byId('prompts-list');
    const apply = byId('prompts-apply');
    const confirmation = byId('prompts-replace-confirm');
    const typeNames = {code: 'Código', 'non-code': 'Não código'};
    const complexityNames = {simple: 'Simples', intermediate: 'Intermediário', advanced: 'Avançado'};
    let selected = null;
    let active = false;
    let lastApplied = textarea.defaultValue;
    let lastSeenText = textarea.value;
    let consentText = null;
    let consentSelection = null;
    const blocked = () => active || textarea.disabled;
    const needsConfirmation = () => textarea.value.trim() !== '' &&
      textarea.value !== textarea.defaultValue && textarea.value !== lastApplied;
    function resetConsent() {
      confirmation.checked = false;
      consentText = null;
      consentSelection = null;
    }
    function controls() {
      if (lastSeenText !== textarea.value) {
        resetConsent();
        lastSeenText = textarea.value;
      }
      const busy = blocked();
      const edited = needsConfirmation();
      const consent = confirmation.checked && consentText === textarea.value && consentSelection === selected?.id;
      opener.disabled = busy;
      confirmation.disabled = busy;
      byId('prompts-replace-warning').hidden = !selected || !edited;
      apply.disabled = busy || !selected || (edited && !consent);
      byId('prompts-status').textContent = busy
        ? 'Teste em andamento. Aguarde para usar um pedido; você pode fechar a biblioteca.'
        : 'Somente o pedido será preenchido. Nenhum teste será iniciado.';
    }
    function preview() {
      byId('prompts-preview-title').textContent = selected ? selected.title : 'Prévia do pedido';
      byId('prompts-preview-description').textContent = selected ? selected.description : 'Selecione um exemplo para ler o texto completo.';
      byId('prompts-preview-text').textContent = selected ? selected.prompt : 'Nenhum pedido selecionado.';
      controls();
    }
    function renderList() {
      const visible = PROMPT_EXAMPLES.filter(item => (type.value === 'all' || item.type === type.value) &&
        (complexity.value === 'all' || item.complexity === complexity.value));
      if (selected && !visible.some(item => item.id === selected.id)) {
        selected = null;
        resetConsent();
      }
      list.replaceChildren();
      visible.forEach(item => {
        const label = document.createElement('label');
        label.className = 'prompts-choice';
        const radio = document.createElement('input');
        radio.type = 'radio';
        radio.name = 'prompt-example';
        radio.value = item.id;
        radio.checked = selected?.id === item.id;
        const copy = document.createElement('span');
        const title = document.createElement('strong');
        title.textContent = item.title;
        const description = document.createElement('span');
        description.className = 'prompts-choice-description';
        description.textContent = item.description;
        const meta = document.createElement('small');
        meta.textContent = typeNames[item.type] + ' · ' + complexityNames[item.complexity];
        copy.append(title, description, meta);
        label.append(radio, copy);
        radio.addEventListener('change', () => {
          selected = item;
          resetConsent();
          preview();
        });
        list.append(label);
      });
      byId('prompts-count').textContent = visible.length + (visible.length === 1 ? ' pedido disponível.' : ' pedidos disponíveis.');
      byId('prompts-empty').hidden = visible.length !== 0;
      preview();
    }
    opener.addEventListener('click', () => {
      controls();
      if (blocked()) return;
      resetConsent();
      renderList();
      dialog.showModal();
      type.focus();
    });
    for (const id of ['prompts-close', 'prompts-cancel']) {
      byId(id).addEventListener('click', () => dialog.close());
    }
    dialog.addEventListener('close', () => {
      resetConsent();
      if (!opener.disabled) opener.focus();
    });
    for (const filter of [type, complexity]) filter.addEventListener('change', renderList);
    textarea.addEventListener('input', controls);
    textarea.addEventListener('change', controls);
    confirmation.addEventListener('change', () => {
      consentText = confirmation.checked ? textarea.value : null;
      consentSelection = confirmation.checked ? selected?.id : null;
      controls();
    });
    apply.addEventListener('click', () => {
      // Revalidate at the action boundary, including edits made while the dialog was open.
      controls();
      const visible = selected && (type.value === 'all' || selected.type === type.value) &&
        (complexity.value === 'all' || selected.complexity === complexity.value);
      if (blocked() || apply.disabled || !visible) return;
      textarea.value = selected.prompt;
      lastApplied = selected.prompt;
      lastSeenText = textarea.value;
      resetConsent();
      textarea.dispatchEvent(new Event('input', {bubbles: true}));
      dialog.close();
    });
    window.addEventListener('benchmark-status', event => {
      active = Boolean(event.detail?.active);
      controls();
    });
    new MutationObserver(controls).observe(textarea, {attributes: true, attributeFilter: ['disabled']});
    controls();
    renderList();
  });
})();
