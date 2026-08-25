import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
import database as db
from handlers import router
import monitor
import discord_bot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

async def main():
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        logger.critical("BOT_TOKEN is missing! Please set the BOT_TOKEN environment variable in .env or on Railway.")
        sys.exit(1)

    logger.info("Initializing database...")
    await db.init_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    # Include handlers router
    dp.include_router(router)

    # Launch background monitoring worker
    monitoring_task = asyncio.create_task(monitor.start_monitoring(bot))

    # Launch Discord voice bot worker (if configured)
    discord_task = asyncio.create_task(discord_bot.start_discord_bot())

    try:
        logger.info("Clearing active webhooks and pending updates...")
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Starting Telegram bot polling...")
        await dp.start_polling(bot)
    finally:
        monitoring_task.cancel()
        discord_task.cancel()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
