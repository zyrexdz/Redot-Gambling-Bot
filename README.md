# 🔴 Redot BET

A professional rigged gambling Discord bot featuring 10+ interactive games, a real time LTC (Litecoin) economy, and advanced logic.

---

## 🚀 Features

- **10 Games**: From classic Dice and Slots to high stakes Crash and Mines.
- **LTC Integration**: Automated deposits via Litecoin with real time price tracking.
- **Advanced Economy**: Balance management, tipping, daily rewards, and transaction logging.
- **Risk Engine**: Behavioral algorithm that adjusts RTP based on player sentiment and bankroll exposure.
- **Admin Suite**: Surveillance tools, manual credit/debit, and house boost controls.
- **Modular Cog Architecture**: Clean, organized codebase using Discord.py.

---

## 🎮 Casino Games

| Game | Multiplier | Description |
| :--- | :--- | :--- |
| **Dice** | 2x | Roll a 20-sided die and match your pick. |
| **Coinflip** | 2x | High-stakes 50/50 bet on heads or tails. |
| **Slots** | Up to 10x | Classic slot machine with multiple symbols. |
| **RPS** | 2x | Rock, paper, scissors against the bot. |
| **Wheel** | Up to 10x | Spin the wheel for instant multipliers or losses. |
| **High-Low** | 1.8x | Predict if the next card is higher or lower. |
| **Blackjack** | 2x - 2.5x | Beat the dealer to 21 without busting. |
| **Roulette** | Up to 35x | Bet on colors, parity, or specific numbers. |
| **Crash** | ∞x | Cash out before the multiplier crashes! |
| **Mines** | Dynamic | Find diamonds and avoid the hidden bombs. |

---

## 🛠️ Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/zyrexdz/Redot-Gambling-Bot.git
   cd Redot-Gambling-Bot
   ```

2. **Install Dependencies**:
   ```bash
   pip install discord.py qrcode aiohttp pillow
   ```

3. **Configure the Bot**:
   Update the `token` and `ltc_addr` in `bot.py` and `utils.py`.

4. **Run the Bot**:
   ```bash
   python bot.py
   ```

---

## 📁 Repository Structure

```text
.
├── Games/               # Individual game cogs
│   ├── dice.py
│   ├── coinflip.py
│   ├── blackjack.py
│   ├── crash.py
│   └── ...
├── bot.py               # Main entry point & event handling
├── economy.py           # Financial systems & commands
├── utils.py             # Shared logic & API helpers
└── users.json           # Persistent data storage (Auto-generated)
```

---

## 🛡️ Admin Surveillance

Redot BET includes a built-in "Auditor Engine" that logs significant wins, losses, and emotional triggers to private channels for staff review. Use `.hb` to manage house boosts for specific players.

---

**Disclaimer**: This bot is for entertainment purposes only. Always gamble responsibly.

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---
*Built with ❤️ by Zyre*
