"""Обработчики для администратора"""
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database import Database
from keyboards.inline import (
    get_moderation_keyboard,
    get_admin_stats_keyboard,
    get_direction_stats_keyboard,
    get_trainers_list_keyboard,
    get_trainer_detail_keyboard,
    get_confirm_delete_keyboard,
    get_back_to_trainer_keyboard,
    get_cancel_keyboard
)
from config import ADMIN_IDS, TRAINING_DIRECTIONS
from states import AdminAddLikes

router = Router()


async def send_admin_trainer_card_smart(message, trainer, keyboard):
    """Умная отправка анкеты тренера для админа с разделением по полю 'О себе'"""
    # Создаем основной текст без поля "О себе"
    main_text = (
        "🆕 <b>Анкета тренера на модерации</b>\n\n"
        f"<b>Имя:</b> {trainer.name}\n"
        f"<b>Возраст:</b> {trainer.age} лет\n"
        f"<b>Опыт:</b> {trainer.experience}\n"
        f"<b>Направление:</b> {trainer.direction}\n\n"
        f"<b>Username:</b> @{trainer.username if trainer.username else 'не указан'}\n"
        f"<b>User ID:</b> {trainer.user_id}"
    )
    
    # Проверяем, помещается ли основной текст + описание в лимит
    full_text = main_text + f"\n\n<b>О себе:</b>\n{trainer.about}"
    
    if len(full_text) <= 1024:
        # Если помещается - отправляем одним сообщением
        try:
            if trainer.photo_id:
                await message.answer_photo(
                    photo=trainer.photo_id,
                    caption=full_text,
                    reply_markup=keyboard
                )
            else:
                await message.answer(
                    full_text,
                    reply_markup=keyboard
                )
        except Exception as e:
            print(f"Ошибка отправки анкеты {trainer.id}: {e}")
            # В случае ошибки отправляем без фото
            await message.answer(full_text, reply_markup=keyboard)
    else:
        # Если не помещается - отправляем основную часть с фото, описание отдельно
        try:
            if trainer.photo_id:
                await message.answer_photo(
                    photo=trainer.photo_id,
                    caption=main_text
                )
            else:
                await message.answer(main_text)
            
            # Отправляем описание отдельным сообщением с кнопками
            await message.answer(
                f"<b>О себе:</b>\n{trainer.about}",
                reply_markup=keyboard
            )
        except Exception as e:
            print(f"Ошибка отправки анкеты {trainer.id}: {e}")
            # В случае ошибки отправляем все текстом
            await message.answer(full_text, reply_markup=keyboard)


def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    return user_id in ADMIN_IDS


@router.message(Command("stats"))
async def cmd_stats(message: Message, state: FSMContext):
    """Команда просмотра статистики (только для админа)"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.")
        return
    
    await state.clear()
    
    await message.answer(
        "📊 <b>Панель администратора</b>\n\n"
        "Выберите действие:",
        reply_markup=get_admin_stats_keyboard()
    )


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    """Альтернативная команда для админ-панели"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.")
        return
    
    await state.clear()
    
    await message.answer(
        "📊 <b>Панель администратора</b>\n\n"
        "Выберите действие:",
        reply_markup=get_admin_stats_keyboard()
    )


@router.callback_query(F.data == "admin_stats")
async def process_admin_stats(callback: CallbackQuery):
    """Главное меню статистики"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📊 <b>Панель администратора</b>\n\n"
        "Выберите действие:",
        reply_markup=get_admin_stats_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_trainers_by_direction")
async def process_trainers_by_direction(callback: CallbackQuery):
    """Выбор направления для просмотра тренеров"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📋 Выберите направление для просмотра тренеров:",
        reply_markup=get_direction_stats_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_dir:"))
async def process_admin_direction(callback: CallbackQuery, db: Database):
    """Просмотр тренеров конкретного направления"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    
    direction = callback.data.split(":", 1)[1]
    trainers = await db.get_approved_trainers_by_direction(direction)
    
    if not trainers:
        await callback.message.edit_text(
            f"📋 <b>Направление: {direction}</b>\n\n"
            "Тренеров пока нет.",
            reply_markup=get_direction_stats_keyboard()
        )
        await callback.answer()
        return
    
    text = f"📋 <b>Направление: {direction}</b>\n\n"
    text += f"Всего тренеров: {len(trainers)}\n\n"
    
    for i, trainer in enumerate(trainers, 1):
        likes_count = len(await db.get_trainer_likes(trainer.id))
        text += f"{i}. {trainer.name} ({trainer.age} лет) - ❤️ {likes_count}\n"
    
    # Создаем клавиатуру со списком тренеров
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    for trainer in trainers:
        builder.row(
            InlineKeyboardButton(
                text=f"👤 {trainer.name}",
                callback_data=f"admin_trainer_dir:{trainer.id}:{direction}"
            )
        )
    builder.row(
        InlineKeyboardButton(
            text="🔙 Назад",
            callback_data="admin_trainers_by_direction"
        )
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "admin_all_trainers")
async def process_all_trainers(callback: CallbackQuery, db: Database):
    """Просмотр всех тренеров"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    
    trainers = await db.get_all_approved_trainers()
    
    if not trainers:
        await callback.message.edit_text(
            "📋 <b>Все тренеры</b>\n\n"
            "Тренеров пока нет.",
            reply_markup=get_admin_stats_keyboard()
        )
        await callback.answer()
        return
    
    # Группируем по направлениям
    by_direction = {}
    for trainer in trainers:
        if trainer.direction not in by_direction:
            by_direction[trainer.direction] = []
        by_direction[trainer.direction].append(trainer)
    
    text = "📋 <b>Все одобренные тренеры</b>\n\n"
    for direction in TRAINING_DIRECTIONS:
        if direction in by_direction:
            text += f"<b>{direction}:</b> {len(by_direction[direction])}\n"
    
    text += f"\n<b>Всего:</b> {len(trainers)}"
    
    # Создаем клавиатуру со списком
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    for trainer in trainers[:10]:  # Показываем первых 10
        likes_count = len(await db.get_trainer_likes(trainer.id))
        builder.row(
            InlineKeyboardButton(
                text=f"{trainer.name} ({trainer.direction}) - ❤️ {likes_count}",
                callback_data=f"admin_trainer:{trainer.id}"
            )
        )
    
    if len(trainers) > 10:
        builder.row(
            InlineKeyboardButton(
                text=f"... и еще {len(trainers) - 10} тренеров",
                callback_data="admin_all_trainers"
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text="🔙 К статистике",
            callback_data="admin_stats"
        )
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("admin_trainer_dir:"))
async def process_trainer_detail_from_dir(callback: CallbackQuery, db: Database):
    """Детальный просмотр тренера из направления"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    
    parts = callback.data.split(":", 2)
    trainer_id = int(parts[1])
    direction = parts[2]
    
    await show_trainer_detail(callback, db, trainer_id, direction)


@router.callback_query(F.data.startswith("admin_trainer:"))
async def process_trainer_detail(callback: CallbackQuery, db: Database):
    """Детальный просмотр тренера"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    
    trainer_id = int(callback.data.split(":", 1)[1])
    await show_trainer_detail(callback, db, trainer_id)


async def show_trainer_detail(callback: CallbackQuery, db: Database, trainer_id: int, from_direction: str = None):
    """Показать детальную информацию о тренере"""
    trainer = await db.get_trainer_by_id(trainer_id)
    
    if not trainer:
        await callback.answer("❌ Тренер не найден", show_alert=True)
        return
    
    likes = await db.get_trainer_likes(trainer_id)
    
    # Создаем основной текст без поля "О себе"
    main_text = (
        f"👤 <b>Детали анкеты</b>\n\n"
        f"<b>Имя:</b> {trainer.name}\n"
        f"<b>Возраст:</b> {trainer.age} лет\n"
        f"<b>Опыт:</b> {trainer.experience}\n"
        f"<b>Направление:</b> {trainer.direction}\n"
        f"<b>Статус:</b> {trainer.status}\n"
        f"<b>Username:</b> @{trainer.username if trainer.username else 'не указан'}\n"
        f"<b>User ID:</b> {trainer.user_id}\n\n"
        f"<b>Количество лайков:</b> {len(likes)}"
    )
    
    # Проверяем, помещается ли основной текст + описание в лимит
    full_text = main_text + f"\n\n<b>О себе:</b>\n{trainer.about}"
    
    keyboard = get_trainer_detail_keyboard(trainer_id, from_direction)
    
    if len(full_text) <= 1024:
        # Если помещается - отправляем одним сообщением
        try:
            await callback.message.delete()
            if trainer.photo_id:
                await callback.message.answer_photo(
                    photo=trainer.photo_id,
                    caption=full_text,
                    reply_markup=keyboard
                )
            else:
                await callback.message.answer(full_text, reply_markup=keyboard)
        except Exception as e:
            print(f"Ошибка отправки деталей тренера {trainer.id}: {e}")
            await callback.message.answer(full_text, reply_markup=keyboard)
    else:
        # Если не помещается - отправляем основную часть с фото, описание отдельно
        try:
            await callback.message.delete()
            if trainer.photo_id:
                await callback.message.answer_photo(
                    photo=trainer.photo_id,
                    caption=main_text
                )
            else:
                await callback.message.answer(main_text)
            
            # Отправляем описание отдельным сообщением с кнопками
            await callback.message.answer(
                f"<b>О себе:</b>\n{trainer.about}",
                reply_markup=keyboard
            )
        except Exception as e:
            print(f"Ошибка отправки деталей тренера {trainer.id}: {e}")
            await callback.message.answer(full_text, reply_markup=keyboard)
    
    await callback.answer()


@router.callback_query(F.data.startswith("admin_likes:"))
async def process_admin_likes(callback: CallbackQuery, db: Database):
    """Просмотр лайков тренера"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    
    trainer_id = int(callback.data.split(":", 1)[1])
    trainer = await db.get_trainer_by_id(trainer_id)
    likes = await db.get_trainer_likes(trainer_id)
    
    if not likes:
        text = f"💕 <b>Лайки для {trainer.name}</b>\n\nПока нет лайков."
    else:
        text = f"💕 <b>Лайки для {trainer.name}</b>\n\n"
        text += f"Всего лайков: {len(likes)}\n\n"
        for i, like in enumerate(likes, 1):
            contact = f"@{like.client_username}" if like.client_username else f"ID: {like.client_id}"
            text += f"{i}. {contact}\n"
    
    # Если сообщение содержит фото, удаляем его и отправляем новое текстовое
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(
            text,
            reply_markup=get_back_to_trainer_keyboard(trainer_id)
        )
    else:
        await callback.message.edit_text(
            text,
            reply_markup=get_back_to_trainer_keyboard(trainer_id)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_delete:"))
async def process_admin_delete(callback: CallbackQuery):
    """Запрос подтверждения удаления"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    
    trainer_id = int(callback.data.split(":", 1)[1])
    
    await callback.message.edit_text(
        "⚠️ <b>Подтверждение удаления</b>\n\n"
        "Вы действительно хотите удалить эту анкету?\n"
        "Это действие нельзя отменить.",
        reply_markup=get_confirm_delete_keyboard(trainer_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete:"))
async def process_confirm_delete(callback: CallbackQuery, bot: Bot, db: Database):
    """Подтверждение удаления анкеты"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    
    trainer_id = int(callback.data.split(":", 1)[1])
    trainer = await db.get_trainer_by_id(trainer_id)
    
    if trainer:
        # Уведомляем тренера
        try:
            await bot.send_message(
                trainer.user_id,
                "❌ Ваша анкета была удалена администратором.\n\n"
                "Вы можете создать новую анкету через /start"
            )
        except Exception:
            pass
        
        # Удаляем анкету
        await db.delete_trainer(trainer_id)
        
        await callback.message.edit_text(
            f"✅ Анкета тренера <b>{trainer.name}</b> успешно удалена.",
            reply_markup=get_admin_stats_keyboard()
        )
    else:
        await callback.message.edit_text(
            "❌ Анкета не найдена.",
            reply_markup=get_admin_stats_keyboard()
        )
    
    await callback.answer()


# === Модерация анкет ===

@router.callback_query(F.data.startswith("approve:"))
async def process_approve(callback: CallbackQuery, bot: Bot, db: Database):
    """Одобрение анкеты тренера"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    
    trainer_id = int(callback.data.split(":", 1)[1])
    trainer = await db.get_trainer_by_id(trainer_id)
    
    if not trainer:
        await callback.answer("❌ Анкета не найдена", show_alert=True)
        return
    
    # Обновляем статус
    await db.update_trainer_status(trainer_id, "approved")
    
    # Уведомляем тренера
    try:
        await bot.send_message(
            trainer.user_id,
            "✅ <b>Ваша анкета одобрена!</b>\n\n"
            "Теперь клиенты могут видеть вашу анкету.\n"
            "Вы будете получать уведомления, когда кто-то лайкнет вашу анкету."
        )
    except Exception:
        pass
    
    # Обновляем сообщение (для анкет с фото используем caption, без фото - text)
    if callback.message.photo:
        await callback.message.edit_caption(
            caption=callback.message.caption + "\n\n✅ <b>ОДОБРЕНО</b>"
        )
    else:
        await callback.message.edit_text(
            text=callback.message.text + "\n\n✅ <b>ОДОБРЕНО</b>"
        )
    await callback.answer("✅ Анкета одобрена!", show_alert=True)


@router.callback_query(F.data.startswith("reject:"))
async def process_reject(callback: CallbackQuery, bot: Bot, db: Database):
    """Отклонение анкеты тренера"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    
    trainer_id = int(callback.data.split(":", 1)[1])
    trainer = await db.get_trainer_by_id(trainer_id)
    
    if not trainer:
        await callback.answer("❌ Анкета не найдена", show_alert=True)
        return
    
    # Обновляем статус
    await db.update_trainer_status(trainer_id, "rejected")
    
    # Уведомляем тренера
    try:
        await bot.send_message(
            trainer.user_id,
            "❌ <b>Ваша анкета отклонена</b>\n\n"
            "К сожалению, ваша анкета не прошла модерацию.\n"
            "Возможные причины:\n"
            "- Некорректная информация\n"
            "- Указаны контактные данные в описании\n"
            "- Нарушение правил платформы\n\n"
            "Вы можете создать новую анкету через /start"
        )
    except Exception:
        pass
    
    # Обновляем сообщение (для анкет с фото используем caption, без фото - text)
    if callback.message.photo:
        await callback.message.edit_caption(
            caption=callback.message.caption + "\n\n❌ <b>ОТКЛОНЕНО</b>"
        )
    else:
        await callback.message.edit_text(
            text=callback.message.text + "\n\n❌ <b>ОТКЛОНЕНО</b>"
        )
    await callback.answer("❌ Анкета отклонена!", show_alert=True)


# === Управление лайками клиентов ===

@router.callback_query(F.data == "admin_add_likes")
async def process_admin_add_likes_button(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Начислить лайки'"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    
    await callback.message.edit_text(
        "💰 <b>Начисление лайков клиенту</b>\n\n"
        "Введите username клиента (с @) или его User ID:\n\n"
        "Например:\n"
        "<code>@john_doe</code>\n"
        "или\n"
        "<code>123456789</code>",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(AdminAddLikes.waiting_for_user)
    await callback.answer()


@router.callback_query(F.data == "admin_cancel")
async def process_admin_cancel(callback: CallbackQuery, state: FSMContext):
    """Обработчик отмены операции"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    
    await state.clear()
    
    await callback.message.edit_text(
        "📊 <b>Панель администратора</b>\n\n"
        "Операция отменена. Выберите действие:",
        reply_markup=get_admin_stats_keyboard()
    )
    await callback.answer()


@router.message(AdminAddLikes.waiting_for_user)
async def process_admin_user_input(message: Message, state: FSMContext, db: Database):
    """Обработчик ввода username или user_id"""
    if not is_admin(message.from_user.id):
        return
    
    user_identifier = message.text.strip()
    
    # Определяем, username или user_id
    client = None
    if user_identifier.startswith("@"):
        # Это username
        username = user_identifier[1:]  # Убираем @
        client = await db.get_client_by_username(username)
        if not client:
            await message.answer(
                f"❌ Клиент с username @{username} не найден.\n\n"
                "Убедитесь, что пользователь уже использовал бота.\n"
                "Попробуйте еще раз или нажмите кнопку 'Отмена':",
                reply_markup=get_cancel_keyboard()
            )
            return
        user_id = client.user_id
    else:
        # Это user_id
        try:
            user_id = int(user_identifier)
            client = await db.get_client(user_id)
            if not client:
                await message.answer(
                    f"❌ Клиент с ID {user_id} не найден.\n\n"
                    "Убедитесь, что пользователь уже использовал бота.\n"
                    "Попробуйте еще раз или нажмите кнопку 'Отмена':",
                    reply_markup=get_cancel_keyboard()
                )
                return
        except ValueError:
            await message.answer(
                "❌ Неверный формат.\n\n"
                "Введите username (с @) или числовой User ID.\n"
                "Попробуйте еще раз или нажмите кнопку 'Отмена':",
                reply_markup=get_cancel_keyboard()
            )
            return
    
    # Сохраняем данные и переходим к следующему шагу
    current_likes = await db.get_client_likes(user_id)
    await state.update_data(
        user_identifier=user_identifier,
        user_id=user_id,
        current_likes=current_likes
    )
    await state.set_state(AdminAddLikes.waiting_for_amount)
    
    await message.answer(
        f"✅ Клиент найден: {user_identifier}\n"
        f"Текущий баланс: <b>{current_likes}</b> лайков\n\n"
        f"Введите количество лайков для начисления:",
        reply_markup=get_cancel_keyboard()
    )


@router.message(AdminAddLikes.waiting_for_amount)
async def process_admin_amount_input(message: Message, state: FSMContext, bot: Bot, db: Database):
    """Обработчик ввода количества лайков"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        likes_amount = int(message.text.strip())
        if likes_amount <= 0:
            await message.answer(
                "❌ Количество лайков должно быть положительным числом.\n"
                "Попробуйте еще раз или нажмите кнопку 'Отмена':",
                reply_markup=get_cancel_keyboard()
            )
            return
    except ValueError:
        await message.answer(
            "❌ Количество лайков должно быть числом.\n"
            "Попробуйте еще раз или нажмите кнопку 'Отмена':",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    # Получаем данные из state
    data = await state.get_data()
    user_identifier = data['user_identifier']
    user_id = data['user_id']
    
    # Начисляем лайки
    await db.add_client_likes(user_id, likes_amount)
    new_balance = await db.get_client_likes(user_id)
    
    await state.clear()
    
    # Уведомляем админа
    await message.answer(
        f"✅ <b>Лайки успешно начислены!</b>\n\n"
        f"Пользователь: {user_identifier}\n"
        f"Начислено: <b>+{likes_amount}</b> лайков\n"
        f"Новый баланс: <b>{new_balance}</b> лайков",
        reply_markup=get_admin_stats_keyboard()
    )
    
    # Уведомляем клиента
    try:
        await bot.send_message(
            user_id,
            f"🎉 <b>Ваш баланс лайков пополнен!</b>\n\n"
            f"Начислено: <b>+{likes_amount}</b> лайков\n"
            f"Текущий баланс: <b>{new_balance}</b> лайков\n\n"
            f"Продолжайте искать своего идеального тренера!"
        )
    except Exception as e:
        await message.answer(f"⚠️ Не удалось отправить уведомление клиенту: {e}")


@router.callback_query(F.data == "admin_pending_trainers")
async def process_admin_pending_trainers(callback: CallbackQuery, db: Database):
    """Обработчик кнопки 'Проверить анкеты на модерации'"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    
    pending_trainers = await db.get_pending_trainers()
    
    if not pending_trainers:
        await callback.message.edit_text(
            "📋 <b>Анкеты на модерации</b>\n\n"
            "Нет анкет, ожидающих модерации.",
            reply_markup=get_admin_stats_keyboard()
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        f"📋 <b>Анкеты на модерации</b>\n\n"
        f"Всего анкет: {len(pending_trainers)}\n\n"
        f"Анкеты отправлены вам в чат."
    )
    
    # Отправляем каждую анкету отдельным сообщением
    for trainer in pending_trainers:
        keyboard = get_moderation_keyboard(trainer.id)
        await send_admin_trainer_card_smart(callback.message, trainer, keyboard)
    
    # В конце отправляем кнопку возврата
    await callback.message.answer(
        "Все анкеты на модерации показаны выше ☝️",
        reply_markup=get_admin_stats_keyboard()
    )
    await callback.answer()


@router.message(Command("addlikes"))
async def cmd_add_likes(message: Message, bot: Bot, db: Database):
    """Команда для начисления лайков клиенту (только для админа)"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.")
        return
    
    # Парсим аргументы команды: /addlikes @username 15 или /addlikes user_id 15
    args = message.text.split()
    
    if len(args) < 3:
        await message.answer(
            "❌ <b>Неверный формат команды</b>\n\n"
            "Используйте:\n"
            "<code>/addlikes @username количество</code>\n"
            "или\n"
            "<code>/addlikes user_id количество</code>\n\n"
            "Например:\n"
            "<code>/addlikes @john_doe 15</code>\n"
            "<code>/addlikes 123456789 15</code>"
        )
        return
    
    user_identifier = args[1]
    
    try:
        likes_amount = int(args[2])
        if likes_amount <= 0:
            await message.answer("❌ Количество лайков должно быть положительным числом.")
            return
    except ValueError:
        await message.answer("❌ Количество лайков должно быть числом.")
        return
    
    # Определяем, username или user_id
    client = None
    if user_identifier.startswith("@"):
        # Это username
        username = user_identifier[1:]  # Убираем @
        client = await db.get_client_by_username(username)
        if not client:
            await message.answer(
                f"❌ Клиент с username @{username} не найден.\n\n"
                "Убедитесь, что пользователь уже использовал бота."
            )
            return
        user_id = client.user_id
    else:
        # Это user_id
        try:
            user_id = int(user_identifier)
            client = await db.get_client(user_id)
            if not client:
                await message.answer(
                    f"❌ Клиент с ID {user_id} не найден.\n\n"
                    "Убедитесь, что пользователь уже использовал бота."
                )
                return
        except ValueError:
            await message.answer("❌ Неверный формат user_id.")
            return
    
    # Начисляем лайки
    await db.add_client_likes(user_id, likes_amount)
    new_balance = await db.get_client_likes(user_id)
    
    # Уведомляем админа
    await message.answer(
        f"✅ <b>Лайки начислены!</b>\n\n"
        f"Пользователь: {user_identifier}\n"
        f"Начислено: +{likes_amount} лайков\n"
        f"Новый баланс: {new_balance} лайков"
    )
    
    # Уведомляем клиента
    try:
        await bot.send_message(
            user_id,
            f"🎉 <b>Ваш баланс лайков пополнен!</b>\n\n"
            f"Начислено: <b>+{likes_amount}</b> лайков\n"
            f"Текущий баланс: <b>{new_balance}</b> лайков\n\n"
            f"Продолжайте искать своего идеального тренера!"
        )
    except Exception as e:
        await message.answer(f"⚠️ Не удалось отправить уведомление клиенту: {e}")

