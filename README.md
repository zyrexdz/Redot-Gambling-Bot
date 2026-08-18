# Redot BET - Discord Casino & Economy Bot

A fully featured, modular Discord gambling and economy bot built with **discord.py**. Features 10+ interactive games, real-time Litecoin (LTC) deposit automation, dynamic player risk management, and persistent balance tracking.

---

## Features

- **10+ Interactive Games**: High-Low, Blackjack, Roulette, Crash, Mines, Slots, Dice, Coinflip, RPS, and Wheel.
- **Crypto & Economy Engine**: Automated LTC deposits with QR code generation, real-time price feeds, daily rewards, and user-to-user transfers.
- **House Risk Controls**: Configurable Return to Player (RTP) algorithm and administrative house boost switches.
- **Role Tier Progression**: Automatic role assignment based on total wager volume ($10+ Bronze up to $10,000+ Legend).
- **Deployment Ready**: Out-of-the-box Docker & Docker Compose support with persistent volumes, plus 1-click install scripts for Linux/macOS and Windows.

---

## Game Catalog

| Game | Multiplier | Rules / Mechanics |
| :--- | :--- | :--- |
| **Blackjack** | `2x - 2.5x` | Standard dealer rules (stand on 17), double down, hit, stand. |
| **Crash** | `Dynamic (1x - ∞)` | Cash out before the multiplier randomly crashes. |
| **Mines** | `Dynamic` | Reveal diamonds on a 5x5 grid while dodging hidden explosives. |
| **Roulette** | `Up to 36x` | Bet on red/black, even/odd, columns, or exact numbers. |
| **Slots** | `Up to 10x` | 3-reel animated slot machine with bonus payouts. |
| **High-Low** | `1.8x` | Guess whether the next drawn card is higher or lower. |
| **Dice** | `2x` | Roll against the house with custom prediction thresholds. |
| **Coinflip** | `2x` | Classic 50/50 flip with animation. |
| **Wheel** | `Up to 10x` | Multi-segment wheel spin with instant payouts. |
| **RPS** | `2x` | Rock, Paper, Scissors with tie refunds. |

---

## Installation & Setup

### Prerequisites
- Python 3.10+ or Docker & Docker Compose
- Discord Bot Token with **Message Content Intent** and **Server Members Intent** enabled in the [Discord Developer Portal](https://discord.com/developers/applications).

---

### Option A: Docker Compose (Recommended)

1. Clone the repository:
   ```bash
   git clone https://github.com/zyrexdz/Redot-Gambling-Bot.git
   cd Redot-Gambling-Bot
   ```

2. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env and enter your DISCORD_TOKEN and Channel IDs
   ```

3. Launch container:
   ```bash
   docker compose up -d
   ```

---

### Option B: Local Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/zyrexdz/Redot-Gambling-Bot.git
   cd Redot-Gambling-Bot
   ```

2. **Automated Setup Script**:
   - **Linux / macOS**:
     ```bash
     chmod +x setup.sh
     ./setup.sh
     ```
   - **Windows**:
     ```cmd
     setup.bat
     ```

3. **Manual Setup**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   cp .env.example .env      # On Windows: copy .env.example .env
   ```

4. **Start the Bot**:
   ```bash
   python bot.py
   ```

---

## Configuration Variables (`.env`)

| Variable | Description |
| :--- | :--- |
| `DISCORD_TOKEN` | Discord Bot authentication token |
| `ADMIN_ROLE_ID` | Discord Role ID authorized to execute admin commands |
| `OWNER_ID` | Discord User ID of the primary owner |
| `GAMBLE_CHANNEL_ID` | Channel ID restricted for game interactions |
| `ALGO_CHANNEL_ID` | Channel ID for system logs and house performance monitoring |
| `DEPOSIT_CHANNEL_ID` | Channel ID for crypto transaction receipts |
| `LTC_ADDRESS` | Litecoin receiving address for automated deposits |

---

## Discord Bot Permissions

When generating your bot invite URL in the Developer Portal, grant the following permissions:
- `Send Messages` & `Embed Links`
- `Attach Files` (for QR codes and generated receipts)
- `Manage Messages` (for cleaning command spam)
- `Read Message History`
- `Manage Roles` (if using wager-tier role assignments)

---

## License

Distributed under the [MIT License](LICENSE).
