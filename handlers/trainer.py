"""Обработчики для тренеров"""
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from database import Database
from database.models import Trainer
from keyboards.inline import get_skip_photo_keyboard, get_moderation_keyboard, get_trainer_profile_keyboard, get_confirm_delete_my_profile_keyboard, get_role_keyboard
from states import TrainerRegistration
from config import ADMIN_IDS, PLACEMENT_COST
from services.trainer_card import send_trainer_card

router = Router()


@router.callback_query(
    F.data.startswith("trainer_direction:"),
    TrainerRegistration.waiting_for_direction
)
async def process_trainer_direction(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора направления тренером"""
    direction = callback.data.split(":", 1)[1]
    
    await state.update_data(direction=direction)
    await state.set_state(TrainerRegistration.waiting_for_name)
    
    await callback.message.edit_text(
        f"Отлично! Вы выбрали направление: <b>{direction}</b>\n\n"
        "Теперь введите ваше <b>имя</b> (как вы хотите представиться клиентам):"
    )
    await callback.answer()


@router.message(TrainerRegistration.waiting_for_name)
async def process_trainer_name(message: Message, state: FSMContext):
    """Обработчик ввода имени"""
    name = message.text.strip()
    
    if not name or len(name) < 2:
        await message.answer("❌ Имя слишком короткое. Введите корректное имя:")
        return
    
    if len(name) > 50:
        await message.answer("❌ Имя слишком длинное. Введите имя покороче (до 50 символов):")
        return
    
    await state.update_data(name=name)
    await state.set_state(TrainerRegistration.waiting_for_age)
    
    await message.answer(
        f"Приятно познакомиться, <b>{name}</b>!\n\n"
        "Теперь укажите ваш <b>возраст</b> (число):"
    )


@router.message(TrainerRegistration.waiting_for_age)
async def process_trainer_age(message: Message, state: FSMContext):
    """Обработчик ввода возраста"""
    try:
        age = int(message.text.strip())
        
        if age < 16 or age > 100:
            await message.answer("❌ Укажите корректный возраст (от 16 до 100 лет):")
            return
        
        await state.update_data(age=age)
        await state.set_state(TrainerRegistration.waiting_for_experience)
        
        await message.answer(
            "Отлично!\n\n"
            "Расскажите о вашем <b>опыте работы</b> тренером.\n"
            "Например: \"5 лет\", \"Более 10 лет\", \"2 года в фитнесе\":"
        )
    except ValueError:
        await message.answer("❌ Пожалуйста, введите возраст числом:")


@router.message(TrainerRegistration.waiting_for_experience)
async def process_trainer_experience(message: Message, state: FSMContext):
    """Обработчик ввода опыта"""
    experience = message.text.strip()
    
    if not experience or len(experience) < 2:
        await message.answer("❌ Опыт указан слишком кратко. Напишите подробнее:")
        return
    
    if len(experience) > 100:
        await message.answer("❌ Слишком длинный текст. Сократите до 100 символов:")
        return
    
    await state.update_data(experience=experience)
    await state.set_state(TrainerRegistration.waiting_for_about)
    
    await message.answer(
        "Замечательно!\n\n"
        "Теперь расскажите <b>о себе</b>:\n"
        "- Ваши достижения\n"
        "- Методики работы\n"
        "- Почему клиенты должны выбрать именно вас\n"
        "- Цена за ваши услуги\n"
        "Минимум 20 символов\n"
        "Максимум 1000 символов\n\n"
        "⚠️ <b>Важно:</b> НЕ указывайте контакты иначе анкета будет отклонена!\n"
        "С вами свяжутся заинтересованные клиенты."
    )


@router.message(TrainerRegistration.waiting_for_about)
async def process_trainer_about(message: Message, state: FSMContext):
    """Обработчик ввода информации о себе"""
    about = message.text.strip()
    
    if not about or len(about) < 20:
        await message.answer(
            "❌ Расскажите о себе подробнее (минимум 20 символов).\n"
            "Это поможет клиентам узнать вас лучше!"
        )
        return
    
    if len(about) > 1000:
        await message.answer("❌ Слишком длинный текст. Сократите до 1000 символов:")
        return
    
    await state.update_data(about=about)
    await state.set_state(TrainerRegistration.waiting_for_photo)
    
    await message.answer(
        "Отлично! Почти готово.\n\n"
        "Теперь отправьте ваше <b>фото</b> (анкеты с фото привлекают больше внимания).\n\n"
        "Или нажмите кнопку ниже, чтобы пропустить этот шаг:",
        reply_markup=get_skip_photo_keyboard()
    )


@router.message(TrainerRegistration.waiting_for_photo, F.photo)
async def process_trainer_photo(message: Message, bot: Bot, state: FSMContext, db: Database):
    """Обработчик загрузки фото"""
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id)
    
    await submit_trainer_profile(message, bot, state, db)


@router.callback_query(F.data == "skip_photo", TrainerRegistration.waiting_for_photo)
async def process_skip_photo(callback: CallbackQuery, bot: Bot, state: FSMContext, db: Database):
    """Обработчик пропуска фото"""
    await state.update_data(photo_id=None)
    await callback.answer()
    
    # Передаем callback.from_user, чтобы получить данные пользователя, а не бота
    await submit_trainer_profile(callback.message, bot, state, db, user=callback.from_user)


@router.message(TrainerRegistration.waiting_for_photo)
async def process_invalid_photo(message: Message):
    """Обработчик некорректного ввода вместо фото"""
    await message.answer(
        "❌ Пожалуйста, отправьте фото или нажмите кнопку 'Пропустить фото'.",
        reply_markup=get_skip_photo_keyboard()
    )


async def submit_trainer_profile(message: Message, bot: Bot, state: FSMContext, db: Database, user=None):
    """Отправка анкеты на модерацию"""
    data = await state.get_data()
    # Если user не передан, берем из message
    if user is None:
        user = message.from_user
    user_id = user.id
    username = user.username
    
    # Создаем объект тренера
    trainer = Trainer(
        id=None,
        user_id=user_id,
        username=username,
        direction=data['direction'],
        name=data['name'],
        age=data['age'],
        experience=data['experience'],
        about=data['about'],
        photo_id=data.get('photo_id'),
        status='pending',
        created_at=None
    )
    
    # Сохраняем в БД
    trainer_id = await db.create_trainer(trainer)
    
    await state.clear()
    
    await message.answer(
        "✅ <b>Анкета создана!</b>\n\n"
        "Ваша анкета отправлена на модерацию администратору.\n"
        "Вы получите уведомление, когда анкета будет рассмотрена.\n\n"
        "Менеджер свяжется с вами для оплаты размещения анкеты. \n"
        f"Стоимость размещения {PLACEMENT_COST} рублей в месяц.\n"
        "После одобрения и оплаты вы начнете получать уведомления о лайках от клиентов!"
    )
    
    # Отправляем анкету всем админам на модерацию
    if ADMIN_IDS:
        # Создаем основной текст без поля "О себе"
        main_text = (
            "🆕 <b>Новая анкета тренера на модерации</b>\n\n"
            f"<b>Имя:</b> {trainer.name}\n"
            f"<b>Возраст:</b> {trainer.age} лет\n"
            f"<b>Опыт:</b> {trainer.experience}\n"
            f"<b>Направление:</b> {trainer.direction}\n\n"
            f"<b>Username:</b> @{username if username else 'не указан'}\n"
            f"<b>User ID:</b> {user_id}"
        )
        
        # Проверяем, помещается ли основной текст + описание в лимит
        full_text = main_text + f"\n\n<b>О себе:</b>\n{trainer.about}"
        
        for admin_id in ADMIN_IDS:
            try:
                if len(full_text) <= 1024:
                    # Если помещается - отправляем одним сообщением
                    if trainer.photo_id:
                        await bot.send_photo(
                            admin_id,
                            photo=trainer.photo_id,
                            caption=full_text,
                            reply_markup=get_moderation_keyboard(trainer_id)
                        )
                    else:
                        await bot.send_message(
                            admin_id,
                            full_text,
                            reply_markup=get_moderation_keyboard(trainer_id)
                        )
                else:
                    # Если не помещается - отправляем основную часть с фото, описание отдельно
                    if trainer.photo_id:
                        await bot.send_photo(
                            admin_id,
                            photo=trainer.photo_id,
                            caption=main_text
                        )
                    else:
                        await bot.send_message(admin_id, main_text)
                    
                    # Отправляем описание отдельным сообщением с кнопками
                    await bot.send_message(
                        admin_id,
                        f"<b>О себе:</b>\n{trainer.about}",
                        reply_markup=get_moderation_keyboard(trainer_id)
                    )
            except Exception as e:
                print(f"Ошибка отправки админу {admin_id}: {e}")
                # В случае ошибки отправляем все текстом
                try:
                    await bot.send_message(
                        admin_id,
                        full_text,
                        reply_markup=get_moderation_keyboard(trainer_id)
                    )
                except Exception as e2:
                    print(f"Критическая ошибка отправки админу {admin_id}: {e2}")


@router.callback_query(F.data.startswith("view_my_profile:"))
async def view_my_profile(callback: CallbackQuery, db: Database):
    """Обработчик просмотра собственной анкеты тренера"""
    trainer_id = int(callback.data.split(":", 1)[1])
    user_id = callback.from_user.id
    
    # Получаем анкету тренера
    trainer = await db.get_trainer_by_id(trainer_id)
    
    if not trainer:
        # Если сообщение содержит фото, удаляем его и отправляем новое текстовое
        if callback.message.photo:
            await callback.message.delete()
            await callback.message.answer("❌ Анкета не найдена.")
        else:
            await callback.message.edit_text("❌ Анкета не найдена.")
        await callback.answer()
        return
    
    # Проверяем, что это анкета текущего пользователя
    if trainer.user_id != user_id:
        # Если сообщение содержит фото, удаляем его и отправляем новое текстовое
        if callback.message.photo:
            await callback.message.delete()
            await callback.message.answer("❌ У вас нет доступа к этой анкете.")
        else:
            await callback.message.edit_text("❌ У вас нет доступа к этой анкете.")
        await callback.answer()
        return
    
    # Определяем статус анкеты
    status_info = f"<b>Статус:</b> {'✅ Одобрена' if trainer.status == 'approved' else '⏳ На модерации' if trainer.status == 'pending' else '❌ Отклонена'}"
    
    # Получаем клавиатуру
    keyboard = get_trainer_profile_keyboard(trainer_id)
    
    # Используем централизованный сервис для отправки анкеты
    try:
        await send_trainer_card(
            message=callback,
            trainer=trainer,
            keyboard=keyboard,
            prefix="👤 <b>Ваша анкета</b>",
            status_info=status_info,
            should_delete_previous=False,
            state=None  # Не используем state для тренеров
        )
    except Exception as e:
        print(f"Ошибка при отправке анкеты: {e}")
        # Fallback - отправляем простым сообщением
        try:
            profile_text = (
                f"👤 <b>Ваша анкета</b>\n\n"
                f"<b>Имя:</b> {trainer.name}\n"
                f"<b>Возраст:</b> {trainer.age} лет\n"
                f"<b>Направление:</b> {trainer.direction}\n"
                f"<b>Опыт:</b> {trainer.experience}\n\n"
                f"<b>О себе:</b>\n{trainer.about}\n\n"
                f"{status_info}"
            )
            
            # Пытаемся сначала отправить с фото
            if trainer.photo_id:
                try:
                    await callback.message.answer_photo(
                        photo=trainer.photo_id,
                        caption=profile_text,
                        reply_markup=keyboard
                    )
                except:
                    await callback.message.answer(profile_text, reply_markup=keyboard)
            else:
                await callback.message.answer(profile_text, reply_markup=keyboard)
        except Exception as e2:
            print(f"Критическая ошибка: {e2}")
    
    await callback.answer()


@router.callback_query(F.data.startswith("delete_my_profile:"))
async def delete_my_profile(callback: CallbackQuery, db: Database):
    """Обработчик запроса на удаление собственной анкеты"""
    trainer_id = int(callback.data.split(":", 1)[1])
    user_id = callback.from_user.id
    
    # Получаем анкету тренера
    trainer = await db.get_trainer_by_id(trainer_id)
    
    if not trainer:
        # Если сообщение содержит фото, удаляем его и отправляем новое текстовое
        if callback.message.photo:
            await callback.message.delete()
            await callback.message.answer("❌ Анкета не найдена.")
        else:
            await callback.message.edit_text("❌ Анкета не найдена.")
        await callback.answer()
        return
    
    # Проверяем, что это анкета текущего пользователя
    if trainer.user_id != user_id:
        # Если сообщение содержит фото, удаляем его и отправляем новое текстовое
        if callback.message.photo:
            await callback.message.delete()
            await callback.message.answer("❌ У вас нет доступа к этой анкете.")
        else:
            await callback.message.edit_text("❌ У вас нет доступа к этой анкете.")
        await callback.answer()
        return
    
    # Если сообщение содержит фото, удаляем его и отправляем новое текстовое
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(
            "⚠️ <b>Внимание!</b>\n\n"
            "Вы действительно хотите удалить свою анкету?\n\n"
            "После удаления:\n"
            "• Анкета будет полностью удалена из системы\n"
            "• Все лайки от клиентов будут потеряны\n"
            "• Вам придется создавать новую анкету с нуля\n\n"
            "Это действие нельзя отменить!",
            reply_markup=get_confirm_delete_my_profile_keyboard(trainer_id)
        )
    else:
        await callback.message.edit_text(
            "⚠️ <b>Внимание!</b>\n\n"
            "Вы действительно хотите удалить свою анкету?\n\n"
            "После удаления:\n"
            "• Анкета будет полностью удалена из системы\n"
            "• Все лайки от клиентов будут потеряны\n"
            "• Вам придется создавать новую анкету с нуля\n\n"
            "Это действие нельзя отменить!",
            reply_markup=get_confirm_delete_my_profile_keyboard(trainer_id)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_my_profile:"))
async def confirm_delete_my_profile(callback: CallbackQuery, db: Database):
    """Обработчик подтверждения удаления собственной анкеты"""
    trainer_id = int(callback.data.split(":", 1)[1])
    user_id = callback.from_user.id
    
    # Получаем анкету тренера
    trainer = await db.get_trainer_by_id(trainer_id)
    
    if not trainer:
        # Если сообщение содержит фото, удаляем его и отправляем новое текстовое
        if callback.message.photo:
            await callback.message.delete()
            await callback.message.answer("❌ Анкета не найдена.")
        else:
            await callback.message.edit_text("❌ Анкета не найдена.")
        await callback.answer()
        return
    
    # Проверяем, что это анкета текущего пользователя
    if trainer.user_id != user_id:
        # Если сообщение содержит фото, удаляем его и отправляем новое текстовое
        if callback.message.photo:
            await callback.message.delete()
            await callback.message.answer("❌ У вас нет доступа к этой анкете.")
        else:
            await callback.message.edit_text("❌ У вас нет доступа к этой анкете.")
        await callback.answer()
        return
    
    try:
        # Удаляем анкету
        await db.delete_trainer(trainer_id)
        
        # Если сообщение содержит фото, удаляем его и отправляем новое текстовое
        if callback.message.photo:
            await callback.message.delete()
            await callback.message.answer(
                "✅ <b>Анкета успешно удалена!</b>\n\n"
                "Ваша анкета была полностью удалена из системы.\n"
                "Если захотите создать новую анкету, просто выберите роль тренера снова.",
                reply_markup=get_role_keyboard()
            )
        else:
            await callback.message.edit_text(
                "✅ <b>Анкета успешно удалена!</b>\n\n"
                "Ваша анкета была полностью удалена из системы.\n"
                "Если захотите создать новую анкету, просто выберите роль тренера снова.",
                reply_markup=get_role_keyboard()
            )
    except Exception as e:
        print(f"Ошибка при удалении анкеты: {e}")
        # Если сообщение содержит фото, удаляем его и отправляем новое текстовое
        if callback.message.photo:
            await callback.message.delete()
            await callback.message.answer(
                "❌ Произошла ошибка при удалении анкеты. Попробуйте позже."
            )
        else:
            await callback.message.edit_text(
                "❌ Произошла ошибка при удалении анкеты. Попробуйте позже."
            )
    
    await callback.answer()


@router.callback_query(F.data == "back_to_main")
async def back_to_main_menu(callback: CallbackQuery):
    """Обработчик возврата в главное меню"""
    await callback.message.edit_text(
        "👋 <b>Добро пожаловать в Tinder для тренеров!</b>\n"
        "<i>made by <b>@cultphysique</b> </i>\n\n"
        "Спасибо, что подписались на нас! 💪\n\n"
        "🎁 <b>Подарок для новых подписчиков:</b>\n"
        "Бесплатная консультация у <b>ЛЮБОГО</b> нашего специалиста по <b>ЛЮБОМУ</b> интересующему вас вопросу!\n\n"
        "Выберите свою роль:",
        reply_markup=get_role_keyboard()
    )
    await callback.answer()

