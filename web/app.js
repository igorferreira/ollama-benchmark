'use strict';

document.addEventListener('DOMContentLoaded', () => {
const $ = id => document.getElementById(id);
const token = document.querySelector('meta[name="benchmark-token"]').content;
let lastState = '';
let active = false;
function setBenchmarkActivity(value){
  if(active===value)return;
  active=value;
  window.dispatchEvent(new CustomEvent('benchmark-status',{detail:{active}}));
}
const statuses = {idle:'Nenhum teste iniciado',running:'Executando',cancelling:'Cancelando; aguardando encerrar a requisição atual',completed:'Teste concluído',cancelled:'Teste cancelado',failed:'Teste com falha'};
const format = value => typeof value === 'number' ? value.toLocaleString('pt-BR',{maximumFractionDigits:2,minimumFractionDigits:2}) : '—';
function error(message){$('error').hidden=!message;$('error').textContent=message||'';}
async function api(path, body){
  const response = await fetch(path, body === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json','X-Benchmark-Token':token},body:JSON.stringify(body)});
  const data = await response.json();
  if(!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
  return data;
}
function cell(row, text){const td=document.createElement('td');td.textContent=text;row.append(td);}
function placeholder(target,columns,text){const row=document.createElement('tr');const td=document.createElement('td');td.colSpan=columns;td.textContent=text;row.append(td);$(target).replaceChildren(row);}
async function models(){
  $('refresh').disabled=true;
  try{
    const data=await api('/api/models');
    const selected=new Set([...document.querySelectorAll('[name=model]:checked')].map(n=>n.value));
    const loaded=new Set(data.loaded.map(m=>m.name));
    const fragment=document.createDocumentFragment();
    for(const model of data.models){
      const label=document.createElement('label');label.className='model';
      const input=document.createElement('input');input.type='checkbox';input.name='model';input.value=model.name;input.checked=selected.has(model.name);input.disabled=active;
      const span=document.createElement('span');span.textContent=model.name;
      const detail=document.createElement('small');detail.textContent=`${(model.size/1e9).toFixed(2)} GB · ${model.details?.quantization_level||'quantização não informada'}${loaded.has(model.name)?' · carregado':''}`;
      span.append(detail);label.append(input,span);fragment.append(label);
    }
    $('models').replaceChildren(fragment);
    $('connection').textContent=`Conectado a ${data.ollama_url}. ${data.models.length} modelo(s) instalado(s).${data.models.length?' Selecione os modelos para comparar.':' Instale um modelo no Ollama para começar.'}`;
    error(null);
  }catch(exc){$('connection').textContent='Ollama indisponível.';error(exc.message);}
  finally{$('refresh').disabled=active;}
}
function setText(id, text){const node=$(id);if(node.textContent!==text)node.textContent=text;}
const count = value => Number.isSafeInteger(value) && value >= 0 ? value.toLocaleString('pt-BR') : 'Não informado';
function renderLive(live){
  $('live-panel').hidden=!live;
  if(!live)return;
  const states={waiting:'Aguardando geração',streaming:'Recebendo conteúdo',completed:'Geração concluída',failed:'Geração com falha; prévia incompleta',cancelled:'Geração cancelada; prévia incompleta'};
  setText('live-title',['completed','failed','cancelled'].includes(live.status)?'Última execução':'Execução ao vivo');
  setText('live-status',`${live.model} · execução ${live.run} · ${states[live.status]||live.status}.`);
  setText('live-elapsed',format(live.elapsed_s)+' s');
  setText('live-first-content',live.first_content_s==null?'Aguardando':format(live.first_content_s)+' s');
  setText('live-first-text',live.first_text_s==null?'Aguardando':format(live.first_text_s)+' s');
  setText('live-characters',count(live.output_characters));
  setText('live-thinking',count(live.thinking_characters));
  setText('live-fragments',count(live.fragments));
  const pending=live.count_status==='pending';
  setText('live-count-status',pending?'Entrada, saída final, cache e total: aguardando medição final.':live.count_status==='final'?'Contadores finais informados pelo Ollama. Campos ausentes aparecem como não informados.':'Contagem final indisponível para esta tentativa; a prévia não permite calcular tokens exatos.');
  for(const [id,key] of [['input','prompt_tokens'],['output','tokens'],['cache','prompt_cached_tokens'],['total','total_tokens']])setText('live-'+id,pending?'Aguardando':count(live[key]));
  const observationStates={disabled:'Contagem instrumentada desativada.',pending:'Provisório; aguardando conferência com a estatística final.',unavailable:'Metadados por token indisponíveis ou inválidos; nenhuma estimativa foi calculada.',matched:'Contagem observada confere com a estatística final.',mismatch:'Contagem observada diverge da estatística final; use o contador final de saída.'};
  const observation=live.token_observation_status||'disabled';
  setText('live-observed',`${observation==='disabled'?'':`Tokens de saída observados (instrumentado): ${count(live.output_tokens_observed)}. `}${observationStates[observation]||observation}`);
  setText('live-response',live.response || (live.thinking_characters?'O modelo está raciocinando; o conteúdo interno não é exibido.':'Aguardando texto…'));
}
function renderUsage(usage){
  const completed=usage?.completed_runs||0;
  const excluded=usage?.excluded_runs||0;
  setText('usage-status',completed?`${completed} execução(ões) concluída(s). ${excluded} tentativa(s) falha(s)/cancelada(s) excluída(s).`:`Ainda não há execuções concluídas. ${excluded} tentativa(s) falha(s)/cancelada(s) excluída(s).`);
  for(const [id,key] of [['input','prompt_tokens'],['output','tokens'],['cache','prompt_cached_tokens'],['total','total_tokens']])setText('usage-'+id,count(usage?.[key]));
}
function render(state){
  setBenchmarkActivity(['running','cancelling'].includes(state.status));
  $('start').disabled=active;$('cancel').disabled=!active || state.status==='cancelling';$('refresh').disabled=active;
  document.querySelectorAll('#benchmark-form input,#benchmark-form textarea,[name=model]').forEach(n=>n.disabled=active);
  const total=state.settings?state.settings.models.length*state.settings.repetitions:0;
  $('progress').textContent=`${statuses[state.status]||state.status}. ${state.rows.length}/${total} execuções.${state.current?` ${state.current.model}, execução ${state.current.run}.`:''}`;
  $('progress-bar').max=total||1;$('progress-bar').value=state.rows.length;
  if(state.error)error(state.error);
  renderLive(state.live);
  renderUsage(state.usage);
  const signature=JSON.stringify([state.rows,state.summary]);
  if(signature===lastState)return;
  lastState=signature;
  const rows=document.createDocumentFragment();
  const responses=document.createDocumentFragment();
  for(const item of state.rows){
    const row=document.createElement('tr');
    for(const value of [`${item.model} / ${item.run}${item.run===1?' (primeira)':''}`,item.status==='completed'?'Concluída':item.status==='cancelled'?'Cancelada':'Falha',item.loaded_before===undefined?'—':item.loaded_before?'Sim':'Não',count(item.prompt_tokens),count(item.prompt_cached_tokens),count(item.tokens),count(item.total_tokens),count(item.output_tokens_observed),({disabled:'Desativada',pending:'Provisória',unavailable:'Indisponível',matched:'Confere',mismatch:'Diverge; use saída final'}[item.token_observation_status]||'Desativada'),...['tokens_per_s','first_content_s','first_text_s','wall_s','total_s','load_s','prompt_s','generation_s'].map(k=>format(item[k]))])cell(row,value);
    rows.append(row);
    const label=document.createElement('h3');label.textContent=`${item.model} · execução ${item.run}`;
    const text=document.createElement('pre');text.textContent=item.error||item.response||'Sem texto gerado.';responses.append(label,text);
  }
  if(state.rows.length)$('rows').replaceChildren(rows);else placeholder('rows',17,'Sem execuções.');
  $('responses').replaceChildren(responses);
  const summary=document.createDocumentFragment();
  for(const item of state.summary){const row=document.createElement('tr');for(const value of [item.model,String(item.repeated_count),format(item.tokens_per_s),format(item.first_text_s),format(item.wall_s),format(item.initial?.wall_s)])cell(row,value);summary.append(row);}
  if(state.summary.length)$('summary').replaceChildren(summary);else placeholder('summary',6,'Os resultados aparecerão aqui.');
}
async function poll(){try{render(await api('/api/state'));}catch(exc){error('Conexão com o app interrompida: '+exc.message);}finally{setTimeout(poll,700);}}
$('refresh').addEventListener('click',models);
$('benchmark-form').addEventListener('submit',async event=>{
  event.preventDefault();error(null);
  const selected=[...document.querySelectorAll('[name=model]:checked')].map(n=>n.value);
  if(!selected.length){error('Selecione pelo menos um modelo.');return;}
  const settings={models:selected,prompt:$('prompt').value,think:$('think').checked,live_token_count:$('live_token_count').checked};
  for(const key of ['num_predict','num_ctx','repetitions','timeout'])settings[key]=Number($(key).value);
  $('start').disabled=true;
  setBenchmarkActivity(true);
  try{await api('/api/start',settings);render(await api('/api/state'));}catch(exc){setBenchmarkActivity(false);error(exc.message);$('start').disabled=false;}
});
$('cancel').addEventListener('click',async()=>{try{await api('/api/cancel',{});render(await api('/api/state'));}catch(exc){error(exc.message);}});
models();poll();

});
