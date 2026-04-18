import discord
from discord.ext import commands
import random
import asyncio
from datetime import datetime, timezone
from utils import *

class CrashView(discord.ui.View):
    def __init__(self, user_id, amount, crash_point):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.amount = amount
        self.crash_point = crash_point
        self.current_mult = 1.00
        self.cashed_out = False
        self.crashed = False
        self.message = None

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user_id

    @discord.ui.button(label="💰 Cash Out!", style=discord.ButtonStyle.success, emoji="💰")
    async def get_out(self, interaction, button):
        if self.crashed or self.cashed_out:
            try:
                await interaction.response.defer()
            except:
                pass
            return

        self.cashed_out = True
        mult = self.current_mult
        winnings = round(self.amount * mult, 2)

        user = fetch_usr(self.user_id)
        user["balance"] += winnings
        user["total_won"] += (winnings - self.amount)
        user["games_won"] += 1
        save_usr(self.user_id, user)
        log_tx(self.user_id, "game_win", winnings, f"Crash — cashed at {mult:.2f}x")
        win_log(self.user_id, (winnings - self.amount), interaction.user.name, member=interaction.user)
        upd_lb(self.user_id, interaction.user.name)

        streak_txt = get_msgs(self.user_id, True)
        em = discord.Embed(
            title="📈 CRASH — Cashed Out! 🎉",
            description=(
                f"```fix\n💰 CASHED OUT AT {mult:.2f}x\n```\n"
                f"💰 Winnings: **{fmt_cash(winnings - self.amount)}**\n"
                f"💵 Balance: **{fmt_cash(user['balance'])}**\n\n"
                f"💥 Crash point was: **{self.crash_point:.2f}x**"
                f"{streak_txt}"
            ),
            color=em_win, timestamp=datetime.now(timezone.utc)
        )
        em.set_footer(text=f"🔴 {bot_name} • Crash")
        await interaction.response.edit_message(embed=em, view=None)
        self.stop()

class Crash(commands.Cog):
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

    @commands.command(name="crash")
    async def go_crash(self, ctx, amount: str = None):
        amount = get_bet(ctx.author.id, amount)
        user, err = self.chk_it(ctx, amount)
        if err:
            return await ctx.send(embed=err)

        user["balance"] -= amount
        user["games_played"] += 1
        
        drift = calc_drift(ctx.author.id, amount, ctx.author.name)
        r = random.random()
        last_cp = user.get("last_crash_point", 1.5)
        
        if drift <= -0.05:
            crash_point = round(random.uniform(1.8, 5.0), 2)
        elif drift > 0.05:
            if r < 0.10:
                crash_point = 1.00
            else:
                crash_point = round(random.uniform(1.01, 1.40), 2)
        else:
            if last_cp < 1.05 and r < 0.90:
                crash_point = round(random.uniform(1.10, 2.50), 2)
            else:
                p = random.random() * 0.96
                natural = 1.0 / (1.0 - p)
                crash_point = round(max(1.01, natural * (1.0 - drift)), 2)

        crash_point = min(99.99, crash_point)
        user["last_crash_point"] = crash_point
        save_usr(ctx.author.id, user)

        view = CrashView(ctx.author.id, amount, crash_point)
        em = discord.Embed(
            title="📈 CRASH — Starting!",
            description=(
                f"```\n📈 Multiplier: 1.00x\n```\n"
                f"💵 Bet: **{fmt_cash(amount)}**\n"
                f"Press **Cash Out** before it crashes!"
            ),
            color=em_info, timestamp=datetime.now(timezone.utc)
        )
        em.set_footer(text=f"🔴 {bot_name} • Crash")
        msg = await ctx.send(embed=em, view=view)
        view.message = msg

        current = 1.00
        while current < crash_point and not view.cashed_out:
            await asyncio.sleep(0.4)
            increment = 0.01 + ((current - 1.00) * 0.08)
            current = round(current + increment, 2)
            current = min(current, crash_point)
            view.current_mult = current

            if view.cashed_out:
                break

            bar_len = min(int(current * 3), 25)
            bar = "█" * bar_len

            em.description = (
                f"```\n📈 {bar} {current:.2f}x\n```\n"
                f"💵 Bet: **{fmt_cash(amount)}**\n"
                f"💰 Potential: **{fmt_cash(amount * current)}**"
            )
            try:
                await msg.edit(embed=em)
            except:
                break

        if not view.cashed_out:
            view.crashed = True
            view.stop()
            user = fetch_usr(ctx.author.id)
            save_usr(ctx.author.id, user)
            log_tx(ctx.author.id, "game_loss", -amount, f"Crash — crashed at {crash_point:.2f}x")
            loss_log(ctx.author.id, amount, ctx.author.name)
            upd_lb(ctx.author.id, ctx.author.name)

            streak_txt = get_msgs(ctx.author.id, False)
            consolation = pity_win(ctx.author.id, amount)
            consolation_txt = f"\n🌟 _Lucky bonus: +{fmt_cash(consolation)}!_" if consolation > 0 else ""

            em = discord.Embed(
                title="📉 CRASH — CRASHED! 💥",
                description=(
                    f"```diff\n- 💥 CRASHED AT {crash_point:.2f}x\n```\n"
                    f"💸 Lost: **{fmt_cash(amount)}**\n"
                    f"💵 Balance: **{fmt_cash(user['balance'])}**"
                    f"{consolation_txt}{streak_txt}"
                ),
                color=em_lose, timestamp=datetime.now(timezone.utc)
            )
            em.set_footer(text=f"🔴 {bot_name} • Crash")
            try:
                await msg.edit(embed=em, view=None)
            except:
                pass

async def setup(bot):
    await bot.add_cog(Crash(bot))
