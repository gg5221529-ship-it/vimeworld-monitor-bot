import asyncio
import logging
import time
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


# Tracks already-sent dungeon alerts (key -> monotonic send time) to prevent duplicates.
# Pruned by age instead of cleared wholesale: a full clear right after an alert was
# added could re-send the very same alert within the same minute.
sent_dungeon_alerts = {}

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
            sent_dungeon_alerts[alert_key] = time.monotonic()

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
            sent_dungeon_alerts[alert_key] = time.monotonic()

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
            sent_dungeon_alerts[alert_key] = time.monotonic()

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
            sent_dungeon_alerts[alert_key] = time.monotonic()

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
            sent_dungeon_alerts[alert_key] = time.monotonic()

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
                sent_dungeon_alerts[alert_key] = time.monotonic()
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
                sent_dungeon_alerts[alert_key] = time.monotonic()
                if sound_clan_enabled:
                    asyncio.create_task(discord_bot.play_voice_sound("clan.mp3"))

    # Prune alert keys older than 2 hours (a key can never legitimately recur within that window)
    if len(sent_dungeon_alerts) > 80:
        cutoff = time.monotonic() - 7200
        for stale_key in [k for k, ts in sent_dungeon_alerts.items() if ts < cutoff]:
            sent_dungeon_alerts.pop(stale_key, None)

# ============================================================================
# ANTI-SPAM: transition confirmation & flap suppression for player alerts
# ============================================================================
# OFFLINE must persist this many consecutive checks before the exit alert fires
REQUIRED_OFFLINE_CHECKS = 8       # 8 * 2s = ~16s
# Any other state change (join, SL entry/exit, game switch) must persist this
# many consecutive checks before alerting. Kills single-tick API blips that
# previously caused instant "зашёл"/"вышел" message pairs.
REQUIRED_STATE_CHECKS = 3         # 3 * 2s = ~6s
# An online session shorter than this produces no exit alerts (likely a relog/blip)
MIN_SESSION_FOR_EXIT_ALERT = 60   # seconds
# A Solo Leveling stint shorter than this produces no "вышел с SL" alert
MIN_SL_STINT_FOR_EXIT_ALERT = 45  # seconds
# When a ghost session is blocked (API says online, /online/staff disagrees),
# online reports for that player are ignored for this long. The lastSeen filter
# in checker.py cleans up the rest of the ghost window.
GHOST_IGNORE_SECONDS = 120
# Ranks for which the /online/staff ghost-gate is applied (mirrors checker.py)
STAFF_RANKS = ("YOUTUBE", "YOUTUBER", "ADMIN", "CHIEF", "WARDEN", "MODER", "DEV")

confirmed_states = {}     # nick -> last confirmed raw state (hydrated on startup)
pending_transitions = {}  # nick -> {"state": str, "count": int} — transition being confirmed
communicated_states = {}  # nick -> last state subscribers were actually told about
session_starts = {}       # nick -> monotonic ts when the current online session started
sl_starts = {}            # nick -> monotonic ts when the current SL stint started
ghost_ignored_until = {}  # nick -> monotonic ts until which online reports are ignored

def mono() -> float:
    """Monotonic clock for anti-spam timers (immune to system clock changes)."""
    return time.monotonic()

def _stint_long_enough(start_ts, min_seconds: float) -> bool:
    """Unknown start (e.g. state adopted after a restart) always counts as long enough."""
    return start_ts is None or (mono() - start_ts) >= min_seconds

async def initialize_player_states():
    """
    Fetches fresh states on startup and adopts them silently (no alerts).
    Any change that happened while the bot was down must not produce stale
    notifications with wrong timestamps after a restart.
    """
    for nick in YOUTUBERS:
        try:
            info = await checker.fetch_player_status(nick)
            if info.get("fetch_failed"):
                saved_state = await db.get_player_last_state(nick)
                confirmed_states[nick] = saved_state
                communicated_states[nick] = saved_state
                logger.warning(f"Could not fetch startup status for {nick}; keeping saved state: {saved_state}")
                continue
            await db.update_player_last_state(nick, info['state'], info['is_online'])
            confirmed_states[nick] = info['state']
            communicated_states[nick] = info['state']
            logger.info(f"Initialized player state for {nick}: State={info['state']}")
        except Exception as e:
            logger.error(f"Error during status check on startup for {nick}: {e}")

async def process_player_state_check(bot: Bot, nick: str, data: dict, info: dict):
    """
    Processes one fetched status for a monitored player.

    Anti-spam rules:
    1. A state change must persist REQUIRED_STATE_CHECKS (or REQUIRED_OFFLINE_CHECKS
       for going offline) consecutive fetches before any alert is sent, so single-tick
       API blips never produce "зашёл"/"вышел" pairs.
    2. Joining the server is additionally verified via /online/staff for staff-ranked
       players to block ghost sessions right away.
    3. Exit alerts are suppressed for very short sessions/SL stints (relog noise).
    4. Alerts are only sent when the new state differs from the last state subscribers
       were actually told about, so suppressed flaps never echo back as messages.
    """
    raw_state = info['state']
    confirmed = confirmed_states.get(nick)
    if confirmed is None:
        confirmed = await db.get_player_last_state(nick)
        confirmed_states[nick] = confirmed
        communicated_states.setdefault(nick, confirmed)

    # Ghost-session window: ignore online reports right after a blocked ghost
    if raw_state != "OFFLINE" and confirmed == "OFFLINE" and mono() < ghost_ignored_until.get(nick, 0.0):
        return

    # No change against the confirmed state -> drop any pending transition
    if raw_state == confirmed:
        pending_transitions.pop(nick, None)
        return

    # Accumulate consecutive fetches observing the same new state
    pending = pending_transitions.get(nick)
    if pending and pending["state"] == raw_state:
        pending["count"] += 1
    else:
        pending = {"state": raw_state, "count": 1}
        pending_transitions[nick] = pending

    required = REQUIRED_OFFLINE_CHECKS if raw_state == "OFFLINE" else REQUIRED_STATE_CHECKS
    if pending["count"] < required:
        return

    # ---------- Transition confirmed ----------
    pending_transitions.pop(nick, None)
    prev_state = confirmed
    new_state = raw_state
    ts = mono()

    # Ghost gate on join: verify via /online/staff for staff/YOUTUBE-ranked players
    if prev_state == "OFFLINE" and new_state != "OFFLINE":
        rank = (info.get("rank") or "").upper()
        if rank in STAFF_RANKS:
            in_staff = await checker.is_in_staff_online(nick)
            if in_staff is False:
                ghost_ignored_until[nick] = ts + GHOST_IGNORE_SECONDS
                logger.info(
                    f"👻 Ghost session for {data['name']} ({nick}) blocked "
                    f"(not in /online/staff). Ignoring online reports for {GHOST_IGNORE_SECONDS}s."
                )
                return
        session_starts[nick] = ts

    confirmed_states[nick] = new_state
    await db.update_player_last_state(nick, new_state, info['is_online'])
    logger.info(f"⚡ Confirmed state change for {data['name']} ({nick}): {prev_state} ➔ {new_state}")

    if new_state == "SOLOLEVELING":
        sl_starts[nick] = ts

    # ---- Build the alert (only vs. the last state subscribers were told about) ----
    communicated = communicated_states.get(nick, prev_state)
    subscribers = await db.get_subscribers_for_player(nick)
    now_str = get_now_msk_str()
    alert_msg = None
    play_sound = False

    # A. Entered Solo Leveling (from OFFLINE, LOBBY or OTHER_GAME)
    if new_state == "SOLOLEVELING" and communicated != "SOLOLEVELING":
        alert_msg = (
            f"🚨 <b>{data['icon']} {data['name'].upper()} ЗАШЁЛ НА SOLO LEVELING!</b> 🚨\n\n"
            f"🎮 <b>{data['name']}</b> (<code>{nick}</code>) зашёл в режим <b>Solo Leveling</b> на VimeWorld!\n"
            f"⏰ Время (МСК): <b>{now_str}</b>\n\n"
            f"🔗 <a href='{data['url']}'>Перейти на профиль VimeWorld</a>"
        )
        play_sound = True
    # B. Left Solo Leveling / Returned to Lobby
    elif (prev_state == "SOLOLEVELING" and new_state in ("LOBBY", "OTHER_GAME")
            and communicated == "SOLOLEVELING"):
        if _stint_long_enough(sl_starts.get(nick), MIN_SL_STINT_FOR_EXIT_ALERT):
            alert_msg = (
                f"🟡 <b>{data['icon']} {data['name'].upper()} ВЫШЕЛ С SOLO LEVELING В ЛОББИ</b>\n\n"
                f"🎮 <b>{data['name']}</b> (<code>{nick}</code>) вышел с Solo Leveling в лобби (или сменил режим).\n"
                f"⏰ Время (МСК): <b>{now_str}</b>"
            )
        else:
            logger.info(f"🔇 Suppressed short SL-stint exit alert for {data['name']} ({nick})")
    # C. Connected to server (In Lobby) from OFFLINE
    elif (prev_state == "OFFLINE" and new_state in ("LOBBY", "OTHER_GAME")
            and communicated == "OFFLINE"):
        alert_msg = (
            f"🟡 <b>{data['icon']} {data['name'].upper()} ЗАШЁЛ НА СЕРВЕР (В ЛОББИ)</b>\n\n"
            f"🎮 <b>{data['name']}</b> (<code>{nick}</code>) зашёл на VimeWorld (сейчас в лобби).\n"
            f"⏰ Время входа (МСК): <b>{now_str}</b>"
        )
    # D. Confirmed exit from the server
    elif new_state == "OFFLINE" and communicated != "OFFLINE":
        if _stint_long_enough(session_starts.get(nick), MIN_SESSION_FOR_EXIT_ALERT):
            alert_msg = (
                f"🔴 <b>{data['icon']} {data['name'].upper()} ВЫШЕЛ С СЕРВЕРА</b>\n\n"
                f"🎮 <b>{data['name']}</b> (<code>{nick}</code>) вышел с сервера VimeWorld.\n"
                f"⏰ Время выхода (МСК): <b>{now_str}</b>"
            )
        else:
            logger.info(f"🔇 Suppressed short-session exit alert for {data['name']} ({nick})")
        session_starts.pop(nick, None)

    # LOBBY <-> OTHER_GAME switches and suppressed flap echoes stay silent on purpose.

    if play_sound and "sound" in data:
        asyncio.create_task(discord_bot.play_voice_sound(data["sound"]))

    if alert_msg:
        communicated_states[nick] = new_state
        if subscribers:
            for user_id in subscribers:
                await safe_send_alert_message(bot, user_id, alert_msg, disable_preview=False)

async def start_monitoring(bot: Bot):
    """
    Main background loop that:
    1. Checks YouTuber online status every 2 seconds with transition confirmation (Anti-Flapping).
    2. Checks upcoming dungeons/raids and triggers 2-min reminders & Discord voice alerts.
    """
    logger.info(
        f"Starting background monitoring loop (check interval: {CHECK_INTERVAL}s, "
        f"online confirm: {REQUIRED_STATE_CHECKS * CHECK_INTERVAL}s, "
        f"offline debounce: {REQUIRED_OFFLINE_CHECKS * CHECK_INTERVAL}s)..."
    )

    # Adopt current real states on startup without alerts
    await initialize_player_states()

    while True:
        try:
            await asyncio.sleep(CHECK_INTERVAL)

            # Check Dungeon & Raid 2-minute pre-alerts
            await check_and_send_dungeon_alerts(bot)

            # Check YouTuber online states (transition confirmation + anti-flap)
            for nick, data in YOUTUBERS.items():
                info = await checker.fetch_player_status(nick)

                # If API call failed/timed out, skip this cycle (pending streaks are preserved)
                if info.get("fetch_failed"):
                    continue

                await process_player_state_check(bot, nick, data, info)

        except asyncio.CancelledError:
            logger.info("Monitoring loop cancelled.")
            break
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
