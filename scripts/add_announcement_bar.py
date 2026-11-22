with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

target = '  <!-- 01. NAVIGATION HEADER                      -->\n  <!-- ========================================== -->\n  <header class="sf-header">'
banner = '''  <!-- TOP ANNOUNCEMENT BAR (VISIBLE ON ALL MOBILE & DESKTOP SURFACES) -->
  <div style="background: linear-gradient(90deg, #07090e 0%, #002b3d 50%, #07090e 100%); border-bottom: 1px solid rgba(0, 242, 254, 0.35); padding: 9px 16px; text-align: center; font-size: 12px; font-weight: 600; color: #e2e8f0; z-index: 60; position: relative;">
    <span style="color: #00f2fe; margin-right: 6px;">⚡</span>
    <strong style="color: #00f2fe;">HYBRID TECH SUPPORT &amp; REPAIR:</strong> 24/7 Aria Remote Desk (AnyDesk flat ₹250) &bull; Surat Doorstep Onsite Repair by Founder (₹500 Deposit) &bull; 
    <a href="techsupport.html" style="color: #00f2fe; text-decoration: underline; font-weight: 800; margin-left: 6px; padding: 2px 6px; background: rgba(0,242,254,0.12); border-radius: 4px;">🛠️ Open Tech Support Portal &rarr;</a>
    <span style="margin: 0 10px; color: rgba(255,255,255,0.3);">|</span>
    <a href="shruhi.html" style="color: #f5d77f; text-decoration: underline; font-weight: 800;">✨ Shruhi Storefront &rarr;</a>
  </div>

  <!-- 01. NAVIGATION HEADER                      -->
  <!-- ========================================== -->
  <header class="sf-header">'''

if target in content and 'HYBRID TECH SUPPORT &amp; REPAIR' not in content:
    content = content.replace(target, banner, 1)
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: Added top announcement banner to index.html")
else:
    print("ALREADY EXISTS or target not found")
