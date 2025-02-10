from utils import NDTOpenAI
from config_data.config import Config, load_config


config: Config = load_config()

course_api_key = config.tg_bot.open_ai_key

client = NDTOpenAI(
    api_key=course_api_key,  # ключ для доступа к апи
)


prompt = "Че каго"

messages = [
    {
        "role": "user",  # Роль - ассистент или юзер
        "content": prompt ,  # Сам промпт для подачи в ChatGPT
    }
]

response = client.chat.completions.create(
    model="gpt-3.5-turbo",  # модель для выбора
    messages=messages,  # сообщение
    temperature=0,  # степень креативности ответа
)

print(response.choices[0].message.content)