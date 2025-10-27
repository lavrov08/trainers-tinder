"""Сервис для отправки анкет тренеров"""
from aiogram.types import Message, CallbackQuery, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from database.models import Trainer


async def send_trainer_card(
    message, 
    trainer: Trainer, 
    keyboard,
    prefix: str = "",
    status_info: str = None,
    should_delete_previous: bool = False,
    state: FSMContext = None
):
    """
    Универсальная функция для отправки анкеты тренера
    
    Args:
        message: Объект Message или CallbackQuery
        trainer: Объект Trainer
        keyboard: Клавиатура для сообщения
        prefix: Префикс текста анкеты (например, "👤 Ваша анкета")
        status_info: Дополнительная информация о статусе
        should_delete_previous: Удалять ли предыдущие сообщения
        state: Контекст состояния для клиентов (для отслеживания ID сообщений)
    """
    # Определяем, является ли текущее сообщение фото
    # Для CallbackQuery нужно проверить message.photo
    is_photo = False
    if hasattr(message, 'photo'):
        is_photo = bool(message.photo)
    elif hasattr(message, 'message') and hasattr(message.message, 'photo'):
        is_photo = bool(message.message.photo)
    
    # Создаем основной текст без поля "О себе"
    if prefix:
        main_text = f"{prefix}\n\n"
    else:
        main_text = ""
    
    main_text += (
        f"<b>{trainer.name}</b>\n"
        f"Возраст: {trainer.age} лет\n"
        f"Опыт: {trainer.experience}\n"
        f"Направление: {trainer.direction}"
    )
    
    if status_info:
        main_text += f"\n\n{status_info}"
    
    # Проверяем, помещается ли основной текст + описание в лимит
    full_text = main_text + f"\n\n<b>О себе:</b>\n{trainer.about}"
    
    if len(full_text) <= 1024:
        # Если помещается - отправляем одним сообщением
        await _send_single_message(message, trainer, full_text, keyboard, should_delete_previous, is_photo, state)
    else:
        # Если не помещается - отправляем основную часть с фото, описание отдельно
        await _send_split_message(message, trainer, main_text, keyboard, should_delete_previous, is_photo, state)


async def _send_single_message(
    message, 
    trainer: Trainer, 
    text: str, 
    keyboard, 
    should_delete_previous: bool, 
    is_photo: bool,
    state: FSMContext
):
    """Отправка одиночного сообщения"""
    try:
        # Определяем правильный объект для отправки сообщения
        message_to_send = message if not hasattr(message, 'message') else message.message
        
        # Если есть фото, отправляем с фото
        if trainer.photo_id:
            # Для callback с фото сначала удаляем старое сообщение
            if is_photo and hasattr(message, 'message'):
                try:
                    await message.message.delete()
                except:
                    pass
            
            # Удаляем предыдущие сообщения если нужно
            if should_delete_previous:
                if state:
                    data = await state.get_data()
                    previous_message_id = data.get('previous_message_id')
                    previous_main_message_id = data.get('previous_main_message_id')
                    
                    await _delete_previous_messages(message, previous_main_message_id, previous_message_id)
            
            # Отправляем новое фото
            sent_message = await message_to_send.answer_photo(
                photo=trainer.photo_id,
                caption=text,
                reply_markup=keyboard
            )
            
            # Сохраняем ID сообщения для последующего удаления
            if state:
                current_message_id = sent_message.message_id
                current_main_message_id = None
                await state.update_data(
                    current_message_id=current_message_id,
                    current_main_message_id=current_main_message_id
                )
                print(f"DEBUG: Сохранили ID одиночного сообщения с фото: {current_message_id}")
        else:
            # Без фото - удаляем старое сообщение если оно было с фото
            if is_photo:
                try:
                    # Если это callback, пробуем удалить через message
                    if hasattr(message, 'message'):
                        await message.message.delete()
                    else:
                        await message.delete()
                except:
                    pass
            
            # Удаляем предыдущие сообщения если нужно
            if should_delete_previous:
                if state:
                    data = await state.get_data()
                    previous_message_id = data.get('previous_message_id')
                    previous_main_message_id = data.get('previous_main_message_id')
                    
                    await _delete_previous_messages(message, previous_main_message_id, previous_message_id)
            
            # Используем answer для отправки текста
            sent_message = await message_to_send.answer(text, reply_markup=keyboard)
            
            # Сохраняем ID сообщения для последующего удаления
            if state:
                current_message_id = sent_message.message_id
                current_main_message_id = None
                await state.update_data(
                    current_message_id=current_message_id,
                    current_main_message_id=current_main_message_id
                )
                print(f"DEBUG: Сохранили ID одиночного сообщения без фото: {current_message_id}")
    except Exception as e:
        print(f"Ошибка при отправке одиночного сообщения: {e}")
        # Fallback - отправляем без фото
        try:
            message_to_send = message if not hasattr(message, 'message') else message.message
            sent_message = await message_to_send.answer(text, reply_markup=keyboard)
            if state:
                await state.update_data(current_message_id=sent_message.message_id)
        except Exception as e2:
            print(f"Критическая ошибка: {e2}")


async def _send_split_message(
    message, 
    trainer: Trainer, 
    main_text: str, 
    keyboard, 
    should_delete_previous: bool, 
    is_photo: bool,
    state: FSMContext
):
    """Отправка разделенного сообщения (фото + описание)"""
    try:
        # Определяем правильный объект для отправки сообщения
        message_to_send = message if not hasattr(message, 'message') else message.message
        
        # Удаляем предыдущие сообщения если нужно
        if should_delete_previous and state:
            data = await state.get_data()
            previous_message_id = data.get('previous_message_id')
            previous_main_message_id = data.get('previous_main_message_id')
            
            await _delete_previous_messages(message, previous_main_message_id, previous_message_id)
        
        # Отправляем основную часть с фото (если есть)
        if trainer.photo_id:
            main_message = await message_to_send.answer_photo(
                photo=trainer.photo_id,
                caption=main_text
            )
        else:
            main_message = await message_to_send.answer(main_text)
        
        # Отправляем описание отдельным сообщением с кнопками
        about_message = await message_to_send.answer(
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
        print(f"Ошибка при отправке разделенного сообщения: {e}")
        # Fallback - отправляем все текстом
        try:
            message_to_send = message if not hasattr(message, 'message') else message.message
            sent_message = await message_to_send.answer(
                f"{main_text}\n\n<b>О себе:</b>\n{trainer.about}",
                reply_markup=keyboard
            )
            if state:
                await state.update_data(current_message_id=sent_message.message_id)
        except Exception as e2:
            print(f"Критическая ошибка: {e2}")


async def _delete_previous_messages(message, previous_main_message_id, previous_message_id):
    """Удаляет предыдущие сообщения если они существуют"""
    print(f"DEBUG: Удаляем предыдущие сообщения - main: {previous_main_message_id}, about: {previous_message_id}")
    
    # Определяем правильный bot объект
    bot = None
    chat_id = None
    
    if hasattr(message, 'bot'):
        bot = message.bot
        chat_id = message.chat.id
    elif hasattr(message, 'message'):
        bot = message.message.bot
        chat_id = message.message.chat.id
    
    if not bot:
        print("DEBUG: Не удалось определить bot объект")
        return
    
    if previous_main_message_id:
        try:
            await bot.delete_message(chat_id, previous_main_message_id)
            print(f"DEBUG: Успешно удалено предыдущее основное сообщение {previous_main_message_id}")
        except Exception as e:
            print(f"DEBUG: Ошибка удаления предыдущего основного сообщения {previous_main_message_id}: {e}")
    
    if previous_message_id:
        try:
            await bot.delete_message(chat_id, previous_message_id)
            print(f"DEBUG: Успешно удалено предыдущее сообщение с кнопками {previous_message_id}")
        except Exception as e:
            print(f"DEBUG: Ошибка удаления предыдущего сообщения с кнопками {previous_message_id}: {e}")

