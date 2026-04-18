import discord
from discord.ext import commands
import random
import asyncio
from datetime import datetime, timezone
from utils import *

class RPS(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def chk_chk(self, ctx, amount):
        if amount is None or amount <= 0:
            return None, build_em("❌ Error", "Bet must be greater than $0.", em_lose)
        user = fetch_usr(ctx.author.id)
        if user["balance"] < amount:
            return None, build_em("❌ Insufficient Funds",
                                    f"Your balance: **{fmt_cash(user['balance'])}**", em_lose)
        return user, None

    @commands.command(name="rps")
    async def play_rps(self, ctx, amount: str = None, move: str = None):
        amount = get_bet(ctx.author.id, amount)
        user, err = self.chk_chk(ctx, amount)
        if err:
            return await ctx.send(embed=err)
        if move is None or move.lower() not in ("rock", "paper", "scissors"):
            return await ctx.send(embed=build_em("❌ Error",
                "Usage: `.rps <amount> <rock/paper/scissors>`", em_lose))

        move = move.lower()
        emojis = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
        moves = ["rock", "paper", "scissors"]
        wins = {"rock": "scissors", "paper": "rock", "scissors": "paper"}
        drift = calc_drift(ctx.author.id, amount, ctx.author.name)
        losses = {"rock": "paper", "paper": "scissors", "scissors": "rock"} 
        
        if check_hb(ctx.author.id) or drift <= -0.05:
            bot_move = random.choice([m for m in moves if wins[m] == move])
        elif drift >= 0.04:
            if random.random() < (0.33 + drift):
                bot_move = losses[move]
            else:
                bot_move = random.choice(moves)
        else:
            bot_move = random.choice(moves)

        user["balance"] -= amount
        user["games_played"] += 1

        anim_em = build_em("✊ Rock Paper Scissors", "```\n✊ ✋ ✌️  Shooting...\n```", em_info)
        msg = await ctx.send(embed=anim_em)

        shoot_frames = ["🤜 Rock...", "🖐️ Paper...", "✌️ Scissors...", "💥 SHOOT!"]
        for f in shoot_frames:
            anim_em.description = f"```\n{f}\n```"
            await msg.edit(embed=anim_em)
            await asyncio.sleep(0.5)

        wins = {"rock": "scissors", "paper": "rock", "scissors": "paper"}
        if move == bot_move:
            user["balance"] += amount
            save_usr(ctx.author.id, user)
            log_tx(ctx.author.id, "game_tie", amount, f"RPS — {move} vs {bot_move}")
            em = discord.Embed(
                title="🤝 RPS — It's a Tie!",
                description=(
                    f"You: {emojis[move]} **{move.upper()}**\n"
                    f"Bot: {emojis[bot_move]} **{bot_move.upper()}**\n\n"
                    f"💵 Bet returned: **{fmt_cash(amount)}**\n"
                    f"💵 Balance: **{fmt_cash(user['balance'])}**"
                ),
                color=em_gold, timestamp=datetime.now(timezone.utc)
            )
        elif wins[move] == bot_move:
            winnings = amount * 2
            user["balance"] += winnings
            user["total_won"] += (winnings - amount)
            user["games_won"] += 1
            save_usr(ctx.author.id, user)
            log_tx(ctx.author.id, "game_win", winnings, f"RPS — {move} vs {bot_move}")
            win_log(ctx.author.id, (winnings - amount), ctx.author.name, member=ctx.author)
            streak_txt = get_msgs(ctx.author.id, True)

            em = discord.Embed(
                title="✊ RPS — YOU WIN! 🎉",
                description=(
                    f"You: {emojis[move]} **{move.upper()}**\n"
                    f"Bot: {emojis[bot_move]} **{bot_move.upper()}**\n\n"
                    f"💰 Winnings: **{fmt_cash(winnings - amount)}**\n"
                    f"💵 Balance: **{fmt_cash(user['balance'])}**{streak_txt}"
                ),
                color=em_win, timestamp=datetime.now(timezone.utc)
            )
        else:
            save_usr(ctx.author.id, user)
            log_tx(ctx.author.id, "game_loss", -amount, f"RPS — {move} vs {bot_move}")
            loss_log(ctx.author.id, amount, ctx.author.name)
            streak_txt = get_msgs(ctx.author.id, False)
            consolation = pity_win(ctx.author.id, amount)
            consolation_txt = f"\n🌟 _Lucky bonus: +{fmt_cash(consolation)}!_" if consolation > 0 else ""

            em = discord.Embed(
                title="✊ RPS — You Lost",
                description=(
                    f"You: {emojis[move]} **{move.upper()}**\n"
                    f"Bot: {emojis[bot_move]} **{bot_move.upper()}**\n\n"
                    f"💸 Lost: **{fmt_cash(amount)}**\n"
                    f"💵 Balance: **{fmt_cash(user['balance'])}**{consolation_txt}{streak_txt}"
                ),
                color=em_lose, timestamp=datetime.now(timezone.utc)
            )

        em.set_footer(text=f"🔴 {bot_name} • RPS")
        upd_lb(ctx.author.id, ctx.author.name)
        await msg.edit(embed=em)

async def setup(bot):
    await bot.add_cog(RPS(bot))
