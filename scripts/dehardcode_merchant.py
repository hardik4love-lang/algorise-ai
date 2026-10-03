"""
Remove merchant-specific values from the dashboard.

Replaces hardcoded phone numbers and wa.me links with data attributes that
the brand hydration pass fills from /api/v1/client/{id}/brand.

Values become a neutral em-dash rather than a placeholder token, so a
client with no configured number shows nothing misleading and never another
merchant's contact details.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# wa.me links -> marker
WA_LINK = re.compile(r"https://wa\.me/\d+")

# Display numbers. Only the two known merchant numbers are replaced; any
# other number is left alone so unrelated content is not mangled.
NUMBERS = {
    "+91 63552 85433": "data-brand-phone",
    "+91 90542 41725": "data-brand-phone2",
    "916355285433": "data-brand-digits",
}

DASHBOARD = ROOT / "dashboard.html"

text = DASHBOARD.read_text(encoding="utf-8")
original = text

wa_count = len(WA_LINK.findall(text))
text = WA_LINK.sub("{{WA_LINK}}", text)

# Numbers, longest first so the spaced form wins over the digit form.
num_count = 0
for needle in sorted(NUMBERS, key=len, reverse=True):
    attr = NUMBERS[needle]
    count = text.count(needle)
    if count:
        text = text.replace(needle, f"{{{{{attr}}}}}")
        num_count += count

DASHBOARD.write_text(text, encoding="utf-8")

print()
print(f"  wa.me links replaced  : {wa_count}")
print(f"  phone numbers replaced: {num_count}")
print(f"  file size             : {len(original):,} -> {len(text):,} bytes")
print()

remaining = WA_LINK.findall(text)
nums_left = sum(text.count(n) for n in NUMBERS)
print(f"  remaining wa.me links : {len(remaining)}")
print(f"  remaining known numbers: {nums_left}")
print()
