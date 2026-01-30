import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

from .config import BOT_TOKEN
from .database import init_db
from .handlers import main_router
from .scheduler import ReminderScheduler
from .storage import set_scheduler

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Основная функция запуска бота"""
    # Инициализация базы данных
    await init_db()
    
    # Создание экземпляра бота
    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
    
    # Создание диспетчера
    dp = Dispatcher()
    
    # Создание и запуск планировщика напоминаний
    scheduler = ReminderScheduler(bot)
    await scheduler.start()
    
    # Сохраняем экземпляр планировщика в глобальное хранилище
    set_scheduler(scheduler)
    
    # Подключение роутера
    dp.include_router(main_router)
    
    logger.info("Бот успешно запущен!")
    
    try:
        # Запуск поллинга
        await dp.start_polling(bot)
    finally:
        # Остановка планировщика при завершении работы
        await scheduler.stop()

if __name__ == "__main__":
    asyncio.run(main())