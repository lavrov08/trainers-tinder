"""FSM состояния для регистрации тренера"""
from aiogram.fsm.state import State, StatesGroup


class TrainerRegistration(StatesGroup):
    """Состояния регистрации тренера"""
    waiting_for_direction = State()
    waiting_for_name = State()
    waiting_for_age = State()
    waiting_for_experience = State()
    waiting_for_about = State()
    waiting_for_photo = State()

