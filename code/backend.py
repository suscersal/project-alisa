from fastapi.responses import FileResponse
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
from typing import List
from pydantic import BaseModel

app = FastAPI()

# Настройка CORS (разрешаем запросы с фронтенда)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Модель данных для объекта


class SportObject(BaseModel):
    name: str
    type: str
    lat: float
    lon: float


class SportObjectDB(SportObject):
    id: int

# Подключение к БД


def get_db():
    conn = sqlite3.connect('sports.db')
    conn.row_factory = sqlite3.Row
    return conn

# Создаём таблицу при старте


def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS objects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


init_db()


@app.get("/")
async def root():
    return FileResponse("index.html")

# --- API endpoints ---


@app.get("/api/objects", response_model=List[SportObjectDB])
async def get_objects():
    """Получить все спортивные объекты"""
    conn = get_db()
    cursor = conn.execute(
        'SELECT id, name, type, lat, lon FROM objects ORDER BY id')
    objects = cursor.fetchall()
    conn.close()
    return [dict(obj) for obj in objects]


@app.post("/api/objects/")
async def add_object(obj: SportObject):
    """Добавить новый объект (с проверкой данных)"""
    name = obj.name.strip()
    type_ = obj.type.strip()
    if not name:
        raise HTTPException(
            status_code=400, detail="Название не может быть пустым")
    if not type_:
        raise HTTPException(status_code=400, detail="Тип не может быть пустым")
    if not (-90 <= obj.lat <= 90):
        raise HTTPException(
            status_code=400, detail="Широта должна быть в диапазоне от -90 до 90")
    if not (-180 <= obj.lon <= 180):
        raise HTTPException(
            status_code=400, detail="Долгота должна быть в диапазоне от -180 до 180")

    conn = get_db()
    # Сравниваем в Python: SQLite LOWER() не понимает кириллицу
    for row in conn.execute('SELECT name FROM objects'):
        if row['name'].strip().casefold() == name.casefold():
            conn.close()
            raise HTTPException(
                status_code=409, detail="Объект с таким названием уже существует")

    cursor = conn.execute(
        'INSERT INTO objects (name, type, lat, lon) VALUES (?, ?, ?, ?)',
        (name, type_, obj.lat, obj.lon)
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return {"id": new_id, "message": "Объект добавлен"}


@app.delete("/api/objects/{object_id}")
async def delete_object(object_id: int):
    """Удалить объект по ID"""
    conn = get_db()
    cursor = conn.execute('DELETE FROM objects WHERE id = ?', (object_id,))
    conn.commit()
    deleted = cursor.rowcount
    conn.close()

    if deleted == 0:
        raise HTTPException(status_code=404, detail="Объект не найден")

    return {"message": "Объект удалён"}


# Запуск сервера (для прямого запуска файла)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
