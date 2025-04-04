import pickle
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

model = SentenceTransformer("sberbank-ai/sbert_large_nlu_ru")


def update_missing_embeddings(conn):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, content FROM articles WHERE embedding IS NULL AND content IS NOT NULL"
    )
    rows = cursor.fetchall()

    print(f"Найдено {len(rows)} статей без эмбеддингов.")
    for article_id, content in tqdm(rows, desc="Векторизация новых статей"):
        try:
            # Генерируем эмбеддинг для текста
            embedding = model.encode(content, convert_to_numpy=True)

            # Преобразуем эмбеддинг в бинарный формат
            embedding_blob = embedding.tobytes()

            # Обновляем эмбеддинг для существующей статьи
            cursor.execute(
                "UPDATE articles SET embedding = ? WHERE id = ?",
                (embedding_blob, article_id),
            )
        except Exception as e:
            print(f"Ошибка при обработке статьи {article_id}: {e}")

    conn.commit()


def get_bert_embedding(text):
    # Векторизация текста с использованием модели
    return model.encode(text, convert_to_numpy=True)


