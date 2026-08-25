import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "8874409890:AAFjNij0a-4qDrzx9iAAdX18un6RmicGIn4")

# Discord Bot Settings
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
DISCORD_VOICE_CHANNEL_ID = int(os.getenv("DISCORD_VOICE_CHANNEL_ID", "1535356648594473000")) if os.getenv("DISCORD_VOICE_CHANNEL_ID", "1535356648594473000").isdigit() else 1535356648594473000

# Admin User IDs
ADMIN_IDS = [5881764740] # Telegram Admin ID
DISCORD_ADMIN_IDS = [1065635355014996098] # Discord Admin User ID

# Target players to monitor
YOUTUBERS = {
    "MrLalalashkaXXL": {
        "name": "Лололошка",
        "nick": "MrLalalashkaXXL",
        "url": "https://vimeworld.com/player/MrLalalashkaXXL",
        "icon": "🎬",
        "sound": "lololoshka_online.mp3"
    },
    "F1xPlay_": {
        "name": "Фиксплей",
        "nick": "F1xPlay_",
        "url": "https://vimeworld.com/player/F1xPlay_",
        "icon": "🎮",
        "sound": "fixplay_online.mp3"
    }
}

# Dungeon & Raid definitions (Pre-alerts sent 2 minutes before start)
DUNGEONS = {
    "dungeon_hard": {
        "name": "Сложное подземелье",
        "icon": "🗡",
        "schedule_desc": "каждые :10 и :40 минут",
        "minutes": [10, 40],
        "alert_minutes": [8, 38],
        "sound": "dungeon_hard.mp3"
    },
    "dungeon_medium": {
        "name": "Среднее подземелье",
        "icon": "⚔️",
        "schedule_desc": "каждые :15 и :45 минут",
        "minutes": [15, 45],
        "alert_minutes": [13, 43],
        "sound": "dungeon_medium.mp3"
    },
    "dungeon_jeju": {
        "name": "Остров Чеджу (Рейд)",
        "icon": "🌋",
        "schedule_desc": "в 17:00 МСК",
        "alert_time": (16, 58),
        "start_time": (17, 0),
        "sound": "jeju_raid.mp3"
    },
    "dark_auction": {
        "name": "Тёмный Аукцион",
        "icon": "🏛",
        "schedule_desc": "суббота в 19:00 МСК",
        "day_of_week": 5,
        "alert_time": (18, 50),
        "start_time": (19, 0),
        "sound": "temnauc.mp3"
    }
}

# Clan Raid configuration (Solo Leveling)
CLAN_RAID_INTERVAL_MINUTES = 75  # 1 hour 15 minutes (reduced by another 10m via clan upgrade)
CLAN_RAID_ALERT_MINUTES_BEFORE = 5
CLAN_RAID_RESTART_HOUR = 3  # Daily restart at 03:00 MSK

# Creator profile info
CREATOR = {
    "name": "dima_286812312",
    "nick": "dima_286812312",
    "url": "https://vimeworld.com/player/dima_286812312",
    "icon": "👑",
}

# Check interval in seconds for background monitoring
CHECK_INTERVAL = 2

# Persistent database path
raw_db_path = os.getenv("DB_PATH")
if not raw_db_path:
    volume_path = os.getenv("RAILWAY_VOLUME_MOUNT_PATH")
    if volume_path:
        raw_db_path = os.path.join(volume_path, "bot_data.db")
    else:
        raw_db_path = os.path.join("data", "bot_data.db")

DB_PATH = raw_db_path
