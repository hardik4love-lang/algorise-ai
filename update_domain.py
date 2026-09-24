import os, glob

replacements = [
    ('<base href="/algorise-ai/">', '<base href="/">'),
    ('https://hardik4love-lang.github.io/algorise-ai/', 'https://algorise-ai.com/'),
    ('https://hardik4love-lang.github.io/algorise-ai', 'https://algorise-ai.com'),
    ('https://algorise-ai.surge.sh/', 'https://algorise-ai.com/'),
    ('https://algorise-ai.surge.sh', 'https://algorise-ai.com'),
]

files = glob.glob('dist/**/*.html', recursive=True) + glob.glob('*.html')
for fpath in set(files):
    if not os.path.isfile(fpath): continue
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    modified = False
    for old, new in replacements:
        if old in content:
            content = content.replace(old, new)
            modified = True
            
    if modified:
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(content)
        print('Patched for algorise-ai.com:', fpath)

print('Domain link patching completed!')
