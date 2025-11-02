"""Обработчики для клиентов"""
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InputMediaPhoto
from aiogram.fsm.context import FSMContext

from database import Database
from keyboards.inline import get_directions_keyboard, get_trainer_view_keyboard, get_refill_tariffs_keyboard, get_role_keyboard, get_liked_trainers_keyboard
from config import ADMIN_IDS, PLACEMENT_COST
from services.trainer_card import send_trainer_card

router = Router()


async def send_trainer_card_smart(message, trainer, current_index: int, total: int, keyboard, should_delete_previous=False, state: FSMContext = None):
    """Умная отправка анкеты тренера с разделением по полю 'О себе'"""
    # Создаем основной текст без поля "О себе"
    main_text = (
        f"<b>{trainer.name}</b>\n"
        f"Возраст: {trainer.age} лет\n"
        f"Опыт: {trainer.experience}\n"
        f"Направление: {trainer.direction}\n\n"
        f"Анкета {current_index + 1}/{total}"
    )
    
    # Проверяем, помещается ли основной текст + описание в лимит
    full_text = main_text + f"\n\n<b>О себе:</b>\n{trainer.about}"
    
    if len(full_text) <= 1024:
        # Если помещается - отправляем одним сообщением
        try:
            if message.photo:
                await message.edit_media(
                    media=InputMediaPhoto(media=trainer.photo_id, caption=full_text),
                    reply_markup=keyboard
                )
                # Сохраняем ID сообщения для последующего удаления
                if state:
                    await state.update_data(current_message_id=message.message_id)
            else:
                if should_delete_previous:
                    await message.delete()
                sent_message = await message.answer_photo(
                    photo=trainer.photo_id,
                    caption=full_text,
                    reply_markup=keyboard
                )
                # Сохраняем ID сообщения для последующего удаления
                if state:
                    # Сначала сохраняем текущий ID как предыдущий (если он есть)
                    data = await state.get_data()
                    current_message_id = data.get('current_message_id')
                    current_main_message_id = data.get('current_main_message_id')
                    
                    # Для одиночных сообщений храним ID только в current_message_id
                    # Для разделенных сообщений храним оба ID
                    if current_main_message_id:
                        # Предыдущее сообщение было разделено на две части
                        await state.update_data(
                            previous_message_id=current_message_id,
                            previous_main_message_id=current_main_message_id
                        )
                        print(f"DEBUG: Сохранили предыдущие ID (разделенное) - main: {current_main_message_id}, about: {current_message_id}")
                    elif current_message_id:
                        # Предыдущее сообщение было одиночным
                        await state.update_data(
                            previous_message_id=current_message_id,
                            previous_main_message_id=None
                        )
                        print(f"DEBUG: Сохранили предыдущий ID (одиночное с фото): {current_message_id}")
                    
                    # Теперь сохраняем новый ID как текущий (сбрасываем main_message_id для одиночного сообщения)
                    await state.update_data(
                        current_message_id=sent_message.message_id,
                        current_main_message_id=None
                    )
                    print(f"DEBUG: Сохранили новый ID одиночного сообщения с фото: {sent_message.message_id}")
        except Exception as e:
            print(f"Ошибка отправки анкеты тренера {trainer.id}: {e}")
            # В случае ошибки отправляем без фото
            try:
                if message.photo and should_delete_previous:
                    await message.delete()
                sent_message = await message.answer(full_text, reply_markup=keyboard)
                # Сохраняем ID сообщения для последующего удаления
                if state:
                    await state.update_data(current_message_id=sent_message.message_id)
            except Exception as e2:
                print(f"Критическая ошибка отправки анкеты тренера {trainer.id}: {e2}")
                sent_message = await message.answer(full_text, reply_markup=keyboard)
                if state:
                    await state.update_data(current_message_id=sent_message.message_id)
    else:
        # Если не помещается - отправляем основную часть с фото, описание отдельно
        try:
            if should_delete_previous:
                # Удаляем предыдущие сообщения если они есть
                data = await state.get_data() if state else {}
                previous_message_id = data.get('previous_message_id')
                previous_main_message_id = data.get('previous_main_message_id')
                
                print(f"DEBUG: Удаляем предыдущие сообщения - main: {previous_main_message_id}, about: {previous_message_id}")
                
                # Удаляем предыдущие сообщения только если они существуют
                if previous_main_message_id:
                    try:
                        await message.bot.delete_message(message.chat.id, previous_main_message_id)
                        print(f"DEBUG: Успешно удалено предыдущее основное сообщение {previous_main_message_id}")
                    except Exception as e:
                        print(f"DEBUG: Ошибка удаления предыдущего основного сообщения {previous_main_message_id}: {e}")
                
                if previous_message_id:
                    try:
                        await message.bot.delete_message(message.chat.id, previous_message_id)
                        print(f"DEBUG: Успешно удалено предыдущее сообщение с кнопками {previous_message_id}")
                    except Exception as e:
                        print(f"DEBUG: Ошибка удаления предыдущего сообщения с кнопками {previous_message_id}: {e}")
            
            # Отправляем фото с основной информацией
            main_message = await message.answer_photo(
                photo=trainer.photo_id,
                caption=main_text
            )
            
            # Отправляем описание отдельным сообщением с кнопками
            about_message = await message.answer(
                f"<b>О себе:</b>\n{trainer.about}",
                reply_markup=keyboard
            )
            
            # Сохраняем ID обоих сообщений для последующего удаления
            if state:
                # Сначала сохраняем текущие ID как предыдущие (если они есть)
                data = await state.get_data()
                current_message_id = data.get('current_message_id')
                current_main_message_id = data.get('current_main_message_id')
                
                # Сохраняем ID предыдущего сообщения (может быть как одиночным, так и разделенным)
                if current_main_message_id:
                    # Предыдущее сообщение было разделено на две части
                    await state.update_data(
                        previous_message_id=current_message_id,
                        previous_main_message_id=current_main_message_id
                    )
                    print(f"DEBUG: Сохранили предыдущие ID (разделенное) - main: {current_main_message_id}, about: {current_message_id}")
                elif current_message_id:
                    # Предыдущее сообщение было одиночным
                    await state.update_data(
                        previous_message_id=current_message_id,
                        previous_main_message_id=None
                    )
                    print(f"DEBUG: Сохранили предыдущий ID (одиночное) - about: {current_message_id}")
                
                # Теперь сохраняем новые ID как текущие (разделенное сообщение)
                await state.update_data(
                    current_message_id=about_message.message_id,
                    current_main_message_id=main_message.message_id
                )
                print(f"DEBUG: Сохранили новые ID (разделенное) - main: {main_message.message_id}, about: {about_message.message_id}")
        except Exception as e:
            print(f"Ошибка отправки анкеты тренера {trainer.id}: {e}")
            # В случае ошибки отправляем все текстом
            try:
                sent_message = await message.answer(full_text, reply_markup=keyboard)
                if state:
                    await state.update_data(current_message_id=sent_message.message_id)
            except Exception as e2:
                print(f"Критическая ошибка отправки анкеты тренера {trainer.id}: {e2}")
                sent_message = await message.answer(full_text, reply_markup=keyboard)
                if state:
                    await state.update_data(current_message_id=sent_message.message_id)


def split_text_for_caption(text: str, max_length: int = 4000) -> list[str]:
    """Разбивает текст на части для отправки в нескольких сообщениях"""
    if len(text) <= max_length:
        return [text]
    
    parts = []
    current_part = ""
    lines = text.split('\n')
    
    for line in lines:
        # Если добавление строки не превысит лимит
        if len(current_part) + len(line) + 1 <= max_length:
            if current_part:
                current_part += '\n' + line
            else:
                current_part = line
        else:
            # Сохраняем текущую часть и начинаем новую
            if current_part:
                parts.append(current_part)
            current_part = line
    
    # Добавляем последнюю часть
    if current_part:
        parts.append(current_part)
    
    return parts


async def send_text_with_photo(message, photo_id: str, text: str, keyboard=None, max_length: int = 4000, should_delete_previous=False):
    """Отправляет текст с фото, разбивая длинный текст на части"""
    text_parts = split_text_for_caption(text, max_length)
    
    if len(text_parts) == 1:
        # Короткий текст - отправляем с фото
        try:
            if message.photo:
                await message.edit_media(
                    media=InputMediaPhoto(media=photo_id, caption=text),
                    reply_markup=keyboard
                )
            else:
                if should_delete_previous:
                    await message.delete()
                await message.answer_photo(
                    photo=photo_id,
                    caption=text,
                    reply_markup=keyboard
                )
        except Exception as e:
            print(f"Ошибка отправки с фото: {e}")
            # Fallback - отправляем без фото
            if message.photo and should_delete_previous:
                await message.delete()
            await message.answer(text, reply_markup=keyboard)
    else:
        # Длинный текст - отправляем частями
        try:
            if should_delete_previous:
                await message.delete()
            
            # Отправляем фото с первой частью текста
            await message.answer_photo(
                photo=photo_id,
                caption=text_parts[0],
                reply_markup=None  # Кнопки только в последнем сообщении
            )
            
            # Отправляем остальные части как обычные сообщения
            for part in text_parts[1:-1]:
                await message.answer(part)
            
            # Последняя часть с кнопками
            if text_parts:
                await message.answer(text_parts[-1], reply_markup=keyboard)
                
        except Exception as e:
            print(f"Ошибка отправки частями: {e}")
            # Fallback - отправляем все как обычные сообщения
            if should_delete_previous:
                await message.delete()
            
            for i, part in enumerate(text_parts):
                if i == len(text_parts) - 1:
                    # Последняя часть с кнопками
                    await message.answer(part, reply_markup=keyboard)
                else:
                    await message.answer(part)


async def format_trainer_card(trainer, current_index: int, total: int) -> str:
    """Форматирование анкеты тренера"""
    # Создаем базовый текст без поля "О себе"
    base_text = (
        f"<b>{trainer.name}</b>\n"
        f"Возраст: {trainer.age} лет\n"
        f"Опыт: {trainer.experience}\n"
        f"Направление: {trainer.direction}\n\n"
        f"<b>О себе:</b>\n"
        f"Анкета {current_index + 1}/{total}"
    )
    
    # Рассчитываем доступное место для описания
    max_caption_length = 4096
    available_length = max_caption_length - len(base_text) - 10  # 10 символов запас
    
    # Обрезаем описание если нужно
    about_text = trainer.about
    if len(about_text) > available_length:
        about_text = about_text[:available_length] + "..."
    
    return (
        f"<b>{trainer.name}</b>\n"
        f"Возраст: {trainer.age} лет\n"
        f"Опыт: {trainer.experience}\n"
        f"Направление: {trainer.direction}\n\n"
        f"<b>О себе:</b>\n{about_text}\n\n"
        f"Анкета {current_index + 1}/{total}"
    )


@router.callback_query(F.data.startswith("client_direction:"))
async def process_client_direction(callback: CallbackQuery, db: Database, state: FSMContext):
    """Обработчик выбора направления клиентом"""
    direction = callback.data.split(":", 1)[1]
    
    # Получаем тренеров по направлению
    trainers = await db.get_approved_trainers_by_direction(direction)
    
    if not trainers:
        # Если сообщение содержит фото, удаляем его и отправляем новое текстовое
        try:
            await callback.message.edit_text(
                f"😔 К сожалению, пока нет тренеров в направлении <b>{direction}</b>.\n\n"
                "Попробуйте выбрать другое направление:",
                reply_markup=get_directions_keyboard(prefix="client_direction", show_back_button=True)
            )
        except Exception:
            if callback.message.photo:
                await callback.message.delete()
            await callback.message.answer(
                f"😔 К сожалению, пока нет тренеров в направлении <b>{direction}</b>.\n\n"
                "Попробуйте выбрать другое направление:",
                reply_markup=get_directions_keyboard(prefix="client_direction", show_back_button=True)
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


async def show_trainer(message, db: Database, state: FSMContext, user_id: int, should_delete_previous=False):
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
    
    keyboard = get_trainer_view_keyboard(
        trainer_id, current_index, len(trainers_ids), already_liked
    )
    
    # Используем централизованный сервис для отправки анкеты
    try:
        await send_trainer_card(
            message=message,
            trainer=trainer,
            keyboard=keyboard,
            prefix="",
            status_info=f"Анкета {current_index + 1}/{len(trainers_ids)}",
            should_delete_previous=should_delete_previous,
            state=state
        )
    except Exception as e:
        print(f"Ошибка при отправке анкеты: {e}")
        # В случае ошибки отправляем простым сообщением
        text = f"<b>{trainer.name}</b>\nВозраст: {trainer.age} лет\nОпыт: {trainer.experience}\nНаправление: {trainer.direction}\n\n<b>О себе:</b>\n{trainer.about}\n\nАнкета {current_index + 1}/{len(trainers_ids)}"
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
    
    await show_trainer(callback.message, db, state, callback.from_user.id, should_delete_previous=True)
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
    
    await show_trainer(callback.message, db, state, callback.from_user.id, should_delete_previous=True)
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
    # Получаем данные перед очисткой состояния
    data = await state.get_data()
    previous_message_id = data.get('previous_message_id') or data.get('current_message_id')
    previous_main_message_id = data.get('previous_main_message_id') or data.get('current_main_message_id')
    
    # Очищаем состояние
    await state.clear()
    
    # Удаляем все предыдущие сообщения если они есть
    if previous_message_id:
        try:
            await callback.message.bot.delete_message(callback.message.chat.id, previous_message_id)
        except Exception:
            pass
    if previous_main_message_id:
        try:
            await callback.message.bot.delete_message(callback.message.chat.id, previous_main_message_id)
        except Exception:
            pass
    
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

@router.callback_query(F.data == "back_to_main_menu")
async def process_back_to_main_menu(callback: CallbackQuery, state: FSMContext):
    """Обработчик возврата в главное меню"""
    # Получаем данные перед очисткой состояния
    data = await state.get_data()
    previous_message_id = data.get('previous_message_id') or data.get('current_message_id')
    previous_main_message_id = data.get('previous_main_message_id') or data.get('current_main_message_id')
    
    # Очищаем состояние
    await state.clear()
    
    # Удаляем все предыдущие сообщения если они есть
    if previous_message_id:
        try:
            await callback.message.bot.delete_message(callback.message.chat.id, previous_message_id)
        except Exception:
            pass
    if previous_main_message_id:
        try:
            await callback.message.bot.delete_message(callback.message.chat.id, previous_main_message_id)
        except Exception:
            pass
    
    # Удаляем старое сообщение если оно с фото
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    await callback.message.answer(
        "👋 <b>Добро пожаловать в Tinder для тренеров!</b>\n"
        "<i>made by <b>@cultphysique</b> </i>\n\n"
        "Спасибо, что подписались на нас! 💪\n\n"
        "🎁 <b>Подарок для новых подписчиков:</b>\n"
        "Бесплатная консультация у <b>ЛЮБОГО</b> нашего специалиста по <b>ЛЮБОМУ</b> интересующему вас вопросу!\n\n"
        "Выберите свою роль:",
        reply_markup=get_role_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "check_likes")
async def process_check_likes(callback: CallbackQuery, db: Database, state: FSMContext):
    """Обработчик просмотра лайкнутых тренеров"""
    user_id = callback.from_user.id
    
    # Получаем список лайкнутых тренеров
    liked_trainers = await db.get_client_liked_trainers(user_id)
    
    if not liked_trainers:
        await callback.answer(
            "😔 У вас пока нет лайкнутых тренеров.\n\n"
            "Начните просматривать анкеты и ставьте лайки интересным тренерам!",
            show_alert=True
        )
        return
    
    # Сохраняем список в state для навигации
    await state.update_data(
        liked_trainers=[t.id for t in liked_trainers],
        liked_page=0
    )
    
    # Показываем список тренеров
    page = 0
    keyboard = get_liked_trainers_keyboard(liked_trainers, page)
    
    text = f"💖 <b>Ваши лайки</b>\n\n"
    text += f"Всего лайкнутых тренеров: {len(liked_trainers)}\n\n"
    text += "Выберите тренера для просмотра:"
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard)
    
    await callback.answer()


@router.callback_query(F.data.startswith("liked_page:"))
async def process_liked_page(callback: CallbackQuery, db: Database, state: FSMContext):
    """Обработчик навигации по страницам лайкнутых тренеров"""
    page = int(callback.data.split(":", 1)[1])
    user_id = callback.from_user.id
    
    # Получаем список лайкнутых тренеров из базы данных
    liked_trainers = await db.get_client_liked_trainers(user_id)
    
    if not liked_trainers:
        await callback.answer("❌ Список тренеров пуст", show_alert=True)
        return
    
    # Сохраняем список в state для навигации
    await state.update_data(
        liked_trainers=[t.id for t in liked_trainers],
        liked_page=page
    )
    
    keyboard = get_liked_trainers_keyboard(liked_trainers, page)
    
    text = f"💖 <b>Ваши лайки</b>\n\n"
    text += f"Всего лайкнутых тренеров: {len(liked_trainers)}\n\n"
    text += "Выберите тренера для просмотра:"
    
    # Если сообщение содержит фото, удаляем его и отправляем новое текстовое
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        if callback.message.photo:
            await callback.message.delete()
        await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("view_liked_trainer:"))
async def process_view_liked_trainer(callback: CallbackQuery, db: Database, state: FSMContext):
    """Обработчик просмотра лайкнутого тренера"""
    trainer_id = int(callback.data.split(":", 1)[1])
    trainer = await db.get_trainer_by_id(trainer_id)
    
    if not trainer:
        await callback.answer("❌ Тренер не найден", show_alert=True)
        return
    
    # Получаем данные перед очисткой состояния (для удаления предыдущих сообщений)
    data = await state.get_data()
    previous_message_id = data.get('previous_message_id') or data.get('current_message_id')
    previous_main_message_id = data.get('previous_main_message_id') or data.get('current_main_message_id')
    
    # Удаляем все предыдущие сообщения если они есть
    if previous_message_id:
        try:
            await callback.message.bot.delete_message(callback.message.chat.id, previous_message_id)
        except Exception:
            pass
    if previous_main_message_id:
        try:
            await callback.message.bot.delete_message(callback.message.chat.id, previous_main_message_id)
        except Exception:
            pass
    
    # Показываем анкету тренера с кнопкой возврата к выбору направления
    keyboard = get_trainer_view_keyboard(
        trainer_id, 0, 1, already_liked=True, from_likes=False
    )
    
    from services.trainer_card import send_trainer_card
    try:
        await send_trainer_card(
            message=callback.message,
            trainer=trainer,
            keyboard=keyboard,
            prefix="",
            status_info="Лайкнутый тренер",
            should_delete_previous=True,
            state=state
        )
    except Exception as e:
        print(f"Ошибка при отправке анкеты: {e}")
        # Удаляем старое сообщение если оно с фото
        try:
            await callback.message.delete()
        except Exception:
            pass
        text = (
            f"<b>{trainer.name}</b>\n"
            f"Возраст: {trainer.age} лет\n"
            f"Опыт: {trainer.experience}\n"
            f"Направление: {trainer.direction}\n\n"
            f"<b>О себе:</b>\n{trainer.about}"
        )
        await callback.message.answer(text, reply_markup=keyboard)
    
    await callback.answer()


@router.callback_query(F.data == "back_to_trainers")
async def process_back_to_trainers(callback: CallbackQuery, db: Database, state: FSMContext):
    """Обработчик возврата к списку лайкнутых тренеров"""
    user_id = callback.from_user.id
    
    # Получаем данные перед очисткой состояния (для удаления предыдущих сообщений)
    data = await state.get_data()
    previous_message_id = data.get('previous_message_id') or data.get('current_message_id')
    previous_main_message_id = data.get('previous_main_message_id') or data.get('current_main_message_id')
    
    # Удаляем все предыдущие сообщения если они есть
    if previous_message_id:
        try:
            await callback.message.bot.delete_message(callback.message.chat.id, previous_message_id)
        except Exception:
            pass
    if previous_main_message_id:
        try:
            await callback.message.bot.delete_message(callback.message.chat.id, previous_main_message_id)
        except Exception:
            pass
    
    # Получаем список лайкнутых тренеров
    liked_trainers = await db.get_client_liked_trainers(user_id)
    
    if not liked_trainers:
        # Удаляем старое сообщение если оно с фото
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            "😔 У вас пока нет лайкнутых тренеров.",
            reply_markup=get_directions_keyboard(prefix="client_direction")
        )
        await callback.answer()
        return
    
    # Получаем сохраненную страницу или используем 0
    page = data.get("liked_page", 0)
    
    # Сохраняем список в state для навигации
    await state.update_data(
        liked_trainers=[t.id for t in liked_trainers],
        liked_page=page,
        from_likes=False
    )
    
    keyboard = get_liked_trainers_keyboard(liked_trainers, page)
    
    text = f"💖 <b>Ваши лайки</b>\n\n"
    text += f"Всего лайкнутых тренеров: {len(liked_trainers)}\n\n"
    text += "Выберите тренера для просмотра:"
    
    # Удаляем старое сообщение если оно с фото
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "refill_likes")
async def process_refill_likes(callback: CallbackQuery):
    """Обработчик запроса на пополнение лайков"""
    # Вычисляем стоимость тарифов
    tariff_5 = PLACEMENT_COST
    tariff_15 = PLACEMENT_COST * 2
    tariff_30 = PLACEMENT_COST * 3
    
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
    try:
        await callback.message.edit_text(
            f"✅ <b>Запрос на пополнение отправлен!</b>\n\n"
            f"Тариф: <b>{likes_amount} лайков</b> за {cost} рублей\n\n"
            f"Менеджер свяжется с вами в ближайшее время для оплаты.\n"
            f"После подтверждения оплаты лайки будут начислены автоматически."
        )
    except Exception:
        if callback.message.photo:
            await callback.message.delete()
        await callback.message.answer(
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
        f"<code>/addlikes {'@' + username if username else user_id} {likes_amount}</code>"
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

