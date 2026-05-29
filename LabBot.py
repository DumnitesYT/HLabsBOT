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
THEME_FILE = 'Lazurite Dream.hwt'
EXAMPLE_THEME = 'Example.hwt'
ICONS_ZIP = "icons.zip"
OTHERS_ZIP = "others.zip"

ALLOWED_USERS_URL = 'https://pastebin.com/raw/VbeVVK9T'
SERVER_URL = os.environ.get('RENDER_EXTERNAL_URL', 'http://localhost:8080')

SUPPORT_ADMIN_ID = 6778865145
SUPPORT_GROUP_ID = -1003763489689
SUPPORT_GROUP_LINK = 'https://t.me/podderzhkahuwi'

# Список иконок, которые НЕ НАДО перекрашивать и включать в icons
IGNORE_ICONS = [
    'icon_background_01.png',
    'icon_border.png',
    'icon_mask.png',
    'icon_shortcut.png',
    'icon_shortcut_arrow.png',
    'icon_shortcut_mask.png'
]

user_languages = {}
user_temp_data = {}

def get_lang(user_id):
    return user_languages.get(user_id, None)

def set_lang(user_id, lang):
    user_languages[user_id] = lang

# ========== ТЕКСТЫ ==========
TEXTS = {
    "ru": {
        "choose_language": "🌐 *Выберите язык:*",
        "welcome": "✨ *HuwiLabs Cloud* ✨\n\nДобро пожаловать в хранилище тем для Huawei.\n\n👇 Что желаете?",
        "themes_available": "🎨 Доступные темы:\n\n💙 Lazurite Dream",
        "guide": "📱 Как установить тему Huawei\n\n1️⃣ Скачайте файл .hwt\n2️⃣ Откройте Файлы → Загрузки\n3️⃣ Скопируйте в Huawei/Themes\n4️⃣ Откройте Темы → Мои темы\n5️⃣ Нажмите на тему → Применить\n\n✅ Готово!",
        "support_text": "🆘 *Поддержка*\n\nПросто напишите любое сообщение — оно будет отправлено администратору.\n\nОтвет придёт сюда.",
        "enter_theme_name": "📝 Введите название темы:\n\nПример: Magic Sunset",
        "theme_name_saved": "✅ Имя: {name}\n\n🎨 Теперь выберите цвет:",
        "building_start": "🎨 Начинаю сборку темы «{name}» в цвете {color}...\n\n⏳ Это займёт до минуты",
        "building_icons": "🖌️ Перекрашиваю иконки...",
        "building_pack": "📦 Упаковываю в .hwt...",
        "done": "✅ Готово!\n\n📝 {name}\n🎨 {color}\n📦 Размер: {size} KB\n📁 Файл: `{filename}`",
        "no_access": "❌ Нет доступа! Приобретите у @crqckoff",
        "theme_not_found": "❌ Файл темы не найден!",
        "example_not_found": "❌ Файл-шаблон Example.hwt не найден!",
        "preparing": "📤 Подготовка...",
        "packing": "📦 Упаковка...",
        "uploading": "🚀 Загрузка...",
        "finalizing": "⚡ Финализация...",
        "ready": "🎨 Готово!",
        "progress_bar": "`[{bar}]` {percent}%",
        "theme_sent": "✅ Lazurite Dream 💙 успешно загружена!",
        "reply_sent": "✅ Ответ отправлен пользователю",
        "reply_fail": "❌ Не удалось определить пользователя",
        "btn_themes": "📁 Темы",
        "btn_builder": "🎨 Билдер иконок",
        "btn_guide": "📖 Гайд на установку",
        "btn_support": "🆘 Поддержка",
        "btn_back": "◀️ Назад",
        "btn_download": "💙 Lazurite Dream",
        "btn_guide_short": "📖 Гайд",
        "btn_menu_short": "◀️ Меню",
        "btn_custom_color": "🎨 Свой цвет",
        "send_wallpaper": "🖼️ Отправьте изображение (обои), чтобы бот подобрал цвет иконок.\n\n(Отправьте фото в чат)",
        "wallpaper_received": "✅ Обои получены. Анализирую цвет...",
        "dominant_color": "🎨 Основной цвет: {color}\n🔄 Сдвиг оттенка: {shift}°\n🎨 Насыщенность иконок: {sat}%\n\n📝 Теперь введите название темы:",
        "error_no_image": "❌ Пожалуйста, отправьте изображение.",
    },
    "en": {
        "choose_language": "🌐 *Choose language:*",
        "welcome": "✨ *HuwiLabs Cloud* ✨\n\nWelcome to Huawei theme storage.\n\n👇 Choose action:",
        "themes_available": "🎨 Available themes:\n\n💙 Lazurite Dream",
        "guide": "📱 How to install Huawei theme\n\n1️⃣ Download .hwt\n2️⃣ Open Files → Downloads\n3️⃣ Copy to Huawei/Themes\n4️⃣ Open Themes → My themes\n5️⃣ Apply theme\n\n✅ Done!",
        "support_text": "🆘 *Support*\n\nWrite any message — it will be sent to admin.\n\nReply will come here.",
        "enter_theme_name": "📝 Enter theme name:\n\nExample: Magic Sunset",
        "theme_name_saved": "✅ Name: {name}\n\n🎨 Now choose a color:",
        "building_start": "🎨 Building theme «{name}» in {color}...\n\n⏳ Up to a minute",
        "building_icons": "🖌️ Recoloring icons...",
        "building_pack": "📦 Packing into .hwt...",
        "done": "✅ Done!\n\n📝 {name}\n🎨 {color}\n📦 Size: {size} KB\n📁 File: `{filename}`",
        "no_access": "❌ No access! Get from @crqckoff",
        "theme_not_found": "❌ Theme file not found!",
        "example_not_found": "❌ Example.hwt template not found!",
        "preparing": "📤 Preparing...",
        "packing": "📦 Packing...",
        "uploading": "🚀 Uploading...",
        "finalizing": "⚡ Finalizing...",
        "ready": "🎨 Ready!",
        "progress_bar": "`[{bar}]` {percent}%",
        "theme_sent": "✅ Lazurite Dream 💙 uploaded!",
        "reply_sent": "✅ Reply sent",
        "reply_fail": "❌ Cannot identify user",
        "btn_themes": "📁 Themes",
        "btn_builder": "🎨 Icon builder",
        "btn_guide": "📖 Installation guide",
        "btn_support": "🆘 Support",
        "btn_back": "◀️ Back",
        "btn_download": "💙 Lazurite Dream",
        "btn_guide_short": "📖 Guide",
        "btn_menu_short": "◀️ Menu",
        "btn_custom_color": "🎨 Custom color",
        "send_wallpaper": "🖼️ Send an image (wallpaper) to auto-detect icon color.\n\n(Send photo in chat)",
        "wallpaper_received": "✅ Wallpaper received. Analyzing color...",
        "dominant_color": "🎨 Dominant color: {color}\n🔄 Hue shift: {shift}°\n🎨 Icon saturation: {sat}%\n\n📝 Now enter theme name:",
        "error_no_image": "❌ Please send an image.",
    }
}

allowed_users_cache = {}
cache_time = 0

# Базовый оттенок лазуревых иконок (Hue ~200°)
BASE_HUE = 200

def get_optimized_color(image_bytes):
    """Возвращает оптимальный цвет для иконок (насыщенный, яркий) и сдвиг оттенка"""
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img.thumbnail((200, 200))
        pixels = list(img.getdata())
        # Ищем цвет с максимальной насыщенностью и достаточной яркостью
        best_color = None
        best_score = -1
        best_hue = 0
        for rgb in set(pixels):  # уникальные цвета для скорости
            r, g, b = rgb
            h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
            # Оценка: насыщенность * яркость (чем ярче и насыщеннее, тем лучше)
            score = s * v
            if score > best_score and v > 0.3 and s > 0.3:
                best_score = score
                best_color = rgb
                best_hue = h * 360
        if best_color is None:
            # Fallback: самый частый цвет
            color_counts = Counter(pixels)
            best_color = color_counts.most_common(1)[0][0]
            r, g, b = best_color
            h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
            best_hue = h * 360
        shift = (best_hue - BASE_HUE) % 360
        if shift > 180:
            shift -= 360
        # Дополнительно увеличиваем насыщенность иконок на 20% (но не выше 1)
        sat_boost = 1.2
        return best_color, best_hue, shift, sat_boost
    except Exception as e:
        print(f"Ошибка анализа: {e}")
        return None, None, None, None

def hue_shift_pixel_with_sat(r, g, b, shift_deg, sat_boost=1.0):
    h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
    h_deg = (h * 360 + shift_deg) % 360
    h = h_deg / 360
    s = min(1.0, s * sat_boost)
    r2, g2, b2 = colorsys.hsv_to_rgb(h, s, v)
    return int(r2 * 255), int(g2 * 255), int(b2 * 255)

def change_icon_hue_shift_advanced(image_bytes, shift_deg, sat_boost=1.0):
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        pixels = img.load()
        for y in range(img.height):
            for x in range(img.width):
                r, g, b, a = pixels[x, y]
                if a < 50:
                    continue
                h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
                if s > 0.05:  # даже слабонасыщенные меняем
                    new_r, new_g, new_b = hue_shift_pixel_with_sat(r, g, b, shift_deg, sat_boost)
                    pixels[x, y] = (new_r, new_g, new_b, a)
        output = io.BytesIO()
        img.save(output, format="PNG")
        return output.getvalue()
    except Exception as e:
        print(f"Ошибка: {e}")
        return None

def get_allowed_users():
    global allowed_users_cache, cache_time
    if time.time() - cache_time < 300:
        return allowed_users_cache
    try:
        response = requests.get(ALLOWED_USERS_URL, timeout=10)
        if response.status_code == 200:
            allowed_users = set()
            for line in response.text.strip().split('\n'):
                line = line.strip()
                if line and line.isdigit():
                    allowed_users.add(int(line))
            allowed_users_cache = allowed_users
            cache_time = time.time()
            print(f"✅ Загружено {len(allowed_users)} разрешённых пользователей")
            return allowed_users
    except Exception as e:
        print(f"⚠️ Ошибка: {e}")
    return allowed_users_cache

def is_allowed(user_id):
    return user_id in get_allowed_users()

user_theme_name = {}

def build_theme_with_shift(chat_id, theme_name, shift_deg, sat_boost, color_name, output_filename, lang="ru"):
    status_msg = bot.send_message(
        chat_id,
        TEXTS[lang]["building_start"].format(name=theme_name, color=color_name),
        parse_mode='Markdown'
    )
    try:
        if not os.path.exists(EXAMPLE_THEME):
            bot.edit_message_text(TEXTS[lang]["example_not_found"], chat_id, status_msg.message_id)
            return None
        if not os.path.exists(ICONS_ZIP):
            bot.edit_message_text(f"❌ Ошибка: {ICONS_ZIP} не найден!", chat_id, status_msg.message_id)
            return None

        with tempfile.TemporaryDirectory() as tmpdir:
            # Копируем шаблон
            template_path = os.path.join(tmpdir, "template.hwt")
            shutil.copy2(EXAMPLE_THEME, template_path)
            extract_dir = os.path.join(tmpdir, "extracted")
            os.makedirs(extract_dir)
            # Распаковываем без сжатия
            with zipfile.ZipFile(template_path, 'r') as zf:
                zf.extractall(extract_dir)

            # 1. Перекрашиваем иконки
            bot.edit_message_text(TEXTS[lang]["building_icons"], chat_id, status_msg.message_id, parse_mode='Markdown')
            with zipfile.ZipFile(ICONS_ZIP, 'r') as icons_zip:
                icon_files = [f for f in icons_zip.namelist() if f.lower().endswith('.png')]
                # Фильтруем служебные иконки
                filtered_icons = [f for f in icon_files if os.path.basename(f).lower() not in [i.lower() for i in IGNORE_ICONS]]
                skipped = len(icon_files) - len(filtered_icons)
                if skipped:
                    print(f"Пропущено {skipped} служебных иконок")
                if not filtered_icons:
                    bot.edit_message_text(f"❌ Нет иконок для перекраски!", chat_id, status_msg.message_id)
                    return None
                shifted_icons = {}
                for i, icon_name in enumerate(filtered_icons):
                    with icons_zip.open(icon_name) as f:
                        original = f.read()
                    shifted = change_icon_hue_shift_advanced(original, shift_deg, sat_boost)
                    if shifted:
                        # Нормализуем имя: нижний регистр, без пробелов и спецсимволов
                        base = os.path.basename(icon_name).lower()
                        clean = re.sub(r'[^a-z0-9._-]', '_', base)
                        shifted_icons[clean] = shifted
                    if (i+1) % 10 == 0:
                        try:
                            bot.edit_message_text(f"🖌️ {i+1}/{len(filtered_icons)}", chat_id, status_msg.message_id, parse_mode='Markdown')
                        except:
                            pass

            # Создаём новый файл icons (ZIP без сжатия, режим STORED)
            new_icons_path = os.path.join(extract_dir, "icons")
            with zipfile.ZipFile(new_icons_path, 'w', zipfile.ZIP_STORED) as zf:
                for name, data in shifted_icons.items():
                    zf.writestr(name, data)

            # 2. Создаём новый description.xml
            safe_theme_name = transliterate(theme_name).lower()
            desc_path = os.path.join(extract_dir, "description.xml")
            xml_content = f"""<HwTheme>
<title>{safe_theme_name}</title>
<title-cn>{safe_theme_name}</title-cn>
<author>HuwiLab</author>
<designer>HuwiLab</designer>
<screen>FHD</screen>
<version>1.0</version>
<font>Default</font>
<font-cn>默认</font-cn>
<theme-banner-show>true</theme-banner-show>
</HwTheme>"""
            with open(desc_path, 'w', encoding='utf-8') as f:
                f.write(xml_content)

            # 3. Упаковываем обратно в .hwt (без сжатия)
            bot.edit_message_text(TEXTS[lang]["building_pack"], chat_id, status_msg.message_id, parse_mode='Markdown')
            out_file = os.path.join(os.getcwd(), output_filename)
            with zipfile.ZipFile(out_file, 'w', zipfile.ZIP_STORED) as zf:
                for root, _, files in os.walk(extract_dir):
                    for file in files:
                        full = os.path.join(root, file)
                        arcname = os.path.relpath(full, extract_dir)
                        zf.write(full, arcname)

        file_size = os.path.getsize(out_file) / 1024
        with open(out_file, 'rb') as f:
            bot.send_document(
                chat_id,
                f,
                caption=TEXTS[lang]["done"].format(
                    name=theme_name,
                    color=color_name,
                    size=round(file_size, 1),
                    filename=output_filename
                ),
                reply_markup=main_menu(lang),
                parse_mode='Markdown'
            )
        os.remove(out_file)
        bot.delete_message(chat_id, status_msg.message_id)
        return True
    except Exception as e:
        bot.edit_message_text(f"❌ Ошибка:\n`{str(e)}`", chat_id, status_msg.message_id, parse_mode='Markdown')
        return None

def transliterate(text):
    mapping = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch', 'ъ': '',
        'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
        'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
        'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
        'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
        'Ф': 'F', 'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sch', 'Ъ': '',
        'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
    }
    result = []
    for ch in text:
        if ch in mapping:
            result.append(mapping[ch])
        elif ch.isalnum() or ch in (' ', '_', '-', '.'):
            result.append(ch)
        else:
            result.append('_')
    return ''.join(result).replace(' ', '_')

# ========== ПРЕДУСТАНОВЛЕННЫЕ ЦВЕТА ==========
HUE_SHIFTS = {
    "red": 160,
    "green": 280,
    "blue": 0,
    "purple": 70,
    "orange": 190,
    "pink": 130,
    "cyan": 340,
}
COLOR_NAMES = {
    "red": {"ru": "🔴 Красный", "en": "🔴 Red"},
    "green": {"ru": "🟢 Зелёный", "en": "🟢 Green"},
    "blue": {"ru": "🔵 Синий", "en": "🔵 Blue"},
    "purple": {"ru": "🟣 Фиолетовый", "en": "🟣 Purple"},
    "orange": {"ru": "🟠 Оранжевый", "en": "🟠 Orange"},
    "pink": {"ru": "🌸 Розовый", "en": "🌸 Pink"},
    "cyan": {"ru": "💎 Бирюзовый", "en": "💎 Cyan"},
}
COLOR_PREFIX = {
    "red": "R",
    "green": "G",
    "blue": "B",
    "purple": "P",
    "orange": "O",
    "pink": "Pk",
    "cyan": "C",
    "custom": "Cst"
}

def build_theme_preset(color_key, chat_id, theme_name, lang="ru"):
    shift_deg = HUE_SHIFTS.get(color_key, 0)
    color_name = COLOR_NAMES.get(color_key, {}).get(lang, color_key)
    prefix = COLOR_PREFIX.get(color_key, "X")
    random_digits = str(random.randint(10, 99))
    output_filename = f"Theme{prefix}{random_digits}.hwt"
    # Для предустановленных цветов sat_boost = 1.0 (без усиления насыщенности)
    return build_theme_with_shift(chat_id, theme_name, shift_deg, 1.0, color_name, output_filename, lang)

def build_theme_custom(chat_id, theme_name, shift_deg, sat_boost, color_hex, lang="ru"):
    color_name = f"🎨 Свой ({color_hex})"
    prefix = "Cst"
    random_digits = str(random.randint(10, 99))
    output_filename = f"Theme{prefix}{random_digits}.hwt"
    return build_theme_with_shift(chat_id, theme_name, shift_deg, sat_boost, color_name, output_filename, lang)

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
    kb.add(InlineKeyboardButton(TEXTS[lang]["btn_download"], callback_data='download_lazurite'))
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
    kb.add(
        InlineKeyboardButton(TEXTS[lang]["btn_guide_short"], callback_data='guide'),
        InlineKeyboardButton(TEXTS[lang]["btn_menu_short"], callback_data='back_to_menu')
    )
    return kb

def language_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton('🇷🇺 Русский', callback_data='lang_ru'),
        InlineKeyboardButton('🇬🇧 English', callback_data='lang_en')
    )
    return kb

def send_lazurite_theme(chat_id, lang="ru", message_id=None):
    if not os.path.exists(THEME_FILE):
        bot.send_message(chat_id, TEXTS[lang]["theme_not_found"], reply_markup=main_menu(lang))
        return
    prog = bot.send_message(chat_id, f"{TEXTS[lang]['preparing']}\n⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0%", parse_mode='Markdown')
    for p in range(0, 101, 10):
        filled = p // 10
        bar = "█" * filled + "⬜" * (10 - filled)
        if p == 0: s = TEXTS[lang]['preparing']
        elif p < 30: s = TEXTS[lang]['packing']
        elif p < 60: s = TEXTS[lang]['uploading']
        elif p < 90: s = TEXTS[lang]['finalizing']
        else: s = TEXTS[lang]['ready']
        try:
            bot.edit_message_text(f"{s}\n{TEXTS[lang]['progress_bar'].format(bar=bar, percent=p)}", chat_id, prog.message_id, parse_mode='Markdown')
        except:
            pass
        time.sleep(0.6)
    with open(THEME_FILE, 'rb') as f:
        bot.send_document(chat_id, f, caption=TEXTS[lang]["theme_sent"], reply_markup=after_download_menu(lang), parse_mode='Markdown')
    try:
        bot.delete_message(chat_id, prog.message_id)
    except:
        pass
    if message_id:
        try:
            bot.delete_message(chat_id, message_id)
        except:
            pass

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    lang = get_lang(user_id)
    if lang is None:
        bot.send_message(message.chat.id, TEXTS["ru"]["choose_language"], reply_markup=language_menu(), parse_mode='Markdown')
        return
    try:
        if len(message.text.split()) > 1 and message.text.split()[1] == 'download_lazurite':
            send_lazurite_theme(message.chat.id, lang)
            return
    except:
        pass
    bot.send_message(message.chat.id, TEXTS[lang]["welcome"], reply_markup=main_menu(lang), parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def language_callback(call):
    lang = call.data.split('_')[1]
    set_lang(call.from_user.id, lang)
    bot.edit_message_text(TEXTS[lang]["welcome"], call.message.chat.id, call.message.message_id, reply_markup=main_menu(lang), parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    lang = get_lang(user_id)
    if lang is None:
        lang = "ru"
    try:
        if call.data == 'themes':
            bot.edit_message_text(TEXTS[lang]["themes_available"], call.message.chat.id, call.message.message_id, reply_markup=themes_menu(lang), parse_mode='Markdown')
        elif call.data == 'builder':
            if not is_allowed(call.from_user.id):
                bot.answer_callback_query(call.id, TEXTS[lang]["no_access"], show_alert=True)
                return
            bot.edit_message_text("🎨 *Выберите вариант:*", call.message.chat.id, call.message.message_id, reply_markup=builder_menu(lang), parse_mode='Markdown')
        elif call.data == 'custom_color':
            msg = bot.send_message(call.message.chat.id, TEXTS[lang]["send_wallpaper"], parse_mode='Markdown')
            bot.register_next_step_handler(msg, process_wallpaper, call.message.chat.id, lang)
            bot.answer_callback_query(call.id)
        elif call.data.startswith('color_'):
            color = call.data.replace('color_', '')
            msg = bot.send_message(call.message.chat.id, TEXTS[lang]["enter_theme_name"], parse_mode='Markdown')
            bot.register_next_step_handler(msg, get_theme_name_for_preset, color, call.message.chat.id, lang)
        elif call.data == 'guide':
            bot.edit_message_text(TEXTS[lang]["guide"], call.message.chat.id, call.message.message_id, reply_markup=main_menu(lang), parse_mode='Markdown')
        elif call.data == 'download_lazurite':
            send_lazurite_theme(call.message.chat.id, lang, call.message.message_id)
        elif call.data == 'support':
            bot.edit_message_text(TEXTS[lang]["support_text"], call.message.chat.id, call.message.message_id, reply_markup=main_menu(lang), parse_mode='Markdown')
        elif call.data == 'back_to_menu':
            bot.edit_message_text(TEXTS[lang]["welcome"], call.message.chat.id, call.message.message_id, reply_markup=main_menu(lang), parse_mode='Markdown')
    except Exception as e:
        print(f"Ошибка: {e}")

def process_wallpaper(message, chat_id, lang):
    if not message.photo:
        bot.send_message(chat_id, TEXTS[lang]["error_no_image"], reply_markup=builder_menu(lang))
        return
    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    best_color, best_hue, shift, sat_boost = get_optimized_color(downloaded_file)
    if best_color is None:
        bot.send_message(chat_id, "❌ Не удалось определить цвет. Попробуйте другое изображение.", reply_markup=builder_menu(lang))
        return
    user_temp_data[chat_id] = {"shift": shift, "sat_boost": sat_boost, "rgb": best_color}
    color_hex = "#{:02x}{:02x}{:02x}".format(*best_color)
    sat_percent = int(sat_boost * 100)
    bot.send_message(chat_id, TEXTS[lang]["dominant_color"].format(color=color_hex, shift=round(shift, 1), sat=sat_percent), parse_mode='Markdown')
    msg = bot.send_message(chat_id, TEXTS[lang]["enter_theme_name"], parse_mode='Markdown')
    bot.register_next_step_handler(msg, get_theme_name_for_custom, chat_id, lang)

def get_theme_name_for_preset(message, color_key, chat_id, lang):
    theme_name = message.text.strip()
    if not theme_name:
        bot.send_message(chat_id, "❌ Название не может быть пустым.", reply_markup=builder_menu(lang))
        return
    build_theme_preset(color_key, chat_id, theme_name, lang)

def get_theme_name_for_custom(message, chat_id, lang):
    theme_name = message.text.strip()
    if not theme_name:
        bot.send_message(chat_id, "❌ Название не может быть пустым.", reply_markup=builder_menu(lang))
        return
    data = user_temp_data.get(chat_id)
    if not data:
        bot.send_message(chat_id, "❌ Ошибка: данные о цвете утеряны. Начните заново.", reply_markup=builder_menu(lang))
        return
    shift = data["shift"]
    sat_boost = data["sat_boost"]
    rgb = data["rgb"]
    color_hex = "#{:02x}{:02x}{:02x}".format(*rgb)
    build_theme_custom(chat_id, theme_name, shift, sat_boost, color_hex, lang)
    del user_temp_data[chat_id]

def forward_to_support(original_message, text_prefix=""):
    try:
        user = original_message.from_user
        user_info = f"👤 @{user.username}" if user.username else f"👤 {user.first_name} (ID: {user.id})"
        caption = f"{text_prefix}\n\n{user_info}\n📝 Сообщение:"
        if SUPPORT_ADMIN_ID:
            try:
                if original_message.text:
                    bot.send_message(SUPPORT_ADMIN_ID, f"{caption}\n\n{original_message.text}")
                elif original_message.photo:
                    bot.send_photo(SUPPORT_ADMIN_ID, original_message.photo[-1].file_id, caption=caption)
                elif original_message.document:
                    bot.send_document(SUPPORT_ADMIN_ID, original_message.document.file_id, caption=caption)
                else:
                    bot.send_message(SUPPORT_ADMIN_ID, f"{caption}\n[Сообщение другого типа]")
            except Exception as e:
                print(f"Ошибка админу: {e}")
        if SUPPORT_GROUP_ID:
            try:
                if original_message.text:
                    bot.send_message(SUPPORT_GROUP_ID, f"{caption}\n\n{original_message.text}")
                else:
                    bot.send_message(SUPPORT_GROUP_ID, caption)
            except Exception as e:
                print(f"Ошибка в группу: {e}")
        bot.reply_to(original_message, "📨 Сообщение отправлено в поддержку.")
    except Exception as e:
        print(f"Ошибка forward: {e}")

@bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'document', 'voice', 'video', 'audio', 'sticker'])
def handle_all_messages(message):
    if message.text and message.text.startswith('/'):
        return
    if message.from_user.id == SUPPORT_ADMIN_ID:
        return
    forward_to_support(message, "🆕 Новое обращение:")

@bot.message_handler(func=lambda message: message.from_user.id == SUPPORT_ADMIN_ID and message.reply_to_message)
def reply_to_user(message):
    try:
        original = message.reply_to_message
        if original and original.forward_from:
            user_id = original.forward_from.id
            bot.send_message(user_id, f"📨 *Ответ поддержки:*\n\n{message.text}", parse_mode='Markdown')
            bot.reply_to(message, "✅ Ответ отправлен")
        elif original and original.text and "ID:" in original.text:
            for part in original.text.split():
                if part.startswith("ID:") and part[3:].isdigit():
                    user_id = int(part[3:])
                    bot.send_message(user_id, f"📨 *Ответ поддержки:*\n\n{message.text}", parse_mode='Markdown')
                    bot.reply_to(message, "✅ Ответ отправлен")
                    return
        else:
            bot.reply_to(message, "❌ Не удалось определить пользователя.")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

def auto_ping():
    while True:
        try:
            requests.get(f'{SERVER_URL}/livez', timeout=10)
        except:
            pass
        time.sleep(240)

@app.route('/')
def health_check():
    return "Bot is running", 200

@app.route('/livez')
def live_check():
    return {"status": "ok"}, 200

def run_flask():
    import sys
    from io import StringIO
    old = sys.stdout
    sys.stdout = StringIO()
    try:
        port = int(os.environ.get('PORT', 8080))
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    finally:
        sys.stdout = old

if __name__ == '__main__':
    print("🤖 HuwiLabs bot v4.0 — без сжатия, игнор служебных иконок, усиление насыщенности")
    print("👤 Админ: 6778865145")
    if not os.path.exists(EXAMPLE_THEME):
        print(f"⚠️ Файл '{EXAMPLE_THEME}' не найден! Скопируйте рабочий Lazurite Dream.hwt в Example.hwt")
    if not os.path.exists(ICONS_ZIP):
        print(f"⚠️ Файл '{ICONS_ZIP}' не найден! Билдер не будет работать.")
    Thread(target=run_flask, daemon=True).start()
    Thread(target=auto_ping, daemon=True).start()
    print("✅ Бот запущен")
    bot.infinity_polling()
