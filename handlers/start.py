"""Обработчики команды start и выбора роли"""
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database import Database
from keyboards.inline import get_role_keyboard, get_directions_keyboard
from states import TrainerRegistration
from config import ADMIN_IDS

router = Router()


def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    return user_id in ADMIN_IDS


@router.message(CommandStart())
async def cmd_start(message: Message, db: Database, state: FSMContext):
    """Обработчик команды /start"""
    await state.clear()
    
    user_id = message.from_user.id
    username = message.from_user.username
    
    # Добавляем пользователя в БД
    await db.add_user(user_id, username)
    
    # Базовое приветствие
    welcome_text = (
        "👋 <b>Добро пожаловать в Tinder для тренеров!</b>\n"
        "<i>made by <b>@cultphysique</b> </i>\n\n"
        "Спасибо, что подписались на нас! 💪\n\n"
        "🎁 <b>Подарок для новых подписчиков:</b>\n"
        "Бесплатная консультация у <b>ЛЮБОГО</b> нашего специалиста по <b>ЛЮБОМУ</b> интересующему вас вопросу!\n\n"
    )

    
    # Если пользователь - администратор, добавляем информацию о командах
    if is_admin(user_id):
        welcome_text += (
            "👨‍💼 <b>Вы являетесь администратором!</b>\n\n"
            "📋 <b>Доступные команды:</b>\n"
            "/start - Главное меню\n"
            "/admin или /stats - Панель администратора\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
        )
    
    welcome_text += "Выберите свою роль:"
    
    await message.answer(
        welcome_text,
        reply_markup=get_role_keyboard()
    )


@router.callback_query(F.data == "role_client")
async def process_client_role(callback: CallbackQuery, db: Database, state: FSMContext):
    """Обработчик выбора роли клиента"""
    await state.clear()
    
    user_id = callback.from_user.id
    username = callback.from_user.username
    
    # Обновляем роль пользователя
    await db.update_user_role(user_id, "client")
    
    # Проверяем, есть ли уже запись клиента
    existing_client = await db.get_client(user_id)
    if not existing_client:
        # Создаем клиента с 5 лайками
        await db.create_client(user_id, username, initial_likes=5)
    
    # Получаем текущее количество лайков
    likes_count = await db.get_client_likes(user_id)
    
    await callback.message.edit_text(
        f"👤 Вы выбрали роль <b>клиента</b>.\n\n"
        f"💖 У вас <b>{likes_count}</b> лайков.\n\n"
        "Выберите интересующее направление тренировок:",
        reply_markup=get_directions_keyboard(prefix="client_direction")
    )
    await callback.answer()


@router.callback_query(F.data == "role_trainer")
async def process_trainer_role(callback: CallbackQuery, db: Database, state: FSMContext):
    """Обработчик выбора роли тренера"""
    user_id = callback.from_user.id
    
    # Проверяем, есть ли уже анкета
    existing_trainer = await db.get_trainer_by_user_id(user_id)
    
    if existing_trainer:
        if existing_trainer.status == "pending":
            await callback.message.edit_text(
                "⏳ Ваша анкета находится на модерации.\n"
                "Пожалуйста, дождитесь решения администратора."
            )
        elif existing_trainer.status == "approved":
            await callback.message.edit_text(
                "✅ Ваша анкета уже одобрена и активна!\n\n"
                "Вы будете получать уведомления, когда клиенты лайкают вашу анкету."
            )
        elif existing_trainer.status == "rejected":
            await callback.message.edit_text(
                "❌ Ваша предыдущая анкета была отклонена.\n\n"
                "Вы можете создать новую анкету.\n"
                "Выберите направление:",
                reply_markup=get_directions_keyboard(prefix="trainer_direction")
            )
            await state.set_state(TrainerRegistration.waiting_for_direction)
        await callback.answer()
        return
    
    # Обновляем роль пользователя
    await db.update_user_role(user_id, "trainer")
    
    await callback.message.edit_text(
        "💪 Вы выбрали роль <b>тренера</b>.\n\n"
        "Давайте создадим вашу анкету!\n\n"
        "⚠️ <b>ВАЖНО:</b> Не указывайте в анкете свои контакты (телефон, email, соцсети).\n"
        "Заинтересованные клиенты смогут связаться с вами через Telegram.\n\n"
        "Выберите ваше основное направление:",
        reply_markup=get_directions_keyboard(prefix="trainer_direction")
    )
    await state.set_state(TrainerRegistration.waiting_for_direction)
    await callback.answer()

