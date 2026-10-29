'use strict';
document.addEventListener('DOMContentLoaded', () => {
  const $ = id => document.getElementById(id);
  if (!$('history-refresh')) return;
  const token = document.querySelector('meta[name="benchmark-token"]').content;
  const statusNames = {idle:'Aguardando',running:'Executando',cancelling:'Cancelando',completed:'Concluída',cancelled:'Cancelada',failed:'Com falha'};
  const format = value => typeof value === 'number' && Number.isFinite(value) ? value.toLocaleString('pt-BR',{maximumFractionDigits:2,minimumFractionDigits:2}) : '—';
  let active=false,loading=false,listing=false,enabled=false,refreshPending=false;
  let current=null,items=[],selected=null,confirmedId=null,lastSavedId=null,lastSignature='';
  let storageWarning='',listWarning='',lastButton=null;
  const busy = () => active || loading || $('prompt').disabled;
  const currentId = () => current?.history?.saved ? current.history.id : null;
  function dateInfo(job){
    const started=new Date(job.started_at||'');
    if(!Number.isNaN(started.getTime()))return {text:started.toLocaleString('pt-BR'),day:started.toLocaleDateString('pt-BR'),time:started.toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit'}),note:'',stamp:started.getTime()};
    const saved=new Date(job.saved_at||'');
    if(!Number.isNaN(saved.getTime()))return {text:saved.toLocaleString('pt-BR'),day:saved.toLocaleDateString('pt-BR'),time:saved.toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit'}),note:'Data de salvamento; início indisponível',stamp:saved.getTime()};
    return {text:'Data não informada',day:'Data não informada',time:'',note:'',stamp:0};
  }
  function warning(){
    $('history-warning').textContent=storageWarning||listWarning;
    $('history-warning').hidden=!$('history-warning').textContent;
  }
  function controls(){
    const locked=busy();
    $('history-refresh').disabled=active||loading||listing;
    $('history-confirm').disabled=locked;
    $('history-apply').disabled=locked||!selected||!$('history-confirm').checked||confirmedId!==selected.id;
    $('history-cancel').disabled=loading;
    document.querySelectorAll('.comparison-details').forEach(button=>button.disabled=locked);
  }
  function cancelConfirmation(){
    $('history-confirmation').hidden=true;
    $('history-confirm').checked=false;
    confirmedId=null;selected=null;
    controls();
  }
  function showCurrentDetails(){
    $('individual-results').open=true;
    $('individual-results').scrollIntoView({block:'start',behavior:'instant'});
    $('individual-results').querySelector('summary').focus({preventScroll:true});
  }
  function choose(job,button){
    controls();
    if(busy())return;
    if(job.isCurrent){showCurrentDetails();return;}
    if(!enabled)return;
    selected=job;lastButton=button;confirmedId=null;
    $('history-confirm').checked=false;
    const date=dateInfo(job);
    $('history-target').textContent='Abrir detalhes de '+date.text+(date.note?' ('+date.note+')':'')+' · '+job.models.join(', ')+'.';
    $('history-confirmation').hidden=false;
    controls();
    $('history-confirmation').scrollIntoView({block:'nearest',behavior:'instant'});
    $('history-confirm').focus({preventScroll:true});
  }
  function cell(row,text,className){
    const node=document.createElement('td');node.textContent=text;if(className)node.className=className;row.append(node);return node;
  }
  function renderTable(){
    const displayedId=currentId();
    const jobs=items.filter(job=>job.id!==displayedId).map(job=>({...job,isCurrent:false}));
    if(current?.settings){jobs.push({id:displayedId,started_at:current.started_at,saved_at:current.history?.saved_at,status:current.status,models:current.settings.models,summary:current.summary||[],isCurrent:true});}
    jobs.sort((a,b)=>(a.isCurrent&&active?-1:b.isCurrent&&active?1:dateInfo(b).stamp-dateInfo(a).stamp));
    const signature=JSON.stringify(jobs);
    if(signature===lastSignature){controls();return;}
    lastSignature=signature;
    const fragment=document.createDocumentFragment();
    for(const job of jobs){
      const date=dateInfo(job);
      for(const model of job.models||[]){
        const summary=(job.summary||[]).find(item=>item.model===model)||{};
        const row=document.createElement('tr');
        if(job.isCurrent)row.className='comparison-current';
        cell(row,model);
        const dateCell=cell(row,date.day,'comparison-date');
        if(date.time){const time=document.createElement('small');time.className='comparison-time';time.textContent=date.time;dateCell.append(time);}
        if(date.note){const note=document.createElement('small');note.textContent=date.note;dateCell.append(note);}
        for(const value of [format(summary.tokens_per_s),format(summary.first_text_s),format(summary.wall_s),String(summary.repeated_count||0),format(summary.initial_wall_s??summary.initial?.wall_s)])cell(row,value);
        cell(row,(statusNames[job.status]||'Estado não informado')+(job.isCurrent?' · detalhes exibidos':''));
        const action=cell(row,'');const button=document.createElement('button');button.type='button';button.className='comparison-details';button.textContent='Detalhes';button.dataset.historyId=job.id||'current';button.setAttribute('aria-label','Detalhes de '+model+' em '+date.text);button.addEventListener('click',()=>choose(job,button));action.append(button);
        fragment.append(row);
      }
    }
    if(!fragment.childNodes.length){const row=document.createElement('tr');const message=cell(row,'Nenhuma comparação disponível. Inicie um teste para medir seus modelos.');message.colSpan=9;fragment.append(row);}
    $('summary').replaceChildren(fragment);controls();
  }
  async function refresh(){
    if(active||loading||listing){refreshPending=true;return;}
    listing=true;controls();
    try{
      const response=await fetch('/api/history',{cache:'no-store'});const data=await response.json();
      if(!response.ok)throw new Error('History unavailable');
      enabled=data.enabled===true;items=Array.isArray(data.items)?data.items:[];
      listWarning=data.warning||'';
      $('history-status').textContent=enabled?items.length+' comparação(ões) salva(s). Cada linha mantém a data e as métricas do seu teste.':'Histórico indisponível; os resultados atuais continuam na memória.';
      warning();renderTable();
    }catch(_error){listWarning='Não foi possível consultar comparações salvas. Os resultados em memória continuam disponíveis.';warning();}
    finally{listing=false;controls();if(refreshPending&&!active&&!loading){refreshPending=false;refresh();}}
  }
  $('history-refresh').addEventListener('click',refresh);
  $('history-cancel').addEventListener('click',()=>{cancelConfirmation();if(lastButton?.isConnected&&!lastButton.disabled)lastButton.focus();});
  $('history-confirm').addEventListener('change',()=>{confirmedId=$('history-confirm').checked?selected?.id:null;controls();});
  function invalidateConsent(){confirmedId=null;$('history-confirm').checked=false;controls();}
  $('benchmark-form').addEventListener('input',invalidateConsent);
  $('benchmark-form').addEventListener('change',invalidateConsent);
  $('models').addEventListener('change',invalidateConsent);
  $('history-apply').addEventListener('click',async()=>{
    controls();if(busy()||$('history-apply').disabled||!selected)return;
    const id=selected.id;loading=true;controls();window.dispatchEvent(new CustomEvent('history-loading',{detail:{active:true}}));
    try{
      const response=await fetch('/api/history/load',{method:'POST',cache:'no-store',headers:{'Content-Type':'application/json','X-Benchmark-Token':token},body:JSON.stringify({id})});
      const state=await response.json();
      if(!response.ok){$('history-status').textContent=response.status === 409?'Há um teste ativo. Aguarde seu término antes de carregar outra comparação.':'Não foi possível carregar esta comparação. Atualize os resultados salvos e tente novamente.';return;}
      window.dispatchEvent(new CustomEvent('history-loaded',{detail:{state}}));cancelConfirmation();showCurrentDetails();
      $('history-status').textContent='Detalhes e formulário restaurados; as demais comparações continuam na tabela. Nenhum teste foi iniciado.';
    }catch(_error){$('history-status').textContent='Conexão interrompida durante o carregamento. O formulário foi preservado; atualize para verificar o servidor.';}
    finally{loading=false;window.dispatchEvent(new CustomEvent('history-loading',{detail:{active:false}}));controls();if(refreshPending&&!active){refreshPending=false;refresh();}}
  });
  window.addEventListener('benchmark-status',event=>{active=Boolean(event.detail?.active);if(active)cancelConfirmation();controls();});
  window.addEventListener('comparison-state',event=>{
    current=event.detail?.state||null;
    storageWarning=current?.history?.warning||'';warning();renderTable();
    const history=current?.history;
    if(history?.saved&&history.id&&history.id!==lastSavedId){lastSavedId=history.id;if(!active&&!loading&&!listing)refresh();else refreshPending=true;}
  });
  window.addEventListener('history-model-warning',event=>{$('history-model-warning').textContent=event.detail?.message||'';$('history-model-warning').hidden=!$('history-model-warning').textContent;});
  new MutationObserver(controls).observe($('prompt'),{attributes:true,attributeFilter:['disabled']});
  refresh();
});
