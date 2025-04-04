from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
import aiohttp
import keyboards.userkb as kb
from aiogram.enums import ChatAction
from keyboards.userkb import cat_keyboard
from database.news_db import (
    get_today_news,
    get_yesterday_news,
    get_news_from_day_before_yesterday_and_older as get_old_news,
    search_news_by_keyword,
)

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime
from aiogram.filters import Command

user = Router()


@user.message(CommandStart())
async def start(message: Message):
    image_url = "https://i.imgur.com/ZgCqwJc.jpeg"
    text = """Привет! 
Напиши о чем хочешь почитать новости или нажми кнопку, чтобы почитать всё подряд
    """

    await message.bot.send_chat_action(
        chat_id=message.from_user.id, action=ChatAction.TYPING
    )
    await message.answer_photo(
        photo=image_url,
        caption=text,
        message_effect_id="5046509860389126442",
        reply_markup=kb.main,
    )


@user.callback_query(F.data == "today")
async def today(callback: CallbackQuery):
    await callback.bot.send_chat_action(
        chat_id=callback.from_user.id, action=ChatAction.TYPING
    )
    news = get_today_news()  # Получаем новости за сегодня

    if not news:
        await callback.message.answer("Сегодня новостей не было 😕")
        return

    # Логируем количество новостей
    print(f"Количество новостей за сегодня: {len(news)}")

    # Индекс новости, которую показываем
    current_news_index = 0  # Начинаем с первой новости

    # Получаем новость по индексу
    news_item = list(news.values())[current_news_index]
    title, url, subtitle, content, date, author = news_item

    formatted_date = datetime.strptime(date, "%Y-%m-%d %H:%M:%S").strftime(
        "%d.%m.%Y, %H:%M"
    )

    # Формируем строку для первой новости
    response_text = (
        f"📅 **Новости за сегодня:**\n\n"
        f"🔹 **[{title}]({url})**\n"
        f"\n"
        f"{content[:3500]} \n"  # Ограничим текст до 300 символов
        f"\n"
        f"   🗓 {formatted_date}\n"
    )

    # Кнопка для следующей новости
    next_button = InlineKeyboardButton(
        text="Еще", callback_data=f"next_news_{current_news_index + 1}_today"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[next_button]])

    # Отправка первой новости с кнопкой "Еще"

    await callback.message.answer(
        response_text,
        parse_mode="Markdown",
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )
    print("Первая новость за сегодня успешно отправлена!")


@user.callback_query(F.data == "yesterday")
async def yesterday(callback: CallbackQuery):
    await callback.bot.send_chat_action(
        chat_id=callback.from_user.id, action=ChatAction.TYPING
    )
    news = get_yesterday_news()  # Получаем новости

    if not news:
        await callback.message.answer("Вчера новостей не было 😕")
        return

    # Логируем количество новостей
    print(f"Количество новостей: {len(news)}")

    # Индекс новости, которую показываем
    current_news_index = 0  # Начинаем с первой новости

    # Получаем новость по индексу
    news_item = list(news.values())[current_news_index]
    title, url, subtitle, content, date, author = news_item

    formatted_date = datetime.strptime(date, "%Y-%m-%d %H:%M:%S").strftime(
        "%d.%m.%Y, %H:%M"
    )

    # Формируем строку для первой новости
    response_text = (
        f"📅 **Новости за вчера:**\n\n"
        f"🔹 **[{title}]({url})**\n"
        f"\n"
        f"{content[:3500]} \n"  # Ограничим текст до 300 символов
        f"\n"
        f"   🗓 {formatted_date}\n"
    )

    # Кнопка для следующей новости
    next_button = InlineKeyboardButton(
        text="Еще", callback_data=f"next_news_{current_news_index + 1}_yesterday"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[next_button]])

    # Отправка первой новости с кнопкой "Еще"
    await callback.message.answer(
        response_text,
        parse_mode="Markdown",
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )


@user.callback_query(F.data == "older")
async def old_news(callback: CallbackQuery):
    await callback.bot.send_chat_action(
        chat_id=callback.from_user.id, action=ChatAction.TYPING
    )
    news = get_old_news()

    if not news:
        await callback.message.answer("Ранних новостей не нашлось 😕")
        return

    print(f"Количество ранних новостей: {len(news)}")
    current_news_index = 0
    news_item = list(news.values())[current_news_index]
    title, url, subtitle, content, date, author = news_item[:6]

    formatted_date = datetime.strptime(date, "%Y-%m-%d %H:%M:%S").strftime(
        "%d.%m.%Y, %H:%M"
    )

    response_text = (
        f"📅 **Более ранние новости:**\n\n"
        f"🔹 **[{title}]({url})**\n\n"
        f"{content[:3500]}\n\n"
        f"🗓 {formatted_date}"
    )

    next_button = InlineKeyboardButton(
        text="Еще", callback_data=f"next_news_{current_news_index + 1}_older"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[next_button]])

    await callback.message.answer(
        response_text,
        parse_mode="Markdown",
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )


@user.callback_query(F.data.startswith("next_news_"))
async def show_next_news(callback: CallbackQuery):
    # Получаем индекс новости и день из callback_data
    await callback.bot.send_chat_action(
        chat_id=callback.from_user.id, action=ChatAction.TYPING
    )
    parts = callback.data.split("_")
    print(parts)

    # Проверяем, что в parts есть достаточно элементов
    if len(parts) != 4:
        await callback.message.answer(
            "Ошибка при обработке данных. Пожалуйста, попробуйте снова."
        )
        return

    current_news_index = int(parts[2])  # Индекс новости
    day = parts[3]  # День (today, yesterday, day_before_yesterday)

    # Выбираем правильную функцию в зависимости от дня
    if day == "today":
        news = get_today_news()  # Новости за сегодня
    elif day == "yesterday":
        news = get_yesterday_news()  # Новости за вчера
    elif day == "older":
        news = get_old_news()  # Старые новости
    else:
        await callback.message.answer("Ошибка: неправильный день в запросе.")
        return

    # Проверяем, есть ли новости
    if current_news_index >= len(news):
        await callback.message.answer("Больше новостей нет 😕")
        return

    # Получаем новость по индексу
    news_item = list(news.values())[current_news_index]
    title, url, subtitle, content, date, author = news_item

    formatted_date = datetime.strptime(date, "%Y-%m-%d %H:%M:%S").strftime(
        "%d.%m.%Y, %H:%M"
    )

    # Формируем строку для новости
    response_text = (
        f"🔹 **[{title}]({url})**\n"
        f"\n"
        f"{content[:3500]} \n"  # Ограничим текст до 300 символов
        f"\n"
        f"   🗓 {formatted_date}\n"
    )

    # Кнопка для следующей новости
    if current_news_index + 1 < len(news):
        next_button = InlineKeyboardButton(
            text="Еще", callback_data=f"next_news_{current_news_index + 1}_{day}"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[next_button]])
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])  # Если новостей больше нет

    # Отправка следующей новости с кнопкой "Еще"
    await callback.message.answer(
        response_text,
        parse_mode="Markdown",
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )


@user.callback_query(F.data == "send_cat")
async def send_cat(callback: CallbackQuery):
    await callback.bot.send_chat_action(
        chat_id=callback.from_user.id, action=ChatAction.TYPING
    )
    url = "https://api.thecatapi.com/v1/images/search"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                image_url = data[0]["url"]  # Достаём ссылку на картинку

                await callback.message.answer_photo(
                    photo=image_url,
                    caption="Вот тебе котик 😺",
                    reply_markup=cat_keyboard,  # Добавляем кнопку
                )
            else:
                await callback.message.answer("Не удалось получить котика 😿")


# Обработчик команды /today# Обработчик команды /today
@user.message(Command("today"))
async def today_command(message: Message):
    print("Команда /today получена")

    # Используем message.bot для отправки действия "печатает"
    await message.bot.send_chat_action(
        chat_id=message.from_user.id, action=ChatAction.TYPING
    )

    # Теперь напрямую вызываем обработчик today, передавая ему message
    news = get_today_news()
    if not news:
        await message.answer("Сегодня новостей не было 😕")
        return

    current_news_index = 0
    news_item = list(news.values())[current_news_index]
    title, url, subtitle, content, date, author = news_item

    formatted_date = datetime.strptime(date, "%Y-%m-%d %H:%M:%S").strftime(
        "%d.%m.%Y, %H:%M"
    )

    response_text = (
        f"📅 **Новости за сегодня:**\n\n"
        f"🔹 **[{title}]({url})**\n"
        f"\n"
        f"{content[:3500]}\n"
        f"\n"
        f"   🗓 {formatted_date}\n"
    )

    next_button = InlineKeyboardButton(
        text="Еще", callback_data=f"next_news_{current_news_index + 1}_today"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[next_button]])

    await message.answer(response_text, parse_mode="Markdown", reply_markup=keyboard)


@user.message(Command("yesterday"))
async def yesterday_command(message: Message):
    print("Команда /yesterday получена")

    # Отправляем действие "печатает"
    await message.bot.send_chat_action(
        chat_id=message.from_user.id, action=ChatAction.TYPING
    )

    # Получаем новости за вчера
    news = get_yesterday_news()
    if not news:
        await message.answer("Вчера новостей не было 😕")
        return

    current_news_index = 0
    news_item = list(news.values())[current_news_index]
    title, url, subtitle, content, date, author = news_item

    formatted_date = datetime.strptime(date, "%Y-%m-%d %H:%M:%S").strftime(
        "%d.%m.%Y, %H:%M"
    )

    response_text = (
        f"📅 **Новости за вчера:**\n\n"
        f"🔹 **[{title}]({url})**\n"
        f"\n"
        f"{content[:3500]}\n"
        f"\n"
        f"   🗓 {formatted_date}\n"
    )

    next_button = InlineKeyboardButton(
        text="Еще", callback_data=f"next_news_{current_news_index + 1}_yesterday"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[next_button]])

    await message.answer(response_text, parse_mode="Markdown", reply_markup=keyboard)
    print("Первая новость за вчера успешно отправлена!")


@user.message(Command("later"))
async def later_command(message: Message):
    print("Команда /later получена")

    # Отправляем действие "печатает"
    await message.bot.send_chat_action(
        chat_id=message.from_user.id, action=ChatAction.TYPING
    )

    # Получаем новости позже
    news = get_old_news()
    if not news:
        await message.answer("Новостей на будущее нет 😕")
        return

    current_news_index = 0
    news_item = list(news.values())[current_news_index]
    title, url, subtitle, content, date, author = news_item

    formatted_date = datetime.strptime(date, "%Y-%m-%d %H:%M:%S").strftime(
        "%d.%m.%Y, %H:%M"
    )

    response_text = (
        f"📅 **Новости на будущее:**\n\n"
        f"🔹 **[{title}]({url})**\n"
        f"\n"
        f"{content[:3500]}\n"
        f"\n"
        f"   🗓 {formatted_date}\n"
    )

    next_button = InlineKeyboardButton(
        text="Еще", callback_data=f"next_news_{current_news_index + 1}_older"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[next_button]])

    await message.answer(response_text, parse_mode="Markdown", reply_markup=keyboard)


@user.message(Command("cat"))
async def cat_command(message: Message):
    print("Команда /cat получена")

    # Отправляем действие "печатает"
    await message.bot.send_chat_action(
        chat_id=message.from_user.id, action=ChatAction.TYPING
    )

    # URL для получения котика
    url = "https://api.thecatapi.com/v1/images/search"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                image_url = data[0]["url"]  # Достаём ссылку на картинку

                # Отправляем котика с кнопкой
                await message.answer_photo(
                    photo=image_url,
                    caption="Вот тебе котик 😺",
                    reply_markup=cat_keyboard,  # Добавляем кнопку
                )
            else:
                await message.answer("Не удалось получить котика 😿")


@user.message()
async def search_news(message: Message):
    print("Получено сообщение для поиска новостей:", message.text)

    # Отправляем действие "печатает"
    await message.bot.send_chat_action(
        chat_id=message.from_user.id, action=ChatAction.TYPING
    )

    # Используем введённое сообщение как ключевое слово для поиска новостей
    query = message.text.strip()

    # Проверим, что строка не пустая
    if not query:
        await message.answer("Пожалуйста, введите тему для поиска новостей.")
        return

    # Ищем новости по запросу (все новости сразу)
    news = search_news_by_keyword(query)

    if not news:
        await message.answer(f"Не найдено новостей по запросу: {query} 😕")
        return

    # Отправляем первую новость и кнопку для перехода к следующей порции
    news_item = news[0]  # Получаем первую новость
    print(news_item)

    formatted_date = datetime.strptime(news_item["date"], "%Y-%m-%d %H:%M:%S").strftime(
        "%d.%m.%Y, %H:%M"
    )

    response_text = (
        f"🔹 **[{news_item['title']}]({news_item['url']})**\n\n"
        f"{news_item['content'][:3500]}\n\n"
        f"🗓 {formatted_date}\n\n"
        f"{news_item['similarity']:.2f}% похоже на запрос"
    )

    # Первая новость, с которой можно начать поиск
    next_button = InlineKeyboardButton(
        text="Еще новости", callback_data=f"next_search_news_1_search_{query}_0"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[next_button]])

    await message.answer(response_text, parse_mode="Markdown", reply_markup=keyboard)


@user.callback_query(F.data.startswith("next_search_news_"))
async def show_next_search_news(callback: CallbackQuery):
    await callback.bot.send_chat_action(
        chat_id=callback.from_user.id, action=ChatAction.TYPING
    )

    # Разбираем данные из callback_data
    parts = callback.data.split("_")

    try:
        # Извлекаем индекс текущей новости и запрос
        current_news_index = int(parts[3])  # Индекс новости
        query = parts[5]  # Запрос (может быть несколько частей)
    except (IndexError, ValueError):
        await callback.message.answer("Ошибка в данных для следующей новости.")
        return

    # Ищем новости с учетом смещения
    news = search_news_by_keyword(query, offset=current_news_index)

    if not news:
        await callback.message.answer("Больше новостей нет по запросу нет 😕")
        return

    # Проверка, если новостей меньше, чем индекс следующей новости
    if current_news_index >= len(news):
        await callback.message.answer("Больше новостей по запросу нет 😕")
        return

    # Получаем следующую новость
    # Здесь мы используем current_news_index для правильного извлечения следующей новости
    next_news_item = news[current_news_index]  # Получаем следующую новость из списка

    formatted_date = datetime.strptime(
        next_news_item["date"], "%Y-%m-%d %H:%M:%S"
    ).strftime("%d.%m.%Y, %H:%M")

    response_text = (
        f"🔹 **[{next_news_item['title']}]({next_news_item['url']})**\n\n"
        f"{next_news_item['content'][:3500]}\n\n"
        f"🗓 {formatted_date}\n\n"
        f"{next_news_item['similarity']:.2f}% похоже на запрос"
    )

    # Кнопка для следующей новости
    next_button = InlineKeyboardButton(
        text="Еще новости",
        callback_data=f"next_search_news_{current_news_index + 1}_search_{query}",
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[next_button]])

    await callback.message.answer(
        response_text, parse_mode="Markdown", reply_markup=keyboard
    )
