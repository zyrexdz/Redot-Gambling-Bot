import discord
from discord.ext import commands
import random
import asyncio
from datetime import datetime, timezone
from utils import *

red_nums = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
black_nums = {2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35}

class Roulette(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def chk_it(self, ctx, amount):
        if amount is None or amount <= 0:
            return None, build_em("❌ Error", "Bet must be greater than $0.", em_lose)
        user = fetch_usr(ctx.author.id)
        if user["balance"] < amount:
            return None, build_em("❌ Insufficient Funds",
                                    f"Your balance: **{fmt_cash(user['balance'])}**", em_lose)
        return user, None

    @commands.command(name="roulette", aliases=["rl"])
    async def play_rl(self, ctx, amount: str = None, bet_type: str = None, value: str = None):
        amount = get_bet(ctx.author.id, amount)
        user, err = self.chk_it(ctx, amount)
        if err:
            return await ctx.send(embed=err)

        valid_types = ["red", "black", "even", "odd", "number"]
        if bet_type is None or bet_type.lower() not in valid_types:
            return await ctx.send(embed=build_em("❌ Error",
                "Usage: `.roulette <amount> <red/black/even/odd/number> [number]`\n"
                "Example: `.roulette 50 red` or `.roulette 50 number 17`", em_lose))

        bet_type = bet_type.lower()
        bet_number = None
        if bet_type == "number":
            if value is None:
                return await ctx.send(embed=build_em("❌ Error",
                    "Specify a number 0-36: `.roulette 50 number 17`", em_lose))
            try:
                bet_number = int(value)
                if bet_number < 0 or bet_number > 36:
                    raise ValueError
            except ValueError:
                return await ctx.send(embed=build_em("❌ Error", "Number must be 0-36.", em_lose))

        user["balance"] -= amount
        user["games_played"] += 1

        spin_em = build_em("🎰 ROULETTE", "```\n🎡 The wheel is spinning...\n```", em_info)
        msg = await ctx.send(embed=spin_em)

        for i in range(8):
            fake = random.randint(0, 36)
            color_e = "🔴" if fake in red_nums else ("⚫" if fake in black_nums else "🟢")
            spin_em.description = f"```\n🎡 Spinning... [{color_e} {fake}]\n```"
            await msg.edit(embed=spin_em)
            await asyncio.sleep(0.4)

        drift = calc_drift(ctx.author.id, amount, ctx.author.name)
        if drift > 0.06 and random.random() < drift:
            result = 0
        else:
            result = random.randint(0, 36)
        is_red = result in red_nums
        is_black = result in black_nums
        is_even = result != 0 and result % 2 == 0
        is_odd = result % 2 == 1
        color_name = "🔴 Red" if is_red else ("⚫ Black" if is_black else "🟢 Green")

        won = False
        multiplier = 0
        if bet_type == "number" and result == bet_number:
            won, multiplier = True, 35
        elif bet_type == "red" and is_red:
            won, multiplier = True, 2
        elif bet_type == "black" and is_black:
            won, multiplier = True, 2
        elif bet_type == "even" and is_even:
            won, multiplier = True, 2
        elif bet_type == "odd" and is_odd:
            won, multiplier = True, 2

        if won:
            winnings = amount * multiplier
            user["balance"] += winnings
            user["total_won"] += (winnings - amount)
            user["games_won"] += 1
            save_usr(ctx.author.id, user)
            log_tx(ctx.author.id, "game_win", winnings, f"Roulette — {result} {color_name}")
            win_log(ctx.author.id, (winnings - amount), ctx.author.name, member=ctx.author)
            streak_txt = get_msgs(ctx.author.id, True)

            em = discord.Embed(
                title="🎰 ROULETTE — YOU WIN! 🎉",
                description=(
                    f"The ball landed on **{color_name} {result}**\n\n"
                    f"Your bet: **{bet_type.upper()}** {f'({bet_number})' if bet_number is not None else ''}\n"
                    f"💰 **{multiplier}x** — Winnings: **{fmt_cash(winnings - amount)}**\n"
                    f"💵 Balance: **{fmt_cash(user['balance'])}**{streak_txt}"
                ),
                color=em_win, timestamp=datetime.now(timezone.utc)
            )
        else:
            save_usr(ctx.author.id, user)
            log_tx(ctx.author.id, "game_loss", -amount, "Roulette — Lose")
            loss_log(ctx.author.id, amount, ctx.author.name)
            streak_txt = get_msgs(ctx.author.id, False)
            consolation = pity_win(ctx.author.id, amount)
            consolation_txt = f"\n🌟 _Lucky bonus: +{fmt_cash(consolation)}!_" if consolation > 0 else ""

            em = discord.Embed(
                title="🎰 ROULETTE — You Lost",
                description=(
                    f"The ball landed on **{color_name} {result}**\n\n"
                    f"Your bet: **{bet_type.upper()}** {f'({bet_number})' if bet_number is not None else ''}\n"
                    f"💸 Lost: **{fmt_cash(amount)}**\n"
                    f"💵 Balance: **{fmt_cash(user['balance'])}**{consolation_txt}{streak_txt}"
                ),
                color=em_lose, timestamp=datetime.now(timezone.utc)
            )

        em.set_footer(text=f"🔴 {bot_name} • Roulette")
        upd_lb(ctx.author.id, ctx.author.name)
        await msg.edit(embed=em)

async def setup(bot):
    await bot.add_cog(Roulette(bot))
