import discord
from discord.ext import commands
import random
import asyncio
from datetime import datetime, timezone
from utils import *

class HighLowView(discord.ui.View):
    def __init__(self, user_id, amount, card1, user_data):
        super().__init__(timeout=30)
        self.user_id = user_id
        self.amount = amount
        self.card1 = card1
        self.user_data = user_data
        self.message = None

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user_id

    async def on_timeout(self):
        if self.message:
            em = build_em("⏰ Timed Out", f"High-Low timed out. You lost **{fmt_cash(self.amount)}**.", em_lose)
            save_usr(self.user_id, self.user_data)
            log_tx(self.user_id, "game_loss", -self.amount, "HighLow — timeout")
            loss_log(self.user_id, self.amount, "User")
            await self.message.edit(embed=em, view=None)

    async def chk_it(self, interaction, guess):
        boosted = check_hb(self.user_id)
        if boosted:
            card2 = random.randint(1, 13)
        elif guess == "higher":
            pool = list(range(1, 14))
            weights = [8 if c <= self.card1 else 1 for c in pool]
            card2 = random.choices(pool, weights=weights, k=1)[0]
        else:
            pool = list(range(1, 14))
            weights = [8 if c >= self.card1 else 1 for c in pool]
            card2 = random.choices(pool, weights=weights, k=1)[0]
        card_names = {1: "A", 11: "J", 12: "Q", 13: "K"}
        c1n = card_names.get(self.card1, str(self.card1))
        c2n = card_names.get(card2, str(card2))

        correct = (guess == "higher" and card2 > self.card1) or \
                  (guess == "lower" and card2 < self.card1)

        user = fetch_usr(self.user_id)
        if card2 == self.card1:
            user["balance"] += self.amount
            save_usr(self.user_id, user)
            em = build_em("🃏 HIGH-LOW — Push!",
                            f"Card 1: **{c1n}** → Card 2: **{c2n}**\nSame card! Bet returned.\n"
                            f"💵 Balance: **{fmt_cash(user['balance'])}**", em_gold)
        elif correct:
            winnings = self.amount * 1.8
            user["balance"] += winnings
            user["total_won"] += (winnings - self.amount)
            user["games_won"] += 1
            save_usr(self.user_id, user)
            log_tx(self.user_id, "game_win", winnings, f"HighLow — {c1n}→{c2n}")
            win_log(self.user_id, (winnings - self.amount), interaction.user.name, member=interaction.user)
            streak_txt = get_msgs(self.user_id, True)
            em = build_em("🃏 HIGH-LOW — YOU WIN! 🎉",
                            f"Card 1: **{c1n}** → Card 2: **{c2n}**\n"
                            f"💰 Winnings: **{fmt_cash(winnings - amount)}**\n"
                            f"💵 Balance: **{fmt_cash(user['balance'])}**{streak_txt}", em_win)
        else:
            save_usr(self.user_id, user)
            log_tx(self.user_id, "game_loss", -self.amount, f"HighLow — {c1n}→{c2n}")
            loss_log(self.user_id, self.amount, interaction.user.name)
            streak_txt = get_msgs(self.user_id, False)
            consolation = pity_win(self.user_id, self.amount)
            consolation_txt = f"\n🌟 _Lucky bonus: +{fmt_cash(consolation)}!_" if consolation > 0 else ""
            em = build_em("🃏 HIGH-LOW — You Lost",
                            f"Card 1: **{c1n}** → Card 2: **{c2n}**\n"
                            f"💸 Lost: **{fmt_cash(self.amount)}**\n"
                            f"💵 Balance: **{fmt_cash(user['balance'])}**{consolation_txt}{streak_txt}", em_lose)

        upd_lb(self.user_id, interaction.user.name)
        await interaction.response.edit_message(embed=em, view=None)
        self.stop()

    @discord.ui.button(label="⬆️ Higher", style=discord.ButtonStyle.green)
    async def up_btn(self, interaction, button):
        await self.chk_it(interaction, "higher")

    @discord.ui.button(label="⬇️ Lower", style=discord.ButtonStyle.red)
    async def down_btn(self, interaction, button):
        await self.chk_it(interaction, "lower")

class HighLow(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def money_chk(self, ctx, amount):
        if amount is None or amount <= 0:
            return None, build_em("❌ Error", "Bet must be greater than $0.", em_lose)
        user = fetch_usr(ctx.author.id)
        if user["balance"] < amount:
            return None, build_em("❌ Insufficient Funds",
                                    f"Your balance: **{fmt_cash(user['balance'])}**", em_lose)
        return user, None

    @commands.command(name="highlow", aliases=["hl"])
    async def play_hl(self, ctx, amount: str = None):
        amount = get_bet(ctx.author.id, amount)
        user, err = self.money_chk(ctx, amount)
        if err:
            return await ctx.send(embed=err)

        user["balance"] -= amount
        user["games_played"] += 1
        save_usr(ctx.author.id, user)

        card1 = random.randint(1, 13)
        card_names = {1: "A", 11: "J", 12: "Q", 13: "K"}
        c1n = card_names.get(card1, str(card1))

        em = build_em("🃏 HIGH-LOW — Starting",
                        f"First card: **{c1n}**\n\n"
                        f"Will the next card be higher or lower?\n"
                        f"💵 Bet: **{fmt_cash(amount)}**", em_info)
        
        view = HighLowView(ctx.author.id, amount, card1, user)
        msg = await ctx.send(embed=em, view=view)
        view.message = msg

async def setup(bot):
    await bot.add_cog(HighLow(bot))
