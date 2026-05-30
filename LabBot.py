import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import zipfile
import shutil
import time
import logging
import requests
from threading import Thread
from flask import Flask
from PIL import Image, ImageDraw, ImageFont
import colorsys
import io
import random
import tempfile
import re
from collections import Counter

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

BOT_TOKEN = '8917439575:AAGiw58_prp8Urx3DcBmXkyVoCesYc6yK0k'
bot = telebot.TeleBot(BOT_TOKEN)

app = Flask(__name__)

# ------------ НАСТРОЙКИ ------------
THEME_LAZURITE = 'Lazurite Dream.hwt'
THEME_COLOROS = 'ColorOS.hwt'
EXAMPLE_THEME = 'Example.hwt'
ICONS_ZIP = "icons.zip"

ALLOWED_USERS_URL = 'https://pastebin.com/raw/VbeVVK9T'
SERVER_URL = os.environ.get('RENDER_EXTERNAL_URL', 'http://localhost:8080')
SUPPORT_ADMIN_ID = 6778865145
SUPPORT_GROUP_ID = -1003763489689

user_languages = {}

def get_lang(user_id):
    return user_languages.get(user_id, None)

def set_lang(user_id, lang):
    user_languages[user_id] = lang

# ========== ТЕКСТЫ (сокращены, но полные в работе) ==========
TEXTS = {
    "ru": {
        "choose_language": "🌐 *Выберите язык:*",
        "welcome": "✨ *HuwiLabs Cloud* ✨\n\nДобро пожаловать в хранилище тем для Huawei.\n\n👇 Что желаете?",
        "themes_available": "🎨 *Доступные темы:*\n\n💙 Lazurite Dream\n⚜️ ColorOS",
        "guide": "📱 *Как установить тему Huawei*\n\n1️⃣ Скачайте файл .hwt\n2️⃣ Откройте «Файлы» → «Загрузки»\n3️⃣ Скопируйте файл в папку `Huawei/Themes`\n4️⃣ Закройте приложение «Темы»\n5️⃣ Откройте «Темы» → «Мои темы»\n\n✅ Готово!",
        "support_text": "🆘 *Поддержка*\n\nНапишите любое сообщение — оно отправится администратору.\n\nОтвет придёт сюда.",
        "enter_theme_name": "📝 Введите название темы:\n\nПример: Magic Sunset",
        "building_start": "🎨 Собираю тему «{name}» в цвете {color}...\n\n⏳ Подождите",
        "building_icons": "🖌️ Применяю сдвиг оттенка к иконкам...",
        "building_pack": "📦 Упаковываю в .hwt...",
        "done": "✅ Готово!\n\n📝 {name}\n🎨 {color}\n📦 Размер: {size} KB\n📁 Файл: `{filename}`",
        "no_access": "❌ Нет доступа! Приобретите у @crqckoff",
        "theme_not_found": "❌ Файл темы не найден!",
        "example_not_found": "❌ Example.hwt не найден!",
        "preparing": "📤 Подготовка...",
        "packing": "📦 Упаковка...",
        "uploading": "🚀 Загрузка...",
        "finalizing": "⚡ Финализация...",
        "ready": "🎨 Готово!",
        "progress_bar": "`[{bar}]` {percent}%",
        "theme_sent": "✅ {name} успешно загружена!\n\n{guide}",
        "btn_themes": "📁 Темы",
        "btn_builder": "🎨 Билдер иконок",
        "btn_guide": "📖 Гайд",
        "btn_support": "🆘 Поддержка",
        "btn_back": "◀️ Назад",
        "btn_download_lazurite": "💙 Lazurite Dream",
        "btn_download_coloros": "⚜️ ColorOS",
        "btn_guide_short": "📖 Гайд",
        "btn_menu_short": "◀️ Меню",
        "btn_custom_color": "🎨 Свой цвет",
        "send_wallpaper": "🖼️ Отправьте фото, бот подберёт сдвиг цвета",
        "dominant_color": "🎨 Цвет иконок: {color}\n🔄 Сдвиг оттенка: {shift}°\n\n📝 Введите название темы:",
        "error_no_image": "❌ Отправьте фото",
        "palette": "🎨 *Цвета:*\n\n🔴 Красный\n🟢 Зелёный\n🔵 Синий\n🟣 Фиолетовый\n🟠 Оранжевый\n🌸 Розовый\n💎 Бирюзовый\n\n👇 Выберите цвет",
    },
    "en": {
        "choose_language": "🌐 *Choose language:*",
        "welcome": "✨ *HuwiLabs Cloud* ✨\n\nWelcome to Huawei theme storage.\n\n👇 Choose action:",
        "themes_available": "🎨 *Available themes:*\n\n💙 Lazurite Dream\n⚜️ ColorOS",
        "guide": "📱 *How to install Huawei theme*\n\n1️⃣ Download .hwt\n2️⃣ Open Files → Downloads\n3️⃣ Copy to `Huawei/Themes`\n4️⃣ Close Themes app\n5️⃣ Open Themes → My themes\n\n✅ Done!",
        "support_text": "🆘 *Support*\n\nWrite any message — admin will reply here.",
        "enter_theme_name": "📝 Enter theme name:\n\nExample: Magic Sunset",
        "building_start": "🎨 Building theme «{name}» in {color}...\n\n⏳ Please wait",
        "building_icons": "🖌️ Applying hue shift to icons...",
        "building_pack": "📦 Packing into .hwt...",
        "done": "✅ Done!\n\n📝 {name}\n🎨 {color}\n📦 Size: {size} KB\n📁 File: `{filename}`",
        "no_access": "❌ No access! Contact @crqckoff",
        "theme_not_found": "❌ Theme file not found!",
        "example_not_found": "❌ Example.hwt not found!",
        "preparing": "📤 Preparing...",
        "packing": "📦 Packing...",
        "uploading": "🚀 Uploading...",
        "finalizing": "⚡ Finalizing...",
        "ready": "🎨 Ready!",
        "progress_bar": "`[{bar}]` {percent}%",
        "theme_sent": "✅ {name} uploaded!\n\n{guide}",
        "btn_themes": "📁 Themes",
        "btn_builder": "🎨 Icon builder",
        "btn_guide": "📖 Guide",
        "btn_support": "🆘 Support",
        "btn_back": "◀️ Back",
        "btn_download_lazurite": "💙 Lazurite Dream",
        "btn_download_coloros": "⚜️ ColorOS",
        "btn_guide_short": "📖 Guide",
        "btn_menu_short": "◀️ Menu",
        "btn_custom_color": "🎨 Custom color",
        "send_wallpaper": "🖼️ Send a photo, bot will detect hue shift",
        "dominant_color": "🎨 Icon color: {color}\n🔄 Hue shift: {shift}°\n\n📝 Enter theme name:",
        "error_no_image": "❌ Please send a photo",
        "palette": "🎨 *Colors:*\n\n🔴 Red\n🟢 Green\n🔵 Blue\n🟣 Purple\n🟠 Orange\n🌸 Pink\n💎 Cyan\n\n👇 Choose color",
    }
}

allowed_users_cache = {}
cache_time = 0

BASE_HUE = 200

PRESET_SHIFTS = {
    "red": 160, "green": 280, "blue": 0, "purple": 70,
    "orange": 190, "pink": 130, "cyan": 340,
}
PRESET_NAMES = {
    "red": {"ru": "🔴 Красный", "en": "🔴 Red"},
    "green": {"ru": "🟢 Зелёный", "en": "🟢 Green"},
    "blue": {"ru": "🔵 Синий", "en": "🔵 Blue"},
    "purple": {"ru": "🟣 Фиолетовый", "en": "🟣 Purple"},
    "orange": {"ru": "🟠 Оранжевый", "en": "🟠 Orange"},
    "pink": {"ru": "🌸 Розовый", "en": "🌸 Pink"},
    "cyan": {"ru": "💎 Бирюзовый", "en": "💎 Cyan"},
}
PRESET_PREFIX = {"red": "R", "green": "G", "blue": "B", "purple": "P", "orange": "O", "pink": "Pk", "cyan": "C"}
PRESET_RGB = {
    "red": (255,80,80), "green": (80,255,120), "blue": (80,160,255),
    "purple": (180,80,255), "orange": (255,160,80), "pink": (255,100,180),
    "cyan": (80,255,220),
}

def get_shift_from_wallpaper(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img.thumbnail((100, 100))
        cnt = Counter(list(img.getdata()))
        best = cnt.most_common(1)[0][0]
        r,g,b = best
        h,_,_ = colorsys.rgb_to_hsv(r/255, g/255, b/255)
        target_hue = h*360
        shift = (target_hue - BASE_HUE) % 360
        if shift > 180: shift -= 360
        return shift, best
    except:
        return 0, (80,160,255)

def hue_shift_icon(img_bytes, shift_deg):
    try:
        img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
        pix = img.load()
        for y in range(img.height):
            for x in range(img.width):
                r,g,b,a = pix[x,y]
                if a<50: continue
                h,s,v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
                h = ((h*360 + shift_deg) % 360)/360
                s = min(1.0, s*1.2)
                nr,ng,nb = colorsys.hsv_to_rgb(h,s,v)
                pix[x,y] = (int(nr*255), int(ng*255), int(nb*255), a)
        out = io.BytesIO()
        img.save(out, format="PNG")
        return out.getvalue()
    except:
        return None

def add_watermark_center(image_bytes, user_id, opacity=6):
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    wm = Image.new('RGBA', img.size, (0,0,0,0))
    draw = ImageDraw.Draw(wm)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
    except:
        font = ImageFont.load_default()
    text = str(user_id)
    bbox = draw.textbbox((0,0), text, font=font)
    text_h = bbox[3]-bbox[1]
    strip_width = max(bbox[2]-bbox[0] + 40, int(img.width*0.6))
    strip = Image.new('RGBA', (strip_width, img.height), (0,0,0,0))
    sdraw = ImageDraw.Draw(strip)
    color = (200,200,200,opacity)
    y = 15
    while y < img.height:
        sdraw.text((20, y), text, fill=color, font=font)
        y += text_h + 30
    paste_x = img.width//2 - strip_width//2 + 20
    paste_x = max(0, min(paste_x, img.width - strip_width))
    img.paste(strip, (paste_x, 0), strip)
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()

def process_icon(icon_bytes, shift_deg, user_id):
    shifted = hue_shift_icon(icon_bytes, shift_deg)
    if not shifted: return None
    return add_watermark_center(shifted, user_id)

def get_allowed_users():
    global allowed_users_cache, cache_time
    if time.time() - cache_time < 300:
        return allowed_users_cache
    try:
        r = requests.get(ALLOWED_USERS_URL, timeout=10)
        if r.status_code == 200:
            users = set()
            for line in r.text.strip().split('\n'):
                line = line.strip()
                if line and line.isdigit():
                    users.add(int(line))
            allowed_users_cache = users
            cache_time = time.time()
            return users
    except:
        pass
    return allowed_users_cache

def is_allowed(uid):
    return uid in get_allowed_users()

def build_theme(chat_id, theme_name, shift_deg, color_rgb, color_name, out_filename, lang, user_id):
    msg = bot.send_message(chat_id, TEXTS[lang]["building_start"].format(name=theme_name, color=color_name), parse_mode='Markdown')
    try:
        if not os.path.exists(EXAMPLE_THEME):
            bot.edit_message_text(TEXTS[lang]["example_not_found"], chat_id, msg.message_id)
            return False
        if not os.path.exists(ICONS_ZIP):
            bot.edit_message_text(f"❌ {ICONS_ZIP} не найден!", chat_id, msg.message_id)
            return False

        with tempfile.TemporaryDirectory() as tmp:
            template = os.path.join(tmp, "template.hwt")
            shutil.copy2(EXAMPLE_THEME, template)
            extract = os.path.join(tmp, "extract")
            os.makedirs(extract, exist_ok=True)
            with zipfile.ZipFile(template, 'r') as zf:
                zf.extractall(extract)

            # Обрабатываем иконки
            bot.edit_message_text(f"{TEXTS[lang]['building_icons']}\n\n⏳ Обработка...", chat_id, msg.message_id, parse_mode='Markdown')

            with zipfile.ZipFile(ICONS_ZIP, 'r') as zicons:
                all_icons = [n for n in zicons.namelist() if n.lower().endswith('.png')]
                total = len(all_icons)
                new_icons = {}
                for i, name in enumerate(all_icons, 1):
                    orig = zicons.read(name)
                    basename = os.path.basename(name).lower()

                    if i % 2 == 0 or i == total:
                        percent = int(i/total*100)
                        bar = "█"*(percent//10) + "⬜"*(10-percent//10)
                        short_name = basename[:35] + '…' if len(basename) > 38 else basename
                        try:
                            bot.edit_message_text(
                                f"{TEXTS[lang]['building_icons']}\n\n`[{bar}]` {percent}%\n📄 `{short_name}`\n{i}/{total}",
                                chat_id, msg.message_id, parse_mode='Markdown'
                            )
                        except: pass

                    processed = process_icon(orig, shift_deg, user_id)
                    clean = re.sub(r'[^a-z0-9._-]', '_', basename)
                    new_icons[clean] = processed if processed else orig

            # Создаём файл icons
            icons_path = os.path.join(extract, "icons")
            with zipfile.ZipFile(icons_path, 'w', zipfile.ZIP_STORED) as zf:
                for n,d in new_icons.items():
                    zf.writestr(n,d)

            # description.xml
            desc_path = os.path.join(extract, "description.xml")
            safe_title = re.sub(r'[<>:"/\\|?*]', '', theme_name)[:50]
            xml = f"""<HwTheme>
<title>{safe_title}</title>
<title-cn>默认中文名</title-cn>
<author>HuwiLabs</author>
<designer>HuwiLabs</designer>
<screen>FHD</screen>
<version>12.0.0</version>
<font>Default</font>
<font-cn>默认</font-cn>
<briefinfo>Made with icon builder. https://t.me/HLabsThemes</briefinfo>
<wallpaper-dark>true</wallpaper-dark>
</HwTheme>"""
            with open(desc_path, 'w', encoding='utf-8') as f:
                f.write(xml)

            # Упаковка
            bot.edit_message_text(TEXTS[lang]["building_pack"], chat_id, msg.message_id, parse_mode='Markdown')
            out_file = out_filename
            with zipfile.ZipFile(out_file, 'w', zipfile.ZIP_STORED) as zf:
                for root,_,files in os.walk(extract):
                    for f in files:
                        full = os.path.join(root, f)
                        arc = os.path.relpath(full, extract)
                        zf.write(full, arc)

        size_kb = os.path.getsize(out_file)/1024
        with open(out_file, 'rb') as f:
            bot.send_document(chat_id, f, caption=TEXTS[lang]["done"].format(name=theme_name, color=color_name, size=round(size_kb,1), filename=out_file), reply_markup=main_menu(lang), parse_mode='Markdown')
        os.remove(out_file)
        bot.delete_message(chat_id, msg.message_id)
        return True
    except Exception as e:
        bot.edit_message_text(f"❌ Ошибка: {e}", chat_id, msg.message_id, parse_mode='Markdown')
        return False

def send_premade_theme(chat_id, theme_file, theme_name, lang, message_id=None):
    if not os.path.exists(theme_file):
        bot.send_message(chat_id, TEXTS[lang]["theme_not_found"], reply_markup=main_menu(lang))
        return
    prog = bot.send_message(chat_id, f"{TEXTS[lang]['preparing']}\n⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0%", parse_mode='Markdown')
    for p in range(0, 101, 10):
        bar = "█"*(p//10)+"⬜"*(10-p//10)
        if p==0: s=TEXTS[lang]['preparing']
        elif p<30: s=TEXTS[lang]['packing']
        elif p<60: s=TEXTS[lang]['uploading']
        elif p<90: s=TEXTS[lang]['finalizing']
        else: s=TEXTS[lang]['ready']
        try:
            bot.edit_message_text(f"{s}\n`[{bar}]` {p}%", chat_id, prog.message_id, parse_mode='Markdown')
        except: pass
        time.sleep(0.6)
    with open(theme_file, 'rb') as f:
        bot.send_document(chat_id, f, caption=TEXTS[lang]["theme_sent"].format(name=theme_name, guide=TEXTS[lang]["guide"]), reply_markup=after_download_menu(lang), parse_mode='Markdown')
    try: bot.delete_message(chat_id, prog.message_id)
    except: pass
    if message_id:
        try: bot.delete_message(chat_id, message_id)
        except: pass

# ========== МЕНЮ ==========
def main_menu(lang="ru"):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton(TEXTS[lang]["btn_themes"], callback_data='themes'))
    kb.add(InlineKeyboardButton(TEXTS[lang]["btn_builder"], callback_data='builder'))
    kb.add(InlineKeyboardButton(TEXTS[lang]["btn_guide"], callback_data='guide'))
    kb.add(InlineKeyboardButton(TEXTS[lang]["btn_support"], callback_data='support'))
    return kb

def themes_menu(lang="ru"):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton(TEXTS[lang]["btn_download_lazurite"], callback_data='download_lazurite'))
    kb.add(InlineKeyboardButton(TEXTS[lang]["btn_download_coloros"], callback_data='download_coloros'))
    kb.add(InlineKeyboardButton(TEXTS[lang]["btn_back"], callback_data='back_to_menu'))
    return kb

def builder_menu(lang="ru"):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton('🔴', callback_data='color_red'),
        InlineKeyboardButton('🟢', callback_data='color_green'),
        InlineKeyboardButton('🔵', callback_data='color_blue'),
        InlineKeyboardButton('🟣', callback_data='color_purple'),
        InlineKeyboardButton('🟠', callback_data='color_orange'),
        InlineKeyboardButton('🌸', callback_data='color_pink'),
        InlineKeyboardButton('💎', callback_data='color_cyan'),
        InlineKeyboardButton(TEXTS[lang]["btn_custom_color"], callback_data='custom_color'),
        InlineKeyboardButton(TEXTS[lang]["btn_back"], callback_data='back_to_menu')
    )
    return kb

def after_download_menu(lang="ru"):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton(TEXTS[lang]["btn_guide_short"], callback_data='guide'), InlineKeyboardButton(TEXTS[lang]["btn_menu_short"], callback_data='back_to_menu'))
    return kb

def language_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton('🇷🇺 Русский', callback_data='lang_ru'), InlineKeyboardButton('🇬🇧 English', callback_data='lang_en'))
    return kb

@bot.message_handler(commands=['start'])
def start(m):
    uid = m.from_user.id
    lang = get_lang(uid)
    if not lang:
        bot.send_message(m.chat.id, TEXTS["ru"]["choose_language"], reply_markup=language_menu(), parse_mode='Markdown')
        return
    try:
        if len(m.text.split())>1 and m.text.split()[1]=='download_lazurite':
            send_premade_theme(m.chat.id, THEME_LAZURITE, "Lazurite Dream", lang)
            return
        elif len(m.text.split())>1 and m.text.split()[1]=='download_coloros':
            send_premade_theme(m.chat.id, THEME_COLOROS, "ColorOS", lang)
            return
    except: pass
    bot.send_message(m.chat.id, TEXTS[lang]["welcome"], reply_markup=main_menu(lang), parse_mode='Markdown')

@bot.callback_query_handler(func=lambda c: c.data.startswith('lang_'))
def lang_cb(c):
    lang = c.data.split('_')[1]
    set_lang(c.from_user.id, lang)
    bot.edit_message_text(TEXTS[lang]["welcome"], c.message.chat.id, c.message.message_id, reply_markup=main_menu(lang), parse_mode='Markdown')

@bot.callback_query_handler(func=lambda c: True)
def cb_handler(c):
    uid = c.from_user.id
    lang = get_lang(uid) or "ru"
    try:
        if c.data == 'themes':
            bot.edit_message_text(TEXTS[lang]["themes_available"], c.message.chat.id, c.message.message_id, reply_markup=themes_menu(lang), parse_mode='Markdown')
        elif c.data == 'builder':
            if not is_allowed(uid):
                bot.answer_callback_query(c.id, TEXTS[lang]["no_access"], True)
                return
            bot.edit_message_text(TEXTS[lang]["palette"], c.message.chat.id, c.message.message_id, reply_markup=builder_menu(lang), parse_mode='Markdown')
        elif c.data == 'custom_color':
            msg = bot.send_message(c.message.chat.id, TEXTS[lang]["send_wallpaper"], parse_mode='Markdown')
            bot.register_next_step_handler(msg, wallpaper_handler, c.message.chat.id, lang)
            bot.answer_callback_query(c.id)
        elif c.data.startswith('color_'):
            key = c.data.replace('color_','')
            if key in PRESET_SHIFTS:
                shift = PRESET_SHIFTS[key]
                color_name = PRESET_NAMES[key][lang]
                prefix = PRESET_PREFIX[key]
                color_rgb = PRESET_RGB[key]
                msg = bot.send_message(c.message.chat.id, TEXTS[lang]["enter_theme_name"], parse_mode='Markdown')
                bot.register_next_step_handler(msg, name_handler, shift, color_rgb, color_name, prefix, lang, uid)
            else:
                bot.answer_callback_query(c.id, "Ошибка", True)
        elif c.data == 'guide':
            bot.edit_message_text(TEXTS[lang]["guide"], c.message.chat.id, c.message.message_id, reply_markup=main_menu(lang), parse_mode='Markdown')
        elif c.data == 'download_lazurite':
            send_premade_theme(c.message.chat.id, THEME_LAZURITE, "Lazurite Dream", lang, c.message.message_id)
        elif c.data == 'download_coloros':
            send_premade_theme(c.message.chat.id, THEME_COLOROS, "ColorOS", lang, c.message.message_id)
        elif c.data == 'support':
            bot.edit_message_text(TEXTS[lang]["support_text"], c.message.chat.id, c.message.message_id, reply_markup=main_menu(lang), parse_mode='Markdown')
        elif c.data == 'back_to_menu':
            bot.edit_message_text(TEXTS[lang]["welcome"], c.message.chat.id, c.message.message_id, reply_markup=main_menu(lang), parse_mode='Markdown')
    except Exception as e:
        print(f"Ошибка: {e}")

def wallpaper_handler(m, chat_id, lang):
    if not m.photo:
        bot.send_message(chat_id, TEXTS[lang]["error_no_image"], reply_markup=builder_menu(lang))
        return
    file_info = bot.get_file(m.photo[-1].file_id)
    data = bot.download_file(file_info.file_path)
    shift, color_rgb = get_shift_from_wallpaper(data)
    hexc = "#{:02x}{:02x}{:02x}".format(*color_rgb)
    bot.send_message(chat_id, TEXTS[lang]["dominant_color"].format(color=hexc, shift=round(shift,1)), parse_mode='Markdown')
    msg = bot.send_message(chat_id, TEXTS[lang]["enter_theme_name"], parse_mode='Markdown')
    bot.register_next_step_handler(msg, name_handler, shift, color_rgb, f"🎨 Свой ({hexc})", "Cst", lang, None)

def name_handler(m, shift, color_rgb, color_name, prefix, lang, user_id):
    name = m.text.strip()
    if not name:
        bot.send_message(m.chat.id, "❌ Введите название", reply_markup=builder_menu(lang))
        return
    filename = f"Theme{prefix}{random.randint(10,99)}.hwt"
    if user_id is None:
        user_id = m.from_user.id
    build_theme(m.chat.id, name, shift, color_rgb, color_name, filename, lang, user_id)

def forward_to_support(original_message, text_prefix=""):
    try:
        user = original_message.from_user
        user_info = f"👤 @{user.username}" if user.username else f"👤 {user.first_name} (ID: {user.id})"
        caption = f"{text_prefix}\n\n{user_info}\n📝 Сообщение:"
        if SUPPORT_ADMIN_ID:
            if original_message.text:
                bot.send_message(SUPPORT_ADMIN_ID, f"{caption}\n\n{original_message.text}")
            elif original_message.photo:
                bot.send_photo(SUPPORT_ADMIN_ID, original_message.photo[-1].file_id, caption=caption)
            elif original_message.document:
                bot.send_document(SUPPORT_ADMIN_ID, original_message.document.file_id, caption=caption)
            else:
                bot.send_message(SUPPORT_ADMIN_ID, f"{caption}\n[Другой тип]")
        if SUPPORT_GROUP_ID:
            bot.send_message(SUPPORT_GROUP_ID, caption)
        bot.reply_to(original_message, "📨 Сообщение отправлено в поддержку.")
    except Exception as e:
        print(e)

@bot.message_handler(func=lambda m: True, content_types=['text','photo','document','voice','video','audio','sticker'])
def catch_all(m):
    if m.text and m.text.startswith('/'):
        return
    if m.from_user.id == SUPPORT_ADMIN_ID:
        return
    forward_to_support(m, "🆕 Новое обращение:")

@bot.message_handler(func=lambda m: m.from_user.id == SUPPORT_ADMIN_ID and m.reply_to_message)
def reply_to_support(m):
    try:
        orig = m.reply_to_message
        if orig and orig.forward_from:
            uid = orig.forward_from.id
            bot.send_message(uid, f"📨 *Ответ поддержки:*\n\n{m.text}", parse_mode='Markdown')
            bot.reply_to(m, "✅ Ответ отправлен")
        elif orig and orig.text and "ID:" in orig.text:
            for part in orig.text.split():
                if part.startswith("ID:") and part[3:].isdigit():
                    uid = int(part[3:])
                    bot.send_message(uid, f"📨 *Ответ поддержки:*\n\n{m.text}", parse_mode='Markdown')
                    bot.reply_to(m, "✅ Ответ отправлен")
                    return
        else:
            bot.reply_to(m, "❌ Не удалось определить пользователя.")
    except Exception as e:
        bot.reply_to(m, f"❌ Ошибка: {e}")

def auto_ping():
    while True:
        try:
            requests.get(f'{SERVER_URL}/livez', timeout=10)
        except:
            pass
        time.sleep(240)

@app.route('/')
def health(): return "OK", 200
@app.route('/livez')
def live(): return {"status": "ok"}, 200

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    print("🤖 HuwiLabs bot — финальная версия с ColorOS и opacity=6")
    Thread(target=run_flask, daemon=True).start()
    Thread(target=auto_ping, daemon=True).start()
    bot.infinity_polling()