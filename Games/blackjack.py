import discord
from discord.ext import commands
import random
import asyncio
from datetime import datetime, timezone
from utils import *

suits = ["♠️", "♥️", "♣️", "♦️"]
card_vals = {
    "A": 11, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6,
    "7": 7, "8": 8, "9": 9, "10": 10, "J": 10, "Q": 10, "K": 10
}

def get_deck(rig_factor=0.0):
    deck = []
    for suit in suits:
        for card in card_vals:
            deck.append((card, suit))
            
    if rig_factor > 0.03:
        extra = int(10 * rig_factor)
        for _ in range(extra):
            deck.append((random.choice(["10", "J", "Q", "K"]), random.choice(suits)))
    elif rig_factor < -0.03:
        extra = int(10 * abs(rig_factor))
        for _ in range(extra):
            deck.append(("A", random.choice(suits)))
            
    random.shuffle(deck)
    return deck

def sum_it(hand):
    value = sum(card_vals[c[0]] for c in hand)
    aces = sum(1 for c in hand if c[0] == "A")
    while value > 21 and aces:
        value -= 10
        aces -= 1
    return value

def show_it(hand, hide_second=False):
    if hide_second and len(hand) >= 2:
        return f"{hand[0][0]}{hand[0][1]}  ❓"
    return "  ".join(f"{c[0]}{c[1]}" for c in hand)

def bj_em(player_hand, dealer_hand, amount, hide_dealer=True, result=None, balance=0):
    p_val = sum_it(player_hand)
    d_val = sum_it(dealer_hand) if not hide_dealer else "?"

    if result == "win":
        title = "🃏 BLACKJACK — YOU WIN! 🎉"
        color = em_win
    elif result == "lose":
        title = "🃏 BLACKJACK — Dealer Wins"
        color = em_lose
    elif result == "push":
        title = "🃏 BLACKJACK — Push!"
        color = em_gold
    elif result == "blackjack":
        title = "🃏 BLACKJACK! 🎉🎉"
        color = em_win
    elif result == "bust":
        title = "🃏 BUST! 💥"
        color = em_lose
    else:
        title = "🃏 BLACKJACK"
        color = em_info

    desc = (
        f"**Dealer's Hand** ({d_val})\n"
        f"```\n{show_it(dealer_hand, hide_dealer)}\n```\n"
        f"**Your Hand** ({p_val})\n"
        f"```\n{show_it(player_hand)}\n```\n"
        f"💵 Bet: **{fmt_cash(amount)}**"
    )

    if result:
        desc += f"\n💰 Balance: **{fmt_cash(balance)}**"

    em = discord.Embed(title=title, description=desc, color=color, timestamp=datetime.now(timezone.utc))
    em.set_footer(text=f"🔴 {bot_name} • Blackjack")
    return em

class BlackjackView(discord.ui.View):
    def __init__(self, user_id, amount, deck, player_hand, dealer_hand):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.amount = amount
        self.deck = deck
        self.player_hand = player_hand
        self.dealer_hand = dealer_hand
        self.message = None
        self.done = False

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user_id

    async def on_timeout(self):
        if not self.done and self.message:
            user = fetch_usr(self.user_id)
            user["total_lost"] += self.amount
            save_usr(self.user_id, user)
            log_tx(self.user_id, "game_loss", -self.amount, "Blackjack — timeout")
            em = bj_em(self.player_hand, self.dealer_hand, self.amount,
                                 hide_dealer=False, result="lose", balance=user["balance"])
            await self.message.edit(embed=em, view=None)

    async def end_game(self, interaction, result):
        self.done = True
        user = fetch_usr(self.user_id)

        if result == "win" or result == "blackjack":
            mult = 2.5 if result == "blackjack" else 2
            winnings = self.amount * mult
            user["balance"] += winnings
            user["total_won"] += (winnings - self.amount)
            user["games_won"] += 1
            save_usr(self.user_id, user)
            log_tx(self.user_id, "game_win", winnings, f"Blackjack — {result}")
            win_log(self.user_id, (winnings - self.amount), interaction.user.name, member=interaction.user)
            streak_txt = get_msgs(self.user_id, True)

        elif result == "push":
            user["balance"] += self.amount
            save_usr(self.user_id, user)
            streak_txt = ""

        else:
            save_usr(self.user_id, user)
            log_tx(self.user_id, "game_loss", -self.amount, f"Blackjack — {result}")
            loss_log(self.user_id, self.amount, interaction.user.name)
            streak_txt = get_msgs(self.user_id, False)
            consolation = pity_win(self.user_id, self.amount)
            if consolation > 0:
                streak_txt = f"\n🌟 _Lucky bonus: +{fmt_cash(consolation)}!_" + streak_txt

        upd_lb(self.user_id, interaction.user.name)
        em = bj_em(self.player_hand, self.dealer_hand, self.amount,
                             hide_dealer=False, result=result, balance=user["balance"])
        em.description += streak_txt
        await interaction.response.edit_message(embed=em, view=None)
        self.stop()

    async def bot_turn(self, interaction):
        while sum_it(self.dealer_hand) < 17:
            self.dealer_hand.append(self.deck.pop())

        pv = sum_it(self.player_hand)
        dv = sum_it(self.dealer_hand)

        if dv > 21 or pv > dv:
            await self.end_game(interaction, "win")
        elif pv == dv:
            await self.end_game(interaction, "push")
        else:
            await self.end_game(interaction, "lose")

    @discord.ui.button(label="Hit 🃏", style=discord.ButtonStyle.primary)
    async def hit_me(self, interaction, button):
        self.player_hand.append(self.deck.pop())
        pv = sum_it(self.player_hand)

        if pv > 21:
            await self.end_game(interaction, "bust")
        elif pv == 21:
            await self.bot_turn(interaction)
        else:
            em = bj_em(self.player_hand, self.dealer_hand, self.amount)
            await interaction.response.edit_message(embed=em, view=self)

    @discord.ui.button(label="Stand ✋", style=discord.ButtonStyle.secondary)
    async def stay_put(self, interaction, button):
        await self.bot_turn(interaction)

class Blackjack(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def chk_bal(self, ctx, amount):
        if amount is None or amount <= 0:
            return None, build_em("❌ Error", "Bet must be greater than $0.", em_lose)
        user = fetch_usr(ctx.author.id)
        if user["balance"] < amount:
            return None, build_em("❌ Insufficient Funds",
                                    f"Your balance: **{fmt_cash(user['balance'])}**", em_lose)
        return user, None

    @commands.command(name="blackjack", aliases=["bj"])
    async def play_bj(self, ctx, amount: str = None):
        amount = get_bet(ctx.author.id, amount)
        user, err = self.chk_bal(ctx, amount)
        if err:
            return await ctx.send(embed=err)

        user["balance"] -= amount
        user["games_played"] += 1
        save_usr(ctx.author.id, user)

        rig_factor = calc_drift(ctx.author.id, amount, ctx.author.name)
        deck = get_deck(rig_factor=rig_factor)
        player = [deck.pop(), deck.pop()]
        dealer = [deck.pop(), deck.pop()]

        if sum_it(player) == 21:
            user = fetch_usr(ctx.author.id)
            winnings = amount * 2.5
            user["balance"] += winnings
            user["total_won"] += (winnings - amount)
            user["games_won"] += 1
            save_usr(ctx.author.id, user)
            log_tx(ctx.author.id, "game_win", winnings, "Blackjack — natural 21")
            win_log(ctx.author.id, (winnings - amount), ctx.author.name, member=ctx.author)
            upd_lb(ctx.author.id, ctx.author.name)
            em = bj_em(player, dealer, amount, hide_dealer=False,
                                 result="blackjack", balance=user["balance"])
            return await ctx.send(embed=em)

        view = BlackjackView(ctx.author.id, amount, deck, player, dealer)
        em = bj_em(player, dealer, amount)
        msg = await ctx.send(embed=em, view=view)
        view.message = msg

async def setup(bot):
    await bot.add_cog(Blackjack(bot))
