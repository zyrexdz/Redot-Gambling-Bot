import discord
from discord.ext import commands
import random
import asyncio
from datetime import datetime, timezone
from utils import *

class Wheel(commands.Cog):
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

    @commands.command(name="wheel")
    async def spin_it(self, ctx, amount: str = None):
        amount = get_bet(ctx.author.id, amount)
        user, err = self.chk_it(ctx, amount)
        if err:
            return await ctx.send(embed=err)

        segments = [
            ("2x", 2), ("3x", 3), ("5x", 5), ("10x", 10), ("Lose", 0),
            ("Lose", 0), ("Lose", 0), ("Lose", 0), ("Lose", 0), ("Lose", 0)
        ]

        user["balance"] -= amount
        user["games_played"] += 1

        spin_em = build_em("🎡 WHEEL SPIN", "```\n🎡 Spinning the wheel...\n```", em_info)
        msg = await ctx.send(embed=spin_em)

        for i in range(10):
            seg = segments[i % len(segments)]
            pointer = "▶️"
            wheel_display = " | ".join(
                [f"**{pointer}{s[0]}**" if j == i % len(segments) else s[0]
                 for j, s in enumerate(segments[:5])]
            )
            spin_em.description = f"🎡 {wheel_display}\n\n⬆️ Spinning..."
            await msg.edit(embed=spin_em)
            await asyncio.sleep(0.4 + i * 0.05)

        drift = calc_drift(ctx.author.id, amount, ctx.author.name)
        if check_hb(ctx.author.id) or drift <= -0.05:
            result = random.choices(segments, weights=[20, 15, 10, 5, 10, 10, 10, 10, 10, 0], k=1)[0]
        elif drift >= 0.05:
            result = random.choices(segments, weights=[5, 5, 2, 1, 15, 15, 20, 20, 15, 2], k=1)[0]
        else:
            result = random.choices(segments, weights=[10, 8, 5, 2, 15, 15, 15, 15, 10, 5], k=1)[0]
        
        if result[1] > 0:
            winnings = amount * result[1]
            user["balance"] += winnings
            user["total_won"] += (winnings - amount)
            user["games_won"] += 1
            save_usr(ctx.author.id, user)
            log_tx(ctx.author.id, "game_win", winnings, f"Wheel — {result[0]}")
            win_log(ctx.author.id, (winnings - amount), ctx.author.name, member=ctx.author)
            streak_txt = get_msgs(ctx.author.id, True)

            em = discord.Embed(
                title=f"🎡 WHEEL — {result[0]}! 🎉",
                description=(
                    f"The wheel landed on **{result[0]}**!\n\n"
                    f"💰 Winnings: **{fmt_cash(winnings - amount)}**\n"
                    f"💵 Balance: **{fmt_cash(user['balance'])}**{streak_txt}"
                ),
                color=em_win, timestamp=datetime.now(timezone.utc)
            )
        else:
            save_usr(ctx.author.id, user)
            log_tx(ctx.author.id, "game_loss", -amount, "Wheel — Lose")
            loss_log(ctx.author.id, amount, ctx.author.name)
            streak_txt = get_msgs(ctx.author.id, False)
            consolation = pity_win(ctx.author.id, amount)
            consolation_txt = f"\n🌟 _Lucky bonus: +{fmt_cash(consolation)}!_" if consolation > 0 else ""

            em = discord.Embed(
                title="🎡 WHEEL — Bad Luck!",
                description=(
                    f"The wheel landed on **LOSE**!\n\n"
                    f"💸 Lost: **{fmt_cash(amount)}**\n"
                    f"💵 Balance: **{fmt_cash(user['balance'])}**{consolation_txt}{streak_txt}"
                ),
                color=em_lose, timestamp=datetime.now(timezone.utc)
            )

        em.set_footer(text=f"🔴 {bot_name} • Wheel")
        upd_lb(ctx.author.id, ctx.author.name)
        await msg.edit(embed=em)

async def setup(bot):
    await bot.add_cog(Wheel(bot))
