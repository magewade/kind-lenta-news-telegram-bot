from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from lexicon.lexicon import LEXICON
import aiohttp
from aiogram import Router

# Инициализируем роутер уровня модуля
router = Router()

@router.message(CommandStart())
async def process_start_command(message: Message):
    await message.answer(text=LEXICON['/start'])

@router.message(Command(commands='help'))
async def process_help_command(message: Message):
    await message.answer(text=LEXICON['/help'])

@router.message(Command(commands="cat"))  # Используем router.message вместо dp.message
async def cat_message(message: Message):

    url = "https://api.thecatapi.com/v1/images/search"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            print(f"Ответ API: {response.status}")  

            if response.status == 200:
                data = await response.json()
                print("Ответ API (JSON):", data)  

                if data and isinstance(data, list) and "url" in data[0]:
                    cat_url = data[0]["url"]
                    await message.answer_photo(photo=cat_url)
                else:
                    print("Ошибка: ключ 'url' не найден в JSON")
                    await message.answer("Не могу найти котика 😿")
            else:
                print(f"Ошибка API: {response.status}")
                await message.answer(f"Ошибка API: {response.status}")
