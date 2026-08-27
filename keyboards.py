from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from config import YOUTUBERS, DUNGEONS, CREATOR, ADMIN_IDS
import database as db

def get_main_keyboard(user_id: int = None) -> ReplyKeyboardMarkup:
    """Returns main menu reply keyboard."""
    keyboard = [
        [
            KeyboardButton(text="🎬 Лололошка"),
            KeyboardButton(text="🎮 Фиксплей")
        ],
        [
            KeyboardButton(text="🗡 Подземелья и Рейды"),
            KeyboardButton(text="🔍 Профиль игрока")
        ],
        [
            KeyboardButton(text="🔔 Настройка уведомлений")
        ],
        [
            KeyboardButton(text=f"👑 Создатель ({CREATOR['name']})")
        ]
    ]
    
    # Show Admin Panel button if user is admin
    if user_id and user_id in ADMIN_IDS:
        keyboard.append([KeyboardButton(text="🛠 Админ-панель")])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        persistent=True
    )

async def get_monitoring_inline_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Generates inline keyboard for notification subscriptions (YouTubers + Dungeons)."""
    subs = await db.get_user_subscriptions(user_id)
    
    lol_sub = "MrLalalashkaXXL" in subs
    fix_sub = "F1xPlay_" in subs
    hard_sub = "dungeon_hard" in subs
    med_sub = "dungeon_medium" in subs
    double_sub = "dungeon_double" in subs
    jeju_sub = "dungeon_jeju" in subs
    auc_sub = "dark_auction" in subs

    keyboard = [
        # YouTubers
        [
            InlineKeyboardButton(
                text=f"🎬 Лололошка: {'🟢 Включен' if lol_sub else '🔴 Выключен'}",
                callback_data="toggle_MrLalalashkaXXL"
            )
        ],
        [
            InlineKeyboardButton(
                text=f"🎮 Фиксплей: {'🟢 Включен' if fix_sub else '🔴 Выключен'}",
                callback_data="toggle_F1xPlay_"
            )
        ],
        # Dungeons
        [
            InlineKeyboardButton(
                text=f"🗡 Сложное (:10, :40): {'🟢 Включен' if hard_sub else '🔴 Выключен'}",
                callback_data="toggle_dungeon_hard"
            )
        ],
        [
            InlineKeyboardButton(
                text=f"⚔️ Среднее (:15, :45): {'🟢 Включен' if med_sub else '🔴 Выключен'}",
                callback_data="toggle_dungeon_medium"
            )
        ],
        [
            InlineKeyboardButton(
                text=f"💀 Двойное (00, 06, 12, 18): {'🟢 Включен' if double_sub else '🔴 Выключен'}",
                callback_data="toggle_dungeon_double"
            )
        ],
        [
            InlineKeyboardButton(
                text=f"🌋 Остров Чеджу (17:00): {'🟢 Включен' if jeju_sub else '🔴 Выключен'}",
                callback_data="toggle_dungeon_jeju"
            )
        ],
        [
            InlineKeyboardButton(
                text=f"🏛 Тёмный Аукцион (Сб 19:00): {'🟢 Включен' if auc_sub else '🔴 Выключен'}",
                callback_data="toggle_dark_auction"
            )
        ],
        # Master toggles
        [
            InlineKeyboardButton(
                text="🟢 Включить ВСЁ",
                callback_data="enable_all"
            ),
            InlineKeyboardButton(
                text="🔴 Выключить ВСЁ",
                callback_data="disable_all"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_admin_inline_keyboard() -> InlineKeyboardMarkup:
    """Returns inline keyboard for Admin Panel including Discord sound test buttons."""
    keyboard = [
        [
            InlineKeyboardButton(text="🔄 Обновить статистику", callback_data="admin_refresh_stats")
        ],
        [
            InlineKeyboardButton(text="🔊 Тест: Среднее подземелье", callback_data="test_sound_dungeon_medium.mp3"),
        ],
        [
            InlineKeyboardButton(text="🔊 Тест: Сложное подземелье", callback_data="test_sound_dungeon_hard.mp3"),
        ],
        [
            InlineKeyboardButton(text="🔊 Тест: Двойное подземелье", callback_data="test_sound_double_dungeon.mp3"),
        ],
        [
            InlineKeyboardButton(text="🔊 Тест: Остров Чеджу", callback_data="test_sound_jeju_raid.mp3"),
        ],
        [
            InlineKeyboardButton(text="🔊 Тест: Тёмный Аукцион", callback_data="test_sound_temnauc.mp3"),
        ],
        [
            InlineKeyboardButton(text="🔊 Тест: Клановый рейд", callback_data="test_sound_clan.mp3"),
        ],
        [
            InlineKeyboardButton(text="🔊 Тест: Лололошка", callback_data="test_sound_lololoshka_online.mp3"),
        ],
        [
            InlineKeyboardButton(text="🔊 Тест: Фиксплей", callback_data="test_sound_fixplay_online.mp3"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
