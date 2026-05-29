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

# ========== ПОДДЕРЖКА ==========
SUPPORT_ADMIN_ID = 6778865145  # Твой user_id
SUPPORT_GROUP_ID = -1003763489689  # Сюда позже вставишь ID группы (например, -1001234567890)
# ИЛИ можно использовать ссылку:
SUPPORT_GROUP_LINK = 'https://t.me/podderzhkahuwi'  #Например: 'https://t.me/your_group'

allowed_users_cache = {}
cache_time = 0

# ПРАВИЛЬНЫЕ СДВИГИ
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
    "red": "🔴 Красный",
    "green": "🟢 Зелёный",
    "blue": "🔵 Синий",
    "purple": "🟣 Фиолетовый",
    "orange": "🟠 Оранжевый",
    "pink": "🌸 Розовый",
    "cyan": "💎 Бирюзовый",
}

# ========== ФУНКЦИЯ ПЕРЕСЫЛКИ В ПОДДЕРЖКУ ==========
def forward_to_support(original_message, text_prefix=""):
    """Пересылает сообщение админу и в группу поддержки"""
    try:
        user = original_message.from_user
        user_info = f"👤 @{user.username}" if user.username else f"👤 {user.first_name} (ID: {user.id})"

        caption = f"{text_prefix}\n\n{user_info}\n📝 Сообщение:"

        # Пересылаем админу
        if SUPPORT_ADMIN_ID:
            try:
                if original_message.text:
                    bot.send_message(SUPPORT_ADMIN_ID, f"{caption}\n\n{original_message.text}")
                elif original_message.photo:
                    bot.send_photo(SUPPORT_ADMIN_ID, original_message.photo[-1].file_id, caption=caption)
                elif original_message.document:
                    bot.send_document(SUPPORT_ADMIN_ID, original_message.document.file_id, caption=caption)
                elif original_message.voice:
                    bot.send_voice(SUPPORT_ADMIN_ID, original_message.voice.file_id, caption=caption)
                elif original_message.video:
                    bot.send_video(SUPPORT_ADMIN_ID, original_message.video.file_id, caption=caption)
                else:
                    bot.send_message(SUPPORT_ADMIN_ID, f"{caption}\n[Другой тип сообщения]")
            except Exception as e:
                print(f"Ошибка отправки админу: {e}")

        # Пересылаем в группу (если указана)
        if SUPPORT_GROUP_ID:
            try:
                if original_message.text:
                    bot.send_message(SUPPORT_GROUP_ID, f"{caption}\n\n{original_message.text}")
                elif original_message.photo:
                    bot.send_photo(SUPPORT_GROUP_ID, original_message.photo[-1].file_id, caption=caption)
                elif original_message.document:
                    bot.send_document(SUPPORT_GROUP_ID, original_message.document.file_id, caption=caption)
                elif original_message.voice:
                    bot.send_voice(SUPPORT_GROUP_ID, original_message.voice.file_id, caption=caption)
                elif original_message.video:
                    bot.send_video(SUPPORT_GROUP_ID, original_message.video.file_id, caption=caption)
                else:
                    bot.send_message(SUPPORT_GROUP_ID, f"{caption}\n[Другой тип сообщения]")
            except Exception as e:
                print(f"Ошибка отправки в группу: {e}")

        # Отправляем пользователю подтверждение
        bot.reply_to(original_message, "📨 Ваше сообщение отправлено в поддержку. Ответ придёт сюда, как только админ ответит.")

    except Exception as e:
        print(f"Ошибка forward_to_support: {e}")

def hue_shift_pixel(r, g, b, shift_deg):
    h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
    h_deg = (h * 360 + shift_deg) % 360
    h = h_deg / 360
    r2, g2, b2 = colorsys.hsv_to_rgb(h, s, v)
    return int(r2 * 255), int(g2 * 255), int(b2 * 255)

def change_icon_hue_shift(image_bytes, shift_deg):
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        pixels = img.load()
        for y in range(img.height):
            for x in range(img.width):
                r, g, b, a = pixels[x, y]
                if a < 50:
                    continue
                h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
                if s > 0.1:
                    new_r, new_g, new_b = hue_shift_pixel(r, g, b, shift_deg)
                    pixels[x, y] = (new_r, new_g, new_b, a)
        output = io.BytesIO()
        img.save(output, format="PNG")
        return output.getvalue()
    except Exception as e:
        print(f"Ошибка Hue Shift: {e}")
        return None

def generate_preview(theme_name, color_key, output_path):
    try:
        width, height = 1080, 1920
        img = Image.new('RGB', (width, height))
        draw = ImageDraw.Draw(img)
        for i in range(height):
            ratio = i / height
            r = int(20 + 50 * ratio)
            g = int(40 + 100 * ratio)
            b = int(100 + 155 * ratio)
            draw.line([(0, i), (width, i)], fill=(r, g, b))

        font_size = 90
        try:
            if FONT_PATH:
                font = ImageFont.truetype(FONT_PATH, font_size)
            else:
                font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()

        y = 250
        lines = theme_name.split('\n')
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            w = bbox[2] - bbox[0]
            x = (width - w) // 2
            draw.text((x, y), line, fill=(255, 255, 255), font=font)
            y += font_size + 20

        try:
            font_small = ImageFont.truetype(FONT_PATH, 40) if FONT_PATH else font
        except:
            font_small = font
        footer = "HuwiLabs • Exclusive Theme"
        bbox = draw.textbbox((0, 0), footer, font=font_small)
        w = bbox[2] - bbox[0]
        draw.text(((width - w) // 2, height - 100), footer, fill=(200, 200, 200), font=font_small)

        img.save(output_path, "PNG")
        return True
    except Exception as e:
        print(f"Ошибка генерации preview: {e}")
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
    return user_id in get_allowed_users()

user_theme_name = {}

def build_theme(color_key, chat_id, theme_name, message_id=None):
    shift_deg = HUE_SHIFTS.get(color_key, 0)
    color_name = COLOR_NAMES.get(color_key, color_key)

    status_msg = bot.send_message(
        chat_id,
        f"🎨 Начинаю сборку темы «{theme_name}» в цвете {color_name}...\n\n⏳ Это займёт до минуты",
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

        # 1. Обработка иконок
        bot.edit_message_text("🖌️ Перекрашиваю иконки...", chat_id, status_msg.message_id, parse_mode='Markdown')
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
                if (i+1) % 10 == 0:
                    try:
                        bot.edit_message_text(f"🖌️ Обработано {i+1}/{len(icon_files)} иконок", chat_id, status_msg.message_id, parse_mode='Markdown')
                    except:
                        pass

        icons_path = os.path.join(build_folder, "icons")
        with zipfile.ZipFile(icons_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for name, data in shifted_icons.items():
                zf.writestr(name, data)

        # 2. Копируем others.zip
        if os.path.exists(OTHERS_ZIP):
            bot.edit_message_text("📁 Копирую дополнительные файлы...", chat_id, status_msg.message_id, parse_mode='Markdown')
            with zipfile.ZipFile(OTHERS_ZIP, 'r') as others_zip:
                for item in others_zip.namelist():
                    if item.endswith('/'):
                        continue
                    with others_zip.open(item) as f:
                        data = f.read()
                    dst = os.path.join(build_folder, item)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    with open(dst, 'wb') as out:
                        out.write(data)
        else:
            bot.edit_message_text("⚠️ others.zip не найден", chat_id, status_msg.message_id, parse_mode='Markdown')

        # 3. Генерируем preview
        bot.edit_message_text("🖼️ Создаю обложку...", chat_id, status_msg.message_id, parse_mode='Markdown')
        preview_path = os.path.join(build_folder, "preview")
        generate_preview(theme_name, color_key, preview_path)

        # 4. description.xml
        desc_path = os.path.join(build_folder, "description.xml")
        xml = f"""<HwTheme>
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
            f.write(xml)

        # 5. Упаковка
        bot.edit_message_text("📦 Упаковываю в .hwt...", chat_id, status_msg.message_id, parse_mode='Markdown')
        safe_name = theme_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
        out_file = f"Theme_{safe_name}_{color_key}_{chat_id}.hwt"
        with zipfile.ZipFile(out_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(build_folder):
                for file in files:
                    full = os.path.join(root, file)
                    arc = os.path.relpath(full, build_folder)
                    zf.write(full, arc)
        shutil.rmtree(build_folder)

        with open(out_file, 'rb') as f:
            bot.send_document(
                chat_id,
                f,
                caption=f"✅ Готово!\n\n📝 {theme_name}\n🎨 {color_name}\n📦 Размер: {os.path.getsize(out_file) / 1024:.1f} KB",
                reply_markup=main_menu(),
                parse_mode='Markdown'
            )
        os.remove(out_file)
        bot.delete_message(chat_id, status_msg.message_id)
        return True
    except Exception as e:
        bot.edit_message_text(f"❌ Ошибка:\n`{str(e)}`", chat_id, status_msg.message_id, parse_mode='Markdown')
        return None

# ========== МЕНЮ С ПОДДЕРЖКОЙ ==========
def main_menu():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton('📁 Темы', callback_data='themes'))
    kb.add(InlineKeyboardButton('🎨 Билдер иконок', callback_data='builder'))
    kb.add(InlineKeyboardButton('📖 Гайд на установку', callback_data='guide'))
    kb.add(InlineKeyboardButton('🆘 Поддержка', callback_data='support'))
    return kb

def themes_menu():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton('💙 Lazurite Dream', callback_data='download_lazurite'))
    kb.add(InlineKeyboardButton('◀️ Назад', callback_data='back_to_menu'))
    return kb

def builder_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton('🔴', callback_data='color_red'),
        InlineKeyboardButton('🟢', callback_data='color_green'),
        InlineKeyboardButton('🔵', callback_data='color_blue'),
        InlineKeyboardButton('🟣', callback_data='color_purple'),
        InlineKeyboardButton('🟠', callback_data='color_orange'),
        InlineKeyboardButton('🌸', callback_data='color_pink'),
        InlineKeyboardButton('💎', callback_data='color_cyan'),
        InlineKeyboardButton('◀️ Назад', callback_data='back_to_menu')
    )
    return kb

def after_download_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton('📖 Гайд', callback_data='guide'),
        InlineKeyboardButton('◀️ Меню', callback_data='back_to_menu')
    )
    return kb

def send_lazurite_theme(chat_id, message_id=None):
    if not os.path.exists(THEME_FILE):
        bot.send_message(chat_id, "❌ Файл темы не найден!", reply_markup=main_menu())
        return
    prog = bot.send_message(chat_id, "📤 Подготовка...\n⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0%", parse_mode='Markdown')
    for p in range(0, 101, 10):
        filled = p // 10
        bar = "█" * filled + "⬜" * (10 - filled)
        if p == 0: s = "📤 Подготовка..."
        elif p < 30: s = "📦 Упаковка..."
        elif p < 60: s = "🚀 Загрузка..."
        elif p < 90: s = "⚡ Финализация..."
        else: s = "🎨 Готово!"
        try:
            bot.edit_message_text(f"{s}\n`[{bar}]` {p}%", chat_id, prog.message_id, parse_mode='Markdown')
        except:
            pass
        time.sleep(0.6)
    with open(THEME_FILE, 'rb') as f:
        bot.send_document(chat_id, f, caption="✅ Lazurite Dream 💙 успешно загружена!", reply_markup=after_download_menu(), parse_mode='Markdown')
    try:
        bot.delete_message(chat_id, prog.message_id)
    except:
        pass
    if message_id:
        try:
            bot.delete_message(chat_id, message_id)
        except:
            pass

GUIDE_TEXT = (
    "📱 Как установить тему Huawei\n\n"
    "1️⃣ Скачайте файл .hwt\n"
    "2️⃣ Откройте Файлы → Загрузки\n"
    "3️⃣ Скопируйте файл в папку Huawei/Themes\n"
    "4️⃣ Откройте Темы → Мои темы\n"
    "5️⃣ Нажмите на тему → Применить\n\n"
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
        "✨ *HuwiLabs Cloud* ✨\n\nДобро пожаловать в хранилище тем для Huawei.\n\n👇 Что желаете?",
        reply_markup=main_menu(),
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    try:
        if call.data == 'themes':
            bot.edit_message_text("🎨 Доступные темы:\n\n💙 Lazurite Dream", call.message.chat.id, call.message.message_id, reply_markup=themes_menu(), parse_mode='Markdown')
        elif call.data == 'builder':
            if not is_allowed(call.from_user.id):
                bot.answer_callback_query(call.id, "❌ Нет доступа! Приобретите у @crqckoff", show_alert=True)
                return
            msg = bot.send_message(call.message.chat.id, "📝 Введите название темы:\n\nПример: Magic Sunset", parse_mode='Markdown')
            bot.register_next_step_handler(msg, get_theme_name, call.message.chat.id, call.message.message_id)
        elif call.data.startswith('color_'):
            color = call.data.replace('color_', '')
            name = user_theme_name.get(call.message.chat.id, "Lazurite Dream")
            build_theme(color, call.message.chat.id, name, call.message.message_id)
        elif call.data == 'guide':
            bot.edit_message_text(GUIDE_TEXT, call.message.chat.id, call.message.message_id, reply_markup=main_menu(), parse_mode='Markdown')
        elif call.data == 'download_lazurite':
            send_lazurite_theme(call.message.chat.id, call.message.message_id)
        elif call.data == 'support':
            # Показываем инструкцию для поддержки
            bot.edit_message_text(
                "🆘 *Поддержка*\n\nПросто напишите любое сообщение в этот чат — оно будет отправлено администратору.\n\nАдминистратор ответит вам сюда.\n\n📌 *Вопросы по билдеру иконок:* только для разрешённых пользователей",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=main_menu(),
                parse_mode='Markdown'
            )
        elif call.data == 'back_to_menu':
            bot.edit_message_text("✨ *HuwiLabs Cloud* ✨\n\n👇 Выберите действие:", call.message.chat.id, call.message.message_id, reply_markup=main_menu(), parse_mode='Markdown')
    except Exception as e:
        print(f"Ошибка: {e}")

def get_theme_name(message, chat_id, original_id):
    name = message.text.strip()
    user_theme_name[chat_id] = name
    bot.send_message(chat_id, f"✅ Имя: {name}\n\n🎨 Теперь выберите цвет:", reply_markup=builder_menu(), parse_mode='Markdown')
    try:
        bot.delete_message(chat_id, original_id)
    except:
        pass

# ========== ОБРАБОТЧИК ЛЮБЫХ СООБЩЕНИЙ (ДЛЯ ПОДДЕРЖКИ) ==========
@bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'document', 'voice', 'video', 'audio', 'sticker'])
def handle_all_messages(message):
    # Игнорируем команды /start и т.д.
    if message.text and message.text.startswith('/'):
        return

    # Игнорируем сообщения от самого админа (чтобы не зациклилось)
    if message.from_user.id == SUPPORT_ADMIN_ID:
        return

    # Если пользователь не админ — пересылаем в поддержку
    forward_to_support(message, "🆕 Новое обращение в поддержку:")

# ========== АДМИН МОЖЕТ ОТВЕЧАТЬ В ЛС ПОЛЬЗОВАТЕЛЮ ==========
@bot.message_handler(func=lambda message: message.from_user.id == SUPPORT_ADMIN_ID and message.reply_to_message)
def reply_to_user(message):
    """Админ отвечает на сообщение пользователя через reply"""
    try:
        # Пытаемся достать user_id из reply_to_message
        original = message.reply_to_message
        if original and original.forward_from:
            user_id = original.forward_from.id
            bot.send_message(user_id, f"📨 *Ответ поддержки:*\n\n{message.text}", parse_mode='Markdown')
            bot.reply_to(message, "✅ Ответ отправлен пользователю")
        elif original and original.text and "ID:" in original.text:
            # Парсим user_id из текста
            for part in original.text.split():
                if part.startswith("ID:") and part[3:].isdigit():
                    user_id = int(part[3:])
                    bot.send_message(user_id, f"📨 *Ответ поддержки:*\n\n{message.text}", parse_mode='Markdown')
                    bot.reply_to(message, "✅ Ответ отправлен пользователю")
                    return
        else:
            bot.reply_to(message, "❌ Не удалось определить пользователя. Ответь на сообщение из очереди поддержки.")
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
    print("🤖 HuwiLabs bot v2.3 — добавлена поддержка")
    print("👤 Админ: 6778865145")
    Thread(target=run_flask, daemon=True).start()
    Thread(target=auto_ping, daemon=True).start()
    print("✅ Бот запущен")
    bot.infinity_polling()