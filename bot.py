import logging
import html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters
)
from config import Config
from database import Database

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
        "👋 <b>Добро пожаловать в бот для анонимных вопросов!</b>\n\n"
        "📝 <b>Как это работает:</b>\n"
        "1. Напишите свой вопрос здесь\n"
        "2. Администратор получит его <b>полностью анонимно</b>\n"
        "3. Администратор ответит вам здесь же\n\n"
        "🔒 <b>Ваша анонимность гарантирована:</b>\n"
        "• Администраторы не видят ваше имя\n"
        "• Не видят ваш ID\n"
        "• Не видят вашу фотографию\n\n"
        "❓ <b>Просто напишите свой вопрос в этот чат...</b>"
    )
    
    await update.message.reply_html(welcome_text)
    
    # Отправляем уведомление админам о новом пользователе
    if Config.ADMIN_IDS:
        admin_text = f"🆕 <b>Новый пользователь запустил бота</b>\nВремя: {update.message.date}\n(Анонимный ID: {user.id})"
        for admin_id in Config.ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=admin_text,
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.error(f"❌ Не удалось уведомить админа {admin_id}: {e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = (
        "ℹ️ <b>Помощь по использованию бота</b>\n\n"
        
        "📝 <b>Как задать вопрос:</b>\n"
        "1. Просто напишите свой вопрос в этот чат\n"
        "2. Бот перешлет его администраторам\n"
        "3. Ожидайте ответа здесь же\n\n"
        
        "🔒 <b>Гарантии анонимности:</b>\n"
        "✓ Администраторы не видят ваше имя\n"
        "✓ Не видят ваш профиль\n"
        "✓ Не видят историю сообщений\n"
        "✓ Видят только текст вопроса\n\n"
        
        "⏱️ <b>Время ответа:</b>\n"
        "Администраторы обычно отвечают в течение 24 часов\n\n"
        
        "⚠️ <b>Правила:</b>\n"
        "• Будьте вежливы\n"
        "• Формулируйте вопросы четко\n"
        "• Не спамьте\n"
        "• Один вопрос - одно сообщение\n\n"
        
        "📋 <b>Команды:</b>\n"
        "/start - Начало работы\n"
        "/help - Эта справка\n"
        "/rules - Правила использования\n"
        "/cancel - Отменить текущее действие\n\n"
        
        "💡 <b>Совет:</b> Чем подробнее вопрос, тем точнее ответ!"
    )
    await update.message.reply_html(help_text)

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /rules"""
    rules_text = (
        "📜 <b>Правила использования бота анонимных вопросов</b>\n\n"
        
        "✅ <b>Можно:</b>\n"
        "• Задавать любые вопросы по теме канала\n"
        "• Просить совета или помощи\n"
        "• Предлагать идеи анонимно\n"
        "• Задавать уточняющие вопросы\n\n"
        
        "❌ <b>Нельзя:</b>\n"
        "• Оскорблять или угрожать\n"
        "• Распространять спам\n"
        "• Задавать незаконные вопросы\n"
        "• Нарушать правила Telegram\n"
        "• Злоупотреблять анонимностью\n\n"
        
        "⚠️ <b>Администраторы вправе:</b>\n"
        "• Не отвечать на нарушающие правила вопросы\n"
        "• Блокировать злоупотребляющих пользователей\n"
        "• Удалять неподобающие вопросы\n\n"
        
        "⚖️ <b>Последствия нарушений:</b>\n"
        "1. Предупреждение\n"
        "2. Временная блокировка\n"
        "3. Перманентная блокировка\n\n"
        
        "📞 <b>По вопросам модерации:</b>\n"
        "Свяжитесь с администрацией через официальные каналы"
    )
    await update.message.reply_html(rules_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений от пользователей"""
    user = update.effective_user
    message = update.message
    
    # Если сообщение от админа - игнорируем (админы отвечают через reply)
    if user.id in Config.ADMIN_IDS:
        return
    
    # Проверяем длину сообщения
    if len(message.text) > 4000:
        await message.reply_text(
            "❌ Слишком длинное сообщение. Пожалуйста, ограничьте вопрос 4000 символами."
        )
        return
    
    # Проверяем минимальную длину
    if len(message.text.strip()) < 5:
        await message.reply_text(
            "❌ Слишком короткий вопрос. Пожалуйста, сформулируйте вопрос подробнее."
        )
        return
    
    # Сохраняем вопрос в БД
    question_id = db.save_question(
        user_id=user.id,
        message_id=message.message_id,
        question_text=message.text
    )
    
    if not question_id:
        await message.reply_text(
            "❌ Произошла ошибка при сохранении вопроса. Попробуйте позже."
        )
        return
    
    # Формируем сообщение для админов
    admin_text = (
        f"❓ <b>НОВЫЙ АНОНИМНЫЙ ВОПРОС</b> [#{question_id}]\n"
        f"🕐 {update.message.date.strftime('%d.%m.%Y %H:%M')}\n"
        f"🔢 ID вопроса: {question_id}\n"
        f"📊 Длина: {len(message.text)} символов\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{html.escape(message.text)}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<i>Чтобы ответить, используйте reply на это сообщение</i>"
    )
    
    # Создаем клавиатуру для быстрых действий
    keyboard = [
        [
            InlineKeyboardButton("📝 Ответить", callback_data=f"reply_{question_id}"),
            InlineKeyboardButton("✅ Отвечено", callback_data=f"done_{question_id}")
        ],
        [
            InlineKeyboardButton("👁️ Просмотрено", callback_data=f"seen_{question_id}"),
            InlineKeyboardButton("📊 Статистика", callback_data="stats")
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
            
            logger.info(f"✅ Вопрос #{question_id} отправлен админу {admin_id}")
            
        except Exception as e:
            logger.error(f"❌ Не удалось отправить вопрос админу {admin_id}: {e}")
    
    if sent_to_admins:
        # Подтверждаем пользователю
        confirmation_text = (
            f"✅ <b>Ваш вопрос отправлен администраторам!</b>\n\n"
            f"🔒 <i>Ваша анонимность сохранена</i>\n"
            f"🆔 Номер вопроса: <code>#{question_id}</code>\n"
            f"🕐 Время отправки: {update.message.date.strftime('%H:%M')}\n\n"
            f"⏳ <b>Ожидайте ответа здесь же в этом чате.</b>\n\n"
            f"💡 <i>Ответ обычно приходит в течение 24 часов</i>"
        )
        await message.reply_html(confirmation_text)
    else:
        error_text = (
            "❌ <b>Не удалось отправить вопрос</b>\n\n"
            "Администраторы временно недоступны.\n"
            "Пожалуйста, попробуйте позже.\n\n"
            "<i>Мы уже уведомлены о проблеме</i>"
        )
        await message.reply_html(error_text)
        
        # Логируем критическую ошибку
        logger.critical(f"❌ Вопрос #{question_id} не отправлен ни одному админу!")

async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ответов админов (reply на сообщение)"""
    user = update.effective_user
    
    # Проверяем, что это админ
    if user.id not in Config.ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для ответа на вопросы.")
        return
    
    # Проверяем, что это reply на сообщение
    if not update.message.reply_to_message:
        await update.message.reply_text("ℹ️ Чтобы ответить на вопрос, используйте reply на сообщение с вопросом.")
        return
    
    admin_message_id = update.message.reply_to_message.message_id
    answer_text = update.message.text
    
    # Проверяем длину ответа
    if len(answer_text) > 4000:
        await update.message.reply_text("❌ Слишком длинный ответ. Ограничьте 4000 символами.")
        return
    
    # Ищем вопрос по ID сообщения админа
    question = db.get_user_by_admin_message(admin_message_id)
    
    if not question:
        await update.message.reply_text("❌ Не удалось найти вопрос. Возможно, он был удален или уже отвечен.")
        return
    
    # Отправляем ответ пользователю
    try:
        response_to_user = (
            f"📨 <b>ОТВЕТ НА ВАШ ВОПРОС #{question['id']}</b>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{html.escape(answer_text)}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🕐 <i>Ответ получен: {update.message.date.strftime('%d.%m.%Y %H:%M')}</i>\n\n"
            f"❓ <b>Есть еще вопросы?</b>\n"
            f"Просто напишите следуюший вопрос в этот чат!"
        )
        
        await context.bot.send_message(
            chat_id=question['user_id'],
            text=response_to_user,
            parse_mode='HTML'
        )
        
        # Отмечаем в БД как отвеченный
        db.mark_as_answered(question['id'], answer_text)
        
        # Подтверждаем админу
        confirmation_to_admin = (
            f"✅ <b>Ответ успешно отправлен!</b>\n\n"
            f"👤 Анонимному пользователю\n"
            f"🆔 Вопрос: #{question['id']}\n"
            f"📝 Длина ответа: {len(answer_text)} символов\n"
            f"🕐 Время: {update.message.date.strftime('%H:%M:%S')}"
        )
        
        await update.message.reply_text(
            confirmation_to_admin,
            parse_mode='HTML',
            reply_to_message_id=update.message.message_id
        )
        
        # Уведомляем других админов
        for admin_id in Config.ADMIN_IDS:
            if admin_id != user.id:
                try:
                    notification_text = (
                        f"📤 <b>Админ ответил на вопрос</b>\n"
                        f"👤 Админ: {user.first_name}\n"
                        f"🆔 Вопрос: #{question['id']}\n"
                        f"🕐 {update.message.date.strftime('%H:%M')}"
                    )
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=notification_text,
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logger.error(f"Не удалось уведомить админа {admin_id}: {e}")
        
        logger.info(f"✅ Админ {user.id} ответил на вопрос #{question['id']}")
                    
    except Exception as e:
        logger.error(f"❌ Ошибка отправки ответа: {e}")
        error_text = (
            f"❌ <b>Не удалось отправить ответ</b>\n\n"
            f"Ошибка: {str(e)[:100]}...\n\n"
            f"<i>Возможно, пользователь заблокировал бота</i>"
        )
        await update.message.reply_text(error_text, parse_mode='HTML')

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на inline-кнопки"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    if user.id not in Config.ADMIN_IDS:
        await query.edit_message_text("❌ У вас нет прав для этого действия.")
        return
    
    data = query.data
    
    if data.startswith('seen_'):
        question_id = data.split('_')[1]
        # Просто убираем кнопку "Просмотрено"
        keyboard = [
            [
                InlineKeyboardButton("📝 Ответить", callback_data=f"reply_{question_id}"),
                InlineKeyboardButton("✅ Отвечено", callback_data=f"done_{question_id}")
            ],
            [
                InlineKeyboardButton("📊 Статистика", callback_data="stats")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Обновляем текст сообщения
        original_text = query.message.text_html
        new_text = original_text + f"\n\n👁️ <i>Просмотрено админом {user.first_name}</i>"
        
        await query.edit_message_text(
            text=new_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        
    elif data.startswith('done_'):
        question_id = data.split('_')[1]
        await query.edit_message_text(
            f"✅ <b>Вопрос #{question_id} отмечен как отвеченный</b>\n\n"
            f"Админ: {user.first_name}\n"
            f"Время: {query.message.date.strftime('%H:%M:%S')}",
            parse_mode='HTML'
        )
        
    elif data.startswith('reply_'):
        question_id = data.split('_')[1]
        await query.message.reply_text(
            f"📝 <b>Отвечайте на это сообщение</b>\n\n"
            f"Вопрос ID: #{question_id}\n"
            f"Админ: {user.first_name}\n\n"
            f"<i>Просто напишите ответ и отправьте</i>",
            parse_mode='HTML',
            reply_to_message_id=query.message.message_id
        )
        
    elif data == "stats":
        stats = db.get_stats()
        stats_text = (
            f"📊 <b>СТАТИСТИКА БОТА</b>\n\n"
            f"📈 Всего вопросов: {stats['total']}\n"
            f"✅ Отвечено: {stats['answered']}\n"
            f"⏳ Ожидают ответа: {stats['pending']}\n"
            f"📅 Процент ответов: {(stats['answered']/stats['total']*100 if stats['total'] > 0 else 0):.1f}%\n\n"
            f"<i>Обновлено: {query.message.date.strftime('%d.%m.%Y %H:%M')}</i>"
        )
        await query.edit_message_text(
            text=stats_text,
            parse_mode='HTML'
        )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика (только для админов)"""
    user = update.effective_user
    if user.id not in Config.ADMIN_IDS:
        await update.message.reply_text("❌ Эта команда только для администраторов.")
        return
    
    stats = db.get_stats()
    
    stats_text = (
        f"📊 <b>СТАТИСТИКА АНОНИМНОГО БОТА</b>\n\n"
        f"👥 Администраторов: {len(Config.ADMIN_IDS)}\n"
        f"📈 Всего вопросов: <b>{stats['total']}</b>\n"
        f"✅ Отвечено: <b>{stats['answered']}</b>\n"
        f"⏳ Ожидают ответа: <b>{stats['pending']}</b>\n\n"
        f"📅 Процент ответов: <b>{(stats['answered']/stats['total']*100 if stats['total'] > 0 else 0):.1f}%</b>\n"
        f"📆 Дата: {update.message.date.strftime('%d.%m.%Y')}\n"
        f"🕐 Время: {update.message.date.strftime('%H:%M:%S')}"
    )
    
    # Добавляем кнопки для админов
    keyboard = [
        [
            InlineKeyboardButton("🔄 Обновить", callback_data="refresh_stats"),
            InlineKeyboardButton("📋 Неотвеченные", callback_data="show_pending")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_html(stats_text, reply_markup=reply_markup)

async def pending_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать неотвеченные вопросы (только для админов)"""
    user = update.effective_user
    if user.id not in Config.ADMIN_IDS:
        await update.message.reply_text("❌ Эта команда только для администраторов.")
        return
    
    pending_questions = db.get_pending_questions()
    
    if not pending_questions:
        await update.message.reply_text("✅ <b>Нет неотвеченных вопросов!</b>\n\nВсе вопросы обработаны.", parse_mode='HTML')
        return
    
    pending_text = f"⏳ <b>НЕОТВЕЧЕННЫЕ ВОПРОСЫ</b> ({len(pending_questions)})\n\n"
    
    for i, question in enumerate(pending_questions[:10], 1):  # Ограничиваем 10 вопросами
        question_preview = question['question_text'][:100] + "..." if len(question['question_text']) > 100 else question['question_text']
        pending_text += (
            f"{i}. <b>#{question['id']}</b>\n"
            f"📝 {html.escape(question_preview)}\n"
            f"🕐 {question['asked_at'].strftime('%d.%m %H:%M')}\n\n"
        )
    
    if len(pending_questions) > 10:
        pending_text += f"\n<i>... и еще {len(pending_questions) - 10} вопросов</i>"
    
    await update.message.reply_html(pending_text)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"❌ Ошибка при обработке обновления: {context.error}")
    
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ Произошла ошибка. Пожалуйста, попробуйте позже.\n\n"
                "<i>Мы уже уведомлены о проблеме</i>",
                parse_mode='HTML'
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
    application.add_handler(CommandHandler("rules", rules_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("pending", pending_command))
    
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
    logger.info("🤖 Бот запускается...")
    logger.info(f"👥 Администраторов: {len(Config.ADMIN_IDS)}")
    logger.info("✅ Бот готов к работе!")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
