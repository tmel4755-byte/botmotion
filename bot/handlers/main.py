from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from ..database import (
    init_db, add_user, add_reminder, get_user_reminders, 
    delete_reminder, clear_all_reminders, get_user_timezone, update_user_timezone,
    get_statistics
)
from ..keyboards import (
    get_main_keyboard, get_reminder_actions_keyboard, get_timezone_keyboard,
    get_repeat_options_keyboard, get_repeat_options_keyboard_for_edit, get_settings_keyboard, 
    get_confirmation_keyboard, get_back_keyboard
)
from ..states import ReminderStates
from ..utils import validate_time_format, format_reminder_info, parse_user_time_input
from ..config import ADMIN_ID
from ..storage import get_scheduler

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Обработка команды /start"""
    await state.clear()
    
    # Добавляем пользователя в базу данных
    await add_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    
    welcome_text = (
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        "Я бот для создания напоминаний 📅\n\n"
        "Вот что я умею:\n"
        "• Создавать напоминания с настройкой времени ⏰\n"
        "• Выбирать тип повтора (однократно, ежедневно, еженедельно) 🔄\n"
        "• Настроить часовой пояс для корректного времени 🌍\n"
        "• Управлять всеми вашими напоминаниями 📋\n\n"
        "Выберите действие:"
    )
    
    await message.answer(welcome_text, reply_markup=get_main_keyboard())

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    await callback.message.edit_text(
        "Вы в главном меню. Выберите действие:",
        reply_markup=get_main_keyboard()
    )

@router.callback_query(F.data == "create_reminder")
async def create_reminder_start(callback: CallbackQuery, state: FSMContext):
    """Начало создания напоминания"""
    await state.clear()
    await state.set_state(ReminderStates.waiting_for_message)
    
    await callback.message.edit_text(
        "Введите текст напоминания:",
        reply_markup=get_back_keyboard()
    )

@router.message(ReminderStates.waiting_for_message)
async def process_reminder_message(message: Message, state: FSMContext):
    """Обработка текста напоминания"""
    await state.update_data(message=message.text)
    await state.set_state(ReminderStates.waiting_for_time)
    
    await message.answer(
        "Введите время в формате ЧЧ:ММ (например, 14:30):",
        reply_markup=get_back_keyboard()
    )

@router.message(ReminderStates.waiting_for_time)
async def process_reminder_time(message: Message, state: FSMContext):
    """Обработка времени напоминания"""
    time_input = message.text.strip()
    
    if not validate_time_format(time_input):
        await message.answer(
            "Неверный формат времени! Пожалуйста, введите время в формате ЧЧ:ММ (например, 14:30):",
            reply_markup=get_back_keyboard()
        )
        return
    
    # Получаем часовой пояс пользователя
    user_timezone = await get_user_timezone(message.from_user.id)
    
    # Преобразуем время пользователя в UTC
    utc_time = parse_user_time_input(time_input, user_timezone)
    if utc_time is None:
        await message.answer(
            "Произошла ошибка при обработке времени. Попробуйте снова.",
            reply_markup=get_back_keyboard()
        )
        return
    
    await state.update_data(time=utc_time)
    await state.set_state(ReminderStates.waiting_for_repeat)
    
    await message.answer(
        "Выберите тип повтора:",
        reply_markup=get_repeat_options_keyboard()
    )

@router.callback_query(F.data.startswith("repeat_"))
async def process_repeat_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора типа повтора"""
    data = await state.get_data()
    user_timezone = await get_user_timezone(callback.from_user.id)
    
    # Преобразуем время обратно в пользовательский формат для отображения
    user_time = parse_user_time_input(data['time'], user_timezone)
    
    repeat_mapping = {
        'repeat_none': 'none',
        'repeat_minute': 'minute',
        'repeat_daily': 'daily',
        'repeat_weekly': 'weekly'
    }
    
    repeat_type = repeat_mapping.get(callback.data, 'none')
    await state.update_data(repeat_type=repeat_type)
    
    # Получаем данные напоминания
    reminder_data = await state.get_data()
    
    # Формируем сообщение с подтверждением
    confirmation_text = (
        "Подтвердите создание напоминания:\n\n"
        f"{format_reminder_info(reminder_data['message'], user_time, repeat_type)}"
    )
    
    await callback.message.edit_text(
        confirmation_text,
        reply_markup=get_confirmation_keyboard("create_reminder")
    )

@router.callback_query(F.data == "confirm_create_reminder")
async def confirm_create_reminder(callback: CallbackQuery, state: FSMContext):
    """Подтверждение создания напоминания"""
    reminder_data = await state.get_data()
    
    # Получим список напоминаний до добавления, чтобы определить ID нового напоминания
    reminders_before = await get_user_reminders(callback.from_user.id)
    last_id_before = max([r[0] for r in reminders_before], default=0) if reminders_before else 0
    
    # Сохраняем напоминание в базу данных
    await add_reminder(
        user_id=callback.from_user.id,
        message=reminder_data['message'],
        reminder_time=reminder_data['time'],
        repeat_type=reminder_data['repeat_type']
    )
    
    # Получим список после добавления и найдем ID только что добавленного напоминания
    reminders_after = await get_user_reminders(callback.from_user.id)
    new_ids = [r[0] for r in reminders_after if r[0] > last_id_before]
    
    # Получаем экземпляр планировщика и добавляем задачу
    scheduler = get_scheduler()
    if scheduler and new_ids:
        new_reminder_id = max(new_ids)
        # Добавляем задачу в планировщик
        await scheduler.add_reminder_job(
            user_id=callback.from_user.id,
            reminder_id=new_reminder_id,
            message=reminder_data['message'],
            time=reminder_data['time'],
            repeat_type=reminder_data['repeat_type']
        )
    
    await state.clear()
    
    await callback.message.edit_text(
        "✅ Напоминание создано!\n\n"
        f"Текст: {reminder_data['message']}\n"
        f"Время: {reminder_data['time']}\n"
        f"Повтор: {reminder_data['repeat_type']}"
    )
    
    # Возвращаемся в главное меню
    await callback.message.answer(
        "Выберите действие:",
        reply_markup=get_main_keyboard()
    )

@router.callback_query(F.data == "my_reminders")
async def show_my_reminders(callback: CallbackQuery):
    """Показать все напоминания пользователя"""
    reminders = await get_user_reminders(callback.from_user.id)
    
    if not reminders:
        await callback.message.edit_text(
            "У вас пока нет активных напоминаний.",
            reply_markup=get_main_keyboard()
        )
        return
    
    response = "Ваши напоминания:\n\n"
    for i, (reminder_id, message, time, repeat_type) in enumerate(reminders, 1):
        # Преобразуем время в пользовательский часовой пояс для отображения
        user_timezone = await get_user_timezone(callback.from_user.id)
        user_time = parse_user_time_input(time, user_timezone)
        
        repeat_labels = {
            'none': 'Без повтора',
            'minute': 'Каждую минуту',
            'daily': 'Ежедневно',
            'weekly': 'Еженедельно'
        }
        repeat_label = repeat_labels.get(repeat_type, 'Неизвестный тип')
        
        response += f"{i}. {message}\n"
        response += f"   ⏰ {user_time} ({repeat_label})\n"
        response += f"   ID: {reminder_id}\n\n"
    
    await callback.message.edit_text(response, reply_markup=get_main_keyboard())

@router.callback_query(F.data.startswith("delete_reminder_"))
async def delete_reminder_callback(callback: CallbackQuery):
    """Удаление конкретного напоминания"""
    reminder_id = int(callback.data.split("_")[2])
    
    await callback.message.edit_text(
        f"Вы уверены, что хотите удалить напоминание?",
        reply_markup=get_confirmation_keyboard(f"delete_reminder_{reminder_id}")
    )

@router.callback_query(F.data.startswith("confirm_delete_reminder_"))
async def confirm_delete_reminder(callback: CallbackQuery):
    """Подтверждение удаления напоминания"""
    reminder_id = int(callback.data.split("_")[3])
    
    # Удаляем напоминание из базы данных
    await delete_reminder(reminder_id, callback.from_user.id)
    
    # Удаляем задачу из планировщика
    scheduler = get_scheduler()
    if scheduler:
        await scheduler.remove_reminder_job(callback.from_user.id, reminder_id)
    
    await callback.message.edit_text(
        "✅ Напоминание удалено!",
        reply_markup=get_main_keyboard()
    )

@router.callback_query(F.data == "clear_all_reminders")
async def clear_all_reminders_callback(callback: CallbackQuery):
    """Очистка всех напоминаний"""
    await callback.message.edit_text(
        "Вы уверены, что хотите удалить все ваши напоминания?",
        reply_markup=get_confirmation_keyboard("clear_all_reminders")
    )

@router.callback_query(F.data == "confirm_clear_all_reminders")
async def confirm_clear_all_reminders(callback: CallbackQuery):
    """Подтверждение очистки всех напоминаний"""
    # Очищаем напоминания из базы данных
    await clear_all_reminders(callback.from_user.id)
    
    # Удаляем все задачи из планировщика для этого пользователя
    scheduler = get_scheduler()
    if scheduler:
        await scheduler.remove_user_reminders(callback.from_user.id)
    
    await callback.message.edit_text(
        "✅ Все напоминания удалены!",
        reply_markup=get_main_keyboard()
    )

@router.callback_query(F.data == "change_timezone")
async def change_timezone_start(callback: CallbackQuery):
    """Изменение часового пояса"""
    current_timezone = await get_user_timezone(callback.from_user.id)
    
    await callback.message.edit_text(
        f"Ваш текущий часовой пояс: {current_timezone}\n\nВыберите новый часовой пояс:",
        reply_markup=get_timezone_keyboard()
    )

@router.callback_query(F.data.startswith("set_tz_"))
async def set_timezone_callback(callback: CallbackQuery):
    """Установка нового часового пояса"""
    new_timezone = callback.data.split("set_tz_")[1]
    
    await update_user_timezone(callback.from_user.id, new_timezone)
    
    await callback.message.edit_text(
        f"✅ Часовой пояс изменен на {new_timezone}",
        reply_markup=get_main_keyboard()
    )

@router.callback_query(F.data == "settings")
async def show_settings(callback: CallbackQuery):
    """Показать настройки"""
    await callback.message.edit_text(
        "Настройки:",
        reply_markup=get_settings_keyboard()
    )

@router.callback_query(F.data.startswith("edit_reminder_"))
async def start_edit_reminder(callback: CallbackQuery, state: FSMContext):
    """Начало процесса редактирования напоминания"""
    reminder_id = int(callback.data.split("_")[2])
    
    # Получаем информацию о напоминании
    user_reminders = await get_user_reminders(callback.from_user.id)
    reminder = next((r for r in user_reminders if r[0] == reminder_id), None)
    
    if not reminder:
        await callback.message.edit_text(
            "❌ Напоминание не найдено.",
            reply_markup=get_main_keyboard()
        )
        return
    
    reminder_id, message, time, repeat_type = reminder
    
    # Сохраняем ID напоминания в состоянии
    await state.update_data(editing_reminder_id=reminder_id)
    
    # Показываем меню редактирования
    edit_menu = (
        f"✏️ Редактирование напоминания:\n\n"
        f"Текущее сообщение: {message}\n"
        f"Текущее время: {time}\n"
        f"Текущий повтор: {repeat_type}\n\n"
        "Выберите, что вы хотите изменить:"
    )
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(
        InlineKeyboardButton(text="📝 Сообщение", callback_data="edit_message"),
        InlineKeyboardButton(text="⏰ Время", callback_data="edit_time"),
        InlineKeyboardButton(text="🔄 Повтор", callback_data="edit_repeat")
    )
    keyboard.add(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action"))
    keyboard.adjust(1)
    
    await callback.message.edit_text(edit_menu, reply_markup=keyboard.as_markup())


@router.callback_query(F.data == "edit_message")
async def edit_reminder_message(callback: CallbackQuery, state: FSMContext):
    """Изменение текста напоминания"""
    await state.set_state(ReminderStates.editing_message)
    
    await callback.message.edit_text(
        "Введите новое сообщение для напоминания:",
        reply_markup=get_back_keyboard()
    )


@router.message(ReminderStates.editing_message)
async def process_new_message(message: Message, state: FSMContext):
    """Обработка нового сообщения для напоминания"""
    data = await state.get_data()
    reminder_id = data.get('editing_reminder_id')
    
    if not reminder_id:
        await message.answer("❌ Ошибка: ID напоминания не найден.", reply_markup=get_main_keyboard())
        await state.clear()
        return
    
    # Получаем текущую информацию о напоминании
    user_reminders = await get_user_reminders(message.from_user.id)
    original_reminder = next((r for r in user_reminders if r[0] == reminder_id), None)
    
    if not original_reminder:
        await message.answer("❌ Напоминание не найдено.", reply_markup=get_main_keyboard())
        await state.clear()
        return
    
    _, _, time, repeat_type = original_reminder
    
    # Обновляем напоминание в базе данных
    async with aiosqlite.connect('reminders.db') as db:
        await db.execute(
            'UPDATE reminders SET message = ? WHERE id = ? AND user_id = ?',
            (message.text, reminder_id, message.from_user.id)
        )
        await db.commit()
    
    # Обновляем задачу в планировщике
    scheduler = get_scheduler()
    if scheduler:
        # Удаляем старую задачу
        await scheduler.remove_reminder_job(message.from_user.id, reminder_id)
        # Добавляем новую задачу с обновленным сообщением
        await scheduler.add_reminder_job(
            user_id=message.from_user.id,
            reminder_id=reminder_id,
            message=message.text,
            time=time,
            repeat_type=repeat_type
        )
    
    await state.clear()
    
    await message.answer(
        f"✅ Сообщение напоминания обновлено!\n\nНовое сообщение: {message.text}",
        reply_markup=get_main_keyboard()
    )


@router.callback_query(F.data == "edit_time")
async def edit_reminder_time(callback: CallbackQuery, state: FSMContext):
    """Изменение времени напоминания"""
    data = await state.get_data()
    reminder_id = data.get('editing_reminder_id')
    
    if not reminder_id:
        await callback.message.edit_text(
            "❌ Ошибка: ID напоминания не найден.",
            reply_markup=get_main_keyboard()
        )
        await state.clear()
        return
    
    await state.update_data(editing_field='time')
    await state.set_state(ReminderStates.editing_time)
    
    await callback.message.edit_text(
        "Введите новое время в формате ЧЧ:ММ (например, 14:30):",
        reply_markup=get_back_keyboard()
    )


@router.message(ReminderStates.editing_time)
async def process_new_time(message: Message, state: FSMContext):
    """Обработка нового времени для напоминания"""
    time_input = message.text.strip()
    
    if not validate_time_format(time_input):
        await message.answer(
            "Неверный формат времени! Пожалуйста, введите время в формате ЧЧ:ММ (например, 14:30):",
            reply_markup=get_back_keyboard()
        )
        return
    
    data = await state.get_data()
    reminder_id = data.get('editing_reminder_id')
    
    if not reminder_id:
        await message.answer("❌ Ошибка: ID напоминания не найден.", reply_markup=get_main_keyboard())
        await state.clear()
        return
    
    # Получаем текущую информацию о напоминании
    user_reminders = await get_user_reminders(message.from_user.id)
    original_reminder = next((r for r in user_reminders if r[0] == reminder_id), None)
    
    if not original_reminder:
        await message.answer("❌ Напоминание не найдено.", reply_markup=get_main_keyboard())
        await state.clear()
        return
    
    _, original_message, _, repeat_type = original_reminder
    
    # Преобразуем время пользователя в UTC
    user_timezone = await get_user_timezone(message.from_user.id)
    utc_time = parse_user_time_input(time_input, user_timezone)
    
    if utc_time is None:
        await message.answer(
            "Произошла ошибка при обработке времени. Попробуйте снова.",
            reply_markup=get_back_keyboard()
        )
        return
    
    # Обновляем напоминание в базе данных
    async with aiosqlite.connect('reminders.db') as db:
        await db.execute(
            'UPDATE reminders SET reminder_time = ? WHERE id = ? AND user_id = ?',
            (utc_time, reminder_id, message.from_user.id)
        )
        await db.commit()
    
    # Обновляем задачу в планировщике
    scheduler = get_scheduler()
    if scheduler:
        # Удаляем старую задачу
        await scheduler.remove_reminder_job(message.from_user.id, reminder_id)
        # Добавляем новую задачу с обновленным временем
        await scheduler.add_reminder_job(
            user_id=message.from_user.id,
            reminder_id=reminder_id,
            message=original_message,
            time=utc_time,
            repeat_type=repeat_type
        )
    
    await state.clear()
    
    await message.answer(
        f"✅ Время напоминания обновлено!\n\nНовое время: {time_input}",
        reply_markup=get_main_keyboard()
    )


@router.callback_query(F.data == "edit_repeat")
async def edit_reminder_repeat(callback: CallbackQuery, state: FSMContext):
    """Изменение типа повтора напоминания"""
    data = await state.get_data()
    reminder_id = data.get('editing_reminder_id')
    
    if not reminder_id:
        await callback.message.edit_text(
            "❌ Ошибка: ID напоминания не найден.",
            reply_markup=get_main_keyboard()
        )
        await state.clear()
        return
    
    await state.update_data(editing_field='repeat')
    
    await callback.message.edit_text(
        "Выберите новый тип повтора:",
        reply_markup=get_repeat_options_keyboard_for_edit()
    )


@router.callback_query(F.data.startswith("repeat_") & F.data.endswith("_for_edit"))
async def process_new_repeat_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора нового типа повтора"""
    data = await state.get_data()
    reminder_id = data.get('editing_reminder_id')
    
    if not reminder_id:
        await callback.message.edit_text(
            "❌ Ошибка: ID напоминания не найден.",
            reply_markup=get_main_keyboard()
        )
        await state.clear()
        return
    
    # Получаем текущую информацию о напоминании
    user_reminders = await get_user_reminders(callback.from_user.id)
    original_reminder = next((r for r in user_reminders if r[0] == reminder_id), None)
    
    if not original_reminder:
        await callback.message.edit_text("❌ Напоминание не найдено.", reply_markup=get_main_keyboard())
        await state.clear()
        return
    
    _, original_message, original_time, _ = original_reminder
    
    repeat_mapping = {
        'repeat_none_for_edit': 'none',
        'repeat_minute_for_edit': 'minute',
        'repeat_daily_for_edit': 'daily',
        'repeat_weekly_for_edit': 'weekly'
    }
    
    repeat_type = repeat_mapping.get(callback.data, 'none')
    
    # Обновляем напоминание в базе данных
    async with aiosqlite.connect('reminders.db') as db:
        await db.execute(
            'UPDATE reminders SET repeat_type = ? WHERE id = ? AND user_id = ?',
            (repeat_type, reminder_id, callback.from_user.id)
        )
        await db.commit()
    
    # Обновляем задачу в планировщике
    scheduler = get_scheduler()
    if scheduler:
        # Удаляем старую задачу
        await scheduler.remove_reminder_job(callback.from_user.id, reminder_id)
        # Добавляем новую задачу с обновленным типом повтора
        await scheduler.add_reminder_job(
            user_id=callback.from_user.id,
            reminder_id=reminder_id,
            message=original_message,
            time=original_time,
            repeat_type=repeat_type
        )
    
    await state.clear()
    
    repeat_labels = {
        'none': 'Без повтора',
        'minute': 'Каждую минуту',
        'daily': 'Ежедневно',
        'weekly': 'Еженедельно'
    }
    
    await callback.message.edit_text(
        f"✅ Тип повтора напоминания обновлен!\n\nНовый тип: {repeat_labels.get(repeat_type, 'Неизвестный тип')}",
        reply_markup=get_main_keyboard()
    )


@router.callback_query(F.data == "notifications")
async def show_notifications_settings(callback: CallbackQuery):
    """Показать настройки уведомлений"""
    # Пока что просто покажем текущие настройки
    await callback.message.edit_text(
        "🔔 Настройки уведомлений:\n\n"
        "В настоящее время все уведомления включены.\n\n"
        "Дополнительные настройки будут доступны в будущих обновлениях.",
        reply_markup=get_back_keyboard()
    )


@router.callback_query(F.data == "statistics")
async def show_statistics(callback: CallbackQuery):
    """Показать статистику использования"""
    stats = await get_statistics()
    
    stats_text = (
        "📊 Статистика использования бота:\n\n"
        f"👥 Всего пользователей: {stats['total_users']}\n"
        f"📝 Всего напоминаний: {stats['total_reminders']}\n\n"
        "Разбивка по типам повтора:\n"
    )
    
    for repeat_type, count in stats['active_reminders_by_type'].items():
        type_names = {
            'none': 'Без повтора',
            'minute': 'Каждую минуту',
            'daily': 'Ежедневно',
            'weekly': 'Еженедельно'
        }
        type_name = type_names.get(repeat_type, repeat_type)
        stats_text += f"- {type_name}: {count}\n"
    
    if not stats['active_reminders_by_type']:
        stats_text += "- Нет активных напоминаний\n"
    
    await callback.message.edit_text(
        stats_text,
        reply_markup=get_back_keyboard()
    )


@router.callback_query(F.data == "disable_all")
async def disable_all_reminders_start(callback: CallbackQuery):
    """Начало процесса отключения всех напоминаний"""
    await callback.message.edit_text(
        "Вы уверены, что хотите отключить ВСЕ напоминания для вашего аккаунта?\n\n"
        "Это действие нельзя будет отменить.",
        reply_markup=get_confirmation_keyboard("disable_all_reminders")
    )


@router.callback_query(F.data == "confirm_disable_all_reminders")
async def confirm_disable_all_reminders(callback: CallbackQuery):
    """Подтверждение отключения всех напоминаний"""
    # Удаляем все напоминания из базы данных
    await clear_all_reminders(callback.from_user.id)
    
    # Удаляем все задачи из планировщика для этого пользователя
    scheduler = get_scheduler()
    if scheduler:
        await scheduler.remove_user_reminders(callback.from_user.id)
    
    await callback.message.edit_text(
        "✅ Все ваши напоминания были отключены!",
        reply_markup=get_main_keyboard()
    )


@router.callback_query(F.data == "cancel_action")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    """Отмена действия"""
    await state.clear()
    await callback.message.edit_text(
        "Действие отменено.",
        reply_markup=get_main_keyboard()
    )