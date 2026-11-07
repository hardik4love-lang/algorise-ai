with open('index.html', 'rb') as f:
    text = f.read().decode('utf-8')

import re
text = re.sub(
    r'<a href="#pricing">Plans & Pricing</a>\s*<a href="#pricing">Pricing</a>',
    '<a href="#pricing">Plans &amp; Pricing</a>\n      <a href="shruhi.html" style="color: #f5d77f; font-weight: 700;"><i class="fa-solid fa-crown text-xs mr-1"></i>Shruhi Storefront</a>',
    text
)

with open('index.html', 'wb') as f:
    f.write(text.encode('utf-8'))

print("NAV_UPDATED")
