import asyncio
import logging
from datetime import datetime, timezone, timedelta
from aiogram import Router, F
from aiogram.filters import Command, or_f
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramRetryAfter, TelegramAPIError
from config import YOUTUBERS, DUNGEONS, CREATOR, ADMIN_IDS
import checker
import dungeon_utils
import database as db
import keyboards
import discord_bot

logger = logging.getLogger(__name__)

# Moscow Timezone (UTC+3)
MSK_TZ = timezone(timedelta(hours=3))

def get_now_msk_str() -> str:
    """Returns current Moscow time formatted as HH:MM:SS."""
    return datetime.now(MSK_TZ).strftime("%H:%M:%S")

router = Router()

def format_status_msg(info: dict, custom_title: str = None) -> str:
    """Formats player info into a clean Telegram HTML message."""
    title = custom_title or info['nickname']
    status_icon = info['status_display']
    
    text = f"<b>{title}</b> (<code>{info['nickname']}</code>)\n\n"
    text += f"Статус: <b>{status_icon}</b>\n"
    if info.get('level') is not None:
        text += f"Уровень: <b>{info['level']}</b>\n"
    if info.get('rank'):
        text += f"Ранг: <b>{info['rank']}</b>\n"
        
    text += f"\n🔗 <a href='{info['url']}'>Открыть профиль на VimeWorld</a>"
    return text

def format_player_profile_card(info: dict) -> str:
    """Formats rich player profile card with Solo Leveling stats."""
    nick = info["nickname"]
    status = info["status_display"]
    rank = info.get("rank", "USER")
    lvl = info.get("level", 0)
    pct = info.get("level_pct", 0)
    hrs = info.get("played_hours", 0)
    guild = info.get("guild_name")
    guild_lvl = info.get("guild_level")
    
    text = f"👤 <b>Статистика игрока {nick}</b> (VimeWorld)\n\n"
    text += f"Текущий статус: <b>{status}</b>\n"
    text += f"Ранг: <b>{rank}</b> | Уровень: <b>{lvl} ({pct}%)</b>\n"
    text += f"Наиграно в игре: <b>{hrs} ч</b>\n"
    if guild:
        text += f"Гильдия: <b>{guild}</b> (Уровень {guild_lvl})\n"
        
    text += "\n🗡 <b>Статистика Solo Leveling:</b>\n"
    text += f"• 🔄 <b>Перерождений:</b> <code>{info['sl_rebirth']}</code>\n"
    text += f"• ⚡ <b>Сила удара:</b> <code>{info['sl_damage_formatted']}</code>\n"
    text += f"• 💰 <b>Золото:</b> <code>{info['sl_gold_formatted']}</code>\n"
    text += f"• 🎯 <b>Очки улучшений:</b> <code>{info['sl_upgrade_points']}</code>\n\n"
    text += f"🔗 <a href='{info['url']}'>Открыть профиль на VimeWorld</a>"
    return text

def format_player_comparison_card(p1: dict, p2: dict) -> str:
    """Formats comparison card between two players."""
    nick1, nick2 = p1["nickname"], p2["nickname"]
    
    dmg1, dmg2 = p1["sl_damage_raw"], p2["sl_damage_raw"]
    reb1, reb2 = p1["sl_rebirth"], p2["sl_rebirth"]
    lvl1, lvl2 = p1.get("level", 0), p2.get("level", 0)
    hrs1, hrs2 = p1.get("played_hours", 0), p2.get("played_hours", 0)
    
    icon_dmg1 = " 🏆" if dmg1 > dmg2 else (" 🤝" if dmg1 == dmg2 else "")
    icon_dmg2 = " 🏆" if dmg2 > dmg1 else (" 🤝" if dmg1 == dmg2 else "")

    icon_reb1 = " 🏆" if reb1 > reb2 else (" 🤝" if reb1 == reb2 else "")
    icon_reb2 = " 🏆" if reb2 > reb1 else (" 🤝" if reb1 == reb2 else "")

    icon_lvl1 = " 🏆" if lvl1 > lvl2 else (" 🤝" if lvl1 == lvl2 else "")
    icon_lvl2 = " 🏆" if lvl2 > lvl1 else (" 🤝" if lvl1 == lvl2 else "")

    if dmg1 > dmg2:
        winner = f"<b>{nick1}</b> (+{(dmg1/dmg2 if dmg2>0 else 1):.1f}x от силы соперника)"
    elif dmg2 > dmg1:
        winner = f"<b>{nick2}</b> (+{(dmg2/dmg1 if dmg1>0 else 1):.1f}x от силы соперника)"
    else:
        winner = "<b>Ничья!</b>"

    text = (
        f"⚔️ <b>Сравнение игроков Solo Leveling</b> ⚔️\n\n"
        f"👤 <b>{nick1}</b> <i>VS</i> 👤 <b>{nick2}</b>\n\n"
        f"⚡ <b>Сила удара:</b>\n"
        f"• {nick1}: <code>{p1['sl_damage_formatted']}</code>{icon_dmg1}\n"
        f"• {nick2}: <code>{p2['sl_damage_formatted']}</code>{icon_dmg2}\n\n"
        f"🔄 <b>Перерождения:</b>\n"
        f"• {nick1}: <b>{p1['sl_rebirth']}</b>{icon_reb1}\n"
        f"• {nick2}: <b>{p2['sl_rebirth']}</b>{icon_reb2}\n\n"
        f"📊 <b>Уровень VimeWorld:</b>\n"
        f"• {nick1}: <b>{p1['level']} ур.</b>{icon_lvl1}\n"
        f"• {nick2}: <b>{p2['level']} ур.</b>{icon_lvl2}\n\n"
        f"⏱ <b>Наигранное время:</b>\n"
        f"• {nick1}: <b>{hrs1} ч</b>\n"
        f"• {nick2}: <b>{hrs2} ч</b>\n\n"
        f"👑 <b>Лидер по силе удара:</b> {winner}"
    )
    return text

async def generate_monitoring_text(user_id: int) -> str:
    """Generates clear monitoring status text for user."""
    subs = await db.get_user_subscriptions(user_id)
    
    lol_active = "MrLalalashkaXXL" in subs
    fix_active = "F1xPlay_" in subs
    hard_active = "dungeon_hard" in subs
    med_active = "dungeon_medium" in subs
    double_active = "dungeon_double" in subs
    jeju_active = "dungeon_jeju" in subs
    auc_active = "dark_auction" in subs

    total_subs_count = sum([lol_active, fix_active, hard_active, med_active, double_active, jeju_active, auc_active])
    
    if total_subs_count == 7:
        overall_status = "🟢 <b>Все уведомления ВКЛЮЧЕНЫ</b> (Ютуберы + Данжи + Двойное + Чеджу + Аукцион)"
    elif total_subs_count > 0:
        overall_status = f"🟡 <b>Уведомления ВКЛЮЧЕНЫ частично</b> ({total_subs_count} из 7 типов)"
    else:
        overall_status = "🔴 <b>Уведомления ВЫКЛЮЧЕНЫ</b>"

    text = (
        f"🔔 <b>Управление уведомлениями онлайна и подземелий</b>\n\n"
        f"Текущее состояние: {overall_status}\n\n"
        "<b>Доступные подписки:</b>\n"
        "• 🎬/🎮 <b>Ютуберы:</b> статус онлайна и входа на Solo Leveling\n"
        "• 🗡 <b>Сложное подземелье:</b> каждые :10 и :40 мин (увед за 2 мин)\n"
        "• ⚔️ <b>Среднее подземелье:</b> каждые :15 и :45 мин (увед за 2 мин)\n"
        "• 💀 <b>Двойное подземелье:</b> в 00:00, 06:00, 12:00, 18:00 МСК (увед за 2 мин)\n"
        "• 🌋 <b>Остров Чеджу (Рейд):</b> в 17:00 МСК (увед в 16:58)\n"
        "• 🏛 <b>Тёмный Аукцион:</b> каждую субботу в 19:00 МСК (увед в 18:50)\n\n"
        "Нажимай на кнопки ниже, чтобы включать или выключать нужные уведомления:"
    )
    return text

async def generate_admin_stats_text() -> str:
    """Generates admin statistics text in MSK timezone including Discord voice bot status."""
    total_users = await db.get_total_users_count()
    active_subs = await db.get_active_subscribers_count()
    breakdown = await db.get_subscriptions_breakdown()
    
    lol_count = breakdown.get("MrLalalashkaXXL", 0)
    fix_count = breakdown.get("F1xPlay_", 0)
    hard_count = breakdown.get("dungeon_hard", 0)
    med_count = breakdown.get("dungeon_medium", 0)
    double_count = breakdown.get("dungeon_double", 0)
    jeju_count = breakdown.get("dungeon_jeju", 0)
    auc_count = breakdown.get("dark_auction", 0)
    
    now_str = get_now_msk_str()
    discord_info = await discord_bot.get_discord_debug_info()
    
    text = (
        "👑 <b>Панель Администратора</b>\n\n"
        f"📊 <b>Статистика бота:</b>\n"
        f"👥 Пользователей в базе: <code>{total_users}</code> | 🔔 Активных подписчиков: <code>{active_subs}</code>\n\n"
        f"• 🗡 Сложное: <b>{hard_count}</b> | ⚔️ Среднее: <b>{med_count}</b> | 💀 Двойное: <b>{double_count}</b>\n"
        f"• 🌋 Чеджу: <b>{jeju_count}</b> | 🏛 Аукцион: <b>{auc_count}</b>\n\n"
        f"<b>Статус Discord Voice:</b>\n{discord_info}\n\n"
        f"⏱ <i>Интервал проверки: 2 сек | Отчет (МСК): {now_str}</i>"
    )
    return text

@router.message(Command("start"))
async def cmd_start(message: Message):
    """Handler for /start command."""
    await db.add_user(message.from_user.id)
    
    welcome_text = (
        "👋 <b>Привет! Я бот-мониторинг VimeWorld (Solo Leveling)!</b>\n\n"
        "Я отслеживаю статус ютуберов, подземелья и статистику игроков:\n"
        "• 🔍 <b>Поиск игрока:</b> `/player ник`\n"
        "• ⚔️ <b>Сравнение игроков:</b> `/compare ник1 ник2`\n"
        "• 🎬 <b>Лололошка</b> и 🎮 <b>Фиксплей</b>\n"
        "• 🗡 <b>Подземелья и Рейды</b>\n\n"
        "Выбери нужный раздел на клавиатуре ниже!"
    )
    
    try:
        await message.answer(
            welcome_text,
            reply_markup=keyboards.get_main_keyboard(message.from_user.id),
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after)
        await message.answer(welcome_text, reply_markup=keyboards.get_main_keyboard(message.from_user.id), parse_mode="HTML")

@router.message(or_f(Command("player"), Command("profile")))
async def cmd_player(message: Message):
    """Handler for /player <nickname> command."""
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("🔍 <b>Укажите никнейм игрока!</b>\n\nПример использования: <code>/player dima_286812312</code>", parse_mode="HTML")
        return
        
    nick = args[1].strip()
    profile = await checker.fetch_full_player_profile(nick)
    
    if not profile.get("exists"):
        await message.answer(f"❌ Игрок с ником <code>{nick}</code> не найден на VimeWorld!", parse_mode="HTML")
        return
        
    text = format_player_profile_card(profile)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🌐 Профиль на VimeWorld", url=profile['url'])
    ]])
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

@router.message(Command("compare"))
async def cmd_compare(message: Message):
    """Handler for /compare <nick1> <nick2> command."""
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("⚔️ <b>Укажите никнеймы двух игроков для сравнения!</b>\n\nПример использования: <code>/compare dima_286812312 MrLalalashkaXXL</code>", parse_mode="HTML")
        return
        
    nick1, nick2 = parts[1].strip(), parts[2].strip()
    
    p1_task = checker.fetch_full_player_profile(nick1)
    p2_task = checker.fetch_full_player_profile(nick2)
    p1, p2 = await asyncio.gather(p1_task, p2_task)
    
    if not p1.get("exists"):
        await message.answer(f"❌ Игрок <code>{nick1}</code> не найден на VimeWorld!", parse_mode="HTML")
        return
    if not p2.get("exists"):
        await message.answer(f"❌ Игрок <code>{nick2}</code> не найден на VimeWorld!", parse_mode="HTML")
        return

    text = format_player_comparison_card(p1, p2)
    await message.answer(text, parse_mode="HTML")

@router.message(F.text.contains("Профиль игрока"))
async def handle_profile_button(message: Message):
    """Guide for player search button."""
    text = (
        "🔍 <b>Поиск и сравнение профилей VimeWorld:</b>\n\n"
        "• Для просмотра профиля игрока отправьте команду:\n"
        "  <code>/player никнейм</code> (например, <code>/player dima_286812312</code>)\n\n"
        "• Для сравнения двух игроков отправьте команду:\n"
        "  <code>/compare ник1 ник2</code> (например, <code>/compare dima_286812312 MrLalalashkaXXL</code>)"
    )
    await message.answer(text, parse_mode="HTML")

@router.message(F.text.contains("Лололошка"))
async def handle_lololoshka(message: Message):
    """Checks Lololoshka status."""
    info = await checker.fetch_player_status(YOUTUBERS["MrLalalashkaXXL"]["nick"])
    msg_text = format_status_msg(info, custom_title="🎬 Ютубер Лололошка")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🌐 Профиль VimeWorld", url=info['url'])
    ]])
    
    try:
        await message.answer(msg_text, reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True)
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after)
        await message.answer(msg_text, reply_markup=kb, parse_mode="HTML")

@router.message(F.text.contains("Фиксплей"))
async def handle_fixplay(message: Message):
    """Checks FixPlay status."""
    info = await checker.fetch_player_status(YOUTUBERS["F1xPlay_"]["nick"])
    msg_text = format_status_msg(info, custom_title="🎮 Ютубер Фиксплей")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🌐 Профиль VimeWorld", url=info['url'])
    ]])
    
    try:
        await message.answer(msg_text, reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True)
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after)
        await message.answer(msg_text, reply_markup=kb, parse_mode="HTML")

@router.message(or_f(Command("dungeons"), F.text.contains("Подземелья"), F.text.contains("подземелья"), F.text.contains("Рейды"), F.text.contains("рейды")))
async def handle_dungeons(message: Message):
    """Shows upcoming dungeons and raids schedule."""
    text = dungeon_utils.generate_dungeon_schedule_text()
    try:
        await message.answer(text, parse_mode="HTML")
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after)
        await message.answer(text, parse_mode="HTML")

@router.message(or_f(Command("monitoring"), F.text.contains("уведомлен"), F.text.contains("Уведомлен"), F.text.contains("Мониторинг"), F.text.contains("мониторинг")))
async def handle_monitoring(message: Message):
    """Shows monitoring menu with toggle controls."""
    user_id = message.from_user.id
    await db.add_user(user_id)
    text = await generate_monitoring_text(user_id)
    kb = await keyboards.get_monitoring_inline_keyboard(user_id)
    try:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after)
        await message.answer(text, reply_markup=kb, parse_mode="HTML")

@router.message(F.text.contains("Создатель"))
async def handle_creator(message: Message):
    """Shows creator info with live VimeWorld status."""
    info = await checker.fetch_player_status(CREATOR["nick"])
    status_icon = info['status_display']
        
    text = (
        f"👑 <b>Создатель бота:</b> <a href='{CREATOR['url']}'>{CREATOR['name']}</a>\n\n"
        f"Текущий статус на VimeWorld: <b>{status_icon}</b>\n"
    )
    if info.get('level') is not None:
        text += f"Уровень: <b>{info['level']}</b>\n"
    if info.get('rank'):
        text += f"Ранг: <b>{info['rank']}</b>\n"
        
    text += f"\n🔗 <a href='{CREATOR['url']}'>Ссылка на профиль VimeWorld</a>"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="👑 Профиль Создателя на VimeWorld", url=CREATOR['url'])
    ]])
    
    try:
        await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after)
        await message.answer(text, parse_mode="HTML")

# ADMIN PANEL HANDLERS
@router.message(Command("admin"))
@router.message(Command("stats"))
@router.message(F.text.contains("Админ"))
@router.message(F.text.contains("админ"))
async def handle_admin_panel(message: Message):
    """Admin panel stats viewer."""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ <b>У вас нет доступа к админ-панели.</b>", parse_mode="HTML")
        return
        
    text = await generate_admin_stats_text()
    kb = keyboards.get_admin_inline_keyboard()
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data == "admin_refresh_stats")
async def cb_admin_refresh_stats(callback: CallbackQuery):
    """Refreshes admin statistics."""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
        
    text = await generate_admin_stats_text()
    kb = keyboards.get_admin_inline_keyboard()
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer("🔄 Статистика обновлена!")
    except TelegramAPIError:
        await callback.answer("Статистика актуальна")

@router.callback_query(F.data.startswith("test_sound_"))
async def cb_test_sound(callback: CallbackQuery):
    """Triggers Discord voice sound playback test from admin panel."""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
        
    sound_filename = callback.data.replace("test_sound_", "")
    await callback.answer("⏳ Запуск звукового теста Discord...")
    
    success, detail_msg = await discord_bot.play_voice_sound(sound_filename)
    
    admin_text = await generate_admin_stats_text()
    admin_text += f"\n\n<b>Результат теста звука ({sound_filename}):</b>\n{detail_msg}"
    
    kb = keyboards.get_admin_inline_keyboard()
    try:
        await callback.message.edit_text(admin_text, reply_markup=kb, parse_mode="HTML")
    except TelegramAPIError:
        pass

# Callback handlers for monitoring inline keyboard
ALL_KEYS = ["MrLalalashkaXXL", "F1xPlay_", "dungeon_hard", "dungeon_medium", "dungeon_double", "dungeon_jeju", "dark_auction"]

@router.callback_query(F.data.startswith("toggle_"))
async def cb_toggle(callback: CallbackQuery):
    key = callback.data.replace("toggle_", "")
    user_id = callback.from_user.id
    await db.add_user(user_id)
    
    is_sub = await db.is_subscribed(user_id, key)
    if is_sub:
        await db.unsubscribe_user(user_id, key)
        await callback.answer("🔴 Уведомление отключено!")
    else:
        await db.subscribe_user(user_id, key)
        await callback.answer("🟢 Уведомление включено!")
        
    text = await generate_monitoring_text(user_id)
    kb = await keyboards.get_monitoring_inline_keyboard(user_id)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except TelegramAPIError:
        pass

@router.callback_query(F.data == "enable_all")
async def cb_enable_all(callback: CallbackQuery):
    user_id = callback.from_user.id
    await db.add_user(user_id)
    
    for key in ALL_KEYS:
        await db.subscribe_user(user_id, key)
    await callback.answer("🟢 Все уведомления ВКЛЮЧЕНЫ!")
    
    text = await generate_monitoring_text(user_id)
    kb = await keyboards.get_monitoring_inline_keyboard(user_id)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except TelegramAPIError:
        pass

@router.callback_query(F.data == "disable_all")
async def cb_disable_all(callback: CallbackQuery):
    user_id = callback.from_user.id
    await db.add_user(user_id)
    
    for key in ALL_KEYS:
        await db.unsubscribe_user(user_id, key)
    await callback.answer("🔴 Все уведомления ВЫКЛЮЧЕНЫ!")
    
    text = await generate_monitoring_text(user_id)
    kb = await keyboards.get_monitoring_inline_keyboard(user_id)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except TelegramAPIError:
        pass
