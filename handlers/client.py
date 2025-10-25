"""Обработчики для клиентов"""
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InputMediaPhoto
from aiogram.fsm.context import FSMContext

from database import Database
from keyboards.inline import get_directions_keyboard, get_trainer_view_keyboard, get_refill_tariffs_keyboard
from config import ADMIN_IDS, PLACEMENT_COST

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
    
    # Проверяем количество лайков
    likes_count = await db.get_client_likes(client_id)
    if likes_count < 1:
        await callback.answer(
            "❌ У вас закончились лайки!\n\n"
            "Используйте кнопку 'Пополнить лайки' для продолжения.",
            show_alert=True
        )
        return
    
    # Уменьшаем количество лайков
    success = await db.decrease_client_likes(client_id, 1)
    
    if not success:
        await callback.answer("❌ Недостаточно лайков!", show_alert=True)
        return
    
    # Добавляем лайк
    like_success = await db.add_like(client_id, client_username, trainer_id)
    
    if like_success:
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
        
        # Получаем новое количество лайков
        new_likes_count = await db.get_client_likes(client_id)
        
        await callback.answer(
            f"❤️ Лайк отправлен! Тренер получит ваш контакт.\n\n"
            f"Осталось лайков: {new_likes_count}",
            show_alert=True
        )
        
        # Обновляем клавиатуру
        await show_trainer(callback.message, db, state, client_id)
    else:
        # Если не удалось добавить лайк, возвращаем лайк обратно
        await db.add_client_likes(client_id, 1)
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


@router.callback_query(F.data == "check_likes")
async def process_check_likes(callback: CallbackQuery, db: Database):
    """Обработчик проверки количества лайков"""
    user_id = callback.from_user.id
    likes_count = await db.get_client_likes(user_id)
    
    await callback.answer(
        f"💖 У вас {likes_count} лайков",
        show_alert=True
    )


@router.callback_query(F.data == "refill_likes")
async def process_refill_likes(callback: CallbackQuery):
    """Обработчик запроса на пополнение лайков"""
    # Вычисляем стоимость тарифов
    tariff_5 = PLACEMENT_COST // 2
    tariff_15 = PLACEMENT_COST
    tariff_30 = PLACEMENT_COST * 2
    
    await callback.message.answer(
        "💰 <b>Выберите тариф пополнения:</b>\n\n"
        f"🔹 <b>5 лайков</b> — {tariff_5} рублей\n"
        f"🔹 <b>15 лайков</b> — {tariff_15} рублей\n"
        f"🔹 <b>30 лайков</b> — {tariff_30} рублей\n\n"
        "После выбора тарифа с вами свяжется менеджер для оплаты.",
        reply_markup=get_refill_tariffs_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tariff:"))
async def process_tariff_selection(callback: CallbackQuery, bot: Bot, db: Database):
    """Обработчик выбора тарифа"""
    likes_amount = int(callback.data.split(":", 1)[1])
    user_id = callback.from_user.id
    username = callback.from_user.username
    
    # Вычисляем стоимость
    if likes_amount == 5:
        cost = PLACEMENT_COST // 2
    elif likes_amount == 15:
        cost = PLACEMENT_COST
    elif likes_amount == 30:
        cost = PLACEMENT_COST * 2
    else:
        await callback.answer("❌ Неверный тариф", show_alert=True)
        return
    
    # Отправляем уведомление клиенту
    await callback.message.edit_text(
        f"✅ <b>Запрос на пополнение отправлен!</b>\n\n"
        f"Тариф: <b>{likes_amount} лайков</b> за {cost} рублей\n\n"
        f"Менеджер свяжется с вами в ближайшее время для оплаты.\n"
        f"После подтверждения оплаты лайки будут начислены автоматически."
    )
    
    # Отправляем уведомление всем админам
    contact_info = f"@{username}" if username else f"ID: {user_id}"
    admin_text = (
        "💰 <b>Запрос на пополнение лайков</b>\n\n"
        f"<b>Пользователь:</b> {contact_info}\n"
        f"<b>User ID:</b> <code>{user_id}</code>\n"
        f"<b>Тариф:</b> {likes_amount} лайков\n"
        f"<b>Стоимость:</b> {cost} рублей\n\n"
        f"После подтверждения оплаты используйте команду:\n"
        f"/addlikes {username if username else user_id} {likes_amount}"
    )
    
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, admin_text)
        except Exception as e:
            print(f"Ошибка отправки админу {admin_id}: {e}")
    
    await callback.answer()


@router.callback_query(F.data == "cancel_refill")
async def process_cancel_refill(callback: CallbackQuery):
    """Обработчик отмены пополнения"""
    await callback.message.delete()
    await callback.answer("Отменено")

