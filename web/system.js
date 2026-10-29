'use strict';

document.addEventListener('DOMContentLoaded', () => {
  const $ = id => document.getElementById(id);
  const container = $('system-environment');
  if (!container) return;
  const details = $('system-details');
  const toggle = $('system-toggle');
  const refresh = $('system-refresh');
  let active = false;
  let loading = false;
  let pinned = false;
  let timer = null;
  let controller = null;
  let nextAllowedAt = 0;
  let intervalMs = 10000;
  let lastSnapshot = null;
  let closeTimer = null;

  const text = value => typeof value === 'string' && value.trim() ? value : 'Não informado';
  const knownNumber = value => typeof value === 'number' && Number.isFinite(value) && value >= 0;
  const integer = value => Number.isSafeInteger(value) && value >= 0 ? value.toLocaleString('pt-BR') : 'Não informado';
  const bytes = value => knownNumber(value) ? `${(value / 1073741824).toLocaleString('pt-BR', {maximumFractionDigits:1})} GiB` : 'Não informado';
  const put = (id, value) => {const node=$(id);if(node.textContent!==value)node.textContent=value;};
  const memoryPair = memory => `${bytes(memory.used_bytes)} / ${bytes(memory.total_bytes)}`;
  const shortCpu = value => text(value).replace(/\((R|TM)\)/gi, '').replace(/\s+with Radeon Graphics\s*$/i, '').replace(/\s+/g, ' ').trim();
  const shortGpu = value => value.replace(/^Advanced Micro Devices,\s*Inc\.\s*(\[AMD\/ATI\]\s*)?/i, '').replace(/^NVIDIA Corporation\s*/i, 'NVIDIA ').replace(/^Intel Corporation\s*/i, 'Intel ').trim();
  const scope = value => ({
    backend_process:'Processo Python desta instância',
    process_visible_shared_kernel:'CPUs visíveis ao processo; kernel compartilhado',
    process_visible_not_exclusive:'CPUs visíveis ao processo; sem exclusividade',
    process_visible:'Dispositivos visíveis ao processo',
    container_visible:'Dispositivos expostos ao container',
    cgroup_limit:'Limite de memória do processo/container',
    container_limit_unknown:'Limite de memória do container não informado',
    system_memory:'Memória do sistema visível ao processo',
    app_filesystem:'Sistema de arquivos onde o app executa',
    shared_kernel:'Kernel compartilhado com o host',
    kernel:'Kernel do sistema',
    unknown:'Não informado'
  }[value] || 'Não informado');
  const uptime = value => {
    if (!knownNumber(value)) return 'Não informado';
    const hours = Math.floor(value / 3600);
    const minutes = Math.floor((value % 3600) / 60);
    const days = Math.floor(hours / 24);
    return days ? `${days.toLocaleString('pt-BR')} d ${hours % 24} h` : `${hours} h ${minutes} min`;
  };
  const status = (message, warning = false) => {
    put('system-status', message);
    $('system-status').classList.toggle('system-warning', warning);
  };
  const show = (pin = false) => {
    clearTimeout(closeTimer);
    pinned ||= pin;
    details.hidden = false;
    container.classList.add('system-open');
    toggle.setAttribute('aria-expanded', 'true');
  };
  const hide = (restoreFocus = false) => {
    clearTimeout(closeTimer);
    // Return focus before hiding so its focus handler cannot reopen the panel.
    if (restoreFocus && details.contains(document.activeElement)) toggle.focus();
    details.hidden = true;
    container.classList.remove('system-open');
    pinned = false;
    toggle.setAttribute('aria-expanded', 'false');
  };
  $('system-summary').addEventListener('pointerenter', () => show());
  $('system-summary').addEventListener('focusin', () => show());
  const closeWhenOutside = () => {
    clearTimeout(closeTimer);
    closeTimer = setTimeout(() => {
      if (!pinned && !container.matches(':hover') && !container.contains(document.activeElement)) hide();
    }, 180);
  };
  container.addEventListener('pointerenter', () => clearTimeout(closeTimer));
  container.addEventListener('pointerleave', closeWhenOutside);
  container.addEventListener('focusout', closeWhenOutside);
  toggle.addEventListener('click', () => {
    if (pinned) hide();
    else show(true);
  });
  $('system-close').addEventListener('click', () => hide(true));
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && !document.querySelector('dialog[open]') && !details.hidden) {
      hide(true);
      event.preventDefault();
    }
  });
  document.addEventListener('pointerdown', event => {
    if (!details.hidden && !container.contains(event.target)) hide();
  });

  function render(snapshot) {
    const environment = snapshot.environment || {};
    const os = snapshot.os || {};
    const cpu = snapshot.cpu || {};
    const gpu = snapshot.gpu || {};
    const memory = snapshot.memory || {};
    const disk = snapshot.disk || {};
    const models = Array.isArray(gpu.models) ? gpu.models.filter(model => typeof model === 'string' && model.trim()) : [];
    const source = environment.kind === 'container' ? 'Ambiente do container' : environment.kind === 'native' ? 'Execução nativa' : 'Origem não informada';
    put('system-source', source);
    put('system-os', text(os.name));
    put('system-summary-hostname', text(snapshot.hostname));
    put('system-cpu', shortCpu(cpu.model));
    put('system-gpu', models.length ? `${shortGpu(models[0])}${models.length>1?` +${models.length-1}`:''}` : 'Não informado');
    const validMemory = knownNumber(memory.total_bytes) && memory.total_bytes > 0 && knownNumber(memory.used_bytes) && memory.used_bytes <= memory.total_bytes;
    put('system-ram', validMemory ? memoryPair(memory) : knownNumber(memory.total_bytes) ? `${bytes(memory.total_bytes)} · uso não informado` : 'Não informado');
    const bar = $('system-memory-bar');
    bar.hidden = !validMemory;
    if (validMemory) {
      bar.value = memory.used_bytes / memory.total_bytes * 100;
      bar.setAttribute('aria-valuetext', `${memoryPair(memory)} no escopo informado`);
    } else {
      bar.removeAttribute('aria-valuetext');
    }
    put('system-detail-title', environment.kind === 'container' ? 'Detalhes do ambiente do container' : 'Detalhes do ambiente da execução');
    const originNote = environment.kind === 'container' ? 'Dados do container; este painel não é um inventário do host. ' : 'Dados do ambiente onde o processo Python executa. ';
    put('system-note', originNote + (typeof environment.note === 'string' ? environment.note : ''));
    put('system-hostname-label', environment.kind === 'container' ? 'Hostname do container' : 'Hostname da máquina');
    put('system-hostname', text(snapshot.hostname));
    put('system-detail-os', text(os.name));
    put('system-architecture', text(os.architecture));
    put('system-kernel', text(os.kernel));
    put('system-detail-cpu', text(cpu.model));
    put('system-cores', `${integer(cpu.physical_cores)} / ${integer(cpu.logical_cpus)}`);
    put('system-cpu-scope', scope(cpu.scope));
    put('system-detail-gpu', models.length ? models.join(', ') : 'Não informado; a lista vazia não demonstra ausência física de GPU.');
    put('system-gpu-scope', scope(gpu.scope));
    put('system-gpu-note', `${typeof gpu.note==='string'?gpu.note+' ':''}Este painel não identifica a GPU usada pelo Ollama.`);
    put('system-detail-ram', memoryPair(memory));
    put('system-memory-available', bytes(memory.available_bytes));
    put('system-memory-scope', scope(memory.scope));
    put('system-disk', `${bytes(disk.used_bytes)} / ${bytes(disk.total_bytes)}`);
    put('system-uptime', uptime(snapshot.uptime_seconds));
    put('system-uptime-scope', scope(snapshot.uptime_scope));
    const collected = typeof snapshot.collected_at === 'string' ? new Date(snapshot.collected_at) : null;
    put('system-collected', collected && !Number.isNaN(collected.getTime()) ? `Coleta: ${collected.toLocaleString('pt-BR')} (horário do navegador)` : 'Coleta: não informada');
    if (active || snapshot.refresh?.paused) status('Atualização pausada durante o benchmark. O último snapshot permanece disponível.');
    else if (snapshot.refresh?.stale) status('Snapshot anterior; dados atuais não disponíveis.', true);
    else status(`Atualização limitada a cada ${intervalMs / 1000} s. Dados separados do alvo Ollama.`);
  }

  function schedule() {
    clearTimeout(timer);
    if (!active) timer = setTimeout(() => update(), Math.max(0, nextAllowedAt - Date.now()));
  }
  async function update(manual = false) {
    if (active || loading) return;
    const remaining = nextAllowedAt - Date.now();
    if (remaining > 0) {
      if (manual) status('Aguarde o intervalo mínimo de atualização; o último snapshot permanece disponível.');
      schedule();
      return;
    }
    loading = true;
    refresh.disabled = true;
    nextAllowedAt = Date.now() + intervalMs;
    const requestController = new AbortController();
    controller = requestController;
    try {
      const response = await fetch('/api/system', {cache:'no-store', signal:requestController.signal});
      if (!response.ok) throw new Error('Sistema indisponível');
      const snapshot = await response.json();
      if (!snapshot || typeof snapshot !== 'object' || Array.isArray(snapshot) || !snapshot.environment) throw new Error('Resposta de ambiente inválida');
      const minInterval = snapshot.refresh?.min_interval_s;
      if (typeof minInterval === 'number' && Number.isFinite(minInterval) && minInterval >= 10) intervalMs = minInterval * 1000;
      nextAllowedAt = Date.now() + intervalMs;
      lastSnapshot = snapshot;
      render(snapshot);
    } catch (error) {
      if (!(error.name === 'AbortError' && requestController.signal.aborted)) {
        status(lastSnapshot ? 'Não foi possível atualizar. Exibindo o último snapshot; os dados podem estar desatualizados.' : 'Ambiente indisponível. Nenhum dado local foi presumido.', true);
      }
    } finally {
      if (controller === requestController) controller = null;
      loading = false;
      refresh.disabled = active;
      schedule();
    }
  }
  window.addEventListener('benchmark-status', event => {
    const next = event.detail?.active === true;
    if (active === next) return;
    active = next;
    refresh.disabled = active || loading;
    clearTimeout(timer);
    if (active) {
      controller?.abort();
      status('Atualização pausada durante o benchmark. O último snapshot permanece disponível.');
    } else {
      status('Benchmark encerrado; atualização retomada respeitando o intervalo mínimo.');
      update();
    }
  });
  refresh.addEventListener('click', () => update(true));
  update();
});
