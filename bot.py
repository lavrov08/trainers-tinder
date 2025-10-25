"""Главный файл бота"""
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, ADMIN_IDS
from database import Database

# Импортируем роутеры
from handlers import start, client, trainer, admin

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


async def main():
    """Главная функция запуска бота"""
    
    # Проверяем наличие токена
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не установлен! Проверьте файл .env")
        return
    
    if not ADMIN_IDS:
        logger.warning("⚠️ ADMIN_ID не установлен! Функции администратора будут недоступны.")
    else:
        logger.info(f"✅ Администраторов: {len(ADMIN_IDS)}")
    
    # Инициализируем бота и диспетчер
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Используем MemoryStorage для FSM
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Инициализируем базу данных
    from config import DATABASE_PATH
    db = Database(DATABASE_PATH)
    await db.init_db()
    logger.info("✅ База данных инициализирована")
    
    # Регистрируем middleware для передачи db в handlers
    @dp.update.outer_middleware()
    async def db_middleware(handler, event, data):
        """Middleware для передачи объекта базы данных в handlers"""
        data['db'] = db
        return await handler(event, data)
    
    # Регистрируем роутеры
    dp.include_router(start.router)
    dp.include_router(client.router)
    dp.include_router(trainer.router)
    dp.include_router(admin.router)
    
    logger.info("✅ Роутеры зарегистрированы")
    
    # Уведомляем всех админов о запуске
    if ADMIN_IDS:
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    "🤖 <b>Бот запущен!</b>\n\n"
                    "Tinder для тренеров готов к работе."
                )
            except Exception as e:
                logger.warning(f"Не удалось отправить уведомление админу {admin_id}: {e}")
    
    # Запускаем polling
    logger.info("🚀 Бот запущен!")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹ Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)

