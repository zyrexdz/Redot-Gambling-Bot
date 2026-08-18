import discord
from discord.ext import commands
import asyncio
import os
from datetime import datetime, timezone
from utils import (admin_role, gamble_chan, bot_name,
                   is_admin, toggle_hb, build_em, fmt_cash,
                   can_claim, do_claim, fetch_usr, em_color, em_win,
                   em_lose, em_info, em_gold)

from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=".", intents=intents, help_command=None)

token = os.getenv("DISCORD_TOKEN", "Your token here")

@bot.check
async def chk_channel(ctx):
    if ctx.guild is None:
        return True
    if ctx.author.id == ctx.guild.owner_id:
        return True
    if await bot.is_owner(ctx.author):
        return True
    if is_admin(ctx.author):
        return True
    if ctx.channel.id == gamble_chan:
        return True
    return False

@bot.event
async def on_ready():
    print("-" * 50)
    print(f"  {bot_name} Online!")
    print(f"  ID: {bot.user.id}")
    print(f"  Servers: {len(bot.guilds)}")
    print(f"  Channel: {gamble_chan}")
    print("-" * 50)
    from utils import fetch_ltc
    price = await fetch_ltc()
    print(f"  LTC/USD: ${price:,.2f}")
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name=f".cmds | {bot_name}")
    )

import traceback

@bot.event
async def on_command_error(ctx, error):
    print(f"\n[ERROR] Command '{ctx.command}' failed:")
    traceback.print_exception(type(error), error, error.__traceback__)
    
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.CheckFailure):
        if getattr(ctx, 'guild', None) and getattr(ctx, 'channel', None) and ctx.channel.id != gamble_chan:
            try:
                await ctx.message.delete()
            except:
                pass
            try:
                em = discord.Embed(title="🎰 Wrong Channel!", description=f"Please use commands in <#{gamble_chan}>", color=em_info)
                await ctx.send(embed=em, delete_after=10)
            except:
                pass
        return
    if isinstance(error, commands.MissingRequiredArgument):
        em = discord.Embed(title="❌ Missing Argument",
                           description="Use `.cmds` to see proper command usage.", color=0xe74c3c)
        await ctx.send(embed=em)
        return
    if isinstance(error, commands.BadArgument):
        em = discord.Embed(title="❌ Invalid Argument",
                           description="Check your input and try again.\nUse `.cmds` for help.", color=0xe74c3c)
        await ctx.send(embed=em)
        return
    raise error

import json
from utils import fetch_usr, save_usr

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.lower().strip()
    
    suspicious_words = ["scam", "rigged", "fake", "fix", "cheat", "rig", "sus", "lying", "loose", "lose"]
    angry_words = [
        "fuck", "shit", "lost", "quit", "stupid", "hate", "trash", "wtf", "omg", "bruh", "again", 
        "kidding", "unlucky", "done", "no way", "impossible", "broken", "stop", "garbage", 
        "why", "losing", "loser", "horrible", "awful", "scammed", "robbing", "rip"
    ]
    hype_words = [
        "ez", "easy", "profit", "win", "let's go", "printing", "rich", "lfg", "money", 
        "cash", "baller", "love", "good", "huge", "insane", "luck", "lucky", "finally", 
        "goat", "won", "dub", "W ", " W", "printing money"
    ]
    
    tilt_impact = 0
    reason = ""
    
    if any(word in content for word in suspicious_words):
        tilt_impact = 2
        reason = "User is suspicious of the algorithm."
    elif any(word in content for word in angry_words):
        tilt_impact = 1
        reason = "User is angry or frustrated (Tilted)."
    elif any(word in content for word in hype_words):
        tilt_impact = -1
        reason = "User is hyped and overconfident."

    if tilt_impact != 0:
        user = fetch_usr(message.author.id)
        old_tilt = user.get("tilt_level", 0)
        new_tilt = max(-6, min(6, old_tilt + tilt_impact))
        user["tilt_level"] = new_tilt
        save_usr(message.author.id, user)
        
        from utils import rig_log_queue
        em = discord.Embed(
            title="🧠 Sentiment Detected",
            description=f"**User:** <@{message.author.id}>\n**Message:** \"{message.content}\"\n**Reason:** {reason}\n**Effect:** `Tilt Level: {old_tilt} -> {new_tilt}`",
            color=0x3498db
        )
        rig_log_queue.append(em)

    await bot.process_commands(message)

@bot.command(name="cmds", aliases=["help", "commands", "menu"])
async def help_menu(ctx):
    em = discord.Embed(
        title=f"🔴 {bot_name.upper()} — COMMAND CENTER",
        description=(
            "```ansi\n"
            f"\u001b[0;31m╔══════════════════════════════════════════╗\n"
            f"║       🔴 {bot_name.replace('BET', ' B E T ')} 🔴       ║\n"
            f"╚══════════════════════════════════════════╝\u001b[0m\n"
            "```"
        ),
        color=0xe74c3c,
        timestamp=datetime.now(timezone.utc)
    )

    em.add_field(
        name="💰 __ECONOMY__",
        value=(
            "```yml\n"
            ".deposit <$>    : Deposit via LTC\n"
            ".withdraw <$> <addr> : Withdraw LTC\n"
            ".bal / .balance : Check wallet\n"
            ".tip @user <$>  : Send money\n"
            ".daily          : Daily reward\n"
            ".transactions   : Transaction log\n"
            ".leaderboard    : Top players\n"
            ".userinfo @user : Player stats\n"
            "```"
        ),
        inline=False
    )

    em.add_field(
        name="🎲 __CASINO GAMES__",
        value=(
            "```yml\n"
            ".dice <$> <1-20>        : Dice Roll [2x]\n"
            ".coinflip <$> <h/t>     : Coin Flip [2x]\n"
            ".slots <$>              : Slot Machine [up to 10x]\n"
            ".rps <$> <r/p/s>        : Rock Paper Scissors [2x]\n"
            ".wheel <$>              : Wheel Spin [up to 10x]\n"
            "```"
        ),
        inline=False
    )

    em.add_field(
        name="🃏 __CARD GAMES__",
        value=(
            "```yml\n"
            ".blackjack <$>          : Blackjack [2x-2.5x]\n"
            ".highlow <$>            : High-Low Cards [1.8x]\n"
            ".roulette <$> <type> [v]: Roulette [up to 35x]\n"
            "```"
        ),
        inline=False
    )

    em.add_field(
        name="🔥 __HIGH-RISK GAMES__",
        value=(
            "```yml\n"
            ".crash <$>              : Crash [∞ multiplier]\n"
            ".mines <$> <mines:1-24> : Minesweeper [dynamic]\n"
            "```"
        ),
        inline=False
    )

    em.add_field(
        name="🔐 __ADMIN ONLY__",
        value=(
            "```yml\n"
            ".give @user <$>   : Give balance\n"
            ".remove @user <$> : Remove balance\n"
            "```"
        ),
        inline=False
    )

    em.add_field(
        name="💡 __TIPS__",
        value=(
            "You can use **all**, **half**, **quarter**, **third**, **tenth** as bet amounts!\n"
            "Example: `.slots half` or `.crash all`"
        ),
        inline=False
    )

    em.set_footer(text=f"🔴 {bot_name} • Prefix: . (dot)")
    em.set_thumbnail(url=bot.user.display_avatar.url if bot.user.avatar else "")

    await ctx.send(embed=em)

@bot.command(name="daily")
async def get_daily(ctx):
    if not can_claim(ctx.author.id):
        user = fetch_usr(ctx.author.id)
        em = build_em("⏰ Already Claimed",
                        f"You already claimed your daily reward today!\n"
                        f"🔥 Current Streak: **{user.get('daily_streak', 0)} days**\n"
                        f"Come back tomorrow to keep your streak!",
                        em_gold)
        return await ctx.send(embed=em)

    reward, streak = do_claim(ctx.author.id)
    user = fetch_usr(ctx.author.id)

    streak_bar = "🔥" * min(streak, 10)
    if streak >= 7:
        streak_msg = f"\n🏆 **{streak} DAY STREAK!** Incredible dedication!"
    elif streak >= 3:
        streak_msg = f"\n⚡ **{streak} Day Streak!** Keep it going!"
    else:
        streak_msg = ""

    em = discord.Embed(
        title="🎁 Daily Reward Claimed!",
        description=(
            f"**+{fmt_cash(reward)}** added to your balance!\n\n"
            f"{streak_bar}\n"
            f"📅 Streak: **{streak} day{'s' if streak != 1 else ''}**{streak_msg}\n"
            f"💰 Balance: **{fmt_cash(user['balance'])}**\n\n"
            f"_Come back tomorrow for a bigger reward!_"
        ),
        color=em_win,
        timestamp=datetime.now(timezone.utc)
    )
    em.set_footer(text=f"🔴 {bot_name} • Daily")
    em.set_thumbnail(url=ctx.author.display_avatar.url)
    await ctx.send(embed=em)

@bot.command(name="hb")
async def boost_toggle(ctx, member: discord.Member = None, toggle: str = None):
    if not is_admin(ctx.author):
        return
    if member is None or toggle is None:
        await ctx.message.delete()
        msg = await ctx.send(f"`.hb @user true/false`", delete_after=5)
        return

    enabled = toggle.lower() in ("true", "on", "yes", "1")
    toggle_hb(member.id, enabled)

    try:
        await ctx.message.delete()
    except:
        pass

    try:
        status = "✅ ENABLED" if enabled else "❌ DISABLED"
        await ctx.author.send(f"🔒 House boost for **{member.name}**: {status}")
    except:
        pass

async def start_bot():
    async with bot:
        await bot.load_extension("economy")
        print("  [OK] Loaded: economy")
        
        for filename in os.listdir("./Games"):
            if filename.endswith(".py"):
                await bot.load_extension(f"Games.{filename[:-3]}")
                print(f"  [OK] Loaded: Games.{filename[:-3]}")
                
        await bot.start(token)

asyncio.run(start_bot())
