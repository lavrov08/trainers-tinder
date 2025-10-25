"""Конфигурация бота"""
import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

# Токен бота
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ID администраторов (может быть несколько через запятую)
def parse_admin_ids() -> List[int]:
    """Парсинг списка ID администраторов"""
    admin_ids_str = os.getenv("ADMIN_IDS", "")
    if not admin_ids_str:
        return []
    
    admin_ids = []
    for id_str in admin_ids_str.split(","):
        id_str = id_str.strip()
        if id_str.isdigit():
            admin_ids.append(int(id_str))
    return admin_ids

ADMIN_IDS = parse_admin_ids()
# Для обратной совместимости
ADMIN_ID = ADMIN_IDS[0] if ADMIN_IDS else 0

# Путь к базе данных
DATABASE_PATH = os.getenv("DATABASE_PATH", "trainers_tinder.db")

# Список направлений тренировок
TRAINING_DIRECTIONS = [
    "Фитнес",
    "Йога",
    "Растяжка/Стретчинг",
]

