import json
import os
import time
import asyncio
import aiohttp
import discord
from datetime import datetime, timezone, timedelta

data_dir = os.path.dirname(os.path.abspath(__file__))
users_file = os.path.join(data_dir, "users.json")
lb_file = os.path.join(data_dir, "leaderboard.json")

ltc_addr = "ur ltc addy here"
bot_name = "Redot BET"
admin_role = #admin role id

gamble_chan = #gamble channel id
algo_chan = #algorithm channel id
deposit_chan = #deposit channel id

gamble_roles = {
    10.0: "💰 Bronze Gambler ($10+)",
    25.0: "🪙 Silver Spinner ($25+)",
    50.0: "🏅 Gold Betmaster ($50+)",
    100.0: "💎 Platinum Punter ($100+)",
    250.0: "🎲 Diamond Risker ($250+)",
    500.0: "🏆 Elite Wagerer ($500+)",
    1000.0: "🔥 Casino Shark ($1,000+)",
    5000.0: "👑 High Roller King/Queen ($5,000+)",
    10000.0: "🌟 Legend of the House ($10,000+)"
}

_ltc_price_cache = {"price": 85.0, "last_fetch": 0}
ltc_ttl = 300

async def fetch_ltc() -> float:
    now = time.time()
    if now - _ltc_price_cache["last_fetch"] < ltc_ttl:
        return _ltc_price_cache["price"]
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=litecoin&vs_currencies=usd"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    price = data.get("litecoin", {}).get("usd", _ltc_price_cache["price"])
                    _ltc_price_cache["price"] = price
                    _ltc_price_cache["last_fetch"] = now
                    print(f"  [LTC] price updated: ${price:,.2f}")
                    return price
    except Exception as e:
        print(f"  [WARN] ltc price fetch failed: {e}")
    return _ltc_price_cache["price"]

def ltc_val() -> float:
    return _ltc_price_cache["price"]

def read_j(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}

def write_j(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def fetch_usr(user_id: int) -> dict:
    users = read_j(users_file)
    uid = str(user_id)
    if uid not in users:
        users[uid] = {
            "balance": 0.0,
            "total_deposited": 0.0,
            "total_withdrawn": 0.0,
            "total_won": 0.0,
            "total_lost": 0.0,
            "transactions": [],
            "games_played": 0,
            "games_won": 0,
            "hb": False,
            "daily_streak": 0,
            "last_daily": None,
            "loss_streak": 0,
            "win_streak": 0,
            "best_win_streak": 0
        }
        write_j(users_file, users)
    u = users[uid]
    for k, v in {"hb": False, "daily_streak": 0, "last_daily": None,
                  "loss_streak": 0, "win_streak": 0, "best_win_streak": 0}.items():
        if k not in u:
            u[k] = v
    return u

def save_usr(user_id: int, data: dict):
    users = read_j(users_file)
    users[str(user_id)] = data
    write_j(users_file, users)

def log_tx(user_id: int, tx_type: str, amount: float, details: str = ""):
    user = fetch_usr(user_id)
    user["transactions"].append({
        "type": tx_type,
        "amount": amount,
        "details": details,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    user["transactions"] = user["transactions"][-50:]
    save_usr(user_id, user)

def upd_lb(user_id: int, username: str):
    lb = read_j(lb_file)
    user = fetch_usr(user_id)
    lb[str(user_id)] = {
        "username": username,
        "balance": user["balance"],
        "total_won": user["total_won"],
        "total_deposited": user["total_deposited"],
        "games_played": user["games_played"],
        "games_won": user["games_won"]
    }
    write_j(lb_file, lb)

def is_admin(member: discord.Member) -> bool:
    if hasattr(member, "guild_permissions") and member.guild_permissions.administrator:
        return True
    if hasattr(member, "roles"):
        return any(role.id == admin_role for role in member.roles)
    return False

em_color = 0xe74c3c
em_win = 0x2ecc71
em_lose = 0xc0392b
em_info = 0xe67e22
em_gold = 0xf39c12

def build_em(title, description, color=em_color, footer=None):
    em = discord.Embed(title=title, description=description, color=color,
                       timestamp=datetime.now(timezone.utc))
    if footer:
        em.set_footer(text=footer)
    else:
        em.set_footer(text=f"🔴 {bot_name}")
    return em

async def check_txs(amount_ltc: float, since_timestamp: float):
    url = f"https://api.blockcypher.com/v1/ltc/main/addrs/{ltc_addr}/full?limit=10"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    return False, 0
                data = await resp.json()
                txs = data.get("txs", [])
                for tx in txs:
                    for output in tx.get("outputs", []):
                        addrs = output.get("addresses", [])
                        if ltc_addr in addrs:
                            value_satoshi = output.get("value", 0)
                            value_ltc = value_satoshi / 1e8
                            if abs(value_ltc - amount_ltc) / amount_ltc < 0.02:
                                return True, value_ltc
                return False, 0
    except Exception as e:
        print(f"ltc api error: {e}")
        return False, 0

async def conv_ltc(usd: float) -> float:
    price = await fetch_ltc()
    return round(usd / price, 8)

def to_ltc(usd: float) -> float:
    return round(usd / ltc_val(), 8)

def fmt_cash(amount: float) -> str:
    if amount == 0:
        return "$0.00"
    sign = "-" if amount < 0 else ""
    abs_amt = abs(amount)
    formatted = f"{abs_amt:,.8f}"
    int_part, dec_part = formatted.rsplit('.', 1)
    dec_trimmed = dec_part.rstrip('0')
    if len(dec_trimmed) < 2:
        dec_trimmed = dec_trimmed.ljust(2, '0')
    return f"{sign}${int_part}.{dec_trimmed}"

def get_bet(user_id: int, amount_str) -> float:
    if amount_str is None:
        return None
    if isinstance(amount_str, (int, float)):
        return float(amount_str)
    amount_str = str(amount_str).lower().strip()
    user = fetch_usr(user_id)
    bal = user["balance"]

    keywords = {
        "all": 1.0, "max": 1.0,
        "half": 0.5, "1/2": 0.5,
        "quarter": 0.25, "1/4": 0.25,
        "third": 1/3, "1/3": 1/3,
        "tenth": 0.1, "1/10": 0.1,
    }

    if amount_str in keywords:
        return bal * keywords[amount_str]
    try:
        return float(amount_str)
    except (ValueError, TypeError):
        return None

def check_hb(user_id: int) -> bool:
    user = fetch_usr(user_id)
    return user.get("hb", False)

def toggle_hb(user_id: int, enabled: bool):
    user = fetch_usr(user_id)
    user["hb"] = enabled
    save_usr(user_id, user)

algo_queue = []
dep_queue = []
rig_log_queue = algo_queue

def calc_drift(user_id: int, bet_amount: float, username: str = "User") -> float:
    if check_hb(user_id):
        return -0.05
        
    user = fetch_usr(user_id)
    
    games_played = user.get("games_played", 0)
    total_won = user.get("total_won", 0)
    total_lost = user.get("total_lost", 0)
    net = total_won - total_lost
    balance = user.get("balance", 0.0)
    ws = user.get("win_streak", 0)
    tilt_level = user.get("tilt_level", 0)
    
    drift = 0.04 
    logs = ["`+4%` Base Expected Value (EV)"]
    
    if games_played <= 3:
        drift -= 0.08
        logs.append("`-8%` **HOOK PHASE:** (Strictly first 3 games only)")
        
    exposure_ratio = bet_amount / max(1, balance + bet_amount)
    if exposure_ratio > 0.15:
        drift += 0.12
        logs.append(f"`+12%` **HIGH EXPOSURE:** Bet is {exposure_ratio*100:.0f}% of total bankroll. Neutralizing risk.")
    elif exposure_ratio > 0.05:
        drift += 0.05
        logs.append("`+5%` Moderate Exposure Tax.")
        
    if net > 100000:
        drift += 0.18
        logs.append(f"`+18%` **KILL SWITCH:** User is +${net/1000:.1f}k. Extraction maximized.")
    elif net > 5000:
        drift += 0.10
        logs.append(f"`+10%` **HEAVY EXTRACTION:** Siphoning significant surplus.")
    elif net > 500:
        drift += 0.05
        logs.append(f"`+5%` **STANDARD EXTRACTION:** Recovering player profit.")

    if ws >= 3:
        streak_penalty = min(0.15, (ws - 2) * 0.05)
        drift += streak_penalty
        logs.append(f"`+{streak_penalty*100:.0f}%` **STREAK DAMPENER:** Braking runaway momentum.")

    if net < 0:
        if tilt_level >= 3:
            drift -= 0.07
            logs.append("`-7%` **RECOVERY INJECTION:** User is angry AND losing. Feeding wins.")
        elif balance < 5:
            drift -= 0.05
            logs.append("`-5%` **RETENTION LUCK:** User is broke. Pity win active.")
    else:
        if tilt_level >= 3:
            logs.append("`[REJECTED]` Recovery injection skipped (User is profitable)")

    final_drift = max(-0.15, min(0.35, drift))
    
    color = 0xe74c3c if final_drift > 0.10 else (0x2ecc71 if final_drift < 0 else 0xf1c40f)
    rig_status = f"{96 - (final_drift*100):.1f}% Dynamic RTP"
    em = discord.Embed(title=f"🛡️ Auditor Engine: {username}", color=color)
    summary = (
        f"**Exposure:** `{exposure_ratio*100:.1f}%` | **Net:** `${net:,.2f}`\n"
        f"**State:** `{'EXTRACTION' if net > 500 else 'NEUTRAL' if net >= 0 else 'RECOVERY'}`\n"
        f"**Rought Edge:** `{rig_status}`"
    )
    em.description = f"{summary}\n\n**Risk Factors:**\n" + "\n".join(logs)
    em.set_footer(text=f"{bot_name} Behavioral Systems")
    
    algo_queue.append(em)
    save_usr(user_id, user)
    return round(final_drift, 4)

def win_log(user_id: int, amount: float, username: str = "User", member: discord.Member = None):
    user = fetch_usr(user_id)
    user["win_streak"] = user.get("win_streak", 0) + 1
    user["loss_streak"] = 0
    if user["win_streak"] > user.get("best_win_streak", 0):
        user["best_win_streak"] = user["win_streak"]
    save_usr(user_id, user)
    
    if member and isinstance(member, discord.Member):
        asyncio.create_task(upd_roles(member, user["total_won"]))
    
    em = discord.Embed(title=f"🏆 WIN DETECTED: {username}", color=0x2ecc71)
    em.description = (
        f"**User:** <@{user_id}> | **Amount:** `+{fmt_cash(amount)}` \n"
        f"**New Balance:** `{fmt_cash(user['balance'])}` | **Streak:** `{user['win_streak']}nd Win`"
    )
    algo_queue.append(em)
    return user["win_streak"]

async def upd_roles(member: discord.Member, total_won: float):
    try:
        target_role_name = None
        sorted_thresholds = sorted(gamble_roles.keys(), reverse=True)
        for threshold in sorted_thresholds:
            if total_won >= threshold:
                target_role_name = gamble_roles[threshold]
                break
        
        if not target_role_name:
            return

        guild_roles = {role.name: role for role in member.guild.roles}
        target_role = guild_roles.get(target_role_name)
        
        if not target_role:
            return

        if target_role in member.roles:
            return

        all_gamble_names = set(gamble_roles.values())
        to_remove = [r for r in member.roles if r.name in all_gamble_names and r.name != target_role_name]
        
        if to_remove:
            await member.remove_roles(*to_remove, reason="Promoted to higher gambling tier")
        
        await member.add_roles(target_role, reason=f"Earned {target_role_name} (${total_won:,.2f} total wins)")
        
        promo_em = discord.Embed(title="🛡️ AUDITOR: RANK PROMOTION", color=0x3498db)
        promo_em.description = f"🎊 <@{member.id}> has been promoted to **{target_role_name}**!\nTotal Wins: **${total_won:,.2f}**"
        algo_queue.append(promo_em)

    except Exception as e:
        print(f"  ⚠️ Role Sync Error for {member.name}: {e}")

def loss_log(user_id: int, amount: float, username: str = "User"):
    user = fetch_usr(user_id)
    user["loss_streak"] = user.get("loss_streak", 0) + 1
    user["win_streak"] = 0
    user["total_lost"] = user.get("total_lost", 0) + amount
    save_usr(user_id, user)
    
    em = discord.Embed(title=f"💸 LOSS DETECTED: {username}", color=0xe74c3c)
    em.description = (
        f"**User:** <@{user_id}> | **Amount:** `-{fmt_cash(amount)}` \n"
        f"**New Balance:** `{fmt_cash(user['balance'])}` | **Streak:** `{user['loss_streak']}rd Loss`"
    )
    algo_queue.append(em)
    return user["loss_streak"]

def get_msgs(user_id: int, won: bool) -> str:
    user = fetch_usr(user_id)
    if won:
        ws = user.get("win_streak", 0)
        if ws >= 5:
            return f"\n\n🔥🔥🔥 **{ws} WIN STREAK!** You're UNSTOPPABLE! 🔥🔥🔥"
        elif ws >= 3:
            return f"\n\n🔥 **{ws} Win Streak!** You're on FIRE! Keep going!"
        elif ws == 2:
            return "\n\n⚡ **2 in a row!** Luck is on your side!"
        return ""
    else:
        ls = user.get("loss_streak", 0)
        if ls >= 5:
            return "\n\n🍀 _You're due for a big win... don't stop now!_"
        elif ls >= 3:
            return "\n\n💫 _Almost there! Winners never quit!_"
        elif ls == 2:
            return "\n\n🎯 _So close! One more try..._"
        return ""

def pity_win(user_id: int, bet_amount: float) -> float:
    user = fetch_usr(user_id)
    ls = user.get("loss_streak", 0)
    if ls >= 4 and ls % 4 == 0:
        bonus = round(bet_amount * 0.05, 8)
        user["balance"] += bonus
        save_usr(user_id, user)
        return bonus
    return 0

def can_claim(user_id: int) -> bool:
    user = fetch_usr(user_id)
    last = user.get("last_daily")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return last != today

def do_claim(user_id: int) -> tuple:
    user = fetch_usr(user_id)
    last = user.get("last_daily")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if last:
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        if last == yesterday:
            user["daily_streak"] = user.get("daily_streak", 0) + 1
        else:
            user["daily_streak"] = 1
    else:
        user["daily_streak"] = 1

    streak = user["daily_streak"]
    reward = 0.005

    user["balance"] += reward
    user["last_daily"] = today
    save_usr(user_id, user)
    return reward, streak
