"""Модели данных"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    """Пользователь бота"""
    user_id: int
    username: Optional[str]
    role: Optional[str]  # 'client' или 'trainer'


@dataclass
class Trainer:
    """Анкета тренера"""
    id: Optional[int]
    user_id: int
    username: Optional[str]
    direction: str
    name: str
    age: int
    experience: str
    about: str
    photo_id: Optional[str]
    status: str  # 'pending', 'approved', 'rejected'
    created_at: Optional[str]


@dataclass
class Like:
    """Лайк клиента тренеру"""
    id: Optional[int]
    client_id: int
    client_username: Optional[str]
    trainer_id: int
    created_at: Optional[str]

