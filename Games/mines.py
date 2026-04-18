import discord
from discord.ext import commands
import random
import asyncio
from datetime import datetime, timezone
from utils import *

class MinesGame:
    def __init__(self, user_id, amount, mines_count, grid):
        self.user_id = user_id
        self.amount = amount
        self.mines_count = mines_count
        self.grid = grid
        self.revealed = [False] * 20
        self.safe_found = 0
        self.total_safe = 20 - mines_count
        self.done = False
        self.message = None

    @property
    def multiplier(self):
        if self.safe_found == 0:
            return 1.0
        
        def combos(n, k):
            if k < 0 or k > n:
                return 0
            if k == 0 or k == n:
                return 1
            if k > n // 2:
                k = n - k
            
            num = 1
            for i in range(k):
                num = num * (n - i) // (i + 1)
            return num

        total_c = combos(20, self.safe_found)
        safe_c = combos(20 - self.mines_count, self.safe_found)
        
        if safe_c == 0:
            return 1.0
            
        raw_mult = total_c / safe_c
        return round(max(raw_mult * 0.96, 1.01), 2)

    @property
    def check_pot(self):
        return round(self.amount * self.multiplier, 2)

    def draw_em(self, result=None, hit_mine=None):
        grid_str = ""
        for row in range(4):
            for col in range(5):
                idx = row * 5 + col
                if self.done:
                    if self.grid[idx]:
                        grid_str += "💥 " if idx == hit_mine else "💣 "
                    else:
                        grid_str += "💎 "
                else:
                    if self.revealed[idx]:
                        grid_str += "💎 "
                    else:
                        grid_str += "⬛ "
            grid_str += "\n"

        if result == "mine":
            title = "💣 MINES — BOOM! 💥"
            color = em_lose
            desc = (f"{grid_str}\n"
                    f"💥 You hit a mine!\n"
                    f"💸 Lost: **{fmt_cash(self.amount)}**")
        elif result == "cashout":
            title = "💎 MINES — Cashed Out! 🎉"
            color = em_win
            desc = (f"{grid_str}\n"
                    f"💎 Tiles found: **{self.safe_found}**\n"
                    f"📈 Multiplier: **{self.multiplier:.2f}x**\n"
                    f"💰 Winnings: **{fmt_cash(self.check_pot - self.amount)}**")
        else:
            title = "💣 MINES"
            color = em_info
            desc = (f"{grid_str}\n"
                    f"💣 Mines: **{self.mines_count}** | 💎 Found: **{self.safe_found}**\n"
                    f"📈 Multiplier: **{self.multiplier:.2f}x**\n"
                    f"💰 Potential: **{fmt_cash(self.check_pot)}**\n"
                    f"💵 Bet: **{fmt_cash(self.amount)}**")

        em = discord.Embed(title=title, description=desc, color=color, timestamp=datetime.now(timezone.utc))
        em.set_footer(text=f"🔴 {bot_name} • Mines")
        return em

class MinesButton(discord.ui.Button):
    def __init__(self, index, game, cog):
        row_num = index // 5
        super().__init__(style=discord.ButtonStyle.secondary, label="⬛",
                         row=row_num, custom_id=f"mines_{game.user_id}_{index}")
        self.index = index
        self.game = game
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.game.user_id:
            return await interaction.response.send_message("Not your game!", ephemeral=True)
        if self.game.done or self.game.revealed[self.index]:
            return

        drift = calc_drift(self.game.user_id, self.game.amount, interaction.user.name)
        
        if drift > 0.05 and not self.game.grid[self.index] and not check_hb(self.game.user_id):
            if random.random() < (drift * 2):
                mine_idx = random.choice([i for i, v in enumerate(self.game.grid) if v])
                self.game.grid[mine_idx] = False
                self.game.grid[self.index] = True

        if self.game.grid[self.index]:
            self.game.done = True
            self.game.revealed[self.index] = True
            user = fetch_usr(self.game.user_id)
            save_usr(self.game.user_id, user)
            log_tx(self.game.user_id, "game_loss", -self.game.amount,
                            f"Mines — hit mine at tile {self.index+1}")
            loss_log(self.game.user_id, self.game.amount, interaction.user.name)
            upd_lb(self.game.user_id, interaction.user.name)
            self.cog.active_mines.pop(self.game.user_id, None)
            streak_txt = get_msgs(self.game.user_id, False)
            consolation = pity_win(self.game.user_id, self.game.amount)
            consolation_txt = f"\n🌟 _Lucky bonus: +{fmt_cash(consolation)}!_" if consolation > 0 else ""

            em = self.game.draw_em(result="mine", hit_mine=self.index)
            em.add_field(name="Balance", value=f"**{fmt_cash(user['balance'])}**{consolation_txt}{streak_txt}")
            await interaction.response.edit_message(embed=em, view=None)
        else:
            self.game.revealed[self.index] = True
            self.game.safe_found += 1
            self.style = discord.ButtonStyle.success
            self.label = "💎"
            self.disabled = True

            em = self.game.draw_em()
            await interaction.response.edit_message(embed=em, view=self.view)

class MinesCashoutButton(discord.ui.Button):
    def __init__(self, game, cog):
        super().__init__(style=discord.ButtonStyle.success, label="💰 Cash Out",
                         row=4, custom_id=f"mines_cashout_{game.user_id}")
        self.game = game
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.game.user_id:
            return await interaction.response.send_message("Not your game!", ephemeral=True)
        if self.game.done or self.game.safe_found == 0:
            return await interaction.response.send_message("Reveal at least one tile first!", ephemeral=True)

        self.game.done = True
        winnings = self.game.check_pot

        user = fetch_usr(self.game.user_id)
        user["balance"] += winnings
        user["total_won"] += (winnings - self.game.amount)
        user["games_won"] += 1
        save_usr(self.game.user_id, user)
        log_tx(self.game.user_id, "game_win", winnings,
                        f"Mines — {self.game.safe_found} tiles, {self.game.multiplier:.2f}x")
        win_log(self.game.user_id, (winnings - self.game.amount), interaction.user.name, member=interaction.user)
        upd_lb(self.game.user_id, interaction.user.name)
        self.cog.active_mines.pop(self.game.user_id, None)
        streak_txt = get_msgs(self.game.user_id, True)

        em = self.game.draw_em(result="cashout")
        em.add_field(name="Balance", value=f"**{fmt_cash(user['balance'])}**{streak_txt}")
        await interaction.response.edit_message(embed=em, view=None)

class MinesView(discord.ui.View):
    def __init__(self, game, cog):
        super().__init__(timeout=300)
        self.game = game
        self.cog = cog
        self.message = None
        for i in range(20):
            self.add_item(MinesButton(i, game, cog))
        self.add_item(MinesCashoutButton(game, cog))

    async def on_timeout(self):
        if not self.game.done:
            self.game.done = True
            user = fetch_usr(self.game.user_id)
            save_usr(self.game.user_id, user)
            log_tx(self.game.user_id, "game_loss", -self.game.amount, "Mines — timeout")
            self.cog.active_mines.pop(self.game.user_id, None)
            if self.message:
                em = build_em("⏰ Mines Timed Out",
                                f"You lost **{fmt_cash(self.game.amount)}**.",
                                em_lose)
                try:
                    await self.message.edit(embed=em, view=None)
                except:
                    pass

class Mines(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_mines = {}

    def chk_it(self, ctx, amount):
        if amount is None or amount <= 0:
            return None, build_em("❌ Error", "Bet must be greater than $0.", em_lose)
        user = fetch_usr(ctx.author.id)
        if user["balance"] < amount:
            return None, build_em("❌ Insufficient Funds",
                                    f"Your balance: **{fmt_cash(user['balance'])}**", em_lose)
        return user, None

    @commands.command(name="mines")
    async def play_mines(self, ctx, amount: str = None, mines_count: int = None):
        amount = get_bet(ctx.author.id, amount)
        user, err = self.chk_it(ctx, amount)
        if err:
            return await ctx.send(embed=err)

        if mines_count is None or mines_count < 1 or mines_count > 19:
            return await ctx.send(embed=build_em("❌ Error",
                "Usage: `.mines <amount> <mines:1-19>`\nExample: `.mines 50 5`", em_lose))

        if ctx.author.id in self.active_mines:
            return await ctx.send(embed=build_em("❌ Active Game",
                "You already have an active mines game. Finish it first!", em_lose))

        user["balance"] -= amount
        user["games_played"] += 1
        save_usr(ctx.author.id, user)

        actual_mines = mines_count
        grid = [False] * 20
        mine_positions = random.sample(range(20), actual_mines)
        for pos in mine_positions:
            grid[pos] = True

        game = MinesGame(ctx.author.id, amount, mines_count, grid)
        self.active_mines[ctx.author.id] = game

        view = MinesView(game, self)
        em = game.draw_em()
        msg = await ctx.send(embed=em, view=view)
        game.message = msg
        view.message = msg

async def setup(bot):
    await bot.add_cog(Mines(bot))
