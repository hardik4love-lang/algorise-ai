/**
 * Client brand hydration.
 *
 * Replaces {{MARKER}} tokens with the signed-in merchant's contact
 * details from /api/v1/client/{id}/brand. When unauthenticated or missing,
 * renders clean neutral placeholders rather than raw {{...}} tokens or another
 * merchant's number.
 */
// Merchant brand hydration.
  const BRAND_ATTRS = {
    WA_LINK: 'wa_link',
    BRAND_PHONE: 'whatsapp_display',
    BRAND_DPHONE: 'whatsapp_display',
    BRAND_PHONE2: 'second_number',
    BRAND_DIGITS: 'whatsapp_digits',
  };

  let _cachedBrandSubs = {
    '{{WA_LINK}}': '#',
    '{{BRAND_PHONE}}': '(Configured on Merchant Sign-In)',
    '{{BRAND_DPHONE}}': '(Configured on Merchant Sign-In)',
    '{{BRAND_PHONE2}}': '(Secondary line optional)',
    '{{BRAND_DIGITS}}': '',
    '{{data-brand-phone}}': '(Configured on Merchant Sign-In)',
    '{{data-brand-phone2}}': '(Secondary line optional)',
  };

  function replaceBrandTokens(str) {
    if (typeof str !== 'string' || !str.includes('{{')) return str;
    let s = str;
    Object.entries(_cachedBrandSubs).forEach(([k, v]) => { s = s.split(k).join(v); });
    return s;
  }

  function applyBrandToRoot(root) {
    if (!root || typeof document === 'undefined') return;
    if (root.querySelectorAll) {
      root.querySelectorAll('a[href*="{{"]').forEach((a) => {
        const cur = a.getAttribute('href') || '';
        const next = replaceBrandTokens(cur);
        if (next !== cur) a.setAttribute('href', next);
      });
      root.querySelectorAll('input[value*="{{"], textarea').forEach((el) => {
        if (el.value && el.value.includes('{{')) {
          const next = replaceBrandTokens(el.value);
          el.value = next.startsWith('(') ? '' : next;
          if (!el.value && el.placeholder !== undefined) {
            el.placeholder = 'Configured after merchant sign-in';
          }
        }
      });
    }
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach((node) => {
      const s = replaceBrandTokens(node.nodeValue);
      if (s !== node.nodeValue) node.nodeValue = s;
    });
  }

  let _brandObserverInstalled = false;
  function installBrandObserver() {
    if (_brandObserverInstalled || typeof MutationObserver === 'undefined' || !document.body) return;
    _brandObserverInstalled = true;
    const obs = new MutationObserver((mutations) => {
      for (const m of mutations) {
        if (m.type === 'childList') {
          m.addedNodes.forEach((n) => {
            if (n.nodeType === 1 || n.nodeType === 3) applyBrandToRoot(n);
          });
        }
      }
    });
    obs.observe(document.body, { childList: true, subtree: true });
  }

  async function hydrateBrand(clientId) {
    let brand = {};
    // Apply clean defaults immediately so no {{...}} token flashes before network resolves
    applyBrandToRoot(document.body);
    installBrandObserver();

    try {
      const savedPin = (typeof localStorage !== 'undefined' && localStorage.getItem('algorise_client_pin')) || '';
      const q = savedPin ? `?pin=${encodeURIComponent(savedPin)}` : '';
      const resp = await apiFetch(`/client/${clientId}/brand${q}`);
      if (resp.ok) {
        brand = (await resp.json()).brand || {};
      }
    } catch (e) {
      console.warn('brand block unavailable; neutral placeholders active', e);
    }

    const value = (key, fallback = '—') => {
      const v = brand[key];
      return (!v || v === '—') ? fallback : v;
    };

    document.querySelectorAll('[data-brand]').forEach((el) => {
      const attr = el.getAttribute('data-brand');
      const val = value(BRAND_ATTRS[attr] || attr);
      if (el.tagName === 'A') {
        el.href = val === '—' ? '#' : val;
      } else {
        el.textContent = val;
      }
    });

    _cachedBrandSubs = {
      '{{WA_LINK}}': value('wa_link', '#'),
      '{{BRAND_PHONE}}': value('whatsapp_display', '(Configured on Merchant Sign-In)'),
      '{{BRAND_DPHONE}}': value('whatsapp_display', '(Configured on Merchant Sign-In)'),
      '{{BRAND_PHONE2}}': value('second_number', '(Secondary line optional)'),
      '{{BRAND_DIGITS}}': value('whatsapp_digits', ''),
      '{{data-brand-phone}}': value('whatsapp_display', '(Configured on Merchant Sign-In)'),
      '{{data-brand-phone2}}': value('second_number', '(Secondary line optional)'),
    };

    applyBrandToRoot(document.body);
  }

if (typeof window !== 'undefined') {
  window.hydrateBrand = hydrateBrand;
  window.formatBrandTokens = replaceBrandTokens;
}
