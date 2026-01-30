import asyncio
import logging
from datetime import datetime
from typing import Dict, List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .database import get_user_reminders, get_user_timezone, get_all_users_ids
from .utils import convert_time_to_user_timezone
from aiogram import Bot

logger = logging.getLogger(__name__)

class ReminderScheduler:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler()
        self.active_jobs: Dict[int, List[str]] = {}  # user_id: [job_ids]

    async def start(self):
        """Запуск планировщика"""
        self.scheduler.start()
        logger.info("Планировщик напоминаний запущен")
        
        # Загружаем все напоминания и создаем для них задачи
        await self.load_all_reminders()

    async def stop(self):
        """Остановка планировщика"""
        self.scheduler.shutdown()
        logger.info("Планировщик напоминаний остановлен")

    async def load_all_reminders(self):
        """Загрузка всех напоминаний из базы данных и создание задач"""
        # Получаем всех пользователей
        user_ids = await get_all_users_ids()
        
        for user_id in user_ids:
            # Получаем все напоминания для пользователя
            reminders = await get_user_reminders(user_id)
            
            for reminder_id, message, time, repeat_type in reminders:
                try:
                    # Добавляем задачу в планировщик
                    await self.add_reminder_job(
                        user_id=user_id,
                        reminder_id=reminder_id,
                        message=message,
                        time=time,
                        repeat_type=repeat_type
                    )
                    logger.info(f"Загружено напоминание {reminder_id} для пользователя {user_id}")
                except Exception as e:
                    logger.error(f"Ошибка при загрузке напоминания {reminder_id} для пользователя {user_id}: {e}")

    async def add_reminder_job(self, user_id: int, reminder_id: int, message: str, time: str, repeat_type: str):
        """Добавление задачи напоминания"""
        job_id = f"reminder_{user_id}_{reminder_id}"
        
        # Определяем триггер в зависимости от типа повтора
        if repeat_type == 'none':
            # Однократное напоминание
            trigger = self._get_single_trigger(time)
        elif repeat_type == 'minute':
            # Каждую минуту
            trigger = CronTrigger(minute='*', timezone=await get_user_timezone(user_id))
        elif repeat_type == 'daily':
            # Ежедневно
            hour, minute = time.split(':')
            trigger = CronTrigger(hour=int(hour), minute=int(minute), timezone=await get_user_timezone(user_id))
        elif repeat_type == 'weekly':
            # Еженедельно (например, каждый понедельник)
            hour, minute = time.split(':')
            trigger = CronTrigger(day_of_week='mon', hour=int(hour), minute=int(minute), timezone=await get_user_timezone(user_id))
        else:
            logger.error(f"Неизвестный тип повтора: {repeat_type}")
            return

        # Создаем задачу
        job = self.scheduler.add_job(
            self.send_reminder,
            trigger=trigger,
            id=job_id,
            args=[user_id, message],
            misfire_grace_time=30  # Пропущенные задачи выполняются в течение 30 секунд
        )
        
        # Сохраняем ID задачи для возможного удаления
        if user_id not in self.active_jobs:
            self.active_jobs[user_id] = []
        self.active_jobs[user_id].append(job_id)
        
        logger.info(f"Добавлено напоминание для пользователя {user_id}, ID: {job_id}")

    def _get_single_trigger(self, time: str):
        """Создание триггера для однократного напоминания"""
        # Преобразуем время в формат, подходящий для выполнения один раз
        hour, minute = time.split(':')
        now = datetime.now()
        
        # Если время уже прошло сегодня, планируем на завтра
        if now.hour > int(hour) or (now.hour == int(hour) and now.minute > int(minute)):
            # Завтра
            run_date = datetime(now.year, now.month, now.day + 1, int(hour), int(minute))
        else:
            # Сегодня
            run_date = datetime(now.year, now.month, now.day, int(hour), int(minute))
            
        return CronTrigger(
            year=run_date.year,
            month=run_date.month,
            day=run_date.day,
            hour=run_date.hour,
            minute=run_date.minute
        )

    async def send_reminder(self, user_id: int, message: str):
        """Отправка напоминания пользователю"""
        try:
            await self.bot.send_message(user_id, f"⏰ Напоминание: {message}")
            logger.info(f"Отправлено напоминание пользователю {user_id}: {message}")
        except Exception as e:
            logger.error(f"Ошибка при отправке напоминания пользователю {user_id}: {e}")

    async def remove_user_reminders(self, user_id: int):
        """Удаление всех задач напоминаний для пользователя"""
        if user_id in self.active_jobs:
            for job_id in self.active_jobs[user_id]:
                if self.scheduler.get_job(job_id):
                    self.scheduler.remove_job(job_id)
            del self.active_jobs[user_id]
            logger.info(f"Удалены все напоминания для пользователя {user_id}")

    async def remove_reminder_job(self, user_id: int, reminder_id: int):
        """Удаление конкретного напоминания"""
        job_id = f"reminder_{user_id}_{reminder_id}"
        
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            
            # Удаляем из списка активных задач пользователя
            if user_id in self.active_jobs and job_id in self.active_jobs[user_id]:
                self.active_jobs[user_id].remove(job_id)
                
            logger.info(f"Удалено напоминание для пользователя {user_id}, ID: {job_id}")