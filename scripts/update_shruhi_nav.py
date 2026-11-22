with open('shruhi.html', 'r', encoding='utf-8') as f:
    content = f.read()

target = '<a href="#prebook" class="hover:text-gold-400 transition-colors">How Pre-Booking Works</a>'
new_link = '<a href="#prebook" class="hover:text-gold-400 transition-colors">How Pre-Booking Works</a>\n        <a href="techsupport.html" class="hover:text-cyan-400 text-cyan-300 font-semibold transition-colors"><i class="fa-solid fa-wrench mr-1"></i>Tech Support</a>'

if target in content and 'techsupport.html' not in content:
    content = content.replace(target, new_link, 1)
    with open('shruhi.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: added techsupport.html to shruhi.html nav")
else:
    print("ALREADY EXISTS or target not found in shruhi.html")
