"""Inline клавиатуры"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List
from config import TRAINING_DIRECTIONS


def get_role_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора роли"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="👤 Я клиент", callback_data="role_client")
    )
    builder.row(
        InlineKeyboardButton(text="💪 Я тренер", callback_data="role_trainer")
    )
    return builder.as_markup()


def get_directions_keyboard(prefix: str = "direction") -> InlineKeyboardMarkup:
    """Клавиатура выбора направления тренировок"""
    builder = InlineKeyboardBuilder()
    for direction in TRAINING_DIRECTIONS:
        builder.row(
            InlineKeyboardButton(
                text=direction,
                callback_data=f"{prefix}:{direction}"
            )
        )
    return builder.as_markup()


def get_trainer_view_keyboard(
    trainer_id: int,
    current_index: int,
    total: int,
    already_liked: bool = False
) -> InlineKeyboardMarkup:
    """Клавиатура для просмотра анкеты тренера"""
    builder = InlineKeyboardBuilder()
    
    # Первый ряд: лайк
    if not already_liked:
        builder.row(
            InlineKeyboardButton(
                text="❤️ Лайк",
                callback_data=f"like:{trainer_id}"
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text="✅ Вы уже лайкнули",
                callback_data="already_liked"
            )
        )
    
    # Второй ряд: навигация
    nav_buttons = []
    if total > 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"prev:{current_index}"
            )
        )
        nav_buttons.append(
            InlineKeyboardButton(
                text="➡️ Следующий",
                callback_data=f"next:{current_index}"
            )
        )
        builder.row(*nav_buttons)
    
    # Третий ряд: управление лайками
    builder.row(
        InlineKeyboardButton(
            text="💖 Мои лайки",
            callback_data="check_likes"
        ),
        InlineKeyboardButton(
            text="➕ Пополнить",
            callback_data="refill_likes"
        )
    )
    
    # Четвертый ряд: возврат к выбору направления
    builder.row(
        InlineKeyboardButton(
            text="🔙 К выбору направления",
            callback_data="back_to_directions"
        )
    )
    
    return builder.as_markup()


def get_skip_photo_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для пропуска фото"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="⏭ Пропустить фото",
            callback_data="skip_photo"
        )
    )
    return builder.as_markup()


def get_moderation_keyboard(trainer_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для модерации анкеты"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Одобрить",
            callback_data=f"approve:{trainer_id}"
        ),
        InlineKeyboardButton(
            text="❌ Отклонить",
            callback_data=f"reject:{trainer_id}"
        )
    )
    return builder.as_markup()


def get_admin_stats_keyboard() -> InlineKeyboardMarkup:
    """Главное меню статистики для админа"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="📊 Тренеры по направлениям",
            callback_data="admin_trainers_by_direction"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="👥 Все тренеры",
            callback_data="admin_all_trainers"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="💰 Начислить лайки",
            callback_data="admin_add_likes"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📋 Проверить анкеты на модерации",
            callback_data="admin_pending_trainers"
        )
    )
    return builder.as_markup()


def get_direction_stats_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора направления в статистике"""
    builder = InlineKeyboardBuilder()
    for direction in TRAINING_DIRECTIONS:
        builder.row(
            InlineKeyboardButton(
                text=direction,
                callback_data=f"admin_dir:{direction}"
            )
        )
    builder.row(
        InlineKeyboardButton(
            text="🔙 Назад",
            callback_data="admin_stats"
        )
    )
    return builder.as_markup()


def get_trainers_list_keyboard(trainers: List, page: int = 0, per_page: int = 5) -> InlineKeyboardMarkup:
    """Клавиатура со списком тренеров"""
    builder = InlineKeyboardBuilder()
    
    start = page * per_page
    end = start + per_page
    page_trainers = trainers[start:end]
    
    for trainer in page_trainers:
        builder.row(
            InlineKeyboardButton(
                text=f"{trainer.name} ({trainer.direction})",
                callback_data=f"admin_trainer:{trainer.id}"
            )
        )
    
    # Навигация по страницам
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"admin_page:{page-1}"
            )
        )
    if end < len(trainers):
        nav_buttons.append(
            InlineKeyboardButton(
                text="➡️ Вперёд",
                callback_data=f"admin_page:{page+1}"
            )
        )
    if nav_buttons:
        builder.row(*nav_buttons)
    
    builder.row(
        InlineKeyboardButton(
            text="🔙 К статистике",
            callback_data="admin_stats"
        )
    )
    
    return builder.as_markup()


def get_trainer_detail_keyboard(trainer_id: int, from_direction: str = None) -> InlineKeyboardMarkup:
    """Клавиатура для детального просмотра анкеты тренера админом"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="💕 Лайки",
            callback_data=f"admin_likes:{trainer_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🗑 Удалить анкету",
            callback_data=f"admin_delete:{trainer_id}"
        )
    )
    
    if from_direction:
        builder.row(
            InlineKeyboardButton(
                text="🔙 Назад к направлению",
                callback_data=f"admin_dir:{from_direction}"
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text="🔙 К списку тренеров",
                callback_data="admin_all_trainers"
            )
        )
    
    return builder.as_markup()


def get_confirm_delete_keyboard(trainer_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения удаления"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Да, удалить",
            callback_data=f"confirm_delete:{trainer_id}"
        ),
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=f"admin_trainer:{trainer_id}"
        )
    )
    return builder.as_markup()


def get_back_to_trainer_keyboard(trainer_id: int) -> InlineKeyboardMarkup:
    """Клавиатура возврата к анкете тренера"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🔙 Назад к анкете",
            callback_data=f"admin_trainer:{trainer_id}"
        )
    )
    return builder.as_markup()


def get_refill_tariffs_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора тарифа пополнения лайков"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="5 лайков",
            callback_data="tariff:5"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="15 лайков",
            callback_data="tariff:15"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="30 лайков",
            callback_data="tariff:30"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 Отмена",
            callback_data="cancel_refill"
        )
    )
    return builder.as_markup()


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура отмены операции"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="admin_cancel"
        )
    )
    return builder.as_markup()

