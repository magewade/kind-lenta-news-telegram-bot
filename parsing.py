import time
import sqlite3
from sqlite3 import Error
from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from tqdm import tqdm
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
from model.embeddings import update_missing_embeddings
from database.news_db import update_normalized_dates

SLEEP = 2
BASE_URL = "https://lenta.ru/"
DEBUG_MODE = False


def kind_lenta(goodnews_tumbler=True):
    if goodnews_tumbler:
        try:
            # Ждём, пока элемент появится в DOM
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".goodnews__tumbler"))
            )

            # Заново ищем элемент (если он изменился)
            tumbler = driver.find_element(By.CSS_SELECTOR, ".goodnews__tumbler")

            # Принудительно делаем его видимым
            driver.execute_script("arguments[0].style.opacity = '1';", tumbler)
            driver.execute_script("arguments[0].style.display = 'block';", tumbler)

            # Кликаем через JavaScript
            driver.execute_script("arguments[0].click();", tumbler)

            tqdm.write("Кликнули на тумблер 'Лента добра'!")

        except Exception as e:
            tqdm.write(f"Не удалось кликнуть на тумблер 'Лента добра': {e}")


# Функции для работы с базой данных
def create_connection():
    """Создание подключения к базе данных SQLite"""
    conn = None
    try:
        conn = sqlite3.connect("news_database.db")
        print("Подключение к базе данных успешно установлено.")
    except Error as e:
        print(f"Ошибка подключения: {e}")
    return conn


def create_table(conn):
    """Создание таблицы для хранения новостей, если её нет"""
    try:
        cursor = conn.cursor()

        # Проверим, существует ли уже таблица
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='articles';"
        )
        table_exists = cursor.fetchone()

        if not table_exists:
            sql_create_table = """CREATE TABLE articles (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    url TEXT,
                                    title TEXT,
                                    subtitle TEXT,
                                    author TEXT,
                                    content TEXT,
                                    date TEXT,
                                    tag TEXT,
                                    topic TEXT,
                                    last_updated TEXT
                                  );"""
            cursor.execute(sql_create_table)
            conn.commit()
            print("Таблица 'articles' успешно создана.")
        else:
            print("Таблица 'articles' уже существует.")
    except Error as e:
        print(f"Ошибка при создании таблицы: {e}")


def save_to_db(data, conn):
    """Сохранить данные в базу данных"""
    try:
        cursor = conn.cursor()

        for article_data in data:
            # Проверим, есть ли такая статья в базе
            sql_check_query = "SELECT COUNT(1) FROM articles WHERE url = ?"
            cursor.execute(
                sql_check_query, (article_data[0],)
            )  # article_data[0] — это URL статьи

            # Если статья уже есть, обновим время последнего парсинга
            if cursor.fetchone()[0] > 0:
                tqdm.write(f"Статья с URL {article_data[0]} уже существует в базе.")
                # Обновляем время последнего обновления
                sql_update_query = """UPDATE articles
                                     SET last_updated = ?
                                     WHERE url = ?"""
                cursor.execute(
                    sql_update_query,
                    (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), article_data[0]),
                )
                conn.commit()
                tqdm.write(
                    f"Обновлено время последнего парсинга для статьи {article_data[0]}"
                )
            else:
                # Если нет, то добавляем
                sql_insert_query = """INSERT INTO articles (url, title, subtitle, author, content, date, tag, topic, last_updated)
                                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"""
                cursor.execute(sql_insert_query, article_data)
                conn.commit()

    except Error as e:
        tqdm.write(f"Ошибка при сохранении в базу данных: {e}")


# Инициализация веб-драйвера
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("headless")
chrome_options.add_argument("no-sandbox")
chrome_options.add_argument("disable-dev-shm-usage")
driver = webdriver.Chrome(options=chrome_options)
driver.set_page_load_timeout(300)


def get_topics():
    """Получить список рубрик с сайта lenta.ru"""
    driver.get(BASE_URL)
    time.sleep(SLEEP)

    kind_lenta()

    # Кликнуть на бургер-меню
    menu_button = driver.find_element(
        By.CSS_SELECTOR, ".header__burger.js-burger-to-menu"
    )
    menu_button.click()
    time.sleep(SLEEP)

    # Извлекаем HTML-страницу
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")

    # Ищем все ссылки на рубрики в меню
    topics = soup.select("a.menu__nav-link._is-extra")  # Класс рубрик
    kind_lenta()
    return [
        topic["href"].strip("/")
        for topic in topics
        if topic["href"].startswith("/rubrics")
    ]

TOPICS = get_topics()

print(TOPICS)


def parse_article(article_url, topic):
    """Извлечение данных из страницы статьи"""
    try:
        driver.get(article_url)
        time.sleep(SLEEP)

        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")

        # Заголовок
        title_elem = soup.find("span", {"class": "topic-body__title"})
        title = title_elem.text.strip() if title_elem else None

        # Подзаголовок
        subtitle_elem = soup.find("div", {"class": "topic-body__title-yandex"})
        subtitle = subtitle_elem.text.strip() if subtitle_elem else None

        # Автор
        author_elem_img = soup.find("img", {"class": "topic-authors__photo"})
        author_elem_text = soup.find("span", {"class": "topic-authors__name"})
        if author_elem_img and "alt" in author_elem_img.attrs:
            author = author_elem_img["alt"].strip()
        elif author_elem_text:
            author = author_elem_text.text.strip()
        else:
            author = None

        # Содержание статьи
        content_elem = soup.find("div", {"class": "topic-body__content"})
        if content_elem:
            paragraphs = content_elem.find_all(
                "p", {"class": "topic-body__content-text"}
            )
            content = " ".join(
                paragraph.text.strip() for paragraph in paragraphs
            )  # Берем всю статью
        else:
            content = None

        # Дата публикации
        date_elem = soup.find("a", {"class": "topic-header__item topic-header__time"})
        date = date_elem.text.strip() if date_elem else None

        # Тема
        tag_elem = soup.find("a", {"class": "rubric-header__link _active"})
        tag = tag_elem.text.strip() if tag_elem else topic

        # Текущая дата для last_updated
        last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return [
            article_url,
            title,
            subtitle,
            author,
            content,
            date,
            tag,
            topic,
            last_updated,
        ]

    except Exception as e:
        tqdm.write(f"Ошибка при парсинге статьи {article_url}: {e}")
        return None


def parse_articles_by_topic():
    """Получить статьи по всем рубрикам и сохранить в базу данных"""
    all_articles = []
    processed_articles = set()  # Множество для хранения URL уже обработанных статей

    # Получаем уже сохранённые статьи из базы данных
    cursor = conn.cursor()
    cursor.execute("SELECT url FROM articles")
    existing_articles = {row[0] for row in cursor.fetchall()}

    for topic in tqdm(TOPICS, desc="Парсинг рубрик"):
        try:
            url = BASE_URL + topic
            tqdm.write(f"\nПарсим рубрику {topic}, URL: {url}")
            driver.get(url)
            time.sleep(SLEEP)

            kind_lenta()

            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")
            driver.save_screenshot(f"screenshot_{topic}.png")

            articles = soup.select("h3.card-mini__title")
            tqdm.write(f"Найдено {len(articles)} статей в рубрике {topic}")

            if DEBUG_MODE:
                articles = articles[:50]
                tqdm.write("Включен DEBUG_MODE: берём только 50 статей.")

            for article in tqdm(
                articles, desc=f"Обработка статей ({topic})", leave=False
            ):
                try:
                    parent_link = article.find_parent("a")
                    if parent_link and "href" in parent_link.attrs:
                        article_url = BASE_URL + parent_link["href"]

                        if (
                            article_url in existing_articles
                            or article_url in processed_articles
                        ):
                            # Пропускаем уже обработанные статьи
                            continue

                        tqdm.write(
                            f"Нашли статью: {article.text.strip()}, URL: {article_url}"
                        )
                        article_data = parse_article(article_url, topic)
                        if article_data:
                            all_articles.append(article_data)
                            processed_articles.add(
                                article_url
                            )  # Добавляем URL в список обработанных статей
                except Exception as e:
                    tqdm.write(
                        f"Ошибка при обработке статьи {article.text.strip()}: {e}"
                    )

            kind_lenta()

        except Exception as e:
            tqdm.write(f"Ошибка при парсинге рубрики {topic}: {e}")

    tqdm.write("Сохраняю данные в базу данных...")
    save_to_db(all_articles, conn)


# Создание подключения к базе данных
conn = create_connection()

# Создание таблицы, если она еще не существует
create_table(conn)

# Запуск парсинга и сохранение данных
print("Начало парсинга статей по темам.")

parse_articles_by_topic()

update_missing_embeddings(conn)


update_normalized_dates()

# Закрытие соединения
conn.close()
print("Парсинг завершен. Соединение с базой данных закрыто.")

# Закрытие драйвера
driver.quit()
