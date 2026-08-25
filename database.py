import os
import aiosqlite
import logging

logger = logging.getLogger(__name__)

DB_PATH = os.path.join("data", "bot_database.db")

async def init_db():
    """Initializes SQLite database and creates tables if not present."""
    os.makedirs("data", exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        # Users table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Subscriptions table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id INTEGER,
                sub_key TEXT,
                PRIMARY KEY (user_id, sub_key)
            )
        """)

        # Discord settings table (for audio & alerts toggle)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS discord_settings (
                key TEXT PRIMARY KEY,
                value INTEGER DEFAULT 1
            )
        """)

        # Discord user verifications table (Discord ID -> VimeWorld Nickname)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS discord_verifications (
                discord_user_id INTEGER PRIMARY KEY,
                vimeworld_nickname TEXT,
                verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Player states table (for monitoring online state transitions)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS player_states (
                nickname TEXT PRIMARY KEY,
                state TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await db.commit()
    logger.info("Database initialized successfully.")

async def add_user(user_id: int):
    """Adds a new Telegram user to database if not exists."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
            (user_id,)
        )
        await db.commit()

async def get_user_subscriptions(user_id: int) -> list:
    """Gets list of sub_keys for a given user."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT sub_key FROM subscriptions WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [r[0] for r in rows]

async def is_subscribed(user_id: int, sub_key: str) -> bool:
    """Checks if user is subscribed to a sub_key."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM subscriptions WHERE user_id = ? AND sub_key = ?",
            (user_id, sub_key)
        ) as cursor:
            row = await cursor.fetchone()
            return row is not None

async def subscribe_user(user_id: int, sub_key: str):
    """Subscribes user to a sub_key."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO subscriptions (user_id, sub_key) VALUES (?, ?)",
            (user_id, sub_key)
        )
        await db.commit()

async def unsubscribe_user(user_id: int, sub_key: str):
    """Unsubscribes user from a sub_key."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM subscriptions WHERE user_id = ? AND sub_key = ?",
            (user_id, sub_key)
        )
        await db.commit()

async def remove_user_completely(user_id: int):
    """Removes user and all their subscriptions when bot is blocked."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))
        await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        await db.commit()
    logger.info(f"Cleaned up blocked/deactivated user {user_id} from database.")

async def get_all_subscribers_for_key(sub_key: str) -> list:
    """Gets all user_ids subscribed to a sub_key."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id FROM subscriptions WHERE sub_key = ?",
            (sub_key,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [r[0] for r in rows]

async def get_subscribers_for_player(sub_key: str) -> list:
    """Alias for get_all_subscribers_for_key."""
    return await get_all_subscribers_for_key(sub_key)

async def get_total_users_count() -> int:
    """Returns total count of registered Telegram users."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def get_active_subscribers_count() -> int:
    """Returns count of users with at least 1 active subscription."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(DISTINCT user_id) FROM subscriptions") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def get_subscriptions_breakdown() -> dict:
    """Returns dict of count of subscribers for each key."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT sub_key, COUNT(user_id) FROM subscriptions GROUP BY sub_key") as cursor:
            rows = await cursor.fetchall()
            return {r[0]: r[1] for r in rows}

# PLAYER STATES DB FUNCTIONS (FOR MONITORING)
async def has_player_state(nickname: str) -> bool:
    """Checks if a player has a saved state in database."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM player_states WHERE nickname = ?", (nickname,)) as cursor:
            row = await cursor.fetchone()
            return row is not None

async def get_player_last_state(nickname: str) -> str:
    """Gets the last recorded state for a player (OFFLINE, LOBBY, SOLOLEVELING, OTHER_GAME)."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT state FROM player_states WHERE nickname = ?", (nickname,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else "OFFLINE"

async def set_player_state(nickname: str, state: str):
    """Sets or updates the recorded state for a player."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO player_states (nickname, state, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (nickname, state)
        )
        await db.commit()

async def update_player_last_state(nickname: str, state: str, is_online: bool = False):
    """Alias for set_player_state expected by monitor.py."""
    await set_player_state(nickname, state)

# DISCORD SETTINGS DB FUNCTIONS
async def get_discord_setting(key: str, default: int = 1) -> int:
    """Gets Discord setting value (1 for ON, 0 for OFF)."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM discord_settings WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row is not None else default

async def set_discord_setting(key: str, value: int):
    """Sets Discord setting value."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO discord_settings (key, value) VALUES (?, ?)",
            (key, value)
        )
        await db.commit()

async def get_all_discord_settings() -> dict:
    """Returns all Discord settings as dict."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT key, value FROM discord_settings") as cursor:
            rows = await cursor.fetchall()
            return {r[0]: r[1] for r in rows}

# DISCORD VERIFICATION DB FUNCTIONS
async def save_discord_verification(discord_user_id: int, vimeworld_nickname: str):
    """Saves linked VimeWorld nickname for Discord user ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO discord_verifications (discord_user_id, vimeworld_nickname) VALUES (?, ?)",
            (discord_user_id, vimeworld_nickname)
        )
        await db.commit()

async def get_discord_verification(discord_user_id: int) -> str:
    """Gets linked VimeWorld nickname for Discord user ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT vimeworld_nickname FROM discord_verifications WHERE discord_user_id = ?",
            (discord_user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def delete_discord_verification(discord_user_id: int):
    """Deletes linked VimeWorld verification for Discord user ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM discord_verifications WHERE discord_user_id = ?",
            (discord_user_id,)
        )
        await db.commit()

async def get_all_discord_verifications() -> list:
    """Returns all verified Discord user records as list of (discord_user_id, vimeworld_nickname)."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT discord_user_id, vimeworld_nickname FROM discord_verifications") as cursor:
            rows = await cursor.fetchall()
            return rows
