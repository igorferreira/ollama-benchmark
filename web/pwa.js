'use strict';
(() => {
  let installPrompt = null;
  const button = document.getElementById('install-app');
  const status = document.getElementById('install-status');
  window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault();
    installPrompt = event;
    button.hidden = false;
  });
  button.addEventListener('click', async () => {
    if (!installPrompt) return;
    const prompt = installPrompt;
    installPrompt = null;
    button.hidden = true;
    try {
      await prompt.prompt();
      const choice = await prompt.userChoice;
      status.textContent = choice.outcome === 'accepted' ? 'Instalação solicitada ao navegador.' : 'Instalação adiada. Você pode instalar pelo menu do navegador.';
    } catch (_error) {
      status.textContent = 'Use a opção de instalar aplicativo no menu do navegador.';
    }
  });
  window.addEventListener('appinstalled', () => {
    installPrompt = null;
    button.hidden = true;
    status.textContent = 'Aplicativo instalado. Mantenha o servidor local e o Ollama em execução para medir.';
  });
  if ('serviceWorker' in navigator && window.isSecureContext) {
    navigator.serviceWorker.register('/sw.js', {scope: '/', updateViaCache: 'none'}).catch(() => {
      status.textContent = 'A instalação não ficou disponível. O app continua funcionando nesta aba.';
    });
  }
})();
