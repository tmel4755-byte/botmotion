from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_main_keyboard():
    """Основная клавиатура с главными командами"""
    keyboard = InlineKeyboardBuilder()
    keyboard.add(
        InlineKeyboardButton(text="📝 Создать напоминание", callback_data="create_reminder"),
        InlineKeyboardButton(text="📋 Мои напоминания", callback_data="my_reminders")
    )
    keyboard.add(
        InlineKeyboardButton(text="🌍 Часовой пояс", callback_data="change_timezone"),
        InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")
    )
    keyboard.adjust(1)
    return keyboard.as_markup()

def get_reminder_actions_keyboard(reminder_id):
    """Клавиатура с действиями над напоминанием"""
    keyboard = InlineKeyboardBuilder()
    keyboard.add(
        InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_reminder_{reminder_id}"),
        InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_reminder_{reminder_id}")
    )
    keyboard.add(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="my_reminders")
    )
    keyboard.adjust(2, 1)
    return keyboard.as_markup()

def get_timezone_keyboard():
    """Клавиатура для выбора часового пояса"""
    timezones = [
        ("UTC", "UTC"),
        ("Europe/Moscow", "Москва (MSK)"),
        ("Europe/Kiev", "Киев (EET)"),
        ("Asia/Tokyo", "Токио (JST)"),
        ("America/New_York", "Нью-Йорк (EST)"),
        ("America/Los_Angeles", "Лос-Анджелес (PST)")
    ]
    
    keyboard = InlineKeyboardBuilder()
    for tz_value, tz_label in timezones:
        keyboard.add(InlineKeyboardButton(text=tz_label, callback_data=f"set_tz_{tz_value}"))
    
    keyboard.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu"))
    keyboard.adjust(1)
    return keyboard.as_markup()

def get_repeat_options_keyboard():
    """Клавиатура для выбора типа повтора"""
    keyboard = InlineKeyboardBuilder()
    keyboard.add(
        InlineKeyboardButton(text="❌ Без повтора", callback_data="repeat_none"),
        InlineKeyboardButton(text="🔄 Каждую минуту", callback_data="repeat_minute"),
        InlineKeyboardButton(text="📆 Ежедневно", callback_data="repeat_daily"),
        InlineKeyboardButton(text="🗓️ Еженедельно", callback_data="repeat_weekly")
    )
    keyboard.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu"))
    keyboard.adjust(2, 2, 1)
    return keyboard.as_markup()


def get_repeat_options_keyboard_for_edit():
    """Клавиатура для выбора типа повтора при редактировании"""
    keyboard = InlineKeyboardBuilder()
    keyboard.add(
        InlineKeyboardButton(text="❌ Без повтора", callback_data="repeat_none_for_edit"),
        InlineKeyboardButton(text="🔄 Каждую минуту", callback_data="repeat_minute_for_edit"),
        InlineKeyboardButton(text="📆 Ежедневно", callback_data="repeat_daily_for_edit"),
        InlineKeyboardButton(text="🗓️ Еженедельно", callback_data="repeat_weekly_for_edit")
    )
    keyboard.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu"))
    keyboard.adjust(2, 2, 1)
    return keyboard.as_markup()

def get_settings_keyboard():
    """Клавиатура с настройками"""
    keyboard = InlineKeyboardBuilder()
    keyboard.add(
        InlineKeyboardButton(text="🔔 Уведомления", callback_data="notifications"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="statistics"),
        InlineKeyboardButton(text="🚫 Отключить все", callback_data="disable_all"),
        InlineKeyboardButton(text="🗑️ Очистить все", callback_data="clear_all_reminders")
    )
    keyboard.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu"))
    keyboard.adjust(2, 2, 1)
    return keyboard.as_markup()

def get_confirmation_keyboard(action):
    """Клавиатура с подтверждением действия"""
    keyboard = InlineKeyboardBuilder()
    keyboard.add(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{action}"),
        InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_action")
    )
    keyboard.adjust(2)
    return keyboard.as_markup()

def get_back_keyboard():
    """Клавиатура с кнопкой назад"""
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu"))
    return keyboard.as_markup()