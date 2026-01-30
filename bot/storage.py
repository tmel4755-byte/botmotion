"""Модуль для хранения глобальных объектов"""

from typing import Optional
from .scheduler import ReminderScheduler

# Глобальная переменная для хранения экземпляра планировщика
scheduler: Optional[ReminderScheduler] = None


def set_scheduler(scheduler_instance: ReminderScheduler):
    """Установка экземпляра планировщика"""
    global scheduler
    scheduler = scheduler_instance


def get_scheduler() -> Optional[ReminderScheduler]:
    """Получение экземпляра планировщика"""
    return scheduler