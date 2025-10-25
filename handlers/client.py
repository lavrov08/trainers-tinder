"""Обработчики для клиентов"""
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InputMediaPhoto
from aiogram.fsm.context import FSMContext

from database import Database
from keyboards.inline import get_directions_keyboard, get_trainer_view_keyboard

router = Router()


async def format_trainer_card(trainer, current_index: int, total: int) -> str:
    """Форматирование анкеты тренера"""
    return (
        f"<b>{trainer.name}</b>\n"
        f"Возраст: {trainer.age} лет\n"
        f"Опыт: {trainer.experience}\n"
        f"Направление: {trainer.direction}\n\n"
        f"<b>О себе:</b>\n{trainer.about}\n\n"
        f"Анкета {current_index + 1}/{total}"
    )


@router.callback_query(F.data.startswith("client_direction:"))
async def process_client_direction(callback: CallbackQuery, db: Database, state: FSMContext):
    """Обработчик выбора направления клиентом"""
    direction = callback.data.split(":", 1)[1]
    
    # Получаем тренеров по направлению
    trainers = await db.get_approved_trainers_by_direction(direction)
    
    if not trainers:
        await callback.message.edit_text(
            f"😔 К сожалению, пока нет тренеров в направлении <b>{direction}</b>.\n\n"
            "Попробуйте выбрать другое направление:",
            reply_markup=get_directions_keyboard(prefix="client_direction")
        )
        await callback.answer()
        return
    
    # Сохраняем в state список тренеров и текущий индекс
    await state.update_data(
        direction=direction,
        trainers=[t.id for t in trainers],
        current_index=0
    )
    
    # Показываем первого тренера
    await show_trainer(callback.message, db, state, callback.from_user.id)
    await callback.answer()


async def show_trainer(message, db: Database, state: FSMContext, user_id: int):
    """Показать анкету тренера"""
    data = await state.get_data()
    trainers_ids = data.get("trainers", [])
    current_index = data.get("current_index", 0)
    
    if not trainers_ids:
        await message.edit_text(
            "😔 Нет доступных тренеров.\n\n"
            "Выберите другое направление:",
            reply_markup=get_directions_keyboard(prefix="client_direction")
        )
        return
    
    trainer_id = trainers_ids[current_index]
    trainer = await db.get_trainer_by_id(trainer_id)
    
    if not trainer:
        await message.edit_text("❌ Ошибка: тренер не найден.")
        return
    
    # Проверяем, лайкал ли уже клиент этого тренера
    already_liked = await db.check_like_exists(user_id, trainer_id)
    
    text = await format_trainer_card(trainer, current_index, len(trainers_ids))
    keyboard = get_trainer_view_keyboard(
        trainer_id, current_index, len(trainers_ids), already_liked
    )
    
    # Если есть фото, отправляем с фото
    if trainer.photo_id:
        try:
            if message.photo:
                # Если сообщение уже содержит фото, обновляем его
                await message.edit_media(
                    media=InputMediaPhoto(media=trainer.photo_id, caption=text),
                    reply_markup=keyboard
                )
            else:
                # Если сообщение текстовое, удаляем его и отправляем новое с фото
                await message.delete()
                await message.answer_photo(
                    photo=trainer.photo_id,
                    caption=text,
                    reply_markup=keyboard
                )
        except Exception:
            # В случае ошибки отправляем текстом
            await message.edit_text(text, reply_markup=keyboard)
    else:
        # Без фото
        try:
            if message.photo:
                # Если текущее сообщение с фото, а новое без - удаляем и отправляем новое
                await message.delete()
                await message.answer(text, reply_markup=keyboard)
            else:
                await message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("next:"))
async def process_next_trainer(callback: CallbackQuery, db: Database, state: FSMContext):
    """Обработчик кнопки 'Следующий'"""
    data = await state.get_data()
    trainers_ids = data.get("trainers", [])
    current_index = data.get("current_index", 0)
    
    # Циклический переход
    new_index = (current_index + 1) % len(trainers_ids)
    await state.update_data(current_index=new_index)
    
    await show_trainer(callback.message, db, state, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data.startswith("prev:"))
async def process_prev_trainer(callback: CallbackQuery, db: Database, state: FSMContext):
    """Обработчик кнопки 'Назад'"""
    data = await state.get_data()
    trainers_ids = data.get("trainers", [])
    current_index = data.get("current_index", 0)
    
    # Циклический переход
    new_index = (current_index - 1) % len(trainers_ids)
    await state.update_data(current_index=new_index)
    
    await show_trainer(callback.message, db, state, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data.startswith("like:"))
async def process_like(callback: CallbackQuery, bot: Bot, db: Database, state: FSMContext):
    """Обработчик лайка"""
    trainer_id = int(callback.data.split(":", 1)[1])
    client_id = callback.from_user.id
    client_username = callback.from_user.username
    
    # Проверяем, есть ли уже лайк
    already_liked = await db.check_like_exists(client_id, trainer_id)
    
    if already_liked:
        await callback.answer("Вы уже лайкнули этого тренера!", show_alert=True)
        return
    
    # Добавляем лайк
    success = await db.add_like(client_id, client_username, trainer_id)
    
    if success:
        # Получаем информацию о тренере
        trainer = await db.get_trainer_by_id(trainer_id)
        
        # Отправляем уведомление тренеру
        if trainer:
            contact_info = f"@{client_username}" if client_username else f"ID: {client_id}"
            try:
                await bot.send_message(
                    trainer.user_id,
                    f"❤️ <b>У вас новый лайк!</b>\n\n"
                    f"Клиент заинтересовался вашими услугами.\n"
                    f"Контакт: {contact_info}\n\n"
                    f"Свяжитесь с ним для обсуждения деталей!"
                )
            except Exception:
                pass  # Если не удалось отправить (например, бот заблокирован)
        
        await callback.answer("❤️ Лайк отправлен! Тренер получит ваш контакт.", show_alert=True)
        
        # Обновляем клавиатуру
        await show_trainer(callback.message, db, state, client_id)
    else:
        await callback.answer("❌ Ошибка при добавлении лайка.", show_alert=True)


@router.callback_query(F.data == "already_liked")
async def process_already_liked(callback: CallbackQuery):
    """Обработчик нажатия на кнопку уже лайкнутого тренера"""
    await callback.answer("Вы уже лайкнули этого тренера!", show_alert=True)


@router.callback_query(F.data == "back_to_directions")
async def process_back_to_directions(callback: CallbackQuery, state: FSMContext):
    """Обработчик возврата к выбору направления"""
    await state.clear()
    
    # Удаляем старое сообщение если оно с фото
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    await callback.message.answer(
        "Выберите интересующее направление тренировок:",
        reply_markup=get_directions_keyboard(prefix="client_direction")
    )
    await callback.answer()

