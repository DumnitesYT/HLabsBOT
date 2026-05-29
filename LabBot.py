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
from PIL import Image
import colorsys
import io

# Отключаем логи Flask
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

BOT_TOKEN = '8917439575:AAGiw58_prp8Urx3DcBmXkyVoCesYc6yK0k'
bot = telebot.TeleBot(BOT_TOKEN)

# Создаем Flask приложение для health check
app = Flask(__name__)

# ------------ НАСТРОЙКИ ------------
THEME_FILE = 'Lazurite Dream.hwt'
ICONS_ZIP = "icons.zip"
OTHERS_ZIP = "others.zip"

ALLOWED_USERS_URL = 'https://pastebin.com/raw/VbeVVK9T'
SERVER_URL = os.environ.get('RENDER_EXTERNAL_URL', 'http://localhost:8080')

# Кеш разрешенных пользователей
allowed_users_cache = {}
cache_time = 0

# РАСШИРЕННЫЙ ДИАПАЗОН ЛАЗУРЕВЫХ ЦВЕТОВ (Huawei + голубые оттенки)
# Стокувый цвет #4590D3 (HSV: 208, 67, 83)
# Добавляем больше оттенков синего и голубого
LAZURE_HUES = [208, 210, 205, 200, 195, 215, 220]  # разные оттенки лазури
HUE_RANGE = 25  # расширенный диапазон ±25°
SATURATION_MIN = 20  # снизил порог насыщенности

def is_stock_lazure_color(r, g, b):
    """Проверяет, является ли цвет лазуревым (расширенный диапазон)"""
    h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
    h_deg = h * 360
    s_percent = s * 100
    
    # Проверяем, что оттенок в диапазоне лазуревых (синий/голубой)
    # Диапазон от 170° (голубой) до 250° (синий)
    is_blue_hue = (150 <= h_deg <= 260)
    is_saturated = s_percent >= SATURATION_MIN
    
    return is_blue_hue and is_saturated

def get_allowed_users():
    """Получает список разрешенных user_id из Pastebin"""
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
        else:
            print(f"⚠️ Ошибка загрузки списка: {response.status_code}")
            return allowed_users_cache
    except Exception as e:
        print(f"⚠️ Ошибка: {e}")
        return allowed_users_cache

def is_allowed(user_id):
    allowed = get_allowed_users()
    return user_id in allowed

# ЦВЕТА ДЛЯ ПЕРЕКРАСКИ
COLOR_MAP = {
    "red": {"rgb": (255, 80, 80), "hex": "#FF5050", "name": "🔴 Красный"},
    "green": {"rgb": (80, 255, 120), "hex": "#50FF78", "name": "🟢 Зелёный"},
    "blue": {"rgb": (80, 160, 255), "hex": "#50A0FF", "name": "🔵 Синий"},
    "purple": {"rgb": (180, 80, 255), "hex": "#B450FF", "name": "🟣 Фиолетовый"},
    "orange": {"rgb": (255, 160, 80), "hex": "#FFA050", "name": "🟠 Оранжевый"},
    "pink": {"rgb": (255, 100, 180), "hex": "#FF64B4", "name": "🌸 Розовый"},
    "cyan": {"rgb": (80, 255, 220), "hex": "#50FFDC", "name": "💎 Бирюзовый"},
}

user_theme_name = {}

def change_icon_color_lazure_only(image_bytes, target_rgb):
    """Меняет цвет ТОЛЬКО лазуревых областей иконки"""
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        pixels = img.load()

        changed = 0
        total = 0

        for y in range(img.height):
            for x in range(img.width):
                r, g, b, a = pixels[x, y]
                if a < 50:
                    continue

                if is_stock_lazure_color(r, g, b):
                    total += 1
                    # Сохраняем яркость исходного пикселя
                    brightness = (r + g + b) / 3 / 255

                    new_r = int(target_rgb[0] * min(1, brightness * 1.3))
                    new_g = int(target_rgb[1] * min(1, brightness * 1.3))
                    new_b = int(target_rgb[2] * min(1, brightness * 1.3))

                    pixels[x, y] = (new_r, new_g, new_b, a)
                    changed += 1

        output = io.BytesIO()
        img.save(output, format="PNG")
        if total > 0:
            print(f"  Перекрашено {changed}/{total} пикселей ({changed*100//total}%)")
        return output.getvalue()
    except Exception as e:
        print(f"Ошибка перекраски: {e}")
        return None

def update_description_xml(build_folder, theme_name):
    """Создаёт description.xml с новым именем темы"""
    desc_file = os.path.join(build_folder, "description.xml")

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

    with open(desc_file, 'w', encoding='utf-8') as f:
        f.write(xml_content)
    print(f"✅ Создан description.xml с именем: {theme_name}")

def build_theme(color_key, chat_id, theme_name, message_id=None):
    """Собирает тему из архивов icons.zip и others.zip"""
    if color_key not in COLOR_MAP:
        return None

    target_rgb = COLOR_MAP[color_key]["rgb"]
    color_name = COLOR_MAP[color_key]["name"]

    status_msg = bot.send_message(
        chat_id,
        f"🎨 *Начинаю сборку темы «{theme_name}» в цвете {color_name}...*\n\n⏳ Это займёт несколько секунд",
        parse_mode='Markdown'
    )

    try:
        if not os.path.exists(ICONS_ZIP):
            bot.edit_message_text(
                f"❌ *Ошибка:* Архив `{ICONS_ZIP}` не найден!",
                chat_id,
                status_msg.message_id,
                parse_mode='Markdown'
            )
            return None

        # Создаём временную папку для сборки
        build_folder = f"theme_build_{chat_id}_{int(time.time())}"
        if os.path.exists(build_folder):
            shutil.rmtree(build_folder)
        os.makedirs(build_folder)

        # ========== 1. ОБРАБОТКА ICONS.ZIP ==========
        bot.edit_message_text(
            f"📦 *Обрабатываю иконки из {ICONS_ZIP}...*",
            chat_id,
            status_msg.message_id,
            parse_mode='Markdown'
        )

        icons_data = {}
        
        with zipfile.ZipFile(ICONS_ZIP, 'r') as icons_zip:
            icon_files = [f for f in icons_zip.namelist() if f.lower().endswith('.png')]
            
            if not icon_files:
                bot.edit_message_text(
                    f"❌ *Ошибка:* В архиве `{ICONS_ZIP}` нет PNG файлов!",
                    chat_id,
                    status_msg.message_id,
                    parse_mode='Markdown'
                )
                return None
            
            bot.edit_message_text(
                f"🎨 *Перекрашиваю {len(icon_files)} иконок в {color_name}...*\n(это может занять до минуты)",
                chat_id,
                status_msg.message_id,
                parse_mode='Markdown'
            )
            
            for i, icon_name in enumerate(icon_files):
                with icons_zip.open(icon_name) as f:
                    original_bytes = f.read()
                
                recolored_bytes = change_icon_color_lazure_only(original_bytes, target_rgb)
                if recolored_bytes:
                    icons_data[icon_name] = recolored_bytes
                
                # Показываем прогресс каждые 10 иконок
                if (i + 1) % 10 == 0 or (i + 1) == len(icon_files):
                    try:
                        bot.edit_message_text(
                            f"🎨 *Перекрашиваю иконки...* {i+1}/{len(icon_files)}\n\n✨ {color_name} цвет",
                            chat_id,
                            status_msg.message_id,
                            parse_mode='Markdown'
                        )
                    except:
                        pass
        
        # Создаём файл "icons" (архив с перекрашенными иконками)
        icons_archive_path = os.path.join(build_folder, "icons")
        with zipfile.ZipFile(icons_archive_path, 'w', zipfile.ZIP_DEFLATED) as icons_zip_out:
            for icon_name, icon_bytes in icons_data.items():
                icons_zip_out.writestr(icon_name, icon_bytes)
        
        print(f"✅ Создан файл icons с {len(icons_data)} иконками")

        # ========== 2. ОБРАБОТКА OTHERS.ZIP (ВСЕ ФАЙЛЫ) ==========
        if os.path.exists(OTHERS_ZIP):
            bot.edit_message_text(
                f"📁 *Копирую файлы из {OTHERS_ZIP}...*",
                chat_id,
                status_msg.message_id,
                parse_mode='Markdown'
            )
            
            with zipfile.ZipFile(OTHERS_ZIP, 'r') as others_zip:
                all_files = [f for f in others_zip.namelist() if not f.endswith('/')]
                
                for file_path in all_files:
                    # Извлекаем файл
                    with others_zip.open(file_path) as f:
                        file_bytes = f.read()
                    
                    # Определяем путь назначения
                    dst_path = os.path.join(build_folder, file_path)
                    
                    # Создаём папки если нужно
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                    
                    # Сохраняем файл
                    with open(dst_path, 'wb') as dst_file:
                        dst_file.write(file_bytes)
                    
                    print(f"  📄 {file_path}")
            
            print(f"✅ Скопировано {len(all_files)} файлов из others.zip")
        else:
            bot.edit_message_text(
                f"⚠️ *Предупреждение:* Архив `{OTHERS_ZIP}` не найден",
                chat_id,
                status_msg.message_id,
                parse_mode='Markdown'
            )
            time.sleep(1)

        # ========== 3. СОЗДАЁМ DESCRIPTION.XML ==========
        update_description_xml(build_folder, theme_name)

        # ========== 4. УПАКОВЫВАЕМ В .HWT ==========
        bot.edit_message_text(
            f"📦 *Упаковываю тему в .hwt...*",
            chat_id,
            status_msg.message_id,
            parse_mode='Markdown'
        )

        safe_name = theme_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
        output_file = f"Theme_{safe_name}_{color_key}_{chat_id}.hwt"

        with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(build_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, build_folder)
                    zipf.write(file_path, arcname)

        # Удаляем временную папку
        shutil.rmtree(build_folder)

        # Отправляем файл
        with open(output_file, 'rb') as f:
            bot.send_document(
                chat_id,
                f,
                caption=f"✅ *Готово!*\n\n🎨 Тема «{theme_name}» собрана в цвете {color_name}\n📦 Размер: {os.path.getsize(output_file) / 1024:.1f} KB",
                reply_markup=main_menu(),
                parse_mode='Markdown'
            )

        os.remove(output_file)

        try:
            bot.delete_message(chat_id, status_msg.message_id)
        except:
            pass

        return True

    except Exception as e:
        bot.edit_message_text(
            f"❌ *Ошибка:*\n`{str(e)}`",
            chat_id,
            status_msg.message_id,
            parse_mode='Markdown'
        )
        return None

# ========== МЕНЮ (всё то же самое) ==========
def main_menu():
    keyboard = InlineKeyboardMarkup(row_width=1)
    btn_themes = InlineKeyboardButton('📁 Темы', callback_data='themes')
    btn_builder = InlineKeyboardButton('🎨 Билдер иконок', callback_data='builder')
    btn_guide = InlineKeyboardButton('📖 Гайд на установку', callback_data='guide')
    keyboard.add(btn_themes, btn_builder, btn_guide)
    return keyboard

def themes_menu():
    keyboard = InlineKeyboardMarkup(row_width=1)
    btn_theme = InlineKeyboardButton('💙 Lazurite Dream', callback_data='download_lazurite')
    btn_back = InlineKeyboardButton('◀️ Назад', callback_data='back_to_menu')
    keyboard.add(btn_theme, btn_back)
    return keyboard

def builder_menu():
    keyboard = InlineKeyboardMarkup(row_width=2)
    btn_red = InlineKeyboardButton('🔴 Красный', callback_data='color_red')
    btn_green = InlineKeyboardButton('🟢 Зелёный', callback_data='color_green')
    btn_blue = InlineKeyboardButton('🔵 Синий', callback_data='color_blue')
    btn_purple = InlineKeyboardButton('🟣 Фиолетовый', callback_data='color_purple')
    btn_orange = InlineKeyboardButton('🟠 Оранжевый', callback_data='color_orange')
    btn_pink = InlineKeyboardButton('🌸 Розовый', callback_data='color_pink')
    btn_cyan = InlineKeyboardButton('💎 Бирюзовый', callback_data='color_cyan')
    btn_back = InlineKeyboardButton('◀️ Назад', callback_data='back_to_menu')
    keyboard.add(btn_red, btn_green, btn_blue, btn_purple, btn_orange, btn_pink, btn_cyan, btn_back)
    return keyboard

def after_download_menu():
    keyboard = InlineKeyboardMarkup(row_width=2)
    btn_guide = InlineKeyboardButton('📖 Гайд на установку', callback_data='guide')
    btn_back = InlineKeyboardButton('◀️ Назад в меню', callback_data='back_to_menu')
    keyboard.add(btn_guide, btn_back)
    return keyboard

def send_lazurite_theme(chat_id, message_id=None):
    if not os.path.exists(THEME_FILE):
        bot.send_message(chat_id, "❌ Файл темы не найден!", reply_markup=main_menu())
        return

    progress_msg = bot.send_message(chat_id, "📤 *Подготовка к отправке...*\n\n⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0%", parse_mode='Markdown')

    for percent in range(0, 101, 10):
        filled = int(percent / 10)
        empty = 10 - filled
        bar = "█" * filled + "⬜" * empty

        if percent == 0: status = "📤 Подготовка..."
        elif percent < 30: status = "📦 Упаковка..."
        elif percent < 60: status = "🚀 Загрузка..."
        elif percent < 90: status = "⚡ Финализация..."
        else: status = "🎨 Применяем магию..."

        try:
            bot.edit_message_text(f"{status}\n\n`[{bar}]` {percent}%\n\n✨ *Lazurite Dream* подготавливается!", chat_id, progress_msg.message_id, parse_mode='Markdown')
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
    "📱 *Как установить тему .hwt на Huawei:*\n\n"
    "1️⃣ Скачайте файл темы с расширением `.hwt` через этого бота.\n"
    "2️⃣ Откройте приложение *Файлы* на вашем телефоне Huawei.\n"
    "3️⃣ Найдите скачанный файл (обычно в папке `Download`).\n"
    "4️⃣ Скопируйте или переместите файл в папку:\n"
    "   `Huawei/Themes` (если папки нет — создайте).\n"
    "5️⃣ Откройте приложение *Темы* (Themes).\n"
    "6️⃣ Перейдите в раздел *Мои темы* — ваша тема появится там.\n"
    "7️⃣ Нажмите на тему, чтобы применить.\n\n"
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
    bot.send_message(message.chat.id, "🌟 *HuwiLabs Cloud*\n\n📁 Хранилище тем для Huawei\n\nВыберите действие:", reply_markup=main_menu(), parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    try:
        if call.data == 'themes':
            bot.edit_message_text("🎨 *Доступные темы:*\n\nВыберите тему для скачивания:", call.message.chat.id, call.message.message_id, reply_markup=themes_menu(), parse_mode='Markdown')

        elif call.data == 'builder':
            if not is_allowed(call.from_user.id):
                bot.answer_callback_query(
                    call.id,
                    "❌ У вас нет доступа к билдеру иконок!\n\nПриобретите доступ у @crqckoff",
                    show_alert=True
                )
                return

            msg = bot.send_message(
                call.message.chat.id,
                "📝 *Введите название темы*\n\nПример: `Nice Theme`\n\nПосле ввода названия выберите цвет:",
                parse_mode='Markdown'
            )
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
            bot.edit_message_text("🌟 *HuwiLabs Cloud*\n\n📁 Хранилище тем для Huawei\n\nВыберите действие:", call.message.chat.id, call.message.message_id, reply_markup=main_menu(), parse_mode='Markdown')

    except Exception as e:
        print(f"Ошибка: {e}")

def get_theme_name(message, chat_id, original_message_id):
    theme_name = message.text.strip()
    user_theme_name[chat_id] = theme_name

    bot.send_message(
        chat_id,
        f"✅ *Имя темы:* «{theme_name}»\n\n🎨 Теперь выберите цвет:",
        reply_markup=builder_menu(),
        parse_mode='Markdown'
    )

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
    print("🤖 HuwiLabs bot: Running!")
    print(f"👤 Создатель: @crqckoff")

    if not os.path.exists(THEME_FILE):
        print(f"⚠️ Файл '{THEME_FILE}' не найден!")
    else:
        print(f"✅ Файл темы найден")

    if not os.path.exists(ICONS_ZIP):
        print(f"⚠️ Архив '{ICONS_ZIP}' не найден!")
    else:
        print(f"✅ Архив иконок найден")

    if not os.path.exists(OTHERS_ZIP):
        print(f"⚠️ Архив '{OTHERS_ZIP}' не найден")
    else:
        print(f"✅ Архив others найден")

    Thread(target=run_flask, daemon=True).start()
    Thread(target=auto_ping, daemon=True).start()

    print("✅ Бот запущен!")
    bot.infinity_polling()
