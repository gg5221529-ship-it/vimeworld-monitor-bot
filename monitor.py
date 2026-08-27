import asyncio
import logging
from datetime import datetime, timezone, timedelta
from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter, TelegramAPIError
from config import YOUTUBERS, DUNGEONS, CHECK_INTERVAL
import checker
import database as db
import discord_bot
import dungeon_utils

logger = logging.getLogger(__name__)

# Moscow Timezone (UTC+3)
MSK_TZ = timezone(timedelta(hours=3))

def get_now_msk() -> datetime:
    """Returns current datetime in Moscow timezone (UTC+3)."""
    return datetime.now(MSK_TZ)

def get_now_msk_str() -> str:
    """Returns current Moscow time formatted as HH:MM:SS."""
    return get_now_msk().strftime("%H:%M:%S")

async def safe_send_alert_message(bot: Bot, user_id: int, msg: str, disable_preview: bool = True):
    """Sends Telegram message with automatic handling for flood limits and blocked users cleanup."""
    try:
        await bot.send_message(
            chat_id=user_id,
            text=msg,
            parse_mode="HTML",
            disable_web_page_preview=disable_preview
        )
    except TelegramRetryAfter as err:
        logger.warning(f"Flood limit sending alert to user {user_id}. Waiting {err.retry_after}s...")
        await asyncio.sleep(err.retry_after + 1)
        try:
            await bot.send_message(
                chat_id=user_id,
                text=msg,
                parse_mode="HTML",
                disable_web_page_preview=disable_preview
            )
        except Exception:
            pass
    except Exception as err:
        err_str = str(err).lower()
        if "forbidden" in err_str or "blocked" in err_str or "deactivated" in err_str or "chat not found" in err_str:
            logger.info(f"User {user_id} blocked bot or chat not found. Cleaning up from subscriptions...")
            await db.remove_user_completely(user_id)
        else:
            logger.warning(f"Failed to send alert to user {user_id}: {err}")


# Set to keep track of sent dungeon alerts to prevent duplicate sends
sent_dungeon_alerts = set()

async def check_and_send_dungeon_alerts(bot: Bot):
    """
    Checks if a dungeon or raid starts in 2 minutes and sends notifications + plays Discord voice sound.
    - Hard Dungeon: starts at :10 and :40 -> alert at :08 and :38
    - Medium Dungeon: starts at :15 and :45 -> alert at :13 and :43
    - Jeju Raid: starts at 17:00 MSK -> alert at 16:58 MSK
    """
    now = get_now_msk()
    hour = now.hour
    minute = now.minute
    now_str = now.strftime("%H:%M:%S")
    
    # 1. Hard Dungeon Alert (Alert at :08 and :38 - 2 min before :10 and :40)
    if minute in (8, 38):
        start_min = 10 if minute == 8 else 40
        start_time_str = f"{hour:02d}:{start_min:02d}"
        alert_key = ("dungeon_hard", now.date(), hour, minute)
        
        if alert_key not in sent_dungeon_alerts:
            sent_dungeon_alerts.add(alert_key)
            
            # Play Discord Voice Audio
            asyncio.create_task(discord_bot.play_voice_sound("dungeon_hard.mp3"))
            
            subscribers = await db.get_subscribers_for_player("dungeon_hard")
            if subscribers:
                msg = (
                    f"⏰ <b>НАПОМИНАНИЕ О ПОДЗЕМЕЛЬЕ!</b> ⏰\n\n"
                    f"🗡 <b>Сложное подземелье</b> начнется через <b>2 минуты</b> (в <b>{start_time_str}</b>)!\n"
                    f"⏰ Время МСК: <b>{now_str}</b>"
                )
                for user_id in subscribers:
                    await safe_send_alert_message(bot, user_id, msg)

    # 2. Medium Dungeon Alert (Alert at :13 and :43 - 2 min before :15 and :45)
    if minute in (13, 43):
        start_min = 15 if minute == 13 else 45
        start_time_str = f"{hour:02d}:{start_min:02d}"
        alert_key = ("dungeon_medium", now.date(), hour, minute)
        
        if alert_key not in sent_dungeon_alerts:
            sent_dungeon_alerts.add(alert_key)
            
            # Play Discord Voice Audio
            asyncio.create_task(discord_bot.play_voice_sound("dungeon_medium.mp3"))
            
            subscribers = await db.get_subscribers_for_player("dungeon_medium")
            if subscribers:
                msg = (
                    f"⏰ <b>НАПОМИНАНИЕ О ПОДЗЕМЕЛЬЕ!</b> ⏰\n\n"
                    f"⚔️ <b>Среднее подземелье</b> начнется через <b>2 минуты</b> (в <b>{start_time_str}</b>)!\n"
                    f"⏰ Время МСК: <b>{now_str}</b>"
                )
                for user_id in subscribers:
                    await safe_send_alert_message(bot, user_id, msg)

    # 3. Double Dungeon Alert (Starts at 00:00, 06:00, 12:00, 18:00 MSK -> Telegram Alert at :58)
    if hour in (23, 5, 11, 17) and minute == 58:
        next_hour = (hour + 1) % 24
        start_time_str = f"{next_hour:02d}:00"
        alert_key = ("dungeon_double_tg", now.date(), hour, minute)

        if alert_key not in sent_dungeon_alerts:
            sent_dungeon_alerts.add(alert_key)
            
            subscribers = await db.get_subscribers_for_player("dungeon_double")
            if subscribers:
                msg = (
                    f"💀 <b>НАПОМИНАНИЕ О ДВОЙНОМ ПОДЗЕМЕЛЬЕ!</b> 💀\n\n"
                    f"🚪 <b>Двойное подземелье</b> начнется через <b>2 минуты</b> (в <b>{start_time_str}</b>)!\n"
                    f"⏰ Время МСК: <b>{now_str}</b>"
                )
                for user_id in subscribers:
                    await safe_send_alert_message(bot, user_id, msg)

    # 4. Jeju Island Raid Alert (Alert at 16:58 MSK - 2 min before 17:00 MSK)
    if hour == 16 and minute == 58:
        alert_key = ("dungeon_jeju", now.date(), hour, minute)
        
        if alert_key not in sent_dungeon_alerts:
            sent_dungeon_alerts.add(alert_key)
            
            # Play Discord Voice Audio
            asyncio.create_task(discord_bot.play_voice_sound("jeju_raid.mp3"))
            
            subscribers = await db.get_subscribers_for_player("dungeon_jeju")
            if subscribers:
                msg = (
                    f"🚨 <b>РЕЙД НА ОСТРОВ ЧЕДЖУ!</b> 🚨\n\n"
                    f"🌋 <b>Рейд на Остров Чеджу</b> начнется через <b>2 минуты</b> (в <b>17:00 МСК</b>)!\n"
                    f"⏰ Время МСК: <b>{now_str}</b>"
                )
                for user_id in subscribers:
                    await safe_send_alert_message(bot, user_id, msg)

    # 5. Dark Auction Alert (Alert on Saturday at 18:50 MSK - 10 min before 19:00 MSK)
    if now.weekday() == 5 and hour == 18 and minute == 50:
        alert_key = ("dark_auction", now.date(), hour, minute)
        
        if alert_key not in sent_dungeon_alerts:
            sent_dungeon_alerts.add(alert_key)
            
            # Play Discord Voice Audio
            asyncio.create_task(discord_bot.play_voice_sound("temnauc.mp3"))
            
            subscribers = await db.get_subscribers_for_player("dark_auction")
            if subscribers:
                msg = (
                    f"🏛 <b>ТЁМНЫЙ АУКЦИОН!</b> 🏛\n\n"
                    f"💰 <b>Тёмный Аукцион</b> начнется через <b>10 минут</b> (в <b>19:00 МСК</b>)!\n"
                    f"⏰ Время МСК: <b>{now_str}</b>"
                )
                for user_id in subscribers:
                    await safe_send_alert_message(bot, user_id, msg)

    # 6. Hourly Voice Alert at :55 (Double Dungeon PRIORITY over Clan Raid)
    if minute == 55:
        is_double_dungeon_hour = hour in (23, 5, 11, 17)
        
        if is_double_dungeon_hour:
            # PRIORITY: Double Dungeon Voice Alert in Discord (clan raid sound suppressed)
            sound_double_enabled = await db.get_discord_setting("sound_dungeon_double", 1)
            alert_key = ("dungeon_double_voice", now.date(), hour, minute)
            
            if alert_key not in sent_dungeon_alerts:
                sent_dungeon_alerts.add(alert_key)
                if sound_double_enabled:
                    asyncio.create_task(discord_bot.play_voice_sound("double_dungeon.mp3"))
                else:
                    sound_clan_enabled = await db.get_discord_setting("sound_clan_raid", 1)
                    if sound_clan_enabled:
                        asyncio.create_task(discord_bot.play_voice_sound("clan.mp3"))
        else:
            # All other hours: Clan Raid Voice Alert
            sound_clan_enabled = await db.get_discord_setting("sound_clan_raid", 1)
            alert_key = ("clan_raid", now.date(), hour, minute)
            if alert_key not in sent_dungeon_alerts:
                sent_dungeon_alerts.add(alert_key)
                if sound_clan_enabled:
                    asyncio.create_task(discord_bot.play_voice_sound("clan.mp3"))

    # Clean old alert keys periodically
    if len(sent_dungeon_alerts) > 50:
        sent_dungeon_alerts.clear()

# Debounce tracking for offline state confirmation (prevents false alerts on hub teleportation / API blips)
# 8 checks * 2s interval = ~16 seconds of sustained offline before declaring OFFLINE
REQUIRED_OFFLINE_CHECKS = 8
offline_streak_counts = {}

async def start_monitoring(bot: Bot):
    """
    Main background loop that:
    1. Checks YouTuber online status every 2 seconds with Debounce (Anti-Flapping).
    2. Checks upcoming dungeons/raids and triggers 2-min reminders & Discord voice alerts.
    """
    logger.info(f"Starting background monitoring loop (check interval: {CHECK_INTERVAL}s, offline debounce: {REQUIRED_OFFLINE_CHECKS * CHECK_INTERVAL}s)...")
    
    # Initialize initial state on startup to prevent false notifications
    for nick in YOUTUBERS:
        try:
            state_exists = await db.has_player_state(nick)
            if not state_exists:
                info = await checker.fetch_player_status(nick)
                await db.update_player_last_state(nick, info['state'], info['is_online'])
                logger.info(f"Initialized new player state for {nick}: State={info['state']}")
            else:
                saved_state = await db.get_player_last_state(nick)
                logger.info(f"Preserved existing player state across restart for {nick}: State={saved_state}")
        except Exception as e:
            logger.error(f"Error during status check on startup for {nick}: {e}")

    while True:
        try:
            await asyncio.sleep(CHECK_INTERVAL)
            
            # Check Dungeon & Raid 2-minute pre-alerts
            await check_and_send_dungeon_alerts(bot)
            
            # Check YouTuber online states
            for nick, data in YOUTUBERS.items():
                info = await checker.fetch_player_status(nick)
                
                # If API call failed/timed out, skip this cycle to avoid false offline alerts
                if info.get("fetch_failed"):
                    continue

                current_state = info['state']
                prev_state = await db.get_player_last_state(nick)

                # 1. Player is Online (SOLOLEVELING, LOBBY, OTHER_GAME)
                if current_state != "OFFLINE":
                    offline_streak_counts[nick] = 0
                    
                    if current_state != prev_state:
                        logger.info(f"⚡ State change for {data['name']} ({nick}): {prev_state} ➔ {current_state}")
                        
                        # Play Discord Voice Audio if YouTuber enters Solo Leveling
                        if current_state == "SOLOLEVELING" and "sound" in data:
                            asyncio.create_task(discord_bot.play_voice_sound(data["sound"]))

                        subscribers = await db.get_subscribers_for_player(nick)
                        if subscribers:
                            now_str = get_now_msk_str()
                            alert_msg = None
                            
                            # A. Entered Solo Leveling
                            if current_state == "SOLOLEVELING":
                                alert_msg = (
                                    f"🚨 <b>{data['icon']} {data['name'].upper()} ЗАШЁЛ НА SOLO LEVELING!</b> 🚨\n\n"
                                    f"🎮 <b>{data['name']}</b> (<code>{nick}</code>) зашёл в режим <b>Solo Leveling</b> на VimeWorld!\n"
                                    f"⏰ Время (МСК): <b>{now_str}</b>\n\n"
                                    f"🔗 <a href='{data['url']}'>Перейти на профиль VimeWorld</a>"
                                )
                            # B. Left Solo Leveling / Returned to Lobby
                            elif prev_state == "SOLOLEVELING" and current_state in ("LOBBY", "OTHER_GAME"):
                                alert_msg = (
                                    f"🟡 <b>{data['icon']} {data['name'].upper()} ВЫШЕЛ С SOLO LEVELING В ЛОББИ</b>\n\n"
                                    f"🎮 <b>{data['name']}</b> (<code>{nick}</code>) вышел с Solo Leveling в лобби (или сменил режим).\n"
                                    f"⏰ Время (МСК): <b>{now_str}</b>"
                                )
                            # C. Connected to server (In Lobby) from OFFLINE
                            elif prev_state == "OFFLINE" and current_state in ("LOBBY", "OTHER_GAME"):
                                alert_msg = (
                                    f"🟡 <b>{data['icon']} {data['name'].upper()} ЗАШЁЛ НА СЕРВЕР (В ЛОББИ)</b>\n\n"
                                    f"🎮 <b>{data['name']}</b> (<code>{nick}</code>) зашёл на VimeWorld (сейчас в лобби).\n"
                                    f"⏰ Время входа (МСК): <b>{now_str}</b>"
                                )

                            if alert_msg:
                                for user_id in subscribers:
                                    await safe_send_alert_message(bot, user_id, alert_msg, disable_preview=False)

                        # Save updated online state immediately
                        await db.update_player_last_state(nick, current_state, info['is_online'])

                # 2. Player detected OFFLINE (Apply Debounce)
                else:
                    if prev_state == "OFFLINE":
                        offline_streak_counts[nick] = 0
                    else:
                        # Increment offline streak count for debounce
                        streak = offline_streak_counts.get(nick, 0) + 1
                        offline_streak_counts[nick] = streak
                        
                        if streak >= REQUIRED_OFFLINE_CHECKS:
                            # Confirmed offline after 16 seconds of continuous offline!
                            logger.info(f"⚡ Confirmed OFFLINE for {data['name']} ({nick}): {prev_state} ➔ OFFLINE (confirmed after {streak * CHECK_INTERVAL}s)")
                            offline_streak_counts[nick] = 0
                            
                            subscribers = await db.get_subscribers_for_player(nick)
                            if subscribers:
                                now_str = get_now_msk_str()
                                alert_msg = (
                                    f"🔴 <b>{data['icon']} {data['name'].upper()} ВЫШЕЛ С СЕРВЕРА</b>\n\n"
                                    f"🎮 <b>{data['name']}</b> (<code>{nick}</code>) вышел с сервера VimeWorld.\n"
                                    f"⏰ Время выхода (МСК): <b>{now_str}</b>"
                                )
                                for user_id in subscribers:
                                    await safe_send_alert_message(bot, user_id, alert_msg, disable_preview=False)

                            # Save confirmed OFFLINE state
                            await db.update_player_last_state(nick, "OFFLINE", False)
                
        except asyncio.CancelledError:
            logger.info("Monitoring loop cancelled.")
            break
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
