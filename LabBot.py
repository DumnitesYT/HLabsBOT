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
import math

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

BOT_TOKEN = '8917439575:AAGiw58_prp8Urx3DcBmXkyVoCesYc6yK0k'
bot = telebot.TeleBot(BOT_TOKEN)

app = Flask(__name__)

# ------------ НАСТРОЙКИ ------------
THEME_FILE = 'Lazurite Dream.hwt'
ICONS_ZIP = "icons.zip"
OTHERS_ZIP = "others.zip"
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
if not os.path.exists(FONT_PATH):
    FONT_PATH = None

ALLOWED_USERS_URL = 'https://pastebin.com/raw/VbeVVK9T'
SERVER_URL = os.environ.get('RENDER_EXTERNAL_URL', 'http://localhost:8080')

allowed_users_cache = {}
cache_time = 0

# Хеш оттенков для сдвига (Hue Shift)
def get_hue_shift(color_key):
    """Возвращает угол сдвига оттенка для каждого цвета (в градусах)"""
    shifts = {
        "red": 0,        # красный (оставляем как есть, меняем только синие области)
        "green": 80,     # сдвиг в зелёный
        "blue": 0,       # синий (оставляем)
        "purple": 140,   # сдвиг в фиолетовый
        "orange": 30,    # сдвиг в оранжевый
        "pink": 320,     # сдвиг в розовый
        "cyan": 180,     # сдвиг в бирюзовый
    }
    return shifts.get(color_key, 0)

def hue_shift_pixel(r, g, b, shift_deg):
    """Сдвигает оттенок пикселя на заданный угол (в градусах)"""
    h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
    h_deg = (h * 360 + shift_deg) % 360
    h = h_deg / 360
    r2, g2, b2 = colorsys.hsv_to_rgb(h, s, v)
    return int(r2 * 255), int(g2 * 255), int(b2 * 255)

def change_icon_hue_shift(image_bytes, shift_deg):
    """Меняет оттенок ВСЕХ не-нейтральных цветов иконки"""
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        pixels = img.load()

        for y in range(img.height):
            for x in range(img.width):
                r, g, b, a = pixels[x, y]
                if a < 50:
                    continue

                # Проверяем, что цвет не чёрный/белый/серый (имеет насыщенность)
                h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
                if s > 0.1:  # если есть насыщенность
                    new_r, new_g, new_b = hue_shift_pixel(r, g, b, shift_deg)
                    pixels[x, y] = (new_r, new_g, new_b, a)

        output = io.BytesIO()
        img.save(output, format="PNG")
        return output.getvalue()
    except Exception as e:
        print(f"Ошибка Hue Shift: {e}")
        return None

def generate_preview(theme_name, color_key, output_path):
    """Генерирует красивое preview с названием темы"""
    try:
        # Размер preview Huawei Themes (обычно 1080x1920 или 720x1280)
        width, height = 1080, 1920

        # Создаём градиентный фон
        img = Image.new('RGB', (width, height))
        draw = ImageDraw.Draw(img)

        # Градиент от тёмно-синего к лазурному
        for i in range(height):
            ratio = i / height
            r = int(20 + 50 * ratio)
            g = int(40 + 100 * ratio)
            b = int(100 + 155 * ratio)
            draw.line([(0, i), (width, i)], fill=(r, g, b))

        # Добавляем декоративные круги
        for size, opacity in [(400, 30), (600, 20), (800, 15)]:
            circle_color = (100, 180, 255, opacity)
            # Рисуем круг (через отдельный слой, упрощённо)

        # Загружаем шрифт
        font_size = 80
        font = None
        if FONT_PATH and os.path.exists(FONT_PATH):
            font = ImageFont.truetype(FONT_PATH, font_size)
        else:
            font = ImageFont.load_default()

        # Название темы с отступом сверху (300px)
        y_position = 300
        for line in theme_name.split('\n'):
            # Получаем размер текста
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x_position = (width - text_width) // 2
            draw.text((x_position, y_position), line, fill=(255, 255, 255), font=font)
            y_position += font_size + 20

        # Добавляем подпись внизу
        font_small = ImageFont.truetype(FONT_PATH, 30) if FONT_PATH else font
        footer_text = "HuwiLabs • Exclusive Theme"
        bbox = draw.textbbox((0, 0), footer_text, font=font_small)
        footer_width = bbox[2] - bbox[0]
        draw.text(((width - footer_width) // 2, height - 80), footer_text, fill=(200, 200, 200), font=font_small)

        # Сохраняем (без расширения, как требует Huawei)
        img.save(output_path, "PNG")
        print(f"✅ Сгенерировано preview: {output_path}")
        return True
    except Exception as e:
        print(f"❌ Ошибка генерации preview: {e}")
        return False

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
            print(f"✅ Загружено {len(allowed_users)} разрешенных пользователей")
            return allowed_users
    except Exception as e:
        print(f"⚠️ Ошибка: {e}")
    return allowed_users_cache

def is_allowed(user_id):
    allowed = get_allowed_users()
    return user_id in allowed

COLOR_NAMES = {
    "red": "🔴 Красный",
    "green": "🟢 Зелёный",
    "blue": "🔵 Синий",
    "purple": "🟣 Фиолетовый",
    "orange": "🟠 Оранжевый",
    "pink": "🌸 Розовый",
    "cyan": "💎 Бирюзовый",
}

user_theme_name = {}

def build_theme(color_key, chat_id, theme_name, message_id=None):
    shift_deg = get_hue_shift(color_key)
    color_name = COLOR_NAMES.get(color_key, color_key)

    status_msg = bot.send_message(
        chat_id,
        f"🎨 *Начинаю сборку темы*\n\n📝 Имя: `{theme_name}`\n🎨 Цвет: {color_name}\n🔄 Сдвиг оттенка: {shift_deg}°\n\n⏳ Это займёт до минуты...",
        parse_mode='Markdown'
    )

    try:
        if not os.path.exists(ICONS_ZIP):
            bot.edit_message_text(f"❌ Ошибка: {ICONS_ZIP} не найден!", chat_id, status_msg.message_id)
            return None

        build_folder = f"theme_build_{chat_id}_{int(time.time())}"
        if os.path.exists(build_folder):
            shutil.rmtree(build_folder)
        os.makedirs(build_folder)

        # ===== 1. ОБРАБОТКА ICONS.ZIP (Hue Shift) =====
        bot.edit_message_text("🖌️ *Применяю сдвиг оттенка к иконкам...*", chat_id, status_msg.message_id, parse_mode='Markdown')

        with zipfile.ZipFile(ICONS_ZIP, 'r') as icons_zip:
            icon_files = [f for f in icons_zip.namelist() if f.lower().endswith('.png')]

            if not icon_files:
                bot.edit_message_text(f"❌ В {ICONS_ZIP} нет PNG!", chat_id, status_msg.message_id)
                return None

            shifted_icons = {}
            for i, icon_name in enumerate(icon_files):
                with icons_zip.open(icon_name) as f:
                    original = f.read()
                shifted = change_icon_hue_shift(original, shift_deg)
                if shifted:
                    shifted_icons[icon_name] = shifted
                if (i + 1) % 10 == 0:
                    try:
                        bot.edit_message_text(f"🖌️ *Обработано {i+1}/{len(icon_files)} иконок*", chat_id, status_msg.message_id, parse_mode='Markdown')
                    except:
                        pass

        # Создаём файл "icons"
        icons_archive_path = os.path.join(build_folder, "icons")
        with zipfile.ZipFile(icons_archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for name, data in shifted_icons.items():
                zipf.writestr(name, data)

        # ===== 2. КОПИРУЕМ ФАЙЛЫ ИЗ OTHERS.ZIP =====
        if os.path.exists(OTHERS_ZIP):
            bot.edit_message_text("📁 *Копирую остальные файлы...*", chat_id, status_msg.message_id, parse_mode='Markdown')

            with zipfile.ZipFile(OTHERS_ZIP, 'r') as others_zip:
                for item in others_zip.namelist():
                    if item.endswith('/'):
                        continue
                    with others_zip.open(item) as f:
                        file_data = f.read()
                    dst_path = os.path.join(build_folder, item)
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                    with open(dst_path, 'wb') as dst:
                        dst.write(file_data)
                    print(f"  📄 {item}")
        else:
            bot.edit_message_text("⚠️ others.zip не найден", chat_id, status_msg.message_id, parse_mode='Markdown')

        # ===== 3. ГЕНЕРАЦИЯ PREVIEW =====
        bot.edit_message_text("🖼️ *Генерирую обложку темы...*", chat_id, status_msg.message_id, parse_mode='Markdown')

        preview_path = os.path.join(build_folder, "preview")
        generate_preview(theme_name, color_key, preview_path)

        # ===== 4. СОЗДАЁМ DESCRIPTION.XML =====
        desc_path = os.path.join(build_folder, "description.xml")
        xml_content = f"""<HwTheme>
<title>{theme_name}</title>
<title-cn>{theme_name}</title-cn>
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

        # ===== 5. УПАКОВКА В .HWT =====
        bot.edit_message_text("📦 *Упаковываю в .hwt...*", chat_id, status_msg.message_id, parse_mode='Markdown')

        safe_name = theme_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
        output_file = f"Theme_{safe_name}_{color_key}_{chat_id}.hwt"

        with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(build_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, build_folder)
                    zipf.write(file_path, arcname)

        shutil.rmtree(build_folder)

        with open(output_file, 'rb') as f:
            bot.send_document(
                chat_id,
                f,
                caption=f"✨ *«{theme_name}» готова!*\n\n🎨 Цвет: {color_name}\n🔄 Сдвиг оттенка: {shift_deg}°\n📦 Размер: {os.path.getsize(output_file) / 1024:.1f} KB",
                reply_markup=main_menu(),
                parse_mode='Markdown'
            )

        os.remove(output_file)
        bot.delete_message(chat_id, status_msg.message_id)
        return True

    except Exception as e:
        bot.edit_message_text(f"❌ *Ошибка:*\n`{str(e)}`", chat_id, status_msg.message_id, parse_mode='Markdown')
        return None

# ========== КРАСИВОЕ МЕНЮ ==========
def main_menu():
    keyboard = InlineKeyboardMarkup(row_width=1)
    btn_themes = InlineKeyboardButton('📁📂 Темы', callback_data='themes')
    btn_builder = InlineKeyboardButton('🎨✨ Билдер иконок', callback_data='builder')
    btn_guide = InlineKeyboardButton('📖❓ Гайд на установку', callback_data='guide')
    keyboard.add(btn_themes, btn_builder, btn_guide)
    return keyboard

def themes_menu():
    keyboard = InlineKeyboardMarkup(row_width=1)
    btn_theme = InlineKeyboardButton('💙✨ Lazurite Dream', callback_data='download_lazurite')
    btn_back = InlineKeyboardButton('◀️🔙 Назад', callback_data='back_to_menu')
    keyboard.add(btn_theme, btn_back)
    return keyboard

def builder_menu():
    keyboard = InlineKeyboardMarkup(row_width=2)
    btn_red = InlineKeyboardButton('🔴', callback_data='color_red')
    btn_green = InlineKeyboardButton('🟢', callback_data='color_green')
    btn_blue = InlineKeyboardButton('🔵', callback_data='color_blue')
    btn_purple = InlineKeyboardButton('🟣', callback_data='color_purple')
    btn_orange = InlineKeyboardButton('🟠', callback_data='color_orange')
    btn_pink = InlineKeyboardButton('🌸', callback_data='color_pink')
    btn_cyan = InlineKeyboardButton('💎', callback_data='color_cyan')
    btn_back = InlineKeyboardButton('◀️ Назад', callback_data='back_to_menu')
    keyboard.add(btn_red, btn_green, btn_blue, btn_purple, btn_orange, btn_pink, btn_cyan, btn_back)
    return keyboard

def after_download_menu():
    keyboard = InlineKeyboardMarkup(row_width=2)
    btn_guide = InlineKeyboardButton('📖 Гайд', callback_data='guide')
    btn_back = InlineKeyboardButton('◀️ Меню', callback_data='back_to_menu')
    keyboard.add(btn_guide, btn_back)
    return keyboard

def send_lazurite_theme(chat_id, message_id=None):
    if not os.path.exists(THEME_FILE):
        bot.send_message(chat_id, "❌ Файл темы не найден!", reply_markup=main_menu())
        return
    progress_msg = bot.send_message(chat_id, "📤 *Подготовка...*\n\n⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0%", parse_mode='Markdown')
    for percent in range(0, 101, 10):
        filled = int(percent / 10)
        empty = 10 - filled
        bar = "█" * filled + "⬜" * empty
        if percent == 0: status = "📤 Подготовка..."
        elif percent < 30: status = "📦 Упаковка..."
        elif percent < 60: status = "🚀 Загрузка..."
        elif percent < 90: status = "⚡ Финализация..."
        else: status = "🎨 Готово!"
        try:
            bot.edit_message_text(f"{status}\n\n`[{bar}]` {percent}%", chat_id, progress_msg.message_id, parse_mode='Markdown')
        except:
            pass
        time.sleep(0.6)
    with open(THEME_FILE, 'rb') as f:
        bot.send_document(chat_id, f, caption="✅ *Lazurite Dream 💙* успешно загружена!", reply_markup=after_download_menu(), parse_mode='Markdown')
    try:
        bot.delete_message(chat_id, progress_msg.message_id)
    except:
        pass
    if message_id:
        try:
            bot.delete_message(chat_id, message_id)
        except:
            pass

GUIDE_TEXT = (
    "📱 *✨ Как установить тему Huawei ✨*\n\n"
    "1️⃣ Скачайте файл `.hwt`\n"
    "2️⃣ Откройте «Файлы» → «Загрузки»\n"
    "3️⃣ Скопируйте файл в `Huawei/Themes`\n"
    "4️⃣ Откройте «Темы» → «Мои темы»\n"
    "5️⃣ Нажмите на тему → «Применить»\n\n"
    "✅ Готово!"
)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        if len(message.text.split()) > 1 and message.text.split()[1] == 'download_lazurite':
            send_lazurite_theme(message.chat.id)
            return
    except:
        pass
    bot.send_message(
        message.chat.id,
        "🌟 *HuwiLabs Cloud*\n\n┌─────────────────────┐\n│  📁 Хранилище тем   │\n│  🎨 Билдер иконок   │\n│  📖 Гайд по установке│\n└─────────────────────┘\n\n👇 *Выберите действие:*",
        reply_markup=main_menu(),
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    try:
        if call.data == 'themes':
            bot.edit_message_text("🎨 *Доступные темы:*\n\n💙✨ Lazurite Dream", call.message.chat.id, call.message.message_id, reply_markup=themes_menu(), parse_mode='Markdown')
        elif call.data == 'builder':
            if not is_allowed(call.from_user.id):
                bot.answer_callback_query(call.id, "❌ Нет доступа! @crqckoff", show_alert=True)
                return
            msg = bot.send_message(call.message.chat.id, "📝 *✨ Введите название темы:*\n\nПример: `Magic Sunset`\n\n(можно на русском)", parse_mode='Markdown')
            bot.register_next_step_handler(msg, get_theme_name, call.message.chat.id, call.message.message_id)
        elif call.data.startswith('color_'):
            color = call.data.replace('color_', '')
            theme_name = user_theme_name.get(call.message.chat.id, "Lazurite Dream")
            build_theme(color, call.message.chat.id, theme_name, call.message.message_id)
        elif call.data == 'guide':
            bot.edit_message_text(GUIDE_TEXT, call.message.chat.id, call.message.message_id, reply_markup=main_menu(), parse_mode='Markdown')
        elif call.data == 'download_lazurite':
            send_lazurite_theme(call.message.chat.id, call.message.message_id)
        elif call.data == 'back_to_menu':
            bot.edit_message_text("🌟 *HuwiLabs Cloud*\n\n👇 *Выберите действие:*", call.message.chat.id, call.message.message_id, reply_markup=main_menu(), parse_mode='Markdown')
    except Exception as e:
        print(f"Ошибка: {e}")

def get_theme_name(message, chat_id, original_message_id):
    theme_name = message.text.strip()
    user_theme_name[chat_id] = theme_name
    bot.send_message(chat_id, f"✅ *Имя:* «{theme_name}»\n\n🎨 *Теперь выберите цвет сдвига оттенка:*\n\n(красный/зелёный/синий/фиолетовый/оранжевый/розовый/бирюзовый)", reply_markup=builder_menu(), parse_mode='Markdown')
    try:
        bot.delete_message(chat_id, original_message_id)
    except:
        pass

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
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    try:
        port = int(os.environ.get('PORT', 8080))
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    finally:
        sys.stdout = old_stdout

if __name__ == '__main__':
    print("🤖 HuwiLabs bot v2.0 — Hue Shift Edition")
    print("👤 Создатель: @crqckoff")
    print("✨ Новая функция: сдвиг оттенка (Hue Shift) + генерация preview")

    if not os.path.exists(THEME_FILE):
        print(f"⚠️ Файл '{THEME_FILE}' не найден!")
    if not os.path.exists(ICONS_ZIP):
        print(f"⚠️ Архив '{ICONS_ZIP}' не найден!")
    if not os.path.exists(OTHERS_ZIP):
        print(f"⚠️ Архив '{OTHERS_ZIP}' не найден!")

    Thread(target=run_flask, daemon=True).start()
    Thread(target=auto_ping, daemon=True).start()

    print("✅ Бот запущен!")
    bot.infinity_polling()