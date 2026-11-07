import re

with open('index.html', 'rb') as f:
    text = f.read().decode('utf-8')

# Remove sf-journey
text = re.sub(
    r'<!--\s*==========================================\s*-->\s*<!--\s*05\.\s*DUAL JOURNEY SPLIT[\s\S]*?<!--\s*==========================================\s*-->\s*<!--\s*06\.\s*100 HERO BOTS SUITE PREVIEW\s*-->',
    '<!-- ==========================================\\n  03. HOW IT WORKS\\n  ========================================== -->',
    text
)

# Remove roi-simulator
text = re.sub(
    r'<!--\s*==========================================\s*-->\s*<section class="sf-section" id="roi-simulator"[\s\S]*?</section>\s*(?=<section class="sf-section" id="pricing">)',
    '',
    text
)

# Also remove sf-platform if it's redundant with how-it-works or keep it minimal
# Update nav to match compact sections
text = text.replace('href="#roi-simulator"', 'href="#pricing"')
text = text.replace('ROI Calculator', 'Plans & Pricing')

with open('index.html', 'wb') as f:
    f.write(text.encode('utf-8'))

print('DONE_COMPACT')
