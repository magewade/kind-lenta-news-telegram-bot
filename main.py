import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from aiogram import Bot, Dispatcher
from handlers.user import user


async def main():
    bot = Bot(token=os.getenv("BOT_TOKEN"))
    dp = Dispatcher()
    dp.include_router(user)
    await dp.start_polling(bot)


if __name__ == "__main__":
    print("It's alive!")
    if os.getenv("RUN_PARSER") == "1":
        import model.parsing
    else:
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            print("Bot stopped!")
