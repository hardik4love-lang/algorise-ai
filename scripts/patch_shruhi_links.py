import sys

def main():
    path = 'shruhi.html'
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()

    text = text.replace('916355285433', '919054241725')
    text = text.replace('+91 63552 85433', '+91 90542 41725')

    # Add direct flagship link to top bar
    old_top = '<a href="https://wa.me/919054241725?text=Namaste!%20I%20am%20visiting%20shruhicollections.in%20and%20want%20to%20view%20the%20VIP%20Catalog" class="underline font-bold text-gold-400 ml-1 hover:text-white transition-colors">\n      WhatsApp: +91 90542 41725\n    </a>'
    new_top = '<a href="https://wa.me/919054241725?text=Namaste!%20I%20am%20visiting%20shruhicollections.in%20and%20want%20to%20view%20the%20VIP%20Catalog" class="underline font-bold text-gold-400 ml-1 hover:text-white transition-colors">WhatsApp: +91 90542 41725</a>\n    <span class="mx-2 text-white/30">|</span>\n    <a href="https://shruhicollections.in/" target="_blank" class="underline font-bold text-amber-300 hover:text-white transition-colors">Official Flagship: shruhicollections.in &rarr;</a>'
    text = text.replace(old_top, new_top)

    # In nav add link to shruhicollections.in
    old_nav_cta = '<div class="flex items-center gap-3">\n        <a href="https://wa.me/919054241725?text=Namaste!%20I%20want%20to%20pre-book%20an%20outfit%20from%20Shruhi%20Collections" target="_blank" class="flex items-center gap-2 bg-gradient-to-r from-gold-500 to-amber-600 hover:from-gold-400 hover:to-amber-500 text-black font-extrabold text-xs py-2.5 px-4 rounded-full transition-all shadow-lg hover:shadow-gold-500/30">\n          <i class="fa-brands fa-whatsapp text-sm"></i>\n          <span>VIP WhatsApp Desk</span>\n        </a>\n      </div>'
    new_nav_cta = '<div class="flex items-center gap-3">\n        <a href="https://shruhicollections.in/" target="_blank" class="hidden sm:inline-flex items-center gap-1.5 border border-gold-400/50 hover:bg-gold-500/10 text-gold-300 font-bold text-xs py-2 px-3.5 rounded-full transition-all">\n          <span>Visit Live Boutique</span> <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>\n        </a>\n        <a href="https://wa.me/919054241725?text=Namaste!%20I%20want%20to%20pre-book%20an%20outfit%20from%20Shruhi%20Collections" target="_blank" class="flex items-center gap-2 bg-gradient-to-r from-gold-500 to-amber-600 hover:from-gold-400 hover:to-amber-500 text-black font-extrabold text-xs py-2.5 px-4 rounded-full transition-all shadow-lg hover:shadow-gold-500/30">\n          <i class="fa-brands fa-whatsapp text-sm"></i>\n          <span>VIP WhatsApp Desk</span>\n        </a>\n      </div>'
    text = text.replace(old_nav_cta, new_nav_cta)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)

    print("Successfully patched shruhi.html!")
    return 0

if __name__ == '__main__':
    sys.exit(main())
