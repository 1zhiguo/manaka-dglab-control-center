(() => {
  'use strict';
  const section = document.querySelector('#original-work');
  if (!section) return;
  const panels = [...section.querySelectorAll('.original-info')];
  function show(value) {
    const language = ['zh', 'en', 'ja'].includes(value) ? value : 'zh';
    panels.forEach(panel => {
      panel.hidden = panel.id !== 'original-' + language;
      if (!panel.hidden) {
        const heading = section.querySelector('h2');
        heading.textContent = panel.dataset.originalTitle;
        heading.lang = panel.lang;
      }
    });
  }
  window.addEventListener('manaka:languagechange', event => show(event.detail?.language));
  show(document.documentElement.lang.split('-')[0]);
})();
