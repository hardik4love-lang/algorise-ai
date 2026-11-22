with open('scripts/build.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = '"shruhi.html",'
replacement = '"shruhi.html",\n    "techsupport.html",'

if target in content and '"techsupport.html"' not in content:
    content = content.replace(target, replacement, 1)
    with open('scripts/build.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: added techsupport.html to build.py")
else:
    print("ALREADY EXISTS or target not found")
