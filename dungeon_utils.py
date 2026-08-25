from datetime import datetime, timezone, timedelta
from config import DUNGEONS, CLAN_RAID_INTERVAL_MINUTES, CLAN_RAID_ALERT_MINUTES_BEFORE, CLAN_RAID_RESTART_HOUR

MSK_TZ = timezone(timedelta(hours=3))

def get_now_msk() -> datetime:
    """Returns current datetime in Moscow timezone (UTC+3)."""
    return datetime.now(MSK_TZ)

def get_next_hard_dungeon(now: datetime = None) -> dict:
    """Calculates next Hard Dungeon (:10, :40)."""
    now = now or get_now_msk()
    minute = now.minute
    
    if minute < 10:
        target = now.replace(minute=10, second=0, microsecond=0)
    elif minute < 40:
        target = now.replace(minute=40, second=0, microsecond=0)
    else:
        # Next hour at :10
        next_hour = now + timedelta(hours=1)
        target = next_hour.replace(minute=10, second=0, microsecond=0)
        
    delta_sec = int((target - now).total_seconds())
    mins_left = delta_sec // 60
    secs_left = delta_sec % 60
    
    return {
        "key": "dungeon_hard",
        "name": DUNGEONS["dungeon_hard"]["name"],
        "icon": DUNGEONS["dungeon_hard"]["icon"],
        "formatted_time": target.strftime("%H:%M"),
        "total_seconds": delta_sec,
        "mins_left": mins_left,
        "secs_left": secs_left,
    }

def get_next_medium_dungeon(now: datetime = None) -> dict:
    """Calculates next Medium Dungeon (:15, :45)."""
    now = now or get_now_msk()
    minute = now.minute
    
    if minute < 15:
        target = now.replace(minute=15, second=0, microsecond=0)
    elif minute < 45:
        target = now.replace(minute=45, second=0, microsecond=0)
    else:
        # Next hour at :15
        next_hour = now + timedelta(hours=1)
        target = next_hour.replace(minute=15, second=0, microsecond=0)
        
    delta_sec = int((target - now).total_seconds())
    mins_left = delta_sec // 60
    secs_left = delta_sec % 60
    
    return {
        "key": "dungeon_medium",
        "name": DUNGEONS["dungeon_medium"]["name"],
        "icon": DUNGEONS["dungeon_medium"]["icon"],
        "formatted_time": target.strftime("%H:%M"),
        "total_seconds": delta_sec,
        "mins_left": mins_left,
        "secs_left": secs_left,
    }

def get_next_jeju_raid(now: datetime = None) -> dict:
    """Calculates next Jeju Island Raid (17:00 MSK)."""
    now = now or get_now_msk()
    target = now.replace(hour=17, minute=0, second=0, microsecond=0)
    
    if now >= target:
        # Tomorrow at 17:00 MSK
        target += timedelta(days=1)
        
    delta_sec = int((target - now).total_seconds())
    hours_left = delta_sec // 3600
    mins_left = (delta_sec % 3600) // 60
    
    time_str = target.strftime("%H:%M")
    date_str = "сегодня" if target.date() == now.date() else "завтра"
    
    return {
        "key": "dungeon_jeju",
        "name": DUNGEONS["dungeon_jeju"]["name"],
        "icon": DUNGEONS["dungeon_jeju"]["icon"],
        "formatted_time": f"{time_str} МСК ({date_str})",
        "total_seconds": delta_sec,
        "hours_left": hours_left,
        "mins_left": mins_left,
    }

def get_next_dark_auction(now: datetime = None) -> dict:
    """Calculates next Dark Auction (Saturday at 19:00 MSK)."""
    now = now or get_now_msk()
    days_ahead = (5 - now.weekday()) % 7
    target = (now + timedelta(days=days_ahead)).replace(hour=19, minute=0, second=0, microsecond=0)
    
    if now >= target:
        target += timedelta(days=7)
        
    delta_sec = int((target - now).total_seconds())
    days_left = delta_sec // 86400
    hours_left = (delta_sec % 86400) // 3600
    mins_left = (delta_sec % 3600) // 60
    
    time_str = target.strftime("%H:%M")
    if target.date() == now.date():
        date_str = "сегодня"
    elif target.date() == (now + timedelta(days=1)).date():
        date_str = "завтра"
    else:
        date_str = target.strftime("%d.%m")
    
    time_parts = []
    if days_left > 0:
        time_parts.append(f"{days_left} д")
    if hours_left > 0 or days_left > 0:
        time_parts.append(f"{hours_left} ч")
    time_parts.append(f"{mins_left} мин")
    time_remaining = " ".join(time_parts)

    return {
        "key": "dark_auction",
        "name": DUNGEONS["dark_auction"]["name"],
        "icon": DUNGEONS["dark_auction"]["icon"],
        "formatted_time": f"{time_str} МСК ({date_str})",
        "total_seconds": delta_sec,
        "days_left": days_left,
        "hours_left": hours_left,
        "mins_left": mins_left,
        "time_remaining": time_remaining,
    }

def generate_dungeon_schedule_text() -> str:
    """Generates user-friendly text for upcoming dungeons and raids schedule."""
    hard = get_next_hard_dungeon()
    medium = get_next_medium_dungeon()
    jeju = get_next_jeju_raid()
    auction = get_next_dark_auction()
    now_str = get_now_msk().strftime("%H:%M:%S")
    
    text = (
        "🗡 <b>Расписание Подземелий, Рейдов и Аукциона (Solo Leveling VimeWorld):</b>\n\n"
        f"1. {hard['icon']} <b>{hard['name']}</b> ({DUNGEONS['dungeon_hard']['schedule_desc']})\n"
        f"   🕒 Ближайшее: <b>{hard['formatted_time']}</b> (через <b>{hard['mins_left']} мин</b>)\n\n"
        f"2. {medium['icon']} <b>{medium['name']}</b> ({DUNGEONS['dungeon_medium']['schedule_desc']})\n"
        f"   🕒 Ближайшее: <b>{medium['formatted_time']}</b> (через <b>{medium['mins_left']} мин</b>)\n\n"
        f"3. {jeju['icon']} <b>{jeju['name']}</b> ({DUNGEONS['dungeon_jeju']['schedule_desc']})\n"
        f"   🕒 Ближайшее: <b>{jeju['formatted_time']}</b> (через <b>{jeju['hours_left']} ч {jeju['mins_left']} мин</b>)\n\n"
        f"4. {auction['icon']} <b>{auction['name']}</b> ({DUNGEONS['dark_auction']['schedule_desc']})\n"
        f"   🕒 Ближайшее: <b>{auction['formatted_time']}</b> (через <b>{auction['time_remaining']}</b>)\n\n"
        f"🔔 <i>Уведомления и голосовые анонсы приходят за 2 мин до подземелий/рейда и за 10 мин до Тёмного Аукциона!</i>\n"
        f"🕒 <i>Текущее время (МСК): {now_str}</i>"
    )
    return text


# --- CLAN RAIDS (Solo Leveling Clan Events - Interval: 1 hour / Every hour :00 from 03:00 to 03:00) ---

def get_clan_raids_for_date(target_date, restart_mode: bool = True) -> list[datetime]:
    """
    Returns list of datetime objects for clan raids on target_date (MSK).
    Clan raids run every hour on the hour: 03:00, 04:00, 05:00... 23:00, 00:00, 01:00, 02:00.
    """
    raids = [
        datetime(target_date.year, target_date.month, target_date.day, h, 0, tzinfo=MSK_TZ)
        for h in range(24)
    ]
    return sorted(raids)

def get_next_clan_raid(now: datetime = None, restart_mode: bool = True) -> dict:
    """
    Calculates next upcoming clan raid and time until start/alert.
    """
    now = now or get_now_msk()
    raids_today = get_clan_raids_for_date(now.date(), restart_mode=restart_mode)
    raids_tomorrow = get_clan_raids_for_date((now + timedelta(days=1)).date(), restart_mode=restart_mode)
    
    all_upcoming = [r for r in raids_today + raids_tomorrow if r >= now]
    target = all_upcoming[0] if all_upcoming else now + timedelta(minutes=CLAN_RAID_INTERVAL_MINUTES)

    delta_sec = int((target - now).total_seconds())
    hours_left = delta_sec // 3600
    mins_left = (delta_sec % 3600) // 60
    
    time_str = target.strftime("%H:%M")
    if target.date() == now.date():
        date_str = "сегодня"
    elif target.date() == (now + timedelta(days=1)).date():
        date_str = "завтра"
    else:
        date_str = target.strftime("%d.%m")
        
    time_parts = []
    if hours_left > 0:
        time_parts.append(f"{hours_left} ч")
    time_parts.append(f"{mins_left} мин")
    time_remaining = " ".join(time_parts) if time_parts else "0 мин"

    alert_dt = target - timedelta(minutes=CLAN_RAID_ALERT_MINUTES_BEFORE)
    alert_time_str = alert_dt.strftime("%H:%M")

    return {
        "key": "clan_raid",
        "name": "Клановый рейд",
        "icon": "🏰",
        "target_dt": target,
        "alert_dt": alert_dt,
        "formatted_time": f"{time_str} МСК ({date_str})",
        "alert_formatted": f"{alert_time_str} МСК",
        "total_seconds": delta_sec,
        "hours_left": hours_left,
        "mins_left": mins_left,
        "time_remaining": time_remaining,
        "restart_mode": restart_mode
    }

