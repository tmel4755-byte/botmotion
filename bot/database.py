import aiosqlite
import logging
from typing import List, Tuple

DATABASE_PATH = 'reminders.db'

async def init_db():
    """Инициализация базы данных"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                timezone TEXT DEFAULT 'UTC'
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message TEXT NOT NULL,
                reminder_time TEXT,
                repeat_type TEXT,
                created_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        await db.commit()
        logging.info("База данных инициализирована")

async def get_user_timezone(user_id: int) -> str:
    """Получение часового пояса пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute('SELECT timezone FROM users WHERE id = ?', (user_id,)) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else 'UTC'

async def update_user_timezone(user_id: int, timezone: str):
    """Обновление часового пояса пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('UPDATE users SET timezone = ? WHERE id = ?', (timezone, user_id))
        await db.commit()

async def add_user(user_id: int, username: str = None, first_name: str = None, last_name: str = None):
    """Добавление пользователя в базу данных"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('''
            INSERT OR IGNORE INTO users (id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name))
        await db.commit()

async def add_reminder(user_id: int, message: str, reminder_time: str, repeat_type: str = None):
    """Добавление напоминания"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('''
            INSERT INTO reminders (user_id, message, reminder_time, repeat_type)
            VALUES (?, ?, ?, ?)
        ''', (user_id, message, reminder_time, repeat_type))
        await db.commit()

async def get_user_reminders(user_id: int) -> List[Tuple]:
    """Получение всех напоминаний пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute('''
            SELECT id, message, reminder_time, repeat_type
            FROM reminders
            WHERE user_id = ?
        ''', (user_id,)) as cursor:
            return await cursor.fetchall()

async def delete_reminder(reminder_id: int, user_id: int):
    """Удаление напоминания"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('DELETE FROM reminders WHERE id = ? AND user_id = ?', (reminder_id, user_id))
        await db.commit()

async def clear_all_reminders(user_id: int):
    """Удаление всех напоминаний пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('DELETE FROM reminders WHERE user_id = ?', (user_id,))
        await db.commit()

async def get_all_users():
    """Получение всех пользователей из базы данных"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute('SELECT id, timezone FROM users') as cursor:
            return await cursor.fetchall()

async def get_all_users_ids():
    """Получение всех ID пользователей из базы данных"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute('SELECT id FROM users') as cursor:
            return [row[0] for row in await cursor.fetchall()]

async def get_statistics():
    """Получение статистики использования бота"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Количество пользователей
        async with db.execute('SELECT COUNT(*) FROM users') as cursor:
            total_users = (await cursor.fetchone())[0]
        
        # Количество напоминаний
        async with db.execute('SELECT COUNT(*) FROM reminders') as cursor:
            total_reminders = (await cursor.fetchone())[0]
        
        # Количество активных напоминаний (по типам повтора)
        async with db.execute('SELECT repeat_type, COUNT(*) FROM reminders GROUP BY repeat_type') as cursor:
            active_reminders_by_type = await cursor.fetchall()
        
        return {
            'total_users': total_users,
            'total_reminders': total_reminders,
            'active_reminders_by_type': dict(active_reminders_by_type)
        }