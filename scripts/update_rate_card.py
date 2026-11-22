import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent.parent

# 1. Update techsupport.html
html_path = ROOT / "techsupport.html"
html_content = html_path.read_text(encoding="utf-8")

old_row = """              <tr class="hover:bg-slate-800/30 transition-colors">
                <td class="py-4 px-6 font-semibold text-white">Laptop Deep Thermal Overhaul &amp; Fan Cleaning</td>
                <td class="py-4 px-6 text-amber-400 font-mono">Surat In-Person</td>
                <td class="py-4 px-6">1 - 2 Hours</td>
                <td class="py-4 px-6 text-right font-mono font-bold text-white">₹600 + visit</td>
              </tr>"""

new_row = """              <tr class="hover:bg-slate-800/30 transition-colors">
                <td class="py-4 px-6 font-semibold text-white">Laser Printer Cartridge Refill (HP, Canon, Brother)</td>
                <td class="py-4 px-6 text-amber-400 font-mono">Surat In-Person</td>
                <td class="py-4 px-6">30 Mins</td>
                <td class="py-4 px-6 text-right font-mono font-bold text-amber-400">₹300 flat</td>
              </tr>"""

if old_row in html_content:
    html_content = html_content.replace(old_row, new_row)
    html_path.write_text(html_content, encoding="utf-8")
    print("SUCCESS: Updated techsupport.html with Laser Printer Cartridge Refill Rs 300")
else:
    print("WARNING: Target row not found in techsupport.html")

# 2. Update config/clients/client_algorise_support.json
config_path = ROOT / "config" / "clients" / "client_algorise_support.json"
config_content = config_path.read_text(encoding="utf-8")

old_item = '{"item": "Laptop Thermal Paste & Deep Dust Cleanout", "moq": "Per Unit", "ex_factory_rate": "₹600 + visit"},'
new_item = '{"item": "Laser Printer Cartridge Refill (HP, Canon, Brother)", "moq": "Per Cartridge", "ex_factory_rate": "₹300 flat"},'

if old_item in config_content:
    config_content = config_content.replace(old_item, new_item)
    config_path.write_text(config_content, encoding="utf-8")
    print("SUCCESS: Updated client_algorise_support.json with Laser Printer Cartridge Refill Rs 300")
else:
    import re
    config_content = re.sub(
        r'\{"item":\s*"Laptop Thermal Paste[^"]*",\s*"moq":\s*"[^"]*",\s*"ex_factory_rate":\s*"[^"]*"\},?',
        new_item,
        config_content
    )
    config_path.write_text(config_content, encoding="utf-8")
    print("SUCCESS: Regex replaced item in client_algorise_support.json")
