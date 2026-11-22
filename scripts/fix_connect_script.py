with open('scripts/connect_support_page.py', 'r', encoding='utf-8') as f:
    c = f.read()

c = c.replace("nlp_res['phone']", "nlp_res.get('extracted_phone', 'None')")

with open('scripts/connect_support_page.py', 'w', encoding='utf-8') as f:
    f.write(c)

print("Updated connect_support_page.py")
