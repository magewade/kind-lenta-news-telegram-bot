from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

main = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Сегодня", callback_data="today")
        ],
        [
            InlineKeyboardButton(text="Вчера", callback_data="yesterday")
        ],
        [
            InlineKeyboardButton(text="Еще более ранние новости", callback_data="older")
        ],
        [
            InlineKeyboardButton(
                text="Просто глянуть на котика 🐈", callback_data="send_cat"
            )
        ]
    ]
)


cat_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Ещё котик 🐈‍⬛", callback_data="send_cat")]
    ]
)
