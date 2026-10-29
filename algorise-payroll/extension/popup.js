document.addEventListener('DOMContentLoaded', () => {
  const portalUrl = 'https://algorise-ai.com/algorise-payroll/';

  function showMessage(msg) {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.classList.remove('hidden');
    setTimeout(() => t.classList.add('hidden'), 3500);
  }

  function playGujaratiPrompt() {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance('હાજરી સફળતાપૂર્વક નોંધાઈ છે.');
      u.lang = 'gu-IN';
      u.rate = 0.95;
      window.speechSynthesis.speak(u);
    }
  }

  document.getElementById('btnQuickPunch').addEventListener('click', () => {
    playGujaratiPrompt();
    showMessage('Quick Punch Verified: SONU KAUSHAL (JMFU2)');
  });

  document.getElementById('btnOpenPortal').addEventListener('click', async () => {
    if (typeof chrome !== 'undefined' && chrome.tabs && chrome.tabs.create) {
      await chrome.tabs.create({ url: portalUrl + 'index.html' });
    } else {
      window.open(portalUrl + 'index.html', '_blank');
    }
  });

  document.getElementById('btnOpenMaster').addEventListener('click', async () => {
    if (typeof chrome !== 'undefined' && chrome.tabs && chrome.tabs.create) {
      await chrome.tabs.create({ url: portalUrl + 'employee-master.html' });
    } else {
      window.open(portalUrl + 'employee-master.html', '_blank');
    }
  });

  document.getElementById('btnOpenSentinel').addEventListener('click', async () => {
    if (typeof chrome !== 'undefined' && chrome.tabs && chrome.tabs.create) {
      await chrome.tabs.create({ url: portalUrl + 'cctv-sentinel.html' });
    } else {
      window.open(portalUrl + 'cctv-sentinel.html', '_blank');
    }
  });
});
