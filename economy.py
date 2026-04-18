import discord
from discord.ext import commands, tasks
import asyncio
import qrcode
import io
from datetime import datetime, timedelta, timezone
from utils import *

pending_deposits = {}

class DepositCheckView(discord.ui.View):
    def __init__(self, user_id, amount_usd, amount_ltc, expires):
        super().__init__(timeout=1800)
        self.user_id = user_id
        self.amount_usd = amount_usd
        self.amount_ltc = amount_ltc
        self.expires = expires
        self.cancelled = False

    @discord.ui.button(label="Cancel Deposit", style=discord.ButtonStyle.danger, emoji="❌")
    async def stop_it(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Not your deposit.", ephemeral=True)
        self.cancelled = True
        if self.user_id in pending_deposits:
            del pending_deposits[self.user_id]
        em = build_em("❌ Deposit Cancelled", "Your deposit request has been cancelled.", em_lose)
        await interaction.response.edit_message(embed=em, view=None)
        self.stop()

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.chk_deps.start()
        self.do_logs.start()

    def cog_unload(self):
        self.chk_deps.cancel()
        self.do_logs.cancel()

    @tasks.loop(seconds=2)
    async def do_logs(self):
        try:
            if algo_queue:
                algo_channel = self.bot.get_channel(algo_chan)
                if algo_channel:
                    to_send = algo_queue[:5]
                    for em in to_send:
                        await algo_channel.send(embed=em)
                    del algo_queue[:len(to_send)]
                else:
                    algo_queue.clear()

            if dep_queue:
                dep_channel = self.bot.get_channel(deposit_chan)
                if dep_channel:
                    to_send = dep_queue[:5]
                    for em in to_send:
                        await dep_channel.send(embed=em)
                    del dep_queue[:len(to_send)]
                else:
                    dep_queue.clear()
        except Exception:
            pass

    @do_logs.before_loop
    async def before_do_logs(self):
        await self.bot.wait_until_ready()

    @tasks.loop(minutes=2)
    async def chk_deps(self):
        now = datetime.now(timezone.utc)
        to_remove = []
        for uid, dep in list(pending_deposits.items()):
            if now > dep["expires"]:
                to_remove.append(uid)
                try:
                    user = self.bot.get_user(int(uid))
                    if user:
                        em = build_em("⏰ Deposit Expired",
                                        f"Your deposit of **{fmt_cash(dep['amount_usd'])}** "
                                        f"(`{dep['amount_ltc']:.8f} LTC`) has expired.\n"
                                        "Please try again with `.deposit`.",
                                        em_lose)
                        await user.send(embed=em)
                except:
                    pass
                continue

            found, actual = await check_txs(dep["amount_ltc"], dep["since"])
            if found:
                to_remove.append(uid)
                udata = fetch_usr(int(uid))
                udata["balance"] += dep["amount_usd"]
                udata["total_deposited"] += dep["amount_usd"]
                save_usr(int(uid), udata)
                log_tx(int(uid), "deposit", dep["amount_usd"],
                                f"{dep['amount_ltc']:.8f} LTC confirmed")
                
                dep_em = discord.Embed(title="💰 DEPOSIT CONFIRMED", color=em_win)
                dep_em.description = (
                    f"**User:** <@{uid}>\n"
                    f"**Amount:** `${dep['amount_usd']:,.2f}`\n"
                    f"**Crypto:** `{dep['amount_ltc']:.8f} LTC`"
                )
                dep_queue.append(dep_em)

                user_obj = self.bot.get_user(int(uid))
                if user_obj:
                    upd_lb(int(uid), user_obj.name)
                try:
                    user = self.bot.get_user(int(uid))
                    if user:
                        em = build_em("✅ Deposit Confirmed!",
                                        f"**{fmt_cash(dep['amount_usd'])}** has been added to your balance!\n\n"
                                        f"💰 New Balance: **{fmt_cash(udata['balance'])}**",
                                        em_win)
                        await user.send(embed=em)
                except:
                    pass

        for uid in to_remove:
            pending_deposits.pop(uid, None)

    @chk_deps.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    @commands.command(name="deposit")
    async def in_money(self, ctx, amount: float = None):
        if amount is None or amount <= 0:
            return await ctx.send(embed=build_em("❌ Error", "Usage: `.deposit <amount>`\nExample: `.deposit 50`", em_lose))

        if ctx.author.id in pending_deposits:
            return await ctx.send(embed=build_em("⏳ Pending", "You already have a pending deposit. Wait for it to complete or cancel it.", em_gold))

        amount_ltc = await conv_ltc(amount)
        ltc_price = await fetch_ltc()
        expires = datetime.now(timezone.utc) + timedelta(minutes=30)

        pending_deposits[ctx.author.id] = {
            "amount_usd": amount,
            "amount_ltc": amount_ltc,
            "expires": expires,
            "since": datetime.now(timezone.utc).timestamp()
        }

        qr = qrcode.QRCode(version=1, box_size=6, border=2)
        qr.add_data(f"litecoin:{ltc_addr}?amount={amount_ltc}")
        qr.make(fit=True)
        img = qr.make_image(fill_color="#e74c3c", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        em = discord.Embed(
            title=f"🔴 {bot_name} — Deposit",
            description=(
                f"Send exactly **`{amount_ltc:.8f} LTC`** to the address below.\n\n"
                f"```\n{ltc_addr}\n```\n"
                f"💵 Amount: **{fmt_cash(amount)}**\n"
                f"🪙 LTC Amount: **{amount_ltc:.8f} LTC**\n"
                f"📊 LTC Price: **${ltc_price:,.2f}** (live)\n"
                f"⏰ Expires: <t:{int(expires.timestamp())}:R>\n\n"
                "✅ We check for your transaction every **2 minutes**.\n"
                "Your balance will be updated automatically once confirmed."
            ),
            color=em_color,
            timestamp=datetime.now(timezone.utc)
        )
        em.set_thumbnail(url="attachment://qr.png")
        em.set_footer(text=f"🔴 {bot_name} • Deposit")

        view = DepositCheckView(ctx.author.id, amount, amount_ltc, expires)
        file = discord.File(buf, filename="qr.png")

        try:
            await ctx.author.send(embed=em, file=file, view=view)
            await ctx.send(embed=build_em("📩 Check Your DMs!",
                                            f"{ctx.author.mention}, deposit instructions have been sent to your DMs!",
                                            em_info))
        except discord.Forbidden:
            await ctx.send(embed=build_em("❌ Error", "I can't DM you! Please enable DMs.", em_lose))
            pending_deposits.pop(ctx.author.id, None)

    @commands.command(name="withdraw")
    async def out_money(self, ctx):
        em = build_em(
            "💸 Withdrawal",
            "Please open a ticket to withdraw your balance.\n\nA staff member will assist you manually.",
            em_info
        )
        await ctx.send(embed=em)

    @commands.command(name="bal", aliases=["balance"])
    async def check_bal(self, ctx):
        user = fetch_usr(ctx.author.id)
        em = discord.Embed(
            title=f"💰 {ctx.author.display_name}'s Wallet",
            color=em_color,
            timestamp=datetime.now(timezone.utc)
        )
        em.add_field(name="💵 Balance", value=f"**{fmt_cash(user['balance'])}**", inline=True)
        em.add_field(name="📈 Total Deposited", value=fmt_cash(user["total_deposited"]), inline=True)
        em.add_field(name="📉 Total Withdrawn", value=fmt_cash(user["total_withdrawn"]), inline=True)
        em.add_field(name="🏆 Total Won", value=fmt_cash(user["total_won"]), inline=True)
        em.add_field(name="🎮 Games Played", value=str(user["games_played"]), inline=True)
        em.set_thumbnail(url=ctx.author.display_avatar.url)
        em.set_footer(text=f"🔴 {bot_name}")
        await ctx.send(embed=em)

    @commands.command(name="tip")
    async def give_tip(self, ctx, member: discord.Member = None, amount: str = None):
        amount = get_bet(ctx.author.id, amount) if amount else None
        if member is None or amount is None or amount <= 0:
            return await ctx.send(embed=build_em("❌ Error", "Usage: `.tip @user <amount>`\nYou can also use: `all`, `half`, `quarter`", em_lose))
        if member.id == ctx.author.id:
            return await ctx.send(embed=build_em("❌ Error", "You can't tip yourself!", em_lose))

        user = fetch_usr(ctx.author.id)
        if user["balance"] < amount:
            return await ctx.send(embed=build_em("❌ Insufficient Funds",
                f"Your balance: **{fmt_cash(user['balance'])}**", em_lose))

        user["balance"] -= amount
        save_usr(ctx.author.id, user)
        log_tx(ctx.author.id, "tip_sent", -amount, f"To {member.name}")

        target = fetch_usr(member.id)
        target["balance"] += amount
        save_usr(member.id, target)
        log_tx(member.id, "tip_received", amount, f"From {ctx.author.name}")
        upd_lb(ctx.author.id, ctx.author.name)
        upd_lb(member.id, member.name)

        em = build_em("💝 Tip Sent!",
                        f"{ctx.author.mention} tipped {member.mention} **{fmt_cash(amount)}**!\n\n"
                        f"Your Balance: **{fmt_cash(user['balance'])}**",
                        em_win)
        await ctx.send(embed=em)

    @commands.command(name="transactions")
    async def see_tx(self, ctx):
        user = fetch_usr(ctx.author.id)
        txs = user.get("transactions", [])[-10:]
        if not txs:
            return await ctx.send(embed=build_em("📜 Transactions", "No transactions yet.", em_info))

        lines = []
        for tx in reversed(txs):
            emoji = {"deposit": "📥", "withdraw": "📤", "tip_sent": "💝", "tip_received": "💰",
                     "game_win": "🏆", "game_loss": "💸", "admin_give": "🎁", "admin_remove": "🔻"
                     }.get(tx["type"], "📋")
            sign = "+" if tx["amount"] > 0 else ""
            lines.append(f"{emoji} **{tx['type'].replace('_',' ').title()}** — "
                         f"`{sign}{fmt_cash(tx['amount'])}` • {tx.get('details','')}")

        em = build_em(f"📜 {ctx.author.display_name}'s Transactions",
                        "\n".join(lines), em_info)
        await ctx.send(embed=em)

    @commands.command(name="leaderboard", aliases=["lb"])
    async def lb_top(self, ctx):
        lb = read_j(lb_file)
        if not lb:
            return await ctx.send(embed=build_em("🏆 Leaderboard", "No data yet.", em_gold))

        sorted_lb = sorted(lb.items(), key=lambda x: x[1]["balance"], reverse=True)[:10]
        lines = []
        medals = ["🥇", "🥈", "🥉"]
        for i, (uid, data) in enumerate(sorted_lb):
            medal = medals[i] if i < 3 else f"`#{i+1}`"
            lines.append(f"{medal} **{data['username']}** — {fmt_cash(data['balance'])} "
                         f"| Won: {fmt_cash(data['total_won'])} | 🎮 {data['games_played']}")

        em = build_em("🏆 Redot BET Leaderboard — Top 10", "\n".join(lines), em_gold)
        await ctx.send(embed=em)

    @commands.command(name="userinfo")
    async def u_stats(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        user = fetch_usr(member.id)
        wr = (user["games_won"] / user["games_played"] * 100) if user["games_played"] > 0 else 0

        em = discord.Embed(title=f"📊 {member.display_name}'s Profile", color=em_color,
                           timestamp=datetime.now(timezone.utc))
        em.set_thumbnail(url=member.display_avatar.url)
        em.add_field(name="💵 Balance", value=fmt_cash(user["balance"]), inline=True)
        em.add_field(name="📈 Deposited", value=fmt_cash(user["total_deposited"]), inline=True)
        em.add_field(name="📉 Withdrawn", value=fmt_cash(user["total_withdrawn"]), inline=True)
        em.add_field(name="🏆 Won", value=fmt_cash(user["total_won"]), inline=True)
        em.add_field(name="📊 Win Rate", value=f"{wr:.1f}%", inline=True)
        em.add_field(name="🎮 Games", value=f"{user['games_played']} played / {user['games_won']} won", inline=False)
        em.set_footer(text=f"🔴 {bot_name}")
        await ctx.send(embed=em)

    @commands.command(name="spy")
    async def spy_on(self, ctx, member: discord.Member = None):
        if not is_admin(ctx.author):
            return
        
        if member is None:
            return await ctx.send("Usage: `.spy @user`", delete_after=5)

        user = fetch_usr(member.id)
        
        tilt = user.get("tilt_level", 0)
        tilt_status = "Neutral 🧍"
        if tilt >= 3:
            tilt_status = "Tilted / Angry 🤬"
        elif tilt <= -3:
            tilt_status = "Overconfident / Hyped 🤑"
            
        total_won = user.get("total_won", 0)
        total_lost = user.get("total_lost", 0)
        net = total_won - total_lost
        net_str = f"**{fmt_cash(net)}**"
        if net > 0:
            net_str = f"**+{fmt_cash(net)}** (Taking house money)"
        
        rigged = "Yes (Taking profits back)" if net > 0 else "Normal (House edge)"
        if tilt >= 3:
            rigged = "Feeding Pity Wins (To prevent quitting)"
        if check_hb(member.id):
            rigged = "House Boost Active (Winning 💰)"

        em = discord.Embed(title=f"👁️ Surveillance: {member.display_name}", color=0x2c3e50, 
                           timestamp=datetime.now(timezone.utc))
        em.add_field(name="Emotional State", value=tilt_status, inline=True)
        em.add_field(name="Current Streak", value=f"Wins: {user.get('win_streak', 0)} | Losses: {user.get('loss_streak', 0)}", inline=True)
        em.add_field(name="Net Profit", value=net_str, inline=False)
        em.add_field(name="Current Algorithm State", value=rigged, inline=False)
        em.set_footer(text="Admin Surveillance Menu")
        try:
            await ctx.author.send(embed=em)
            await ctx.message.delete()
        except:
            await ctx.send("I cannot DM you.", delete_after=5)

    @commands.command(name="give")
    async def add_money(self, ctx, member: discord.Member = None, *, amount_str: str = None):
        if not is_admin(ctx.author):
            return await ctx.send(embed=build_em("🔒 Access Denied", "You lack permission.", em_lose))
        
        if member is None or amount_str is None:
            return await ctx.send(embed=build_em("❌ Error", "Usage: `.give @user <amount>`", em_lose))

        try:
            amount = float(amount_str)
        except ValueError:
            return await ctx.send(embed=build_em("❌ Error", "Amount must be a valid number.", em_lose))

        if amount <= 0:
            return await ctx.send(embed=build_em("❌ Error", "Amount must be greater than 0.", em_lose))

        user = fetch_usr(member.id)
        user["balance"] += amount
        save_usr(member.id, user)
        log_tx(member.id, "admin_give", amount, f"By {ctx.author.name}")
        upd_lb(member.id, member.name)

        audit_em = discord.Embed(title="🎁 MANUAL CREDIT", color=0x3498db)
        audit_em.description = (
            f"**To:** <@{member.id}>\n"
            f"**Amount:** `{fmt_cash(amount)}`\n"
            f"**By Admin:** {ctx.author.mention}"
        )
        dep_queue.append(audit_em)

        em = build_em("🎁 Balance Given",
                        f"**{fmt_cash(amount)}** added to {member.mention}\n"
                        f"New Balance: **{fmt_cash(user['balance'])}**",
                        em_win)
        await ctx.send(embed=em)

    @commands.command(name="remove")
    async def del_money(self, ctx, member: discord.Member = None, *, amount_str: str = None):
        if not is_admin(ctx.author):
            return await ctx.send(embed=build_em("🔒 Access Denied", "You lack permission.", em_lose))
        
        if member is None or amount_str is None:
            return await ctx.send(embed=build_em("❌ Error", "Usage: `.remove @user <amount>`\nYou can also use: `all`", em_lose))

        amount = get_bet(member.id, amount_str)
        if amount is None or amount <= 0:
            return await ctx.send(embed=build_em("❌ Error", "Usage: `.remove @user <amount>`\nYou can also use: `all`", em_lose))

        user = fetch_usr(member.id)
        user["balance"] = max(0, user["balance"] - amount)
        save_usr(member.id, user)
        log_tx(member.id, "admin_remove", -amount, f"By {ctx.author.name}")
        upd_lb(member.id, member.name)

        audit_em = discord.Embed(title="🔻 MANUAL DEBIT", color=0xe74c3c)
        audit_em.description = (
            f"**From:** <@{member.id}>\n"
            f"**Amount:** `{fmt_cash(amount)}`\n"
            f"**By Admin:** {ctx.author.mention}"
        )
        dep_queue.append(audit_em)

        em = build_em("🔻 Balance Removed",
                        f"**{fmt_cash(amount)}** removed from {member.mention}\n"
                        f"New Balance: **{fmt_cash(user['balance'])}**",
                        em_lose)
        await ctx.send(embed=em)

async def setup(bot):
    await bot.add_cog(Economy(bot))
