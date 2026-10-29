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
    if (!select) return;
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
  let active = null;
  const hide = () => {
    if (!active) return;
    active.tooltip.hidden = true;
    active.button.setAttribute('aria-expanded', 'false');
    active.button.classList.remove('help-anchor');
    active.pinned = false;
    active = null;
  };
  for (const wrapper of document.querySelectorAll('.help')) {
    const button = wrapper.querySelector('.help-trigger');
    const tooltip = wrapper.querySelector('[role="tooltip"]');
    const item = {wrapper, button, tooltip, pinned: false};
    const show = (pin = false) => {
      if (active !== item) hide();
      active = item;
      item.pinned ||= pin;
      button.classList.add('help-anchor');
      tooltip.hidden = false;
      button.setAttribute('aria-expanded', 'true');
    };
    wrapper.addEventListener('pointerenter', () => show());
    // Keep hover content reachable; Escape, outside click or focus loss dismisses it.
    button.addEventListener('focus', () => show());
    button.addEventListener('blur', () => {if (active === item) hide();});
    button.addEventListener('click', () => {
      if (active === item && item.pinned) hide();
      else show(true);
    });
  }
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && !document.querySelector('dialog[open]') && active) {
      hide();
      event.preventDefault();
    }
  });
  document.addEventListener('pointerdown', event => {
    if (active && !active.wrapper.contains(event.target)) hide();
  });
});
