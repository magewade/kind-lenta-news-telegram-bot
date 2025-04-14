import streamlit as st
import pandas as pd
import sqlite3
from parsing import run_parsing
from datetime import datetime, timedelta
from sentence_transformers import SentenceTransformer
import matplotlib.pyplot as plt
from database.news_db import search_news_by_keyword
from wordcloud import WordCloud
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
from model.nltk_stopwords import russian_stopwords
from pymorphy2 import MorphAnalyzer
import re

morph = MorphAnalyzer()

def lemmatize_text(text):
    words = re.findall(r"\b[а-яА-ЯёЁ]{3,}\b", text.lower())
    lemmas = [
        morph.parse(word)[0].normal_form
        for word in words
        if word not in russian_stopwords
    ]
    return " ".join(lemmas)

# Загрузка данных из базы данных
def load_articles_from_db(path_to_db="news_database.db"):
    conn = sqlite3.connect(path_to_db)
    df = pd.read_sql("SELECT * FROM articles", conn)
    conn.close()
    df["normalized_date"] = pd.to_datetime(df["normalized_date"], errors="coerce")
    return df

st.set_page_config(page_title="Новости", layout="wide")
st.title("🗞️ Добрые новости с сайта Lenta.ru")

@st.cache_resource
def load_model():
    return SentenceTransformer("sberbank-ai/sbert_large_nlu_ru")

model = load_model()

# # Кнопка для запуска парсинга
# if st.button("🔃 Обновить новости"):
#     with st.spinner("Парсим новости..."):
#         run_parsing()
#     st.success("✅ Новости обновлены!")
# Уведомление о задержке в парсинге
st.info(
    "Это демонстрация работы, и новости могут быть отпарсены с задержкой во времени. Пожалуйста, имейте в виду, что новости за 'сегодня' или 'вчера' будут отображаться от последнего доступного дня."
)

# Загрузка данных
df = load_articles_from_db()

# ВКЛАДКИ
tab1, tab2, tab3 = st.tabs(["🔍 Новости по теме", "🗓️ Новости по дате", "📊 Статистика"])

# --- ТАБ 1: Поиск по теме ---
with tab1:
    st.header("🔎 Поиск новостей по теме")

    # Инициализация переменных в session_state
    if "search_clicked" not in st.session_state:
        st.session_state.search_clicked = False
    if "last_keyword" not in st.session_state:
        st.session_state.last_keyword = ""

    # Ввод ключевого слова
    keyword = st.text_input("Введите ключевое слово или фразу для поиска:")

    # Обнуляем флаг при изменении запроса
    if keyword != st.session_state.last_keyword:
        st.session_state.search_clicked = False
        st.session_state.last_keyword = keyword

    # Кнопка запуска поиска
    if st.button("🔍 Искать"):
        st.session_state.search_clicked = True

    # Порог сходства (threshold)
    similarity_threshold = st.slider(
        "Минимальное сходство для отображения", 0.0, 1.0, 0.25, 0.05
    )

    # Сортировка по дате
    sort_by_date = st.selectbox(
        "Сортировать по дате:", ["От новых к старым", "От старых к новым"]
    )

    # Сортировка по похожести
    sort_by_similarity = st.selectbox(
        "Сортировать по похожести:",
        ["От большего к меньшему", "От меньшего к большему"],
    )

    # Отображение результатов поиска
    if st.session_state.search_clicked and keyword:
        with st.spinner("Ищем похожие новости..."):
            try:
                results = search_news_by_keyword(keyword)

                if not results:
                    st.info("К сожалению, похожих новостей не найдено.")
                else:
                    # Фильтрация по порогу сходства
                    results = [
                        res
                        for res in results
                        if res["similarity"] >= similarity_threshold
                    ]

                    # Сортировка по дате
                    if sort_by_date == "От новых к старым":
                        results = sorted(results, key=lambda x: x["date"], reverse=True)
                    else:
                        results = sorted(results, key=lambda x: x["date"])

                    # Сортировка по похожести
                    if sort_by_similarity == "От большего к меньшему":
                        results = sorted(
                            results, key=lambda x: x["similarity"], reverse=True
                        )
                    else:
                        results = sorted(results, key=lambda x: x["similarity"])

                    # Отображение результатов
                    for res in results:
                        st.markdown(f"### [{res['title']}]({res['url']})")
                        st.write(f"{res['content'][:3000]}...")
                        st.write(f"Дата: {res['date']}")
                        st.write(f"Сходство: {res['similarity']:.2f}")
                        st.write("---")

            except Exception as e:
                st.error(f"Ошибка при поиске: {e}")


# --- ТАБ 2: Новости по дате ---
with tab2:
    st.header("🗓️ Фильтр по дате")
    

    # Получаем самую последнюю дату в базе
    last_date = df["normalized_date"].max().date()

    date_filter = st.selectbox(
        "Выберите период:", ("Сегодня", "Вчера", "Более ранние новости")
    )

    def filter_news_by_date(date_filter):
        if date_filter == "Сегодня":
            filtered_df = df[df["normalized_date"].dt.date == last_date]
        elif date_filter == "Вчера":
            yesterday = last_date - timedelta(days=1)
            filtered_df = df[df["normalized_date"].dt.date == yesterday]
        else:
            filtered_df = df[
                df["normalized_date"].dt.date
                < (last_date - timedelta(days=1)).date()
            ]
        return filtered_df.sort_values(by="normalized_date", ascending=False)

    filtered_news = filter_news_by_date(date_filter)

    if filtered_news.empty:
        st.write(f"Новости за {date_filter.lower()} не найдены.")
    else:
        for _, news_item in filtered_news.iterrows():
            st.markdown(f"### [{news_item['title']}]({news_item['url']})")
            st.write(f"{news_item['content'][:3000]}...")
            st.write(
                f"Дата: {news_item['normalized_date'].strftime('%d.%m.%Y, %H:%M')}"
            )
            st.write(f"Автор: {news_item['author']}")
            st.write("---")


# --- ТАБ 3: Статистика ---
with tab3:
    st.header("📊 Статистика новостей")
    st.info(
        "Для подгрузки некоторых графиков, типа облака слов, требуется время. Пожалуйста, подождите."
    )

    # Определение ваших цветов
    colors = ["#D28782", "#EBC678", "#B4C6D0", "#1B78AF"]

    # Создание карты цветов
    cmap = LinearSegmentedColormap.from_list("custom_cmap", colors, N=256)

    # График количества новостей по дням
    df["date_only"] = df["normalized_date"].dt.date
    news_per_day = df.groupby("date_only").size().reset_index(name="count")

    fig, ax = plt.subplots(figsize=(15, 7))
    ax.plot(
        news_per_day["date_only"],
        news_per_day["count"],
        marker="o",
        color=colors[2],  # Используем первый цвет для линии
        markersize=6,
    )
    ax.set_title(
        "Количество новостей по дням", fontsize=16, color="black"
    )  # Черный цвет для заголовка
    ax.set_xlabel("Дата", fontsize=14)
    ax.set_ylabel("Количество", fontsize=14)
    plt.xticks(rotation=45)
    st.pyplot(fig, use_container_width=False)

    # Показать статистику по тегам (гистограмма по категориям)
    if "tag" in df.columns:
        st.subheader("Распределение новостей по тегам")
        tag_counts = df["tag"].value_counts()
        fig_tags, ax_tags = plt.subplots(figsize=(15, 7))
        ax_tags.bar(
            tag_counts.index,
            tag_counts.values,
            color=cmap(
                np.linspace(0, 1, len(tag_counts))
            ),  # Преобразуем cmap в список цветов
        )
        ax_tags.set_title(
            "Количество новостей по тегам", fontsize=16, color="black"
        )  # Черный цвет для заголовка
        ax_tags.set_xlabel("Тег", fontsize=14)
        ax_tags.set_ylabel("Количество", fontsize=14)
        plt.xticks(rotation=90)
        st.pyplot(fig_tags, use_container_width=False)

    # Облако слов по всем новостям без стоп-слов
    all_texts = " ".join(df["content"].dropna())
    lemmatized_text = lemmatize_text(all_texts)
    wordcloud = WordCloud(
        width=1500,
        height=700,
        background_color="white",
        colormap=cmap,  # Используем наш кастомный colormap
        max_words=200,
        stopwords=russian_stopwords,  # Добавляем стандартные стоп-слова
    ).generate(lemmatized_text)

    st.subheader("Облако слов по всем новостям")
    st.image(wordcloud.to_array(), use_container_width=False)

    # Показать статистику по темам (гистограмма по категориям)
    if "topic" in df.columns:
        st.subheader("Распределение новостей по темам")
        topic_counts = df["topic"].value_counts()
        fig_topics, ax_topics = plt.subplots(figsize=(10, 6))
        ax_topics.bar(
            topic_counts.index,
            topic_counts.values,
            color=cmap(
                np.linspace(0, 1, len(topic_counts))
            ),  # Преобразуем cmap в список цветов
        )
        ax_topics.set_title(
            "Количество новостей по темам", fontsize=16, color="black"
        )  # Черный цвет для заголовка
        ax_topics.set_xlabel("Тема", fontsize=14)
        ax_topics.set_ylabel("Количество", fontsize=14)
        plt.xticks(rotation=90)
        st.pyplot(fig_topics, use_container_width=False)
