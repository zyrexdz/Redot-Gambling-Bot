import discord
from discord.ext import commands
import random
import asyncio
from datetime import datetime, timezone
from utils import *

class Dice(commands.Cog):
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

    @commands.command(name="dice")
    async def go_dice(self, ctx, amount: str = None, number: int = None):
        amount = get_bet(ctx.author.id, amount)
        user, err = self.bet_ok(ctx, amount)
        if err:
            return await ctx.send(embed=err)
        if number is None or number < 1 or number > 20:
            return await ctx.send(embed=build_em("❌ Error",
                "Usage: `.dice <amount> <1-20>`", em_lose))

        user["balance"] -= amount
        user["games_played"] += 1
        save_usr(ctx.author.id, user)

        roll_em = build_em("🎲 Rolling...", "```\n🎲 Shaking the dice...\n```", em_info)
        msg = await ctx.send(embed=roll_em)

        trajectory = [
            "   🎲   \n\n\n",
            "\n     🎲 \n\n",
            "\n\n       🎲\n",
            "\n         🎲\n",
            "\n\n       🎲\n",
            "\n     🎲 \n\n",
            "   🎲   \n\n\n",
            "\n 🎲     \n\n"
        ]

        for i in range(8):
            fake = random.randint(1, 20)
            desc_text = f"```\n{trajectory[i]}  [ {fake} ]\n```"
            roll_em.description = desc_text
            await msg.edit(embed=roll_em)
            await asyncio.sleep(0.3)

        result = random.randint(1, 20) if check_hb(ctx.author.id) else random.randint(1, 40)
        won = result == number

        if won:
            winnings = amount * 2
            user["balance"] += winnings
            user["total_won"] += (winnings - amount)
            user["games_won"] += 1
            save_usr(ctx.author.id, user)
            log_tx(ctx.author.id, "game_win", winnings, f"Dice — rolled {result}")
            win_log(ctx.author.id, (winnings - amount), ctx.author.name, member=ctx.author)
            streak_txt = get_msgs(ctx.author.id, True)

            em = discord.Embed(
                title="🎲 DICE — YOU WIN! 🎉",
                description=(
                    f"```fix\n🎲 Dice Rolled: {result}\n"
                    f"🎯 Your Pick:   {number}\n"
                    f"💰 Winnings:    {fmt_cash(winnings - amount)}\n```\n"
                    f"💵 New Balance: **{fmt_cash(user['balance'])}**{streak_txt}"
                ),
                color=em_win, timestamp=datetime.now(timezone.utc)
            )
        else:
            display_result = min(result, 20) if result != number else result
            save_usr(ctx.author.id, user)
            log_tx(ctx.author.id, "game_loss", -amount, f"Dice — rolled {display_result}")
            loss_log(ctx.author.id, amount, ctx.author.name)
            streak_txt = get_msgs(ctx.author.id, False)
            consolation = pity_win(ctx.author.id, amount)
            consolation_txt = f"\n🌟 _Lucky bonus: +{fmt_cash(consolation)}!_" if consolation > 0 else ""

            em = discord.Embed(
                title="🎲 DICE — You Lost",
                description=(
                    f"```diff\n- 🎲 Dice Rolled: {display_result}\n"
                    f"- 🎯 Your Pick:   {number}\n"
                    f"- 💸 Lost:        {fmt_cash(amount)}\n```\n"
                    f"💵 New Balance: **{fmt_cash(user['balance'])}**{consolation_txt}{streak_txt}"
                ),
                color=em_lose, timestamp=datetime.now(timezone.utc)
            )

        em.set_footer(text=f"🔴 {bot_name} • Dice")
        upd_lb(ctx.author.id, ctx.author.name)
        await msg.edit(embed=em)

async def setup(bot):
    await bot.add_cog(Dice(bot))
