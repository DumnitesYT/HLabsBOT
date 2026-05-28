import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os

# Замените на ваш токен
BOT_TOKEN = '8917439575:AAGiw58_prp8Urx3DcBmXkyVoCesYc6yK0k'
bot = telebot.TeleBot(BOT_TOKEN)

# Имя файла темы
THEME_FILE = 'Lazurite Dream.hwt'

# Создаем главное меню с кнопками
def main_menu():
    keyboard = InlineKeyboardMarkup(row_width=1)
    btn_themes = InlineKeyboardButton('📁 Темы', callback_data='themes')
    btn_guide = InlineKeyboardButton('📖 Гайд на темы', callback_data='guide')
    keyboard.add(btn_themes, btn_guide)
    return keyboard

# Меню выбора темы
def themes_menu():
    keyboard = InlineKeyboardMarkup(row_width=1)
    btn_theme = InlineKeyboardButton('✨ Lazurite Dream ✨', callback_data='download_lazurite')
    btn_back = InlineKeyboardButton('◀️ Назад', callback_data='back_to_menu')
    keyboard.add(btn_theme, btn_back)
    return keyboard

# Текст гайда
GUIDE_TEXT = (
    "📱 *Как установить тему .hwt на Huawei:*\n\n"
    "1️⃣ Скачайте файл с расширением `.hwt` через этого бота.\n"
    "2️⃣ Откройте приложение *Файлы* на вашем телефоне Huawei.\n"
    "3️⃣ Найдите скачанный файл (обычно в папке `Download`).\n"
    "4️⃣ Скопируйте или переместите файл в папку:\n"
    "   `Huawei/Themes` (если папки нет — создайте).\n"
    "5️⃣ Откройте приложение *Темы* (Themes).\n"
    "6️⃣ Перейдите в раздел *Мои темы* — ваша тема появится там.\n"
    "7️⃣ Нажмите на тему, чтобы применить.\n\n"
    "✅ Готово! Наслаждайтесь новым оформлением."
)

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(
        message.chat.id,
        "🌟 *Добро пожаловать в хранилище тем!*\n\nВыберите действие:",
        reply_markup=main_menu(),
        parse_mode='Markdown'
    )

# Обработчик нажатий на кнопки
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == 'themes':
        bot.edit_message_text(
            "🎨 *Выберите тему для скачивания:*",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=themes_menu(),
            parse_mode='Markdown'
        )
    elif call.data == 'guide':
        bot.edit_message_text(
            GUIDE_TEXT,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=main_menu(),
            parse_mode='Markdown'
        )
    elif call.data == 'download_lazurite':
        # Отправляем файл .hwt
        if os.path.exists(THEME_FILE):
            with open(THEME_FILE, 'rb') as f:
                bot.send_document(
                    call.message.chat.id,
                    f,
                    caption="✨ *Lazurite Dream* — ваша новая тема готова к установке!",
                    reply_markup=themes_menu(),
                    parse_mode='Markdown'
                )
        else:
            bot.answer_callback_query(
                call.id,
                "❌ Файл темы не найден! Сообщите администратору.",
                show_alert=True
            )
        # Не редактируем предыдущее сообщение, чтобы остаться в меню тем
    elif call.data == 'back_to_menu':
        bot.edit_message_text(
            "🌟 *Главное меню*\n\nВыберите действие:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=main_menu(),
            parse_mode='Markdown'
        )

# Запуск бота
if __name__ == '__main__':
    print("✅ Бот запущен и готов к работе!")
    # Проверяем, существует ли файл темы
    if not os.path.exists(THEME_FILE):
        print(f"⚠️ ВНИМАНИЕ: Файл '{THEME_FILE}' не найден в папке с ботом!")
        print(f"   Поместите файл темы в ту же директорию, что и скрипт.")
    bot.infinity_polling()