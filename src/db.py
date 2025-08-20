import sqlite3
from contextlib import contextmanager
from typing import List

from .config import settings

@contextmanager
def get_conn():
    """
    Открывает соединение с БД и гарантированно закрывает его после use.
    Используем файл из settings.database_url (по умолчанию 'weather.db').
    """
    conn = sqlite3.connect(settings.database_url)
    try:
        yield conn
    finally:
        conn.close()

def init_db() -> None:
    """
    Создаёт таблицу favorites, если её ещё нет.
    Храним пары (user_id, city).
    """
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS favorites (
                user_id INTEGER NOT NULL,
                city    TEXT    NOT NULL,
                PRIMARY KEY (user_id, city)
            )
            """
        )
        conn.commit()

def add_favorite(user_id: int, city: str) -> bool:
    """
    Добавляет город в избранное пользователя.
    Возвращает True, если реально вставили (не было дубликата), иначе False.
    """
    city = city.strip()
    if not city:
        return False
    with get_conn() as conn:
        cur = conn.cursor()
        # INSERT OR IGNORE — не кидает ошибку, если уже есть такая пара
        cur.execute(
            "INSERT OR IGNORE INTO favorites (user_id, city) VALUES (?, ?)",
            (user_id, city),
        )
        conn.commit()
        return cur.rowcount > 0  # >0 — вставка произошла; 0 — была игнорирована (дубликат)

def remove_favorite(user_id: int, city: str) -> bool:
    """
    Удаляет город из избранного. True, если что-то удалили.
    """
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM favorites WHERE user_id = ? AND city = ?",
            (user_id, city.strip()),
        )
        conn.commit()
        return cur.rowcount > 0

def list_favorites(user_id: int) -> List[str]:
    """
    Возвращает список городов пользователя, отсортированный по алфавиту (без учёта регистра).
    """
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT city FROM favorites WHERE user_id = ? ORDER BY city COLLATE NOCASE",
            (user_id,),
        )
        rows = cur.fetchall()
        return [r[0] for r in rows]
