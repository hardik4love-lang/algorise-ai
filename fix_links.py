import os, glob

base_tag = """  <base href="/algorise-ai/">"""

replacements = [
    ('href="/dashboard.html"', 'href="dashboard.html"'),
    ('href="/creator_studio.html"', 'href="creator_studio.html"'),
    ('href="/cocopeat.html"', 'href="cocopeat.html"'),
    ('href="/field_pitch.html"', 'href="field_pitch.html"'),
    ('href="/admin.html"', 'href="admin.html"'),
    ('href="/sitemap.xml"', 'href="sitemap.xml"'),
    ('href="/index.html"', 'href="index.html"'),
    ('href="/index.html#pricing"', 'href="index.html#pricing"'),
    ('href="/compare/manychat-alternative.html"', 'href="compare/manychat-alternative.html"'),
    ('href="/compare/wati-alternative.html"', 'href="compare/wati-alternative.html"'),
    ('href="/industry/textile-saree-wholesale-ai-agent.html"', 'href="industry/textile-saree-wholesale-ai-agent.html"'),
    ('href="/industry/diamond-cvd-sales-agent.html"', 'href="industry/diamond-cvd-sales-agent.html"'),
    ('href="/"', 'href="index.html"'),
    ('src="/assets/', 'src="assets/'),
    ('href="/assets/', 'href="assets/'),
]

files = glob.glob('dist/**/*.html', recursive=True) + glob.glob('*.html')
for fpath in set(files):
    if not os.path.isfile(fpath): continue
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Inject base tag right after <head>
    if '<base href="/algorise-ai/">' not in content and '<head>' in content:
        content = content.replace('<head>', '<head>\n' + base_tag, 1)
        
    for old, new in replacements:
        content = content.replace(old, new)
        
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Updated:', fpath)
print('ALL HTML files updated with <base href="/algorise-ai/"> and clean relative links!')
