import discord
from discord.ext import commands
import random
import asyncio
from datetime import datetime, timezone
from utils import *

class Slots(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def chk_money(self, ctx, amount):
        if amount is None or amount <= 0:
            return None, build_em("❌ Error", "Bet must be greater than $0.", em_lose)
        user = fetch_usr(ctx.author.id)
        if user["balance"] < amount:
            return None, build_em("❌ Insufficient Funds",
                                    f"Your balance: **{fmt_cash(user['balance'])}**", em_lose)
        return user, None

    @commands.command(name="slots")
    async def play_slots(self, ctx, amount: str = None):
        amount = get_bet(ctx.author.id, amount)
        user, err = self.chk_money(ctx, amount)
        if err:
            return await ctx.send(embed=err)

        drift = calc_drift(ctx.author.id, amount, ctx.author.name)
        symbols = ["🍒", "🍋", "💎", "7️⃣", "⭐"]
        
        if drift < -0.05:
            weights = [20, 20, 20, 20, 20]
        elif drift > 0.05:
            weights = [45, 30, 15, 8, 2]
        else:
            weights = [35, 30, 20, 10, 5] 

        user["balance"] -= amount
        user["games_played"] += 1

        lines = [
            [random.choice(symbols) for _ in range(3)],
            [random.choice(symbols) for _ in range(3)],
            [random.choice(symbols) for _ in range(3)]
        ]
        
        spin_em = build_em("🎰 SLOTS — Spinning...", "```\nGetting ready...\n```", em_info)
        msg = await ctx.send(embed=spin_em)

        final_reels = random.choices(symbols, weights=weights, k=3)

        for step in range(12):
            lines[2] = lines[1]
            lines[1] = lines[0]
            
            r1 = final_reels[0] if step >= 7 else random.choice(symbols)
            r2 = final_reels[1] if step >= 9 else random.choice(symbols)
            r3 = final_reels[2] if step >= 11 else random.choice(symbols)
            lines[0] = [r1, r2, r3]

            anim_desc = (
                f"╔══════════════════╗\n"
                f"║  🎰 | {lines[0][0]} | {lines[0][1]} | {lines[0][2]} |  ║\n"
                f"║  🎰 | {lines[1][0]} | {lines[1][1]} | {lines[1][2]} | ◄║\n"
                f"║  🎰 | {lines[2][0]} | {lines[2][1]} | {lines[2][2]} |  ║\n"
                f"╚══════════════════╝"
            )
            spin_em.description = f"```\n{anim_desc}\n```"
            sleep_time = 0.15 + (step * 0.05) 
            await msg.edit(embed=spin_em)
            await asyncio.sleep(sleep_time)

        r1, r2, r3 = lines[1]

        multiplier = 0
        if r1 == r2 == r3:
            if r1 == "💎":
                multiplier = 10
            elif r1 == "7️⃣":
                multiplier = 8
            elif r1 == "⭐":
                multiplier = 5
            elif r1 == "🍒":
                multiplier = 3
            else:
                multiplier = 2

        if multiplier > 0:
            winnings = amount * multiplier
            user["balance"] += winnings
            user["total_won"] += (winnings - amount)
            user["games_won"] += 1
            save_usr(ctx.author.id, user)
            log_tx(ctx.author.id, "game_win", winnings, f"Slots — {r1}{r2}{r3} ({multiplier}x)")
            win_log(ctx.author.id, (winnings - amount), ctx.author.name, member=ctx.author)
            streak_txt = get_msgs(ctx.author.id, True)

            em = discord.Embed(
                title="🎰 SLOTS — JACKPOT! 🎉",
                description=(
                    f"```\n╔══════════════════╗\n"
                    f"║  🎰 | {lines[0][0]} | {lines[0][1]} | {lines[0][2]} |  ║\n"
                    f"║  🎰 | {r1} | {r2} | {r3} | ◄║\n"
                    f"║  🎰 | {lines[2][0]} | {lines[2][1]} | {lines[2][2]} |  ║\n"
                    f"╚══════════════════╝\n```\n"
                    f"💰 Multiplier: **{multiplier}x**\n"
                    f"💰 Winnings: **{fmt_cash(winnings - amount)}**\n"
                    f"💵 New Balance: **{fmt_cash(user['balance'])}**{streak_txt}"
                ),
                color=em_win, timestamp=datetime.now(timezone.utc)
            )
        else:
            save_usr(ctx.author.id, user)
            log_tx(ctx.author.id, "game_loss", -amount, f"Slots — {r1}{r2}{r3} (Lose)")
            loss_log(ctx.author.id, amount, ctx.author.name)
            streak_txt = get_msgs(ctx.author.id, False)
            consolation = pity_win(ctx.author.id, amount)
            consolation_txt = f"\n🌟 _Lucky bonus: +{fmt_cash(consolation)}!_" if consolation > 0 else ""

            em = discord.Embed(
                title="🎰 SLOTS — Better luck next time",
                description=(
                    f"```\n╔══════════════════╗\n"
                    f"║  🎰 | {lines[0][0]} | {lines[0][1]} | {lines[0][2]} |  ║\n"
                    f"║  🎰 | {r1} | {r2} | {r3} | ◄║\n"
                    f"║  🎰 | {lines[2][0]} | {lines[2][1]} | {lines[2][2]} |  ║\n"
                    f"╚══════════════════╝\n```\n"
                    f"💸 Lost: **{fmt_cash(amount)}**\n"
                    f"💵 New Balance: **{fmt_cash(user['balance'])}**{consolation_txt}{streak_txt}"
                ),
                color=em_lose, timestamp=datetime.now(timezone.utc)
            )

        em.set_footer(text=f"🔴 {bot_name} • Slots")
        upd_lb(ctx.author.id, ctx.author.name)
        await msg.edit(embed=em)

async def setup(bot):
    await bot.add_cog(Slots(bot))
