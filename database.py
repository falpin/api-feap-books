import json
import sqlite3
from dotenv import load_dotenv
import os
import string
import random

load_dotenv()

DB_PATH = os.getenv("DB_PATH")

def SQL_request(query, params=(), fetch='one', jsonify_result=False):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)

            if fetch == 'all':
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                result = [
                    {
                        col: json.loads(row[i]) if isinstance(row[i], str) and row[i].startswith('{') else row[i]
                        for i, col in enumerate(columns)
                    }
                    for row in rows
                ]

            elif fetch == 'one':
                row = cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    result = {
                        col: json.loads(row[i]) if isinstance(row[i], str) and row[i].startswith('{') else row[i]
                        for i, col in enumerate(columns)
                    }
                else:
                    result = None
            else:
                conn.commit()
                result = None

        except sqlite3.Error as e:
            print(f"Ошибка SQL: {e}")
            raise

    if jsonify_result and result is not None:
        return json.dumps(result, ensure_ascii=False, indent=2)
    return result

def create_tables():
    # Пользователи
    SQL_request('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        login TEXT NOT NULL,
        role TEXT CHECK(role IN ('user', 'admin', 'developer')) DEFAULT 'user',
        password TEXT,
        books JSON DEFAULT {},
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_login DATETIME,
        telegram_id TEXT,
        is_approved BOOLEAN DEFAULT 1
    )''')

    # книги
    SQL_request('''
    CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        author TEXT CHECK(role IN ('user', 'admin', 'developer')) DEFAULT 'user',
        description TEXT,
        image TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        user_create INTEGER REFERENCES users(id)
        is_approved BOOLEAN DEFAULT 1
    )''')


create_tables()