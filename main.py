import logging
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aiogram import Bot, Dispatcher
from config.settings import settings
from database.models import init_db
from handlers.student_commands import router as student_router
from handlers.admin_commands import router as admin_router
from handlers.communication import router as communication_router
from handlers.cabinet import router as cabinet_router
from handlers.ics_schedule import router as ics_router
from handlers.teacher_commands import router as teacher_router
from services.scheduler import SchedulerService

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def main():
    """Основна функція запуску бота"""
    # Check settings validity
    if not settings.is_valid():
        logger.error("Invalid configuration! Please check .env file")
        return
    
    init_db()
    logger.info("Database initialized")
    
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()
    
    # Register routers
    dp.include_router(student_router)
    dp.include_router(admin_router)
    dp.include_router(communication_router)
    dp.include_router(cabinet_router)
    dp.include_router(ics_router)
    dp.include_router(teacher_router)
    
    scheduler = SchedulerService(bot)
    scheduler.start()
    
    logger.info("Bot starting...")
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    finally:
        scheduler.stop()
        logger.info("Cleanup completed")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
