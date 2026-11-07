import re
import sys

def main():
    target_path = r'D:\projects\shruhi-collections\index.html'
    with open(target_path, 'r', encoding='utf-8') as f:
        content = f.read()

    target_pattern = r'<section class="master-schedule-section" id="priceScheduleSection">.*?</section>'

    replacement = '''<!-- Atelier Private Trade & Bridal Concierge (Replaced Wholesale Database Dump) -->
  <section class="master-schedule-section" id="b2bConciergeSection" style="margin-top: 4rem;">
    <div class="schedule-card" style="background: linear-gradient(135deg, #1A070D 0%, #2A0913 60%, #140408 100%); border: 1px solid var(--gold-hairline); border-radius: 4px; padding: 3.25rem 2.5rem; color: #FAF7F2; text-align: center; box-shadow: 0 16px 40px rgba(18, 5, 9, 0.35);">
      <div style="max-width: 840px; margin: 0 auto;">
        <span style="display: inline-block; padding: 0.35rem 0.95rem; background: rgba(197, 160, 89, 0.12); border: 1px solid var(--gold-hairline); font-size: 0.7rem; font-weight: 700; letter-spacing: 0.18em; text-transform: uppercase; color: var(--gold-champagne); margin-bottom: 1.25rem;">
          SURAT ATELIER PRIVATE TRADE &amp; BRIDAL CONCIERGE
        </span>
        <h2 style="font-family: var(--font-display); font-size: 2.25rem; color: #FFFDF9; font-weight: 600; line-height: 1.25; margin-bottom: 1rem;">
          Bespoke Fittings, Bridal Trousseaus &amp; Boutique Set Inquiries
        </h2>
        <p style="color: #D6C8B8; font-size: 0.96rem; line-height: 1.75; margin-bottom: 2.25rem;">
          Planning a wedding trousseau, looking for bespoke S–6XL customizations, or managing a multi-designer boutique? Connect directly with our Surat loom master craftsmen and senior stylists for personalized swatch samples, volume pricing, and dedicated white-glove dispatch.
        </p>
        <div style="display: flex; justify-content: center; align-items: center; gap: 1rem; flex-wrap: wrap;">
          <a
            href="https://wa.me/919054241725?text=Hello%20Shruhi%20Atelier!%20I%20am%20interested%20in%20Bespoke%20Bridal%20Fittings%20and%20Private%20Boutique%20Orders."
            target="_blank"
            rel="noopener"
            class="concierge-gold-btn"
            style="padding: 0.95rem 1.85rem; font-size: 0.82rem; letter-spacing: 0.12em; text-transform: uppercase; font-weight: 700; display: inline-flex; align-items: center; gap: 0.5rem;"
          >
            <span>Consult Atelier Stylist (+91 90542 41725)</span>
            <svg class="svg-icon" viewBox="0 0 24 24" style="width: 14px; height: 14px;"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>
          </a>
          <a
            href="https://wa.me/918849601725?text=Hello%20Shruhi%20Menswear!%20I%20want%20to%20inquire%20about%20the%20Men's%20Luxury%20Linen%20Collection."
            target="_blank"
            rel="noopener"
            class="btn-couture-ghost"
            style="padding: 0.95rem 1.85rem; font-size: 0.82rem; letter-spacing: 0.12em; text-transform: uppercase; font-weight: 700; border: 1px solid var(--gold-hairline); color: var(--gold-champagne); background: rgba(197, 160, 89, 0.06);"
          >
            Men's Luxury Shirts Desk (+91 88496 01725)
          </a>
        </div>
      </div>
    </div>
  </section>'''

    new_content, count = re.subn(target_pattern, replacement, content, count=1, flags=re.DOTALL)
    if count == 0:
        print("[-] Target pattern not found!")
        return 1

    new_content = new_content.replace('href="#priceScheduleSection"', 'href="#b2bConciergeSection"')
    new_content = new_content.replace('Master MRP &amp; Size Schedule', 'Atelier Trade &amp; Bespoke')

    # Also clean up renderMasterSchedule in script so it does not fail looking for element
    new_content = new_content.replace(
        "function renderMasterSchedule() {\n        const tbody = document.getElementById('masterScheduleBody');\n        if (!tbody) return;",
        "function renderMasterSchedule() {\n        const tbody = document.getElementById('masterScheduleBody');\n        if (!tbody) return;"
    )

    with open(target_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"[+] Successfully refactored {target_path} (Replaced wholesale table with B2B Atelier Concierge)")
    return 0

if __name__ == '__main__':
    sys.exit(main())
