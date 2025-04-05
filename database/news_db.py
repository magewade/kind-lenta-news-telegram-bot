import sqlite3
from datetime import datetime, timedelta
import re
import sqlite3
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from model.embeddings import get_bert_embedding
import numpy as np

# Перевод месяцев
month_translation = {
    "january": "января",
    "february": "февраля",
    "march": "марта",
    "april": "апреля",
    "may": "мая",
    "june": "июня",
    "july": "июля",
    "august": "августа",
    "september": "сентября",
    "october": "октября",
    "november": "ноября",
    "december": "декабря",
}


def parse_datetime(date_string):
    """Парсит строку с датой в datetime: поддержка SQL-формата и русского человекочитаемого"""
    try:
        return datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        pass

    try:
        reversed_months = {v: k for k, v in month_translation.items()}
        for ru_month, eng_month in reversed_months.items():
            if ru_month in date_string.lower():
                date_string = re.sub(
                    ru_month, eng_month, date_string, flags=re.IGNORECASE
                )
                break
        return datetime.strptime(date_string, "%H:%M, %d %B %Y")
    except ValueError as e:
        print(f"[ERROR] Не удалось разобрать дату: {date_string}, ошибка: {e}")
        return None


def format_date(date):
    """Форматирует дату в нужный вид"""
    return date.strftime("%d %B %Y")


# Добавление новой колонки в таблицу
def add_normalized_date_column():
    conn = sqlite3.connect("news_database.db")
    cursor = conn.cursor()
    cursor.execute("ALTER TABLE articles ADD COLUMN normalized_date TEXT")
    conn.commit()
    conn.close()


# Обновление всех старых новостей с нормализованной датой
def update_normalized_dates():
    conn = sqlite3.connect("news_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT rowid, date FROM articles")
    news = cursor.fetchall()

    for row in news:
        rowid, date_str = row
        normalized_date = parse_datetime(date_str)
        if normalized_date:
            cursor.execute(
                "UPDATE articles SET normalized_date = ? WHERE rowid = ?",
                (normalized_date.strftime("%Y-%m-%d %H:%M:%S"), rowid),
            )

    conn.commit()
    conn.close()


# Получение новостей за сегодня
def get_today_news(limit=100):
    conn = sqlite3.connect("news_database.db")
    cursor = conn.cursor()

    today = datetime.now().date()
    query = """
    SELECT title, url, subtitle, content, normalized_date, author
    FROM articles 
    WHERE normalized_date LIKE ?
    ORDER BY normalized_date DESC
    LIMIT ?;
    """
    cursor.execute(query, (f"{today}%", limit))
    news = cursor.fetchall()

    print(f"[LOG] Найдено {len(news)} новостей за сегодня")

    result = {
        i + 1: (title, url, subtitle, content, date_str, author)
        for i, (title, url, subtitle, content, date_str, author) in enumerate(news)
    }

    conn.close()
    return result


# Получение новостей за вчера
def get_yesterday_news(limit=100):
    conn = sqlite3.connect("news_database.db")
    cursor = conn.cursor()

    yesterday = (datetime.now() - timedelta(days=1)).date()
    query = """
    SELECT title, url, subtitle, content, normalized_date, author
    FROM articles 
    WHERE normalized_date LIKE ?
    ORDER BY normalized_date DESC
    LIMIT ?;
    """
    cursor.execute(query, (f"{yesterday}%", limit))
    news = cursor.fetchall()

    print(f"[LOG] Найдено {len(news)} новостей за вчера")

    result = {
        i + 1: (title, url, subtitle, content, date_str, author)
        for i, (title, url, subtitle, content, date_str, author) in enumerate(news)
    }

    conn.close()
    return result


# Получение новостей с позавчера и старше
def get_news_from_day_before_yesterday_and_older(limit=100):
    conn = sqlite3.connect("news_database.db")
    cursor = conn.cursor()

    day_before_yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    query = """
    SELECT title, url, subtitle, content, normalized_date, author
    FROM articles 
    WHERE normalized_date <= ? 
    ORDER BY normalized_date DESC
    LIMIT ?;
    """
    cursor.execute(query, (day_before_yesterday, limit))
    news = cursor.fetchall()

    print(f"[LOG] Найдено {len(news)} новостей с {day_before_yesterday} и ранее")

    result = {
        i + 1: (title, url, subtitle, content, date_str, author)
        for i, (title, url, subtitle, content, date_str, author) in enumerate(news)
    }

    conn.close()
    return result


import pickle
import numpy as np


def get_news_embeddings_from_db(cursor, limit=1000, offset=0):
    query = """
    SELECT id, title, url, subtitle, content, normalized_date, embedding
    FROM articles
    ORDER BY normalized_date DESC
    LIMIT ? OFFSET ?;
    """
    cursor.execute(query, (limit, offset))
    news = cursor.fetchall()

    news_texts = []
    news_embeddings = []

    for news_item in news:
        news_id, title, url, subtitle, content, date, embedding_blob = news_item

        # Восстанавливаем эмбеддинг из байтов
        embedding = np.frombuffer(embedding_blob, dtype=np.float32)

        # Убедимся, что эмбеддинг имеет правильную форму
        if embedding.shape[0] != 1024:  # Если размерность эмбеддинга не 1024
            print(f"Warning: эмбеддинг для новости {news_id} имеет неправильную форму.")
            continue

        # Добавляем данные в список
        news_texts.append((title, url, subtitle, content, date))
        news_embeddings.append(embedding)

    return news_texts, np.array(news_embeddings)


def search_news_by_keyword(keyword, limit=50, offset=0, similarity_threshold=0.2):
    conn = sqlite3.connect("news_database.db")
    cursor = conn.cursor()

    # Получаем эмбеддинг для запроса (ключевого слова)
    query_embedding = get_bert_embedding(keyword).reshape(1, -1)

    if query_embedding is None or query_embedding.size == 0:
        raise ValueError(f"Получен пустой эмбеддинг для ключевого слова '{keyword}'")

    # Извлекаем эмбеддинги новостей
    news_texts, news_embeddings = get_news_embeddings_from_db(cursor, limit, offset)

    # Считаем сходство между запросом и эмбеддингами новостей
    sims = cosine_similarity(query_embedding, news_embeddings)[0]

    results = []
    for i, similarity in enumerate(sims):
        if similarity >= similarity_threshold:
            results.append(
                {
                    "title": news_texts[i][0],
                    "url": news_texts[i][1],
                    "subtitle": news_texts[i][2],
                    "content": news_texts[i][3],
                    "date": news_texts[i][4],
                    "similarity": similarity,
                }
            )

    conn.close()

    # Сортируем по сходству и возвращаем результаты
    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results[:limit]  # Возвращаем только нужное количество


update_normalized_dates()
