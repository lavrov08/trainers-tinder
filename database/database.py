"""Работа с базой данных"""
import aiosqlite
from typing import Optional, List
from .models import User, Client, Trainer, Like


class Database:
    """Класс для работы с SQLite базой данных"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    async def init_db(self):
        """Инициализация базы данных"""
        async with aiosqlite.connect(self.db_path) as db:
            # Таблица пользователей
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    role TEXT
                )
            """)
            
            # Таблица клиентов с лайками
            await db.execute("""
                CREATE TABLE IF NOT EXISTS clients (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    likes_count INTEGER DEFAULT 5,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Таблица анкет тренеров
            await db.execute("""
                CREATE TABLE IF NOT EXISTS trainers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE,
                    username TEXT,
                    direction TEXT NOT NULL,
                    name TEXT NOT NULL,
                    age INTEGER NOT NULL,
                    experience TEXT NOT NULL,
                    about TEXT NOT NULL,
                    photo_id TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Таблица лайков
            await db.execute("""
                CREATE TABLE IF NOT EXISTS likes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id INTEGER NOT NULL,
                    client_username TEXT,
                    trainer_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(client_id, trainer_id),
                    FOREIGN KEY (client_id) REFERENCES users (user_id),
                    FOREIGN KEY (trainer_id) REFERENCES trainers (id)
                )
            """)
            
            await db.commit()
    
    # === Пользователи ===
    
    async def add_user(self, user_id: int, username: Optional[str], role: Optional[str] = None):
        """Добавить или обновить пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO users (user_id, username, role) VALUES (?, ?, ?)",
                (user_id, username, role)
            )
            await db.commit()
    
    async def get_user(self, user_id: int) -> Optional[User]:
        """Получить пользователя по ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return User(**dict(row))
                return None
    
    async def update_user_role(self, user_id: int, role: str):
        """Обновить роль пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET role = ? WHERE user_id = ?",
                (role, user_id)
            )
            await db.commit()
    
    # === Клиенты ===
    
    async def create_client(self, user_id: int, username: Optional[str], initial_likes: int = 5):
        """Создать клиента с начальным количеством лайков"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO clients (user_id, username, likes_count) VALUES (?, ?, ?)",
                (user_id, username, initial_likes)
            )
            await db.commit()
    
    async def get_client(self, user_id: int) -> Optional[Client]:
        """Получить клиента по ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM clients WHERE user_id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return Client(**dict(row))
                return None
    
    async def get_client_likes(self, user_id: int) -> int:
        """Получить количество лайков клиента"""
        client = await self.get_client(user_id)
        return client.likes_count if client else 0
    
    async def decrease_client_likes(self, user_id: int, amount: int = 1) -> bool:
        """Уменьшить количество лайков клиента. Возвращает True если успешно"""
        async with aiosqlite.connect(self.db_path) as db:
            # Проверяем, достаточно ли лайков
            async with db.execute(
                "SELECT likes_count FROM clients WHERE user_id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if not row or row[0] < amount:
                    return False
            
            # Уменьшаем
            await db.execute(
                "UPDATE clients SET likes_count = likes_count - ? WHERE user_id = ?",
                (amount, user_id)
            )
            await db.commit()
            return True
    
    async def add_client_likes(self, user_id: int, amount: int):
        """Добавить лайки клиенту"""
        async with aiosqlite.connect(self.db_path) as db:
            # Если клиента нет, создаем с указанным количеством
            await db.execute(
                "INSERT INTO clients (user_id, likes_count) VALUES (?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET likes_count = likes_count + ?",
                (user_id, amount, amount)
            )
            await db.commit()
    
    async def get_client_by_username(self, username: str) -> Optional[Client]:
        """Получить клиента по username"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM clients WHERE username = ?", (username,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return Client(**dict(row))
                return None
    
    # === Тренеры ===
    
    async def create_trainer(self, trainer: Trainer) -> int:
        """Создать или обновить анкету тренера"""
        async with aiosqlite.connect(self.db_path) as db:
            # Проверяем, есть ли уже анкета у этого пользователя
            async with db.execute(
                "SELECT id FROM trainers WHERE user_id = ?", (trainer.user_id,)
            ) as cursor:
                existing = await cursor.fetchone()
            
            if existing:
                # Обновляем существующую анкету
                trainer_id = existing[0]
                await db.execute("""
                    UPDATE trainers 
                    SET username = ?, direction = ?, name = ?, age = ?, 
                        experience = ?, about = ?, photo_id = ?, status = ?
                    WHERE user_id = ?
                """, (
                    trainer.username, trainer.direction, trainer.name, 
                    trainer.age, trainer.experience, trainer.about, 
                    trainer.photo_id, trainer.status, trainer.user_id
                ))
                await db.commit()
                return trainer_id
            else:
                # Создаем новую анкету
                cursor = await db.execute("""
                    INSERT INTO trainers 
                    (user_id, username, direction, name, age, experience, about, photo_id, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    trainer.user_id, trainer.username, trainer.direction,
                    trainer.name, trainer.age, trainer.experience,
                    trainer.about, trainer.photo_id, trainer.status
                ))
                await db.commit()
                return cursor.lastrowid
    
    async def get_trainer_by_user_id(self, user_id: int) -> Optional[Trainer]:
        """Получить анкету тренера по user_id"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM trainers WHERE user_id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return Trainer(**dict(row))
                return None
    
    async def get_trainer_by_id(self, trainer_id: int) -> Optional[Trainer]:
        """Получить анкету тренера по ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM trainers WHERE id = ?", (trainer_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return Trainer(**dict(row))
                return None
    
    async def get_pending_trainers(self) -> List[Trainer]:
        """Получить анкеты тренеров на модерации"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM trainers WHERE status = 'pending' ORDER BY created_at"
            ) as cursor:
                rows = await cursor.fetchall()
                return [Trainer(**dict(row)) for row in rows]
    
    async def get_approved_trainers_by_direction(self, direction: str) -> List[Trainer]:
        """Получить одобренных тренеров по направлению"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM trainers WHERE status = 'approved' AND direction = ? ORDER BY created_at DESC",
                (direction,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [Trainer(**dict(row)) for row in rows]
    
    async def get_all_approved_trainers(self) -> List[Trainer]:
        """Получить всех одобренных тренеров"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM trainers WHERE status = 'approved' ORDER BY direction, created_at DESC"
            ) as cursor:
                rows = await cursor.fetchall()
                return [Trainer(**dict(row)) for row in rows]
    
    async def update_trainer_status(self, trainer_id: int, status: str):
        """Обновить статус анкеты тренера"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE trainers SET status = ? WHERE id = ?",
                (status, trainer_id)
            )
            await db.commit()
    
    async def delete_trainer(self, trainer_id: int):
        """Удалить анкету тренера"""
        async with aiosqlite.connect(self.db_path) as db:
            # Сначала удаляем связанные лайки
            await db.execute("DELETE FROM likes WHERE trainer_id = ?", (trainer_id,))
            # Затем удаляем тренера
            await db.execute("DELETE FROM trainers WHERE id = ?", (trainer_id,))
            await db.commit()
    
    # === Лайки ===
    
    async def add_like(self, client_id: int, client_username: Optional[str], trainer_id: int):
        """Добавить лайк"""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute(
                    "INSERT INTO likes (client_id, client_username, trainer_id) VALUES (?, ?, ?)",
                    (client_id, client_username, trainer_id)
                )
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                # Лайк уже существует
                return False
    
    async def get_trainer_likes(self, trainer_id: int) -> List[Like]:
        """Получить все лайки для тренера"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM likes WHERE trainer_id = ? ORDER BY created_at DESC",
                (trainer_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [Like(**dict(row)) for row in rows]
    
    async def check_like_exists(self, client_id: int, trainer_id: int) -> bool:
        """Проверить, есть ли уже лайк"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT 1 FROM likes WHERE client_id = ? AND trainer_id = ?",
                (client_id, trainer_id)
            ) as cursor:
                row = await cursor.fetchone()
                return row is not None

