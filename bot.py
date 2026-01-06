import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters
)
from config import Config
from database import Database
import html
import json

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация базы данных
db = Database(Config.DATABASE_URL)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    welcome_text = (
        "👋 <b>Привет! Я бот для анонимных вопросов</b>\n\n"
        "📝 <b>Как это работает:</b>\n"
        "1. Напишите свой вопрос здесь\n"
        "2. Администратор получит его анонимно\n"
        "3. Администратор ответит вам здесь же\n\n"
        "❗ <b>Ваш вопрос и ответ будут полностью анонимными!</b>\n\n"
        "Просто напишите свой вопрос в этот чат..."
    )
    
    await update.message.reply_html(welcome_text)
    
    # Отправляем уведомление админам о новом пользователе
    if Config.ADMIN_IDS:
        admin_text = f"🆕 Новый пользователь запустил бота\nID: {user.id}"
        for admin_id in Config.ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=admin_text
                )
            except Exception as e:
                logger.error(f"Не удалось уведомить админа {admin_id}: {e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = (
        "❓ <b>Помощь</b>\n\n"
        "Просто напишите свой вопрос в этот чат, и он будет переслан администраторам.\n"
        "Администраторы увидят только текст вопроса, без вашего имени.\n"
        "Ответ придет вам сюда же.\n\n"
        "📌 <b>Команды:</b>\n"
        "/start - Начало работы\n"
        "/help - Эта справка\n"
        "/cancel - Отменить текущее действие\n\n"
        "💡 <b>Совет:</b> Формулируйте вопрос четко и подробно."
    )
    await update.message.reply_html(help_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений от пользователей"""
    user = update.effective_user
    message = update.message
    
    # Если сообщение от админа - игнорируем (админы отвечают через reply)
    if user.id in Config.ADMIN_IDS:
        return
    
    # Сохраняем вопрос в БД
    question_id = db.save_question(
        user_id=user.id,
        message_id=message.message_id,
        question_text=message.text
    )
    
    if not question_id:
        await message.reply_text("❌ Произошла ошибка при сохранении вопроса. Попробуйте позже.")
        return
    
    # Формируем сообщение для админов
    admin_text = (
        f"❓ <b>Новый анонимный вопрос</b> (ID: {question_id})\n\n"
        f"{html.escape(message.text)}\n\n"
        f"<i>Чтобы ответить, просто reply на это сообщение</i>"
    )
    
    # Создаем клавиатуру для быстрых действий
    keyboard = [
        [
            InlineKeyboardButton("📝 Ответить", callback_data=f"reply_{question_id}"),
            InlineKeyboardButton("👁️ Просмотрено", callback_data=f"seen_{question_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем вопрос всем админам
    sent_to_admins = []
    for admin_id in Config.ADMIN_IDS:
        try:
            admin_message = await context.bot.send_message(
                chat_id=admin_id,
                text=admin_text,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            
            # Сохраняем ID сообщения у админа
            db.save_admin_message_id(question_id, admin_message.message_id)
            sent_to_admins.append(admin_id)
            
        except Exception as e:
            logger.error(f"Не удалось отправить вопрос админу {admin_id}: {e}")
    
    if sent_to_admins:
        # Подтверждаем пользователю
        await message.reply_text(
            "✅ Ваш вопрос отправлен администраторам анонимно.\n"
            "Ожидайте ответа здесь же в этом чате."
        )
    else:
        await message.reply_text("❌ Не удалось отправить вопрос. Администраторы недоступны.")

async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ответов админов (reply на сообщение)"""
    user = update.effective_user
    
    # Проверяем, что это админ
    if user.id not in Config.ADMIN_IDS:
        return
    
    # Проверяем, что это reply на сообщение
    if not update.message.reply_to_message:
        return
    
    admin_message_id = update.message.reply_to_message.message_id
    answer_text = update.message.text
    
    # Ищем вопрос по ID сообщения админа
    question = db.get_user_by_admin_message(admin_message_id)
    
    if not question:
        await update.message.reply_text("❌ Не удалось найти вопрос. Возможно, он был удален.")
        return
    
    # Отправляем ответ пользователю
    try:
        await context.bot.send_message(
            chat_id=question['user_id'],
            text=f"📨 <b>Ответ на ваш вопрос:</b>\n\n{html.escape(answer_text)}",
            parse_mode='HTML'
        )
        
        # Отмечаем в БД как отвеченный
        db.mark_as_answered(question['id'], answer_text)
        
        # Подтверждаем админу
        await update.message.reply_text(
            f"✅ Ответ отправлен пользователю (Вопрос ID: {question['id']})",
            reply_to_message_id=update.message.message_id
        )
        
        # Уведомляем других админов
        for admin_id in Config.ADMIN_IDS:
            if admin_id != user.id:
                try:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=f"📤 Админ ответил на вопрос ID: {question['id']}"
                    )
                except:
                    pass
                    
    except Exception as e:
        logger.error(f"Ошибка отправки ответа: {e}")
        await update.message.reply_text("❌ Не удалось отправить ответ пользователю.")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на inline-кнопки"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    if user.id not in Config.ADMIN_IDS:
        await query.message.reply_text("У вас нет прав для этого действия.")
        return
    
    data = query.data
    
    if data.startswith('seen_'):
        question_id = data.split('_')[1]
        # Просто убираем кнопку "Просмотрено"
        keyboard = [
            [InlineKeyboardButton("📝 Ответить", callback_data=f"reply_{question_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_reply_markup(reply_markup=reply_markup)
        
    elif data.startswith('reply_'):
        question_id = data.split('_')[1]
        await query.message.reply_text(
            f"Отвечайте на это сообщение, чтобы ответить на вопрос ID: {question_id}",
            reply_to_message_id=query.message.message_id
        )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика (только для админов)"""
    user = update.effective_user
    if user.id not in Config.ADMIN_IDS:
        await update.message.reply_text("Эта команда только для администраторов.")
        return
    
    try:
        conn = db.get_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT COUNT(*) FROM questions")
        total = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM questions WHERE is_answered = TRUE")
        answered = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        stats_text = (
            f"📊 <b>Статистика бота</b>\n\n"
            f"Всего вопросов: {total}\n"
            f"Отвечено: {answered}\n"
            f"Ожидают ответа: {total - answered}\n"
            f"Процент ответов: {(answered/total*100 if total > 0 else 0):.1f}%"
        )
        
        await update.message.reply_html(stats_text)
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        await update.message.reply_text("❌ Ошибка получения статистики.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Ошибка при обработке обновления: {context.error}")
    
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ Произошла ошибка. Попробуйте позже или свяжитесь с администратором."
            )
        except:
            pass

def main():
    """Запуск бота"""
    # Создаем Application
    application = Application.builder().token(Config.BOT_TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    
    # Регистрируем обработчик inline-кнопок
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Регистрируем обработчики сообщений
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        handle_message
    ))
    
    # Обработчик ответов админов
    application.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.PRIVATE & filters.REPLY,
        handle_admin_reply
    ))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запуск бота
    logger.info("Бот запускается...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
