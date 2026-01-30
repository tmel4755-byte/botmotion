import pytz
from datetime import datetime
from typing import Optional

def convert_time_to_user_timezone(time_str: str, user_timezone: str) -> str:
    """
    Преобразование времени из UTC в пользовательский часовой пояс
    
    Args:
        time_str: Время в формате HH:MM (по UTC)
        user_timezone: Часовой пояс пользователя (например, 'Europe/Moscow')
    
    Returns:
        Время в формате HH:MM в пользовательском часовом поясе
    """
    try:
        # Создаем объект datetime с сегодняшней датой и указанным временем (в UTC)
        utc_time = datetime.strptime(time_str, '%H:%M').time()
        combined_datetime = datetime.combine(datetime.today(), utc_time)
        
        # Устанавливаем часовой пояс UTC
        utc_tz = pytz.UTC
        utc_datetime = utc_tz.localize(combined_datetime)
        
        # Преобразуем в пользовательский часовой пояс
        user_tz = pytz.timezone(user_timezone)
        user_datetime = utc_datetime.astimezone(user_tz)
        
        return user_datetime.strftime('%H:%M')
    except Exception as e:
        print(f"Ошибка преобразования времени: {e}")
        return time_str

def validate_time_format(time_str: str) -> bool:
    """
    Проверка формата времени HH:MM
    
    Args:
        time_str: Время в строковом формате
    
    Returns:
        True если формат правильный, иначе False
    """
    try:
        parts = time_str.split(':')
        if len(parts) != 2:
            return False
        
        hour = int(parts[0])
        minute = int(parts[1])
        
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            return False
        
        return True
    except ValueError:
        return False

def format_reminder_info(message: str, time: str, repeat_type: str) -> str:
    """
    Форматирование информации о напоминании для вывода пользователю
    
    Args:
        message: Текст напоминания
        time: Время напоминания
        repeat_type: Тип повтора
    
    Returns:
        Форматированная строка с информацией о напоминании
    """
    repeat_labels = {
        'none': 'Без повтора',
        'minute': 'Каждую минуту',
        'daily': 'Ежедневно',
        'weekly': 'Еженедельно'
    }
    
    repeat_label = repeat_labels.get(repeat_type, 'Неизвестный тип')
    
    return f"📝 Напоминание: {message}\n⏰ Время: {time}\n🔄 Повтор: {repeat_label}"

def get_current_time_in_timezone(timezone: str) -> datetime:
    """
    Получение текущего времени в заданном часовом поясе
    
    Args:
        timezone: Часовой пояс (например, 'Europe/Moscow')
    
    Returns:
        Объект datetime с текущим временем в указанном часовом поясе
    """
    tz = pytz.timezone(timezone)
    return datetime.now(tz)

def parse_user_time_input(time_input: str, user_timezone: str) -> Optional[str]:
    """
    Парсинг пользовательского ввода времени и конвертация в UTC
    
    Args:
        time_input: Время в формате HH:MM в пользовательском часовом поясе
        user_timezone: Часовой пояс пользователя
    
    Returns:
        Время в формате HH:MM по UTC или None при ошибке
    """
    try:
        if not validate_time_format(time_input):
            return None
            
        # Создаем объект datetime с сегодняшней датой и введенным временем в пользовательском часовом поясе
        user_time = datetime.strptime(time_input, '%H:%M').time()
        combined_datetime = datetime.combine(datetime.today(), user_time)
        
        user_tz = pytz.timezone(user_timezone)
        user_dt_with_tz = user_tz.localize(combined_datetime)
        
        # Конвертируем во временной пояс UTC
        utc_tz = pytz.UTC
        utc_dt = user_dt_with_tz.astimezone(utc_tz)
        
        return utc_dt.strftime('%H:%M')
    except Exception as e:
        print(f"Ошибка при парсинге пользовательского времени: {e}")
        return None