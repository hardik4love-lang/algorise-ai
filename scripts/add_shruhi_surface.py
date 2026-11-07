with open('scripts/build.py', 'rb') as f:
    text = f.read().decode('utf-8')

if '"shruhi.html"' not in text:
    text = text.replace('"dashboard.html",', '"dashboard.html",\n    "shruhi.html",')
    with open('scripts/build.py', 'wb') as f:
        f.write(text.encode('utf-8'))
    print("Added shruhi.html to SURFACES")
else:
    print("shruhi.html already in SURFACES")
