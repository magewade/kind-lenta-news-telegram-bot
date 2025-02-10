import asyncio
from aiogram import Bot, Dispatcher
from config_data.config import Config, load_config
from handlers import other_handlers, user_handlers
import logging
from aiogram.types import BotCommand



# Функция конфигурирования и запуска бота
async def main():
    logging.basicConfig(
    level=logging.INFO,
    format='%(filename)s:%(lineno)d #%(levelname)-8s '
            '[%(asctime)s] - %(name)s - %(message)s')

    # Загружаем конфиг в переменную config
    config: Config = load_config()
    
    # Инициализируем бот и диспетчер
    try:
        bot = Bot(token=config.tg_bot.token)
    except AttributeError:
        logging.critical("Ошибка: не могу инициализировать бота, "
                         "проверьте корректность конфигурации")
        return

    bot = Bot(token=config.tg_bot.token)
    dp = Dispatcher()

    # Регистриуем роутеры в диспетчере
    dp.include_router(user_handlers.router)
    dp.include_router(other_handlers.router)
    

    # Пропускаем накопившиеся апдейты и запускаем polling
    dp.startup.register(set_main_menu)
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        logging.error(f"Ошибка при удалении вебхука: {e}")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logging.critical(f"Ошибка при запуске поллинга: {e}")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)
    
async def set_main_menu(bot: Bot):

    # Создаем список с командами и их описанием для кнопки menu
    main_menu_commands = [
        BotCommand(command='/help',
                   description='Справка по работе бота'),
        BotCommand(command='/cat',
                   description='Отправляет картинку котика')
    ]

    try:
        await bot.set_my_commands(main_menu_commands)
    except Exception as e:
        logging.error(f"Ошибка при установке кнопки menu: {e}")
    await bot.set_my_commands(main_menu_commands)


asyncio.run(main())
