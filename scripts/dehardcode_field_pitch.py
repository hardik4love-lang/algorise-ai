"""Dehardcode field_pitch.html: the operator's own WhatsApp link."""
import re
from pathlib import Path

p = Path(__file__).resolve().parent.parent / "field_pitch.html"
text = p.read_text(encoding="utf-8")

before = len(re.findall(r"https://wa\.me/\d+", text))

# The pitch page links to the operator's personal number. That is contact
# data for whoever owns the deployment, not for the merchant being pitched,
# so it moves behind the same brand endpoint as everything else.
text = re.sub(r"https://wa\.me/\d+", "{{WA_LINK}}", text)

p.write_text(text, encoding="utf-8")

print(f"  wa.me links replaced: {before}")
print(f"  remaining          : {len(re.findall(r'wa\.me/[0-9]', text))}")
