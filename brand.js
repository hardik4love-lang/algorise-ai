/**
 * Client brand hydration. GENERATED from dashboard.html by
 * scripts/extract_brand_js.py — edit the dashboard and re-run.
 *
 * Replaces {{MARKER}} tokens with the signed-in merchant's contact
 * details from /api/v1/client/{id}/brand. A missing value renders as
 * an em-dash rather than as another merchant's number.
 */
// Merchant brand hydration.
  //
  // One merchant's phone numbers were hardcoded in 34 places here, so
  // onboarding a second merchant required editing this file. Those values
  // are now {{MARKERS}} filled from /api/v1/client/{id}/brand.
  //
  // A missing value renders as an em-dash rather than as another client's
  // number, and never as a raw un-substituted marker.
  const BRAND_ATTRS = {
    WA_LINK: 'wa_link',
    BRAND_PHONE: 'whatsapp_display',
    BRAND_DPHONE: 'whatsapp_display',
    BRAND_PHONE2: 'second_number',
    BRAND_DIGITS: 'whatsapp_digits',
  };

  async function hydrateBrand(clientId) {
    let brand = {};
    try {
      const resp = await apiFetch(`/client/${clientId}/brand`);
      brand = (await resp.json()).brand || {};
    } catch (e) {
      console.warn('brand block unavailable; merchant values will be blank', e);
    }

    const value = (key) => {
      const v = brand[key];
      return (!v || v === '—') ? '—' : v;
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

    // Replace any marker text left inside larger strings.
    const subs = {
      '{{WA_LINK}}': value('wa_link'),
      '{{BRAND_PHONE}}': value('whatsapp_display'),
      '{{BRAND_DPHONE}}': value('whatsapp_display'),
      '{{BRAND_PHONE2}}': value('second_number'),
      '{{BRAND_DIGITS}}': value('whatsapp_digits'),
    };
    const walker = document.createTreeWalker(
      document.body, NodeFilter.SHOW_TEXT
    );
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach((node) => {
      let s = node.nodeValue;
      if (!s) return;
      Object.entries(subs).forEach(([k, v]) => { s = s.split(k).join(v); });
      if (s !== node.nodeValue) node.nodeValue = s;
    });
  }

if (typeof window !== 'undefined') window.hydrateBrand = hydrateBrand;
