'use strict';
(() => {
  const root = document.documentElement;
  const storageKey = 'ollama-benchmark-theme';
  const systemTheme = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;
  let preference = null;
  try {
    const saved = localStorage.getItem(storageKey);
    if (saved === 'dark' || saved === 'light') preference = saved;
  } catch (_error) {
    // The current tab remains usable when the browser blocks local storage.
  }
  const currentTheme = () => preference || (systemTheme?.matches ? 'dark' : 'light');
  root.dataset.theme = currentTheme();
  document.addEventListener('DOMContentLoaded', () => {
    const select = document.getElementById('theme-select');
    select.value = currentTheme();
    select.addEventListener('change', () => {
      preference = select.value === 'dark' ? 'dark' : 'light';
      root.dataset.theme = preference;
      try {
        localStorage.setItem(storageKey, preference);
      } catch (_error) {
        // A blocked storage API must not prevent switching the visible theme.
      }
    });
    systemTheme?.addEventListener('change', () => {
      if (preference === null) {
        root.dataset.theme = currentTheme();
        select.value = currentTheme();
      }
    });
  });
})();

document.addEventListener('DOMContentLoaded', () => {
const $ = id => document.getElementById(id);
const token = document.querySelector('meta[name="benchmark-token"]').content;
let lastState = '';
let active = false;
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
function render(state){
  active=['running','cancelling'].includes(state.status);
  $('start').disabled=active;$('cancel').disabled=!active || state.status==='cancelling';$('refresh').disabled=active;
  document.querySelectorAll('#benchmark-form input,#benchmark-form textarea,[name=model]').forEach(n=>n.disabled=active);
  const total=state.settings?state.settings.models.length*state.settings.repetitions:0;
  $('progress').textContent=`${statuses[state.status]||state.status}. ${state.rows.length}/${total} execuções.${state.current?` ${state.current.model}, execução ${state.current.run}.`:''}`;
  $('progress-bar').max=total||1;$('progress-bar').value=state.rows.length;
  if(state.error)error(state.error);
  const signature=JSON.stringify([state.rows,state.summary]);
  if(signature===lastState)return;
  lastState=signature;
  const rows=document.createDocumentFragment();
  const responses=document.createDocumentFragment();
  for(const item of state.rows){
    const row=document.createElement('tr');
    for(const value of [`${item.model} / ${item.run}${item.run===1?' (primeira)':''}`,item.status==='completed'?'Concluída':item.status==='cancelled'?'Cancelada':'Falha',item.loaded_before===undefined?'—':item.loaded_before?'Sim':'Não',item.tokens??'—',...['tokens_per_s','first_content_s','first_text_s','wall_s','total_s','load_s','prompt_s','generation_s'].map(k=>format(item[k]))])cell(row,value);
    rows.append(row);
    const label=document.createElement('h3');label.textContent=`${item.model} · execução ${item.run}`;
    const text=document.createElement('pre');text.textContent=item.error||item.response||'Sem texto gerado.';responses.append(label,text);
  }
  if(state.rows.length)$('rows').replaceChildren(rows);else placeholder('rows',12,'Sem execuções.');
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
  const settings={models:selected,prompt:$('prompt').value,think:$('think').checked};
  for(const key of ['num_predict','num_ctx','repetitions','timeout'])settings[key]=Number($(key).value);
  $('start').disabled=true;
  try{await api('/api/start',settings);render(await api('/api/state'));}catch(exc){error(exc.message);$('start').disabled=false;}
});
$('cancel').addEventListener('click',async()=>{try{await api('/api/cancel',{});render(await api('/api/state'));}catch(exc){error(exc.message);}});
models();poll();

});
