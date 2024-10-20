from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler

# Определяем состояния для сборщика данных
INCOMES, EXPENSES, TRANSFERS, REMAINDER, TOTAL_OUTPUT, USDT, AVG_COEF, CONFIRM = range(8)

# Словари для хранения данных по пользователям
user_data = {
    'user1': {
        'incomes': [],
        'expenses': [],
        'transfers': [],
        'remainder': 0,
        'output': 0,
        'usdt': 0.0,
        'avg_coef': 0.0,
        'date': None
    },
    'user2': {
        'incomes': [],
        'expenses': [],
        'transfers': [],
        'remainder': 0,
        'output': 0,
        'usdt': 0.0,
        'avg_coef': 0.0,
        'date': None
    }
}

# Словарь для архива трат
expense_archive = {}

# Функция старта бота
async def start(update: Update, context):
    user_id = update.message.from_user.id
    keyboard = [
        [InlineKeyboardButton("Создать", callback_data='create')],
        [InlineKeyboardButton("Траты сегодня", callback_data='today_expenses')],
        [InlineKeyboardButton("Архив трат", callback_data='archive')],
        [InlineKeyboardButton("Готово", callback_data='done')],
        [InlineKeyboardButton("Отмена", callback_data='cancel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f'Ваш ID: {user_id}\nВыберите действие:', reply_markup=reply_markup)

# Обработчик для кнопок
async def button_handler(update: Update, context):
    query = update.callback_query
    await query.answer()

    if query.data == 'create':
        await query.edit_message_text("Приходы: укажите количество приходов в формате (13020 - сбер г). Введите 0, если нет данных.")
        return INCOMES

    elif query.data == 'today_expenses':
        await query.edit_message_text(generate_report())
    
    elif query.data == 'archive':
        if expense_archive:
            keyboard = [[InlineKeyboardButton(date, callback_data=date)] for date in expense_archive]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("Выберите дату для просмотра трат:", reply_markup=reply_markup)
        else:
            await query.edit_message_text("Архив пуст.")
    
    elif query.data in expense_archive:
        # Отправка трат по выбранной дате
        report = generate_archive_report(query.data)
        await query.edit_message_text(report)

    elif query.data == 'done':
        save_to_archive()
        await query.edit_message_text("Данные сохранены. Вы можете создать новый отчёт или просмотреть архив.")

    elif query.data == 'cancel':
        await query.edit_message_text("Операция отменена.")
        return ConversationHandler.END

# Сбор данных по этапам
async def incomes(update: Update, context):
    user_id = update.message.from_user.id
    user_key = 'user1' if user_id == USER1_ID else 'user2'

    income = update.message.text
    if income != "0":
        user_data[user_key]['incomes'].append(income)

    await update.message.reply_text("Выводы: укажите количество выводов в формате (31000 - сбер х). Введите 0, если нет данных.")
    return EXPENSES

async def expenses(update: Update, context):
    user_id = update.message.from_user.id
    user_key = 'user1' if user_id == USER1_ID else 'user2'

    expense = update.message.text
    if expense != "0":
        user_data[user_key]['expenses'].append(expense)

    await update.message.reply_text("Траты: укажите траты в формате (28794 - взял из своих). Введите 0, если нет данных.")
    return TRANSFERS

async def transfers(update: Update, context):
    user_id = update.message.from_user.id
    user_key = 'user1' if user_id == USER1_ID else 'user2'

    transfer = update.message.text
    if transfer != "0":
        user_data[user_key]['transfers'].append(transfer)

    await update.message.reply_text("Остаток: укажите ваш остаток. Введите 0, если нет данных.")
    return REMAINDER

async def remainder(update: Update, context):
    user_id = update.message.from_user.id
    user_key = 'user1' if user_id == USER1_ID else 'user2'

    remainder = update.message.text
    if remainder != "0":
        user_data[user_key]['remainder'] = int(remainder)

    await update.message.reply_text("Введите общий вывод (Пример: 31000 - сбер х):")
    return TOTAL_OUTPUT

async def total_output(update: Update, context):
    user_id = update.message.from_user.id
    user_key = 'user1' if user_id == USER1_ID else 'user2'

    output = update.message.text
    if output != "0":
        user_data[user_key]['output'] = int(output.split()[0])

    await update.message.reply_text("Введите количество USDT (Пример: 301,76):")
    return USDT

async def usdt(update: Update, context):
    user_id = update.message.from_user.id
    user_key = 'user1' if user_id == USER1_ID else 'user2'

    usdt_value = update.message.text
    user_data[user_key]['usdt'] = float(usdt_value.replace(',', '.'))

    await update.message.reply_text("Введите средний коэффициент (Пример: 102,73):")
    return AVG_COEF

async def avg_coef(update: Update, context):
    user_id = update.message.from_user.id
    user_key = 'user1' if user_id == USER1_ID else 'user2'

    avg_coef_value = update.message.text
    user_data[user_key]['avg_coef'] = float(avg_coef_value.replace(',', '.'))

    final_report = generate_report()
    await update.message.reply_text(final_report)

    # Предложить пользователю завершить сбор данных
    keyboard = [[InlineKeyboardButton("Готово", callback_data='done')],
                [InlineKeyboardButton("Отмена", callback_data='cancel')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Отчёт готов. Нажмите 'Готово', чтобы сохранить или 'Отмена' для отмены:", reply_markup=reply_markup)
    return CONFIRM

# Генерация отчета
def generate_report():
    total_transfers = sum([int(t.split()[0]) for t in user_data['user1']['transfers']] + [int(t.split()[0]) for t in user_data['user2']['transfers']])
    total_expenses = sum([int(e.split()[0]) for e in user_data['user1']['expenses']] + [int(e.split()[0]) for e in user_data['user2']['expenses']])
    total_remainder = user_data['user1']['remainder'] + user_data['user2']['remainder']

    # Используем обычную строку и метод format для подстановки значений
    report = """
    Отчет:
    Приходы: 
    {incomes}
    
    Выводы: 
    {expenses}
    Общий: {total_output}
    USDT: {total_usdt}
    ср.кф: {avg_coef}

    Траты: 
    {expenses}
    
    Переводы: 
    {transfers}
    
    Всего переводов: {total_transfers}
    Всего трат: {total_expenses}
    Остаток: {total_remainder}
    """.format(
        incomes='\n'.join(user_data['user1']['incomes'] + user_data['user2']['incomes']),
        expenses='\n'.join(user_data['user1']['expenses'] + user_data['user2']['expenses']),
        transfers='\n'.join(user_data['user1']['transfers'] + user_data['user2']['transfers']),
        total_output=user_data['user1']['output'] + user_data['user2']['output'],
        total_usdt=user_data['user1']['usdt'] + user_data['user2']['usdt'],
        avg_coef=(user_data['user1']['avg_coef'] + user_data['user2']['avg_coef']) / 2,
        total_transfers=total_transfers,
        total_expenses=total_expenses,
        total_remainder=total_remainder
    )
    
    return report

# Генерация отчета из архива
def generate_archive_report(date):
    report = f"Отчет за {date}:\n"
    report += f"Приходы:\n{expense_archive[date]['incomes']}\n"
    report += f"Выводы:\n{expense_archive[date]['expenses']}\n"
    report += f"Траты:\n{expense_archive[date]['transfers']}\n"
    return report

# Сохранение данных в архив
def save_to_archive():
    date = user_data['user1']['date']
    expense_archive[date] = {
        'incomes': '\n'.join(user_data['user1']['incomes'] + user_data['user2']['incomes']),
        'expenses': '\n'.join(user_data['user1']['expenses'] + user_data['user2']['expenses']),
        'transfers': '\n'.join(user_data['user1']['transfers'] + user_data['user2']['transfers'])
    }

# Завершаем диалог в любой момент
async def cancel(update: Update, context):
    await update.message.reply_text("Операция отменена.")
    return ConversationHandler.END

if __name__ == '__main__':
    USER1_ID = 911869829  # Укажите реальные ID
    USER2_ID = 7815148543
    
    application = ApplicationBuilder().token('7841001024:AAGpDOwzDxscDs9YXJrF0CFGVVsO7NGmExY').build()
    
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern='create')],
        states={
            INCOMES: [MessageHandler(filters.TEXT & ~filters.COMMAND, incomes)],
            EXPENSES: [MessageHandler(filters.TEXT & ~filters.COMMAND, expenses)],
            TRANSFERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, transfers)],
            REMAINDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, remainder)],
            TOTAL_OUTPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, total_output)],
            USDT: [MessageHandler(filters.TEXT & ~filters.COMMAND, usdt)],
            AVG_COEF: [MessageHandler(filters.TEXT & ~filters.COMMAND, avg_coef)],
            CONFIRM: [CallbackQueryHandler(button_handler)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_chat=True
    )

    application.add_handler(CommandHandler('start', start))
    application.add_handler(conv_handler)

    application.run_polling()
