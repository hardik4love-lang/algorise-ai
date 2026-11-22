with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

target = '<a href="shruhi.html" style="color: #f5d77f; font-weight: 700;"><i class="fa-solid fa-crown text-xs mr-1"></i>Shruhi Storefront</a>'
support_link = '\n      <a href="techsupport.html" style="color: #00f2fe; font-weight: 700;"><i class="fa-solid fa-screwdriver-wrench text-xs mr-1"></i>Tech Support &amp; Repair</a>'

if target in content and 'techsupport.html' not in content:
    content = content.replace(target, target + support_link, 1)
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: added techsupport.html to index.html nav")
else:
    print("ALREADY EXISTS or target not found in index.html")
