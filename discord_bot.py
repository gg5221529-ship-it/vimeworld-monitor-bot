import os
import asyncio
import logging
from config import DISCORD_BOT_TOKEN, DISCORD_ADMIN_IDS
import database as db
import checker
import dungeon_utils

logger = logging.getLogger(__name__)

# List of ignored/excluded Voice Channel IDs (AFK, Гостиная 2, etc.)
EXCLUDED_AFK_CHANNEL_IDS = [553187808630538240, 541663825892737034]

# Reference Role ID below which Rebirth Ranks will be placed
REFERENCE_ROLE_ID = 541667269634424862

# Discord client & command tree placeholder
discord_client = None
voice_client = None
tree = None

# Full VimeWorld Donator Ranks List (Highest to lowest hierarchy)
VIME_RANK_ROLES = [
    {"name": "🔱 Ultimate", "color_rgb": (255, 0, 128), "match": "ULTIMATE"},
    {"name": "👑 Imperial", "color_rgb": (255, 215, 0), "match": "IMPERIAL"},
    {"name": "💥 Absolute", "color_rgb": (255, 50, 50), "match": "ABSOLUTE"},
    {"name": "🌌 Celestial", "color_rgb": (180, 100, 255), "match": "CELESTIAL"},
    {"name": "🔮 Eternal", "color_rgb": (147, 112, 219), "match": "ETERNAL"},
    {"name": "⚔️ Elite", "color_rgb": (220, 20, 60), "match": "ELITE"},
    {"name": "🛡 Thane", "color_rgb": (70, 130, 180), "match": "THANE"},
    {"name": "✨ Divine", "color_rgb": (255, 223, 0), "match": "DIVINE"},
    {"name": "☠️ Immortal", "color_rgb": (178, 34, 34), "match": "IMMORTAL"},
    {"name": "🙏 Holy", "color_rgb": (255, 182, 193), "match": "HOLY"},
    {"name": "⚡ Premium", "color_rgb": (155, 89, 182), "match": "PREMIUM"},
    {"name": "⭐ VIP", "color_rgb": (46, 204, 113), "match": "VIP"},
    {"name": "👤 Игрок VimeWorld", "color_rgb": (149, 165, 166), "match": "USER"},
]

# Solo Leveling Rebirth Ranks List ("Герой SSS+" down to "Охотник F")
# Heroes are STRONGER than Hunters (Hero SSS+ -> Hero EEE -> Hunter SSS+ -> Hunter F)
REBIRTH_RANK_ROLES = [
    {"title": "Герой SSS+", "name": "⚔️ Герой SSS+", "color_rgb": (255, 0, 255)},
    {"title": "Герой SSS", "name": "⚔️ Герой SSS", "color_rgb": (255, 20, 147)},
    {"title": "Герой SS+", "name": "⚔️ Герой SS+", "color_rgb": (255, 69, 0)},
    {"title": "Герой SS", "name": "⚔️ Герой SS", "color_rgb": (255, 140, 0)},
    {"title": "Герой S+", "name": "⚔️ Герой S+", "color_rgb": (255, 215, 0)},
    {"title": "Герой S", "name": "⚔️ Герой S", "color_rgb": (255, 255, 0)},
    {"title": "Герой AAA+", "name": "⚔️ Герой AAA+", "color_rgb": (173, 255, 47)},
    {"title": "Герой AAA", "name": "⚔️ Герой AAA", "color_rgb": (0, 255, 0)},
    {"title": "Герой AA+", "name": "⚔️ Герой AA+", "color_rgb": (0, 255, 127)},
    {"title": "Герой AA", "name": "⚔️ Герой AA", "color_rgb": (0, 255, 255)},
    {"title": "Герой A+", "name": "⚔️ Герой A+", "color_rgb": (30, 144, 255)},
    {"title": "Герой A", "name": "⚔️ Герой A", "color_rgb": (0, 0, 255)},
    {"title": "Герой BBB+", "name": "⚔️ Герой BBB+", "color_rgb": (138, 43, 226)},
    {"title": "Герой BBB", "name": "⚔️ Герой BBB", "color_rgb": (147, 112, 219)},
    {"title": "Герой BB+", "name": "⚔️ Герой BB+", "color_rgb": (186, 85, 211)},
    {"title": "Герой BB", "name": "⚔️ Герой BB", "color_rgb": (218, 112, 214)},
    {"title": "Герой B+", "name": "⚔️ Герой B+", "color_rgb": (255, 20, 147)},
    {"title": "Герой B", "name": "⚔️ Герой B", "color_rgb": (255, 105, 180)},
    {"title": "Герой CCC+", "name": "⚔️ Герой CCC+", "color_rgb": (250, 128, 114)},
    {"title": "Герой CCC", "name": "⚔️ Герой CCC", "color_rgb": (233, 150, 122)},
    {"title": "Герой CC+", "name": "⚔️ Герой CC+", "color_rgb": (240, 128, 128)},
    {"title": "Герой CC", "name": "⚔️ Герой CC", "color_rgb": (205, 92, 92)},
    {"title": "Герой C+", "name": "⚔️ Герой C+", "color_rgb": (220, 20, 60)},
    {"title": "Герой C", "name": "⚔️ Герой C", "color_rgb": (178, 34, 34)},
    {"title": "Герой DDD+", "name": "⚔️ Герой DDD+", "color_rgb": (184, 134, 11)},
    {"title": "Герой DDD", "name": "⚔️ Герой DDD", "color_rgb": (218, 165, 32)},
    {"title": "Герой DD+", "name": "⚔️ Герой DD+", "color_rgb": (238, 232, 170)},
    {"title": "Герой DD", "name": "⚔️ Герой DD", "color_rgb": (189, 183, 107)},
    {"title": "Герой D+", "name": "⚔️ Герой D+", "color_rgb": (154, 205, 50)},
    {"title": "Герой D", "name": "⚔️ Герой D", "color_rgb": (85, 107, 47)},
    {"title": "Герой EEE", "name": "⚔️ Герой EEE", "color_rgb": (152, 251, 152)},
    {"title": "SSS+", "name": "⚔️ Охотник SSS+", "color_rgb": (255, 0, 0)},
    {"title": "SSS", "name": "⚔️ Охотник SSS", "color_rgb": (220, 20, 60)},
    {"title": "SS+", "name": "⚔️ Охотник SS+", "color_rgb": (255, 69, 0)},
    {"title": "SS", "name": "⚔️ Охотник SS", "color_rgb": (255, 140, 0)},
    {"title": "S+", "name": "⚔️ Охотник S+", "color_rgb": (255, 215, 0)},
    {"title": "S", "name": "⚔️ Охотник S", "color_rgb": (255, 255, 0)},
    {"title": "AAA+", "name": "⚔️ Охотник AAA+", "color_rgb": (173, 255, 47)},
    {"title": "AAA", "name": "⚔️ Охотник AAA", "color_rgb": (0, 255, 0)},
    {"title": "AA+", "name": "⚔️ Охотник AA+", "color_rgb": (0, 255, 127)},
    {"title": "AA", "name": "⚔️ Охотник AA", "color_rgb": (0, 255, 255)},
    {"title": "A+", "name": "⚔️ Охотник A+", "color_rgb": (30, 144, 255)},
    {"title": "A", "name": "⚔️ Охотник A", "color_rgb": (0, 0, 255)},
    {"title": "BBB+", "name": "⚔️ Охотник BBB+", "color_rgb": (138, 43, 226)},
    {"title": "BBB", "name": "⚔️ Охотник BBB", "color_rgb": (147, 112, 219)},
    {"title": "BB+", "name": "⚔️ Охотник BB+", "color_rgb": (186, 85, 211)},
    {"title": "BB", "name": "⚔️ Охотник BB", "color_rgb": (218, 112, 214)},
    {"title": "B+", "name": "⚔️ Охотник B+", "color_rgb": (255, 20, 147)},
    {"title": "B", "name": "⚔️ Охотник B", "color_rgb": (255, 105, 180)},
    {"title": "CCC+", "name": "⚔️ Охотник CCC+", "color_rgb": (250, 128, 114)},
    {"title": "CCC", "name": "⚔️ Охотник CCC", "color_rgb": (233, 150, 122)},
    {"title": "CC+", "name": "⚔️ Охотник CC+", "color_rgb": (240, 128, 128)},
    {"title": "CC", "name": "⚔️ Охотник CC", "color_rgb": (205, 92, 92)},
    {"title": "C+", "name": "⚔️ Охотник C+", "color_rgb": (220, 20, 60)},
    {"title": "C", "name": "⚔️ Охотник C", "color_rgb": (178, 34, 34)},
    {"title": "DDD+", "name": "⚔️ Охотник DDD+", "color_rgb": (184, 134, 11)},
    {"title": "DDD", "name": "⚔️ Охотник DDD", "color_rgb": (218, 165, 32)},
    {"title": "DD+", "name": "⚔️ Охотник DD+", "color_rgb": (238, 232, 170)},
    {"title": "DD", "name": "⚔️ Охотник DD", "color_rgb": (189, 183, 107)},
    {"title": "D+", "name": "⚔️ Охотник D+", "color_rgb": (154, 205, 50)},
    {"title": "D", "name": "⚔️ Охотник D", "color_rgb": (85, 107, 47)},
    {"title": "EEE+", "name": "⚔️ Охотник EEE+", "color_rgb": (144, 238, 144)},
    {"title": "EEE", "name": "⚔️ Охотник EEE", "color_rgb": (152, 251, 152)},
    {"title": "EE+", "name": "⚔️ Охотник EE+", "color_rgb": (175, 238, 238)},
    {"title": "EE", "name": "⚔️ Охотник EE", "color_rgb": (0, 206, 209)},
    {"title": "E+", "name": "⚔️ Охотник E+", "color_rgb": (70, 130, 180)},
    {"title": "E", "name": "⚔️ Охотник E", "color_rgb": (100, 149, 237)},
    {"title": "FFF+", "name": "⚔️ Охотник FFF+", "color_rgb": (176, 196, 222)},
    {"title": "FFF", "name": "⚔️ Охотник FFF", "color_rgb": (119, 136, 153)},
    {"title": "FF+", "name": "⚔️ Охотник FF+", "color_rgb": (112, 128, 144)},
    {"title": "FF", "name": "⚔️ Охотник FF", "color_rgb": (105, 105, 105)},
    {"title": "F+", "name": "⚔️ Охотник F+", "color_rgb": (128, 128, 128)},
    {"title": "F", "name": "⚔️ Охотник F", "color_rgb": (169, 169, 169)},
]

# Title to numeric rank value mapping for strict anti-demotion protection
REBIRTH_TITLE_TO_VAL = {
    "Герой SSS+": 72, "Герой SSS": 71, "Герой SS+": 70, "Герой SS": 69,
    "Герой S+": 68, "Герой S": 67, "Герой AAA+": 66, "Герой AAA": 65,
    "Герой AA+": 64, "Герой AA": 63, "Герой A+": 62, "Герой A": 61,
    "Герой BBB+": 60, "Герой BBB": 59, "Герой BB+": 58, "Герой BB": 57,
    "Герой B+": 56, "Герой B": 55, "Герой CCC+": 54, "Герой CCC": 53,
    "Герой CC+": 52, "Герой CC": 51, "Герой C+": 50, "Герой C": 49,
    "Герой DDD+": 48, "Герой DDD": 47, "Герой DD+": 46, "Герой DD": 45,
    "Герой D+": 44, "Герой D": 43, "Герой EEE": 42,
    "SSS+": 41, "SSS": 40, "SS+": 39, "SS": 38, "S+": 37, "S": 36,
    "AAA+": 35, "AAA": 34, "AA+": 33, "AA": 32, "A+": 31, "A": 30,
    "BBB+": 29, "BBB": 28, "BB+": 27, "BB": 26, "B+": 25, "B": 24,
    "CCC+": 23, "CCC": 22, "CC+": 21, "CC": 20, "C+": 19, "C": 18,
    "DDD+": 17, "DDD": 16, "DD+": 15, "DD": 14, "D+": 13, "D": 12,
    "EEE+": 11, "EEE": 10, "EE+": 9, "EE": 8, "E+": 7, "E": 6,
    "FFF+": 5, "FFF": 4, "FF+": 3, "FF": 2, "F+": 1, "F": 0
}

ALL_MANAGED_ROLE_NAMES = [r["name"] for r in VIME_RANK_ROLES] + [r["name"] for r in REBIRTH_RANK_ROLES]

try:
    import discord
    from discord import app_commands
    from discord.ext import commands
    
    # Use standard non-privileged intents for voice channels and guilds
    intents = discord.Intents.default()
    intents.voice_states = True
    intents.guilds = True
    intents.messages = True
    intents.message_content = True
    intents.members = True
    
    discord_client = commands.Bot(command_prefix=["!", "/"], intents=intents)
    tree = discord_client.tree

    @discord_client.event
    async def on_ready():
        logger.info(f"Discord Bot connected as {discord_client.user} (ID: {discord_client.user.id})")
        # Sync slash commands globally & instantly to all connected guilds
        try:
            synced_global = await tree.sync()
            logger.info(f"Synced {len(synced_global)} global Discord slash commands.")
            
            for guild in discord_client.guilds:
                try:
                    tree.copy_global_to(guild=guild)
                    await tree.sync(guild=guild)
                    logger.info(f"Instantly synced slash commands to guild: {guild.name} ({guild.id})")
                    # Setup monolithic role hierarchy on startup
                    asyncio.create_task(setup_guild_role_hierarchy(guild))
                except Exception as ge:
                    logger.warning(f"Failed to sync guild {guild.name}: {ge}")
        except Exception as e:
            logger.error(f"Error syncing Discord slash commands: {e}")

        # Launch fast auto role synchronization loop
        asyncio.create_task(auto_role_sync_task())

    @discord_client.event
    async def on_message(message: discord.Message):
        if message.author.bot:
            return
            
        content = message.content.strip()
        lower_content = content.lower()
        
        # 1. Admin Panel text command (Restricted to Admin ID)
        if lower_content in ("/admin", "!admin", "admin"):
            if message.author.id not in DISCORD_ADMIN_IDS:
                await message.channel.send("⛔ **У вас нет доступа к этой админ-панели.**", delete_after=5)
                return
                
            try:
                await message.delete()
            except Exception:
                pass
                
            settings = await db.get_all_discord_settings()
            embed = generate_admin_embed(settings)
            view = DiscordAdminView(admin_id=message.author.id, settings=settings)
            await message.channel.send(embed=embed, view=view)
            return

        # 2. Unverify admin text command (!unverify @User or /unverify @User)
        if lower_content.startswith("!unverify") or lower_content.startswith("/unverify") or lower_content.startswith("unverify "):
            if message.author.id not in DISCORD_ADMIN_IDS:
                await message.channel.send("⛔ **Эта команда доступна только администратору.**", delete_after=5)
                return
                
            target_member = None
            if message.mentions:
                target_member = message.mentions[0]
            else:
                parts = content.split()
                if len(parts) > 1 and parts[1].isdigit():
                    user_id = int(parts[1])
                    try:
                        target_member = message.guild.get_member(user_id) or await message.guild.fetch_member(user_id)
                    except Exception:
                        target_member = None
                    
            if not target_member:
                await message.channel.send("❌ **Укажите участника (упоминание или ID)!** Пример: `!unverify @User`")
                return

            embed_out = await process_user_unverify(message.guild, target_member)
            await message.channel.send(embed=embed_out)
            return

        # 3. Verify text command (!verify nick or /verify nick or verify nick)
        if lower_content.startswith("!verify") or lower_content.startswith("/verify") or lower_content.startswith("verify "):
            parts = content.split(maxsplit=1)
            if len(parts) > 1:
                nick = parts[1].strip()
                embed_out = await process_user_verification(message.guild, message.author, nick)
                await message.channel.send(embed=embed_out)
            else:
                await message.channel.send("🔗 **Укажите ваш никнейм VimeWorld!** Пример: `!verify dima_286812312`")
            return

        # 4. Sync text command (!sync or /sync or sync)
        if lower_content in ("!sync", "/sync", "sync"):
            embed_out = await process_user_sync(message.guild, message.author)
            await message.channel.send(embed=embed_out)
            return

        # 5. Player Profile text command - OPEN TO ALL USERS (!player nick or /player nick or player nick)
        if lower_content.startswith("!player") or lower_content.startswith("/player") or lower_content.startswith("!profile") or lower_content.startswith("/profile") or lower_content.startswith("player ") or lower_content.startswith("профиль "):
            parts = content.split(maxsplit=1)
            if len(parts) > 1:
                nick = parts[1].strip()
                profile = await checker.fetch_full_player_profile(nick)
                if not profile.get("exists"):
                    await message.channel.send(f"❌ Игрок `{nick}` не найден на VimeWorld!")
                    return
                embed = build_player_embed(profile)
                await message.channel.send(embed=embed)
            else:
                await message.channel.send("🔍 **Укажите никнейм игрока!** Пример: `!player dima_286812312`")
            return

        # 6. Player Comparison text command - OPEN TO ALL USERS (!compare nick1 nick2 or /compare nick1 nick2)
        if lower_content.startswith("!compare") or lower_content.startswith("/compare") or lower_content.startswith("!сравнить") or lower_content.startswith("/сравнить") or lower_content.startswith("сравнить "):
            parts = content.split()
            if len(parts) >= 3:
                nick1, nick2 = parts[1].strip(), parts[2].strip()
                p1_task = checker.fetch_full_player_profile(nick1)
                p2_task = checker.fetch_full_player_profile(nick2)
                p1, p2 = await asyncio.gather(p1_task, p2_task)

                if not p1.get("exists"):
                    await message.channel.send(f"❌ Игрок `{nick1}` не найден на VimeWorld!")
                    return
                if not p2.get("exists"):
                    await message.channel.send(f"❌ Игрок `{nick2}` не найден на VimeWorld!")
                    return

                embed = build_compare_embed(p1, p2)
                await message.channel.send(embed=embed)
            else:
                await message.channel.send("⚔️ **Укажите 2 никнейма для сравнения!** Пример: `!compare dima_286812312 MrLalalashkaXXL`")
            return

except ImportError:
    logger.warning("discord.py is not installed. Discord voice notifications will be disabled.")
    discord_client = None


def is_discord_ready() -> bool:
    """Checks if Discord bot is initialized and logged in."""
    return bool(discord_client and discord_client.is_ready())


async def setup_guild_role_hierarchy(guild: discord.Guild):
    """
    Reorders ALL managed roles into a strict continuous hierarchy under the Bot's top role:
    1. Rebirth Block (TOP of managed roles): Герой SSS+ (highest) down to Герой EEE, then Охотник SSS+ down to Охотник F.
    2. Reference Role 541667269634424862 (if present).
    3. Donator Block (BOTTOM of managed roles): Ultimate down to User.
    """
    bot_member = guild.get_member(discord_client.user.id)
    if not bot_member:
        return

    bot_top_pos = bot_member.top_role.position

    # 1. Ensure all managed roles exist
    donator_roles = []
    for cfg in VIME_RANK_ROLES: # Ultimate down to User
        role = await ensure_role_exists(guild, cfg)
        if role:
            donator_roles.append(role)

    rebirth_roles = []
    for cfg in REBIRTH_RANK_ROLES: # Герой SSS+ down to Охотник F
        role = await ensure_role_exists(guild, cfg)
        if role:
            rebirth_roles.append(role)

    ref_role = guild.get_role(REFERENCE_ROLE_ID)

    # List of managed roles from TOP to BOTTOM:
    # Top -> Rebirth Ranks (Герой SSS+ -> ... -> Герой EEE -> Охотник SSS+ -> ... -> Охотник F)
    # Middle -> Reference role (if present)
    # Bottom -> Donator Ranks (Ultimate -> ... -> User)
    
    top_to_bottom = []
    top_to_bottom.extend(rebirth_roles)
    if ref_role and ref_role not in top_to_bottom:
        top_to_bottom.append(ref_role)
    top_to_bottom.extend(donator_roles)

    # Position assignment: highest position right below bot_top_pos
    max_pos = max(1, bot_top_pos - 1)
    
    positions = {}
    current_pos = max_pos
    
    for role in top_to_bottom: # From TOP role to BOTTOM role
        if current_pos > 0 and role.position < bot_top_pos:
            positions[role] = current_pos
            current_pos -= 1

    try:
        if positions:
            await guild.edit_role_positions(positions=positions)
            logger.info(
                f"Successfully aligned role hierarchy positions for guild '{guild.name}' "
                f"(Heroes at TOP -> Hunters -> Reference Role -> Donators at bottom, under Bot pos {bot_top_pos})"
            )
    except Exception as e:
        logger.warning(f"Could not edit role positions for guild '{guild.name}': {e}")


async def auto_role_sync_task():
    """Background task that re-syncs all verified Discord users every 3 seconds cleanly."""
    logger.info("Starting Discord Auto-Role Sync Loop...")
    while True:
        try:
            await asyncio.sleep(3) # 3 seconds safe interval
            if not is_discord_ready():
                continue
                
            verifications = await db.get_all_discord_verifications()
            if not verifications:
                continue

            for discord_user_id, nick in verifications:
                try:
                    profile = await checker.fetch_full_player_profile(nick)
                    if not profile.get("exists"):
                        continue

                    for guild in discord_client.guilds:
                        member = guild.get_member(discord_user_id)
                        if not member:
                            try:
                                member = await guild.fetch_member(discord_user_id)
                            except Exception:
                                member = None
                        if member:
                            await sync_user_roles(guild, member, profile)
                except Exception as ue:
                    logger.warning(f"Error auto-syncing user {discord_user_id} ({nick}): {ue}")
        except asyncio.CancelledError:
            logger.info("Auto-role sync loop cancelled.")
            break
        except Exception as e:
            logger.error(f"Error in auto_role_sync_task: {e}")


async def ensure_role_exists(guild: discord.Guild, role_cfg: dict) -> discord.Role:
    """Creates role on guild if it doesn't exist, ensuring hoist=True."""
    role_name = role_cfg["name"]
    role = discord.utils.get(guild.roles, name=role_name)
    if not role:
        try:
            r, g, b = role_cfg["color_rgb"]
            role = await guild.create_role(
                name=role_name,
                color=discord.Color.from_rgb(r, g, b),
                hoist=True,
                mentionable=False,
                reason="VimeWorld Auto-Role System"
            )
            logger.info(f"Created Discord role '{role_name}' on server {guild.name}")
        except Exception as e:
            logger.warning(f"Could not create role '{role_name}' on guild {guild.name}: {e}")
    else:
        # Ensure hoist is enabled for sidebar grouping
        if not role.hoist:
            try:
                await role.edit(hoist=True)
            except Exception:
                pass
    return role


async def sync_user_roles(guild: discord.Guild, member: discord.Member, profile: dict) -> list[str]:
    """
    Assigns ONLY 2 roles with STRICT ANTI-DEMOTION PROTECTION:
    1. VimeWorld Rank Role (e.g. Imperial, Ultimate, Divine)
    2. Rebirth Rank Role based on Solo Leveling Rebirths (e.g. Охотник SSS, Герой EEE, Герой D)
    And assigns the user's exact VimeWorld nickname as their server nickname in Discord!
    """
    if not guild or not member:
        return []
        
    vime_nickname = profile.get("nickname")
    
    # 1. Automatic VimeWorld Nickname assignment
    if vime_nickname and member.id != guild.owner_id:
        if member.nick != vime_nickname and member.display_name != vime_nickname:
            try:
                await member.edit(nick=vime_nickname, reason="VimeWorld Auto Nickname Sync")
                logger.info(f"Updated server nickname for {member.name} -> '{vime_nickname}'")
            except discord.Forbidden:
                logger.warning(
                    f"❌ Cannot change nickname for {member.display_name}: Bot lacks 'Manage Nicknames' permission "
                    f"or member role is higher than bot."
                )
            except Exception as ne:
                logger.warning(f"Error updating nickname for {member.display_name}: {ne}")

    user_rank = (profile.get("rank") or "USER").upper()
    fetched_rebirth_title = profile.get("sl_rebirth_rank", "F")
    sl_stats_loaded = profile.get("sl_stats_loaded", False)
    
    # 2. Determine target VimeWorld Rank Role
    target_rank_cfg = None
    for cfg in VIME_RANK_ROLES:
        if cfg["match"] == user_rank:
            target_rank_cfg = cfg
            break
    if not target_rank_cfg:
        target_rank_cfg = [c for c in VIME_RANK_ROLES if c["match"] == "USER"][0]

    # 3. STRICT ANTI-DEMOTION PROTECTION FOR REBIRTH RANK
    existing_max_val = -1
    existing_reb_cfg = None

    for r in member.roles:
        for cfg in REBIRTH_RANK_ROLES:
            if r.name == cfg["name"]:
                val = REBIRTH_TITLE_TO_VAL.get(cfg["title"], 0)
                if val > existing_max_val:
                    existing_max_val = val
                    existing_reb_cfg = cfg

    fetched_val = REBIRTH_TITLE_TO_VAL.get(fetched_rebirth_title, 0)

    target_reb_cfg = None
    if sl_stats_loaded:
        # Pick the HIGHER rank between existing rank and newly fetched rank!
        if existing_max_val > fetched_val:
            target_reb_cfg = existing_reb_cfg
        else:
            for cfg in REBIRTH_RANK_ROLES:
                if cfg["title"] == fetched_rebirth_title:
                    target_reb_cfg = cfg
                    break
            if not target_reb_cfg:
                target_reb_cfg = [c for c in REBIRTH_RANK_ROLES if c["title"] == "F"][0]
    else:
        # If stats weren't loaded, keep existing rank
        target_reb_cfg = existing_reb_cfg or [c for c in REBIRTH_RANK_ROLES if c["title"] == "F"][0]

    assigned_role_names = []
    roles_to_add = []
    
    # Donator rank role
    if target_rank_cfg:
        r_donator = await ensure_role_exists(guild, target_rank_cfg)
        if r_donator:
            roles_to_add.append(r_donator)
            assigned_role_names.append(r_donator.name)
            
    # Rebirth rank role (protected from demotion)
    if target_reb_cfg:
        r_rebirth = await ensure_role_exists(guild, target_reb_cfg)
        if r_rebirth:
            roles_to_add.append(r_rebirth)
            assigned_role_names.append(r_rebirth.name)

    # Managed role names list
    donator_role_names = [r["name"] for r in VIME_RANK_ROLES]
    rebirth_role_names = [r["name"] for r in REBIRTH_RANK_ROLES]
    managed_to_check = donator_role_names + rebirth_role_names

    # Build final role list atomically
    current_roles = list(member.roles)
    new_roles = [
        r for r in current_roles 
        if not (r.name in managed_to_check or "Level" in r.name or "Rank " in r.name) or r in roles_to_add
    ]
    for r in roles_to_add:
        if r not in new_roles:
            new_roles.append(r)

    roles_changed = set(new_roles) != set(current_roles)

    if roles_changed:
        try:
            await member.edit(roles=new_roles, reason="VimeWorld Auto-Role Sync")
            logger.info(f"Updated roles for {member.display_name}: {[r.name for r in roles_to_add]}")
        except discord.Forbidden:
            logger.error(
                f"❌ FORBIDDEN: Bot lacks permission or bot role is too low in hierarchy to manage roles for {member.display_name}! "
                f"Make sure the Bot role is dragged ABOVE '{assigned_role_names}' in Discord Server Settings -> Roles."
            )
        except Exception as e:
            logger.warning(f"Error syncing roles for member {member.display_name}: {e}")

    return assigned_role_names


async def process_user_verification(guild: discord.Guild, member: discord.Member, nickname: str) -> discord.Embed:
    """Verifies VimeWorld nickname and updates Discord roles, returning rich Embed."""
    profile = await checker.fetch_full_player_profile(nickname)
    if not profile.get("exists"):
        embed_err = discord.Embed(
            title="❌ Ошибка верификации",
            description=f"Игрок `{nickname}` не найден на VimeWorld!",
            color=0x992D22
        )
        return embed_err

    await db.save_discord_verification(member.id, profile["nickname"])
    assigned_roles = await sync_user_roles(guild, member, profile)
    
    roles_str = ", ".join([f"`{r}`" for r in assigned_roles]) if assigned_roles else "нет"
    
    embed = discord.Embed(
        title="✅ Успешная верификация VimeWorld",
        color=0x2ECC71
    )
    embed.set_thumbnail(url=profile['head_url'])
    embed.add_field(name="👤 Аккаунт Discord", value=f"{member.mention}", inline=True)
    embed.add_field(name="🎮 Никнейм VimeWorld", value=f"`{profile['nickname']}`", inline=True)
    embed.add_field(name="📊 Уровень VimeWorld", value=f"`{profile['level']}` ур. ({profile['level_pct']}%)", inline=True)
    embed.add_field(name="🔄 Перерождения", value=f"`{profile['sl_rebirth']}`", inline=True)
    embed.add_field(name="⚔️ Ранг Охотника", value=f"`{profile['sl_rebirth_rank']}`", inline=True)
    embed.add_field(name="⚡ Сила удара", value=f"`{profile['sl_damage_formatted']}`", inline=True)
    embed.add_field(name="🎖 Выданные роли", value=roles_str, inline=False)
    embed.set_footer(text="VimeWorld Solo Leveling Integration")
    return embed


async def process_user_sync(guild: discord.Guild, member: discord.Member) -> discord.Embed:
    """Syncs roles for an already verified Discord user, returning rich Embed."""
    linked_nick = await db.get_discord_verification(member.id)
    if not linked_nick:
        embed_err = discord.Embed(
            title="⚠️ Верификация не найдена",
            description="Вы ещё не привязали никнейм VimeWorld!\nИспользуйте команду: `/verify ваш_ник`",
            color=0xF1C40F
        )
        return embed_err

    profile = await checker.fetch_full_player_profile(linked_nick)
    if not profile.get("exists"):
        embed_err = discord.Embed(
            title="❌ Ошибка синхронизации",
            description=f"Никнейм `{linked_nick}` не найден на VimeWorld!",
            color=0x992D22
        )
        return embed_err

    assigned_roles = await sync_user_roles(guild, member, profile)
    roles_str = ", ".join([f"`{r}`" for r in assigned_roles]) if assigned_roles else "нет"

    embed = discord.Embed(
        title="🔄 Синхронизация ролей VimeWorld",
        color=0x3498DB
    )
    embed.set_thumbnail(url=profile['head_url'])
    embed.add_field(name="👤 Участник", value=f"{member.mention}", inline=True)
    embed.add_field(name="🎮 Никнейм VimeWorld", value=f"`{profile['nickname']}`", inline=True)
    embed.add_field(name="🔄 Перерождения", value=f"`{profile['sl_rebirth']}` (Ранг: `{profile['sl_rebirth_rank']}`)", inline=True)
    embed.add_field(name="⚡ Сила удара", value=f"`{profile['sl_damage_formatted']}`", inline=True)
    embed.add_field(name="🎖 Обновлённые роли", value=roles_str, inline=False)
    embed.set_footer(text="VimeWorld Solo Leveling Integration")
    return embed


async def process_user_unverify(guild: discord.Guild, target_member: discord.Member) -> discord.Embed:
    """Removes VimeWorld verification and strips all bot-assigned roles, returning rich Embed."""
    if not target_member:
        embed_err = discord.Embed(
            title="❌ Ошибка",
            description="Участник не найден на сервере!",
            color=0x992D22
        )
        return embed_err

    # 1. Delete from database
    await db.delete_discord_verification(target_member.id)

    # 2. Find and strip all VimeWorld managed roles
    roles_to_remove = [r for r in target_member.roles if (r.name in ALL_MANAGED_ROLE_NAMES or "Level" in r.name or "Rank " in r.name or "Охотник " in r.name or "Герой " in r.name)]
    removed_role_names = [r.name for r in roles_to_remove]

    try:
        current_roles = list(target_member.roles)
        new_roles = [r for r in current_roles if r not in roles_to_remove]
        if set(new_roles) != set(current_roles):
            await target_member.edit(roles=new_roles, reason="VimeWorld Unverify Admin Command")
        
        # Reset server nickname if possible
        try:
            if target_member.id != guild.owner_id and target_member.nick:
                await target_member.edit(nick=None)
        except Exception:
            pass
    except Exception as e:
        logger.warning(f"Error removing roles during unverify for {target_member.display_name}: {e}")

    roles_str = ", ".join([f"`{r}`" for r in removed_role_names]) if removed_role_names else "нет"

    embed = discord.Embed(
        title="🗑 Отмена верификации VimeWorld",
        color=0xE74C3C
    )
    embed.add_field(name="👤 Участник", value=f"{target_member.mention} (`{target_member.id}`)", inline=True)
    embed.add_field(name="❌ Удаленные роли", value=roles_str, inline=False)
    embed.set_footer(text="Панель Администратора")
    return embed


async def find_active_human_voice_channel():
    """
    Finds an active voice channel across all connected Discord servers (guilds)
    that has at least 1 non-bot human member inside, SKIPPING AFK channels.
    """
    if not is_discord_ready():
        return None
        
    for guild in discord_client.guilds:
        # Get native AFK channel ID if set for guild
        guild_afk_id = guild.afk_channel.id if guild.afk_channel else None
        
        for vc in guild.voice_channels:
            # Skip explicit AFK channel ID, guild AFK channel, or channels named "afk"
            if vc.id in EXCLUDED_AFK_CHANNEL_IDS or vc.id == guild_afk_id:
                continue
            if "afk" in vc.name.lower() or "афк" in vc.name.lower():
                continue
                
            human_members = [m for m in vc.members if not m.bot]
            if len(human_members) > 0:
                return vc

    return None


async def get_discord_debug_info() -> str:
    """Returns human-readable status of Discord bot connection."""
    if not DISCORD_BOT_TOKEN:
        return "❌ <b>Токен DISCORD_BOT_TOKEN не указан</b> в переменных окружения."
        
    if not is_discord_ready():
        return "⏳ <b>Discord-бот в процессе подключения...</b> Попробуйте через 5 секунд."
        
    guilds = discord_client.guilds
    if not guilds:
        return (
            "⚠️ <b>Бот подключен к Discord, но НЕ добавлен ни на один сервер!</b>\n\n"
            "Добавьте бота на ваш Discord-сервер по ссылке авторизации."
        )
        
    text = f"✅ <b>Discord-бот активен:</b> <code>{discord_client.user}</code>\n"
    text += f"🏠 <b>Серверы ({len(guilds)}):</b> " + ", ".join([g.name for g in guilds]) + "\n\n"
    
    active_vc = await find_active_human_voice_channel()
    if active_vc:
        humans = [m.display_name for m in active_vc.members if not m.bot]
        text += f"🔊 <b>Найден активный войс:</b> {active_vc.name} (Людей: {len(humans)} - {', '.join(humans)})\n"
    else:
        text += "🔇 <b>Никого нет в активных голосовых каналах (AFK каналы игнорируются).</b> Зайдите в любой активный войс для теста!\n"
        
    return text


def build_player_embed(profile: dict) -> discord.Embed:
    """Helper to build Discord Embed for player profile."""
    embed = discord.Embed(
        title=f"👤 Профиль игрока {profile['nickname']}",
        url=profile['url'],
        color=0x00FF33 if profile['is_online'] else 0x888888
    )
    embed.set_thumbnail(url=profile['head_url'])
    embed.add_field(name="Текущий статус", value=profile['status_display'], inline=True)
    embed.add_field(name="Ранг", value=profile.get('rank', 'USER'), inline=True)
    embed.add_field(name="Уровень", value=f"{profile['level']} ({profile['level_pct']}%)", inline=True)
    embed.add_field(name="Наиграно времени", value=f"{profile['played_hours']} ч", inline=True)
    if profile.get('guild_name'):
        embed.add_field(name="Гильдия", value=f"{profile['guild_name']} (Ув. {profile['guild_level']})", inline=True)

    embed.add_field(
        name="🗡 Solo Leveling Статистика",
        value=(
            f"🔄 **Перерождений:** `{profile['sl_rebirth']}` (Ранг: `{profile['sl_rebirth_rank']}`)\n"
            f"⚡ **Сила удара:** `{profile['sl_damage_formatted']}`\n"
            f"💰 **Золото:** `{profile['sl_gold_formatted']}`\n"
            f"🎯 **Очки улучшений:** `{profile['sl_upgrade_points']}`"
        ),
        inline=False
    )
    return embed


def build_compare_embed(p1: dict, p2: dict) -> discord.Embed:
    """Helper to build Discord Embed for comparing two players."""
    nick1, nick2 = p1["nickname"], p2["nickname"]
    dmg1, dmg2 = p1["sl_damage_raw"], p2["sl_damage_raw"]
    reb1, reb2 = p1["sl_rebirth"], p2["sl_rebirth"]
    lvl1, lvl2 = p1.get("level", 0), p2.get("level", 0)

    icon_dmg1 = " 🏆" if dmg1 > dmg2 else (" 🤝" if dmg1 == dmg2 else "")
    icon_dmg2 = " 🏆" if dmg2 > dmg1 else (" 🤝" if dmg1 == dmg2 else "")

    icon_reb1 = " 🏆" if reb1 > reb2 else (" 🤝" if reb1 == reb2 else "")
    icon_reb2 = " 🏆" if reb2 > reb1 else (" 🤝" if reb1 == reb2 else "")

    icon_lvl1 = " 🏆" if lvl1 > lvl2 else (" 🤝" if lvl1 == lvl2 else "")
    icon_lvl2 = " 🏆" if lvl2 > lvl1 else (" 🤝" if lvl1 == lvl2 else "")

    winner = nick1 if dmg1 > dmg2 else (nick2 if dmg2 > dmg1 else "Ничья")

    embed = discord.Embed(
        title=f"⚔️ Сравнение: {nick1} vs {nick2}",
        color=0x5865F2
    )
    embed.add_field(
        name="⚡ Сила удара",
        value=f"• **{nick1}:** `{p1['sl_damage_formatted']}`{icon_dmg1}\n• **{nick2}:** `{p2['sl_damage_formatted']}`{icon_dmg2}",
        inline=False
    )
    embed.add_field(
        name="🔄 Перерождения",
        value=f"• **{nick1}:** `{p1['sl_rebirth']}` (Ранг: `{p1['sl_rebirth_rank']}`){icon_reb1}\n• **{nick2}:** `{p2['sl_rebirth']}` (Ранг: `{p2['sl_rebirth_rank']}`){icon_reb2}",
        inline=False
    )
    embed.add_field(
        name="📊 Уровень VimeWorld",
        value=f"• **{nick1}:** `{p1['level']} ур.`{icon_lvl1}\n• **{nick2}:** `{p2['level']} ур.`{icon_lvl2}",
        inline=False
    )
    embed.add_field(
        name="🏆 Лидер по силе удара",
        value=f"**{winner}**",
        inline=False
    )
    return embed


# --- DISCORD UI ADMIN PANEL VIEW ---

class DiscordAdminView(discord.ui.View):
    def __init__(self, admin_id: int, settings: dict):
        super().__init__(timeout=300)
        self.admin_id = admin_id
        self.settings = settings
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        
        # 1. Hard Dungeon
        hard_on = self.settings.get("sound_dungeon_hard", 1)
        btn_hard = discord.ui.Button(
            label=f"🗡 Сложное: {'🟢 ВКЛ' if hard_on else '🔴 ВЫКЛ'}",
            style=discord.ButtonStyle.success if hard_on else discord.ButtonStyle.danger,
            custom_id="toggle_sound_dungeon_hard"
        )
        btn_hard.callback = self.make_toggle_callback("sound_dungeon_hard")
        self.add_item(btn_hard)

        # 2. Medium Dungeon
        med_on = self.settings.get("sound_dungeon_medium", 1)
        btn_med = discord.ui.Button(
            label=f"⚔️ Среднее: {'🟢 ВКЛ' if med_on else '🔴 ВЫКЛ'}",
            style=discord.ButtonStyle.success if med_on else discord.ButtonStyle.danger,
            custom_id="toggle_sound_dungeon_medium"
        )
        btn_med.callback = self.make_toggle_callback("sound_dungeon_medium")
        self.add_item(btn_med)

        # 3. Jeju Raid
        jeju_on = self.settings.get("sound_dungeon_jeju", 1)
        btn_jeju = discord.ui.Button(
            label=f"🌋 Чеджу: {'🟢 ВКЛ' if jeju_on else '🔴 ВЫКЛ'}",
            style=discord.ButtonStyle.success if jeju_on else discord.ButtonStyle.danger,
            custom_id="toggle_sound_dungeon_jeju"
        )
        btn_jeju.callback = self.make_toggle_callback("sound_dungeon_jeju")
        self.add_item(btn_jeju)

        # 4. Dark Auction
        auc_on = self.settings.get("sound_dark_auction", 1)
        btn_auc = discord.ui.Button(
            label=f"🏛 Аукцион: {'🟢 ВКЛ' if auc_on else '🔴 ВЫКЛ'}",
            style=discord.ButtonStyle.success if auc_on else discord.ButtonStyle.danger,
            custom_id="toggle_sound_dark_auction"
        )
        btn_auc.callback = self.make_toggle_callback("sound_dark_auction")
        self.add_item(btn_auc)

        # 5. Clan Raid Voice
        clan_on = self.settings.get("sound_clan_raid", 1)
        btn_clan = discord.ui.Button(
            label=f"🏰 Клан Рейд: {'🟢 ВКЛ' if clan_on else '🔴 ВЫКЛ'}",
            style=discord.ButtonStyle.success if clan_on else discord.ButtonStyle.danger,
            custom_id="toggle_sound_clan_raid"
        )
        btn_clan.callback = self.make_toggle_callback("sound_clan_raid")
        self.add_item(btn_clan)

        # 6. Clan Restart Mode (Reset at 03:00 vs Continuous)
        restart_mode = self.settings.get("clan_restart_mode", 1)
        btn_restart = discord.ui.Button(
            label=f"🔄 Рестарт (03:00): {'🟢 СБРОС' if restart_mode else '🔴 НЕПРЕРЫВНО'}",
            style=discord.ButtonStyle.primary if restart_mode else discord.ButtonStyle.secondary,
            custom_id="toggle_clan_restart_mode"
        )
        btn_restart.callback = self.make_toggle_callback("clan_restart_mode")
        self.add_item(btn_restart)

        # 7. Lololoshka
        lol_on = self.settings.get("sound_MrLalalashkaXXL", 1)
        btn_lol = discord.ui.Button(
            label=f"🎬 Лололошка: {'🟢 ВКЛ' if lol_on else '🔴 ВЫКЛ'}",
            style=discord.ButtonStyle.success if lol_on else discord.ButtonStyle.danger,
            custom_id="toggle_sound_MrLalalashkaXXL"
        )
        btn_lol.callback = self.make_toggle_callback("sound_MrLalalashkaXXL")
        self.add_item(btn_lol)

        # 8. FixPlay
        fix_on = self.settings.get("sound_F1xPlay_", 1)
        btn_fix = discord.ui.Button(
            label=f"🎮 Фиксплей: {'🟢 ВКЛ' if fix_on else '🔴 ВЫКЛ'}",
            style=discord.ButtonStyle.success if fix_on else discord.ButtonStyle.danger,
            custom_id="toggle_sound_F1xPlay_"
        )
        btn_fix.callback = self.make_toggle_callback("sound_F1xPlay_")
        self.add_item(btn_fix)

    def make_toggle_callback(self, key: str):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.admin_id:
                await interaction.response.send_message("⛔ У вас нет доступа к этой панели управления.", ephemeral=True)
                return
                
            current_val = self.settings.get(key, 1)
            new_val = 0 if current_val else 1
            await db.set_discord_setting(key, new_val)
            self.settings[key] = new_val
            
            self.update_buttons()
            embed = generate_admin_embed(self.settings)
            await interaction.response.edit_message(embed=embed, view=self)
            
        return callback


def generate_admin_embed(settings: dict) -> discord.Embed:
    embed = discord.Embed(
        title="👑 Панель Управления Голосовыми Анонсами Discord",
        description="Здесь вы можете включать или выключать отдельные голосовые озвучки для сервера:",
        color=0x5865F2
    )
    embed.add_field(name="🗡 Сложное подземелье", value="🟢 Включено" if settings.get("sound_dungeon_hard", 1) else "🔴 Выключено", inline=True)
    embed.add_field(name="⚔️ Среднее подземелье", value="🟢 Включено" if settings.get("sound_dungeon_medium", 1) else "🔴 Выключено", inline=True)
    embed.add_field(name="🌋 Остров Чеджу (17:00)", value="🟢 Включено" if settings.get("sound_dungeon_jeju", 1) else "🔴 Выключено", inline=True)
    embed.add_field(name="🏛 Тёмный Аукцион (Сб 19:00)", value="🟢 Включено" if settings.get("sound_dark_auction", 1) else "🔴 Выключено", inline=True)
    embed.add_field(name="🏰 Клановый рейд (голос)", value="🟢 Включено (каждый час :00)" if settings.get("sound_clan_raid", 1) else "🔴 Выключено", inline=True)
    embed.add_field(name="🎬 Лололошка", value="🟢 Включено" if settings.get("sound_MrLalalashkaXXL", 1) else "🔴 Выключено", inline=True)
    embed.add_field(name="🎮 Фиксплей", value="🟢 Включено" if settings.get("sound_F1xPlay_", 1) else "🔴 Выключено", inline=True)
    embed.set_footer(text="Интервал кланового рейда: каждый час в :00 (голос за 5 мин в :55)")
    return embed


# Register Discord Slash Commands (ALL EPHEMERAL RESPONSES FOR PRIVACY)
if tree:
    @tree.command(name="admin", description="Админ-панель настройки голосовых уведомлений (только для администратора)")
    async def slash_admin(interaction: discord.Interaction):
        # Strict Admin User ID check ONLY for /admin
        if interaction.user.id not in DISCORD_ADMIN_IDS:
            await interaction.response.send_message("⛔ **У вас нет доступа к этой админ-панели.**", ephemeral=True)
            return
            
        settings = await db.get_all_discord_settings()
        embed = generate_admin_embed(settings)
        view = DiscordAdminView(admin_id=interaction.user.id, settings=settings)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @tree.command(name="unverify", description="Снять верификацию VimeWorld с участника и забрать роли (только для администратора)")
    @app_commands.describe(member="Участник сервера")
    async def slash_unverify(interaction: discord.Interaction, member: discord.Member):
        if interaction.user.id not in DISCORD_ADMIN_IDS:
            await interaction.response.send_message("⛔ **Эта команда доступна только администратору.**", ephemeral=True)
            return
            
        await interaction.response.defer(ephemeral=True)
        embed_out = await process_user_unverify(interaction.guild, member)
        await interaction.followup.send(embed=embed_out, ephemeral=True)

    @tree.command(name="verify", description="Привязать никнейм VimeWorld и автоматически получить роли на сервере")
    @app_commands.describe(nickname="Ваш никнейм на VimeWorld")
    async def slash_verify(interaction: discord.Interaction, nickname: str):
        await interaction.response.defer(ephemeral=True)
        embed_out = await process_user_verification(interaction.guild, interaction.user, nickname)
        await interaction.followup.send(embed=embed_out, ephemeral=True)

    @tree.command(name="sync", description="Обновить ваши роли Discord на основе текущих успехов VimeWorld")
    async def slash_sync(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        embed_out = await process_user_sync(interaction.guild, interaction.user)
        await interaction.followup.send(embed=embed_out, ephemeral=True)

    @tree.command(name="player", description="Посмотреть статистику и профиль Solo Leveling игрока VimeWorld")
    @app_commands.describe(nickname="Никнейм игрока на VimeWorld")
    async def slash_player(interaction: discord.Interaction, nickname: str):
        await interaction.response.defer(ephemeral=True)
        profile = await checker.fetch_full_player_profile(nickname)
        if not profile.get("exists"):
            await interaction.followup.send(f"❌ Игрок `{nickname}` не найден на VimeWorld!", ephemeral=True)
            return
        embed = build_player_embed(profile)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @tree.command(name="compare", description="Сравнить статистику двух игроков Solo Leveling на VimeWorld")
    @app_commands.describe(player1="Никнейм первого игрока", player2="Никнейм второго игрока")
    async def slash_compare(interaction: discord.Interaction, player1: str, player2: str):
        await interaction.response.defer(ephemeral=True)
        p1_task = checker.fetch_full_player_profile(player1)
        p2_task = checker.fetch_full_player_profile(player2)
        p1, p2 = await asyncio.gather(p1_task, p2_task)

        if not p1.get("exists"):
            await interaction.followup.send(f"❌ Игрок `{player1}` не найден на VimeWorld!", ephemeral=True)
            return
        if not p2.get("exists"):
            await interaction.followup.send(f"❌ Игрок `{player2}` не найден на VimeWorld!", ephemeral=True)
            return

        embed = build_compare_embed(p1, p2)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @tree.command(name="clan", description="Расписание клановых рейдов Solo Leveling (каждый час)")
    async def slash_clan(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        now = dungeon_utils.get_now_msk()
        clan_raid = dungeon_utils.get_next_clan_raid(now)
        today_raids = dungeon_utils.get_clan_raids_for_date(now.date())
        
        embed = discord.Embed(
            title="🏰 Расписание Клановых Рейдов Solo Leveling",
            description=(
                f"🕒 **Ближайший рейд:** `{clan_raid['formatted_time']}` (через **{clan_raid['time_remaining']}**)\n"
                f"🔊 **Голосовой анонс:** за 5 минут до старта в `{clan_raid['alert_formatted']}`\n\n"
                f"⚙️ **Расписание:** Каждый час в **:00** (с 03:00 до 03:00 ежедневно)"
            ),
            color=0x9B59B6
        )
        
        # Build schedule list for today
        schedule_lines = []
        for r in today_raids:
            r_str = r.strftime("%H:%M")
            if r == clan_raid["target_dt"]:
                schedule_lines.append(f"👉 **`{r_str}`** ⬅️ *(следующий)*")
            elif r < now:
                schedule_lines.append(f"~~`{r_str}`~~ ✅")
            else:
                schedule_lines.append(f"`{r_str}`")
                
        embed.add_field(
            name=f"📋 Рейды на сегодня ({now.strftime('%d.%m')} МСК)",
            value="\n".join(schedule_lines) if schedule_lines else "Нет рейдов",
            inline=False
        )
        embed.set_footer(text="Интервал: каждый час в :00 | Голосовой анонс за 5 минут до старта (:55)")
        await interaction.followup.send(embed=embed, ephemeral=True)

async def play_voice_sound(sound_filename: str) -> tuple[bool, str]:
    """
    Plays an MP3/OGG sound file in the active Discord Voice Channel ONLY IF:
    1. At least 1 human is inside a non-AFK voice channel.
    2. The setting for this sound is enabled by the admin.
    """
    global voice_client
    if not DISCORD_BOT_TOKEN:
        return False, "❌ Токен DISCORD_BOT_TOKEN не установлен в переменных окружения!"

    if not is_discord_ready():
        return False, "⏳ Discord бот еще не подключился к сетям Discord. Подождите пару секунд."

    # Map sound filenames to setting keys
    setting_key = None
    if sound_filename == "dungeon_hard.mp3":
        setting_key = "sound_dungeon_hard"
    elif sound_filename == "dungeon_medium.mp3":
        setting_key = "sound_dungeon_medium"
    elif sound_filename == "jeju_raid.mp3":
        setting_key = "sound_dungeon_jeju"
    elif sound_filename == "temnauc.mp3":
        setting_key = "sound_dark_auction"
    elif sound_filename == "clan.mp3":
        setting_key = "sound_clan_raid"
    elif sound_filename == "lololoshka_online.mp3":
        setting_key = "sound_MrLalalashkaXXL"
    elif sound_filename == "fixplay_online.mp3":
        setting_key = "sound_F1xPlay_"

    # Check setting status if key mapped
    if setting_key:
        is_enabled = await db.get_discord_setting(setting_key, 1)
        if not is_enabled:
            msg = f"⏸ Звуковое уведомление '{sound_filename}' отключено администратором в Discord /admin."
            logger.info(msg)
            return False, msg

    # Check if any non-AFK voice channel has active human members
    target_vc = await find_active_human_voice_channel()
    if not target_vc:
        msg = "🔇 Ни один человек не найден в активных голосовых каналах (AFK каналы игнорируются)! Зайдите в активный войс и повторите тест."
        logger.info(f"Skipping Discord voice alert '{sound_filename}': {msg}")
        if voice_client and voice_client.is_connected():
            try:
                await voice_client.disconnect()
            except Exception:
                pass
            voice_client = None
        return False, msg
        
    sound_path = os.path.join("sounds", sound_filename)
    if not os.path.exists(sound_path):
        sound_path = sound_filename # Fallback to root dir
        
    if not os.path.exists(sound_path):
        msg = f"❌ Файл звука '{sound_filename}' не найден на сервере!"
        logger.warning(msg)
        return False, msg

    try:
        # Connect or move to the channel with human members
        if voice_client and voice_client.is_connected():
            if voice_client.channel.id != target_vc.id:
                await voice_client.move_to(target_vc)
        else:
            voice_client = await target_vc.connect()
            
        logger.info(f"Connected to Discord Voice Channel '{target_vc.name}' with human members.")

        if voice_client and voice_client.is_connected():
            if voice_client.is_playing():
                voice_client.stop()
                
            # FFmpeg option: -af "volume=4.0" amplifies audio volume to 400% (+12 dB)
            audio_source = discord.FFmpegPCMAudio(sound_path, options='-af "volume=4.0"')
            voice_client.play(audio_source)
            logger.info(f"Playing Discord voice alert (+400% volume): {sound_filename} in channel '{target_vc.name}'")
            
            # Background task to disconnect cleanly after alert finishes
            async def after_alert_action():
                global voice_client
                try:
                    while voice_client and voice_client.is_playing():
                        await asyncio.sleep(0.5)
                    await asyncio.sleep(0.5)
                    
                    if voice_client and voice_client.is_connected():
                        await voice_client.disconnect()
                        voice_client = None
                        logger.info(f"Disconnected from Discord voice channel after playing {sound_filename}.")
                except Exception as ex:
                    logger.warning(f"Error handling post-alert voice action: {ex}")
                    voice_client = None

            asyncio.create_task(after_alert_action())
            
            return True, f"🔊 Проигрываю звук <b>{sound_filename}</b> в канале <b>{target_vc.name}</b>!"
    except Exception as e:
        err_msg = f"❌ Ошибка воспроизведения звука: {e}"
        logger.error(err_msg)
        return False, err_msg
    except Exception as e:
        err_msg = f"❌ Ошибка воспроизведения звука: {e}"
        logger.error(err_msg)
        return False, err_msg


async def start_discord_bot():
    """Launches Discord bot in background if DISCORD_BOT_TOKEN is set."""
    if not DISCORD_BOT_TOKEN:
        logger.info("DISCORD_BOT_TOKEN is not set. Discord voice bot skipped.")
        return
        
    if discord_client:
        logger.info("Starting Discord Voice Bot...")
        try:
            await discord_client.start(DISCORD_BOT_TOKEN)
        except Exception as e:
            logger.error(f"Error running Discord bot: {e}")
