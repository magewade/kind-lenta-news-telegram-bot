from aiogram import Router
from aiogram.types import Message
from lexicon.lexicon import LEXICON
from utils import NDTOpenAI
from config_data.config import Config, load_config

# Инициализируем роутер уровня модуля
router = Router()
config: Config = load_config()

course_api_key = config.tg_bot.open_ai_key


@router.message()
async def open_ai_answer(message: Message):
    try:
        client = NDTOpenAI(api_key=course_api_key)  # ключ для доступа к API

        prompt = message.text  # Получаем текст сообщения пользователя

        messages = [
            {
                "role": "user",  # Роль - ассистент или юзер
                "content": prompt,  # Сам промпт для подачи в ChatGPT
            }
        ]

        response = client.chat.completions.create(
            model="gpt-4o-mini",  # модель для выбора
            messages=messages,  # сообщение
            temperature=1,  # степень креативности ответа
        )

        await message.reply(text=response.choices[0].message.content)

    except Exception as e:
        await message.reply(text=LEXICON['no_echo'])