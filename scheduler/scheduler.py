# scheduler/scheduler.py
from apscheduler.schedulers.blocking import BlockingScheduler
from parser.news_parser import fetch_news_page, parse_news
from db.database import save_news  # Функция сохранения новостей в БД


def job():
    try:
        html = fetch_news_page()
        news_items = parse_news(html)
        for item in news_items:
            save_news(item)  # Сохранить новость в БД (с дополнительной обработкой NLP)
        print("Новости обновлены.")
    except Exception as e:
        print(f"Ошибка при обновлении новостей: {e}")


if __name__ == "__main__":
    scheduler = BlockingScheduler()
    scheduler.add_job(job, "interval", minutes=30)  # Запускать каждые 30 минут
    scheduler.start()
