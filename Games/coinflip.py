import discord
from discord.ext import commands
import random
import asyncio
from datetime import datetime, timezone
from utils import *

class Coinflip(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def bet_ok(self, ctx, amount):
        if amount is None or amount <= 0:
            return None, build_em("❌ Error", "Bet must be greater than $0.", em_lose)
        user = fetch_usr(ctx.author.id)
        if user["balance"] < amount:
            return None, build_em("❌ Insufficient Funds",
                                    f"Your balance: **{fmt_cash(user['balance'])}**", em_lose)
        return user, None

    @commands.command(name="coinflip", aliases=["cf"])
    async def do_flip(self, ctx, amount: str = None, side: str = None):
        amount = get_bet(ctx.author.id, amount)
        user, err = self.bet_ok(ctx, amount)
        if err:
            return await ctx.send(embed=err)
        if side is None or side.lower() not in ("heads", "tails"):
            return await ctx.send(embed=build_em("❌ Error",
                "Usage: `.coinflip <amount> <heads/tails>`", em_lose))

        side = side.lower()
        user["balance"] -= amount
        user["games_played"] += 1

        flip_em = build_em("🪙 Flipping...", "```\n🪙 The coin is in the air...\n```", em_info)
        msg = await ctx.send(embed=flip_em)

        trajectory = [
            "\n\n\n      🪙 ╱",
            "\n\n      🪙 ─\n",
            "\n      🪙 ╲\n\n",
            "      🪙 │\n\n\n",
            "\n      🪙 ╱\n\n",
            "\n\n      🪙 ─\n",
            "\n\n\n      🪙 ╲",
            "\n\n\n\n      🪙 │"
        ]
        
        for i in range(8):
            flip_em.description = f"```\n{trajectory[i]}\n```"
            await msg.edit(embed=flip_em)
            await asyncio.sleep(0.3)

        drift = calc_drift(ctx.author.id, amount, ctx.author.name)
        win_threshold = 0.48 - drift
        
        if check_hb(ctx.author.id):
            result = random.choice(["heads", "tails"])
        elif random.random() < win_threshold:
            result = side
        else:
            result = "tails" if side == "heads" else "heads"
        coin_emoji = "👑" if result == "heads" else "🦅"
        won = side == result

        if won:
            winnings = amount * 2
            user["balance"] += winnings
            user["total_won"] += (winnings - amount)
            user["games_won"] += 1
            save_usr(ctx.author.id, user)
            log_tx(ctx.author.id, "game_win", winnings, f"Coinflip — {result}")
            win_log(ctx.author.id, (winnings - amount), ctx.author.name, member=ctx.author)
            streak_txt = get_msgs(ctx.author.id, True)

            em = discord.Embed(
                title=f"🪙 COINFLIP — YOU WIN! {coin_emoji}",
                description=(
                    f"```fix\n{coin_emoji} Result: {result.upper()}\n"
                    f"🎯 Your Call: {side.upper()}\n"
                    f"💰 Winnings: {fmt_cash(winnings - amount)}\n```\n"
                    f"💵 Balance: **{fmt_cash(user['balance'])}**{streak_txt}"
                ),
                color=em_win, timestamp=datetime.now(timezone.utc)
            )
        else:
            save_usr(ctx.author.id, user)
            log_tx(ctx.author.id, "game_loss", -amount, f"Coinflip — {result}")
            loss_log(ctx.author.id, amount, ctx.author.name)
            streak_txt = get_msgs(ctx.author.id, False)
            consolation = pity_win(ctx.author.id, amount)
            consolation_txt = f"\n🌟 _Lucky bonus: +{fmt_cash(consolation)}!_" if consolation > 0 else ""

            em = discord.Embed(
                title=f"🪙 COINFLIP — You Lost {coin_emoji}",
                description=(
                    f"```diff\n- {coin_emoji} Result: {result.upper()}\n"
                    f"- 🎯 Your Call: {side.upper()}\n"
                    f"- 💸 Lost: {fmt_cash(amount)}\n```\n"
                    f"💵 Balance: **{fmt_cash(user['balance'])}**{consolation_txt}{streak_txt}"
                ),
                color=em_lose, timestamp=datetime.now(timezone.utc)
            )

        em.set_footer(text=f"🔴 {bot_name} • Coinflip")
        upd_lb(ctx.author.id, ctx.author.name)
        await msg.edit(embed=em)

async def setup(bot):
    await bot.add_cog(Coinflip(bot))
