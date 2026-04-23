# Automated Crypto Trading Bot 🚀

An advanced, asynchronous cryptocurrency trading bot built in Python. This bot listens to various Discord signal groups, parses trading setups, and executes them automatically across multiple exchange accounts.

Built with **Domain-Driven Design (DDD)** and **Clean Architecture** principles, this project is highly scalable, modular, and easy to extend.

## 🌟 Features

- **Discord Signal Parsing**: Uses a self-bot to listen to specific VIP/signal channels (Elite, Algo, Andre, Haseeb, Voyager).
- **Multi-Account Support**: Trade on multiple exchange accounts simultaneously with different risk settings.
- **Dynamic Position Sizing**: Configure position sizes, leverage, and default stop-losses per account or signal source.
- **Smart Take Profit Management**: Auto-distributes position closing sizes across multiple take-profit (TP) levels.
- **Exchange Integrations**: Currently supports **Bybit** (both Demo/Testnet and Live accounts).
- **Database & State Management**: PostgreSQL with SQLAlchemy ORM and Alembic migrations tracks all orders, positions, and trades.
- **Task Queue**: Powered by Taskiq and Redis for reliable asynchronous job execution.
- **Dependency Injection**: Utilizes `dishka` for clean dependency management and inversion of control.
- **Containerized**: Fully Dockerized for easy deployment and scaling.

## 🛠 Tech Stack

- **Language**: Python 3.14+
- **Package Manager**: `uv`
- **Database**: PostgreSQL (Asyncpg) + SQLAlchemy 2.0 + Alembic
- **Caching/Queues**: Redis + Taskiq
- **Exchanges**: CCXT / Custom Bybit Adapter
- **Discord Integration**: `discord.py-self`
- **Architecture**: Domain-Driven Design (Entities, Use Cases, Repositories, DTOs)
- **CLI**: Typer
- **Config**: Pydantic Settings (YAML)

## 📂 Project Structure

```text
├── configs/            # YAML configuration files (dev, prod)
├── migrations/         # Alembic database migrations
├── src/trading_bot/
│   ├── core/           # Business logic (Domain & Application Layers)
│   ├── infrastructure/ # External services (DB, Discord, Exchanges)
│   ├── main/           # App initialization, Dependency Injection (Dishka)
│   └── presentation/   # CLI entrypoints
├── pyproject.toml      # Project dependencies and metadata
└── docker-compose.yml  # Docker composition for easy local setup
```

## 🚀 Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- Python 3.14+
- [uv](https://github.com/astral-sh/uv) package manager

### 1. Clone & Install

```bash
git clone <your-repo-url>
cd trading-bot
uv sync
```

### 2. Configuration

Copy the example environment file and fill in your secrets (Discord token, Database URL, etc.):

```bash
cp .env.dist .env
```

Configure your trading strategies, accounts, and Discord sources in the YAML config:

```yaml
# configs/config.dev.yaml
accounts:
    account1:
        exchange: bybit
        demo: true
        position_size: 0.05
```

### 3. Database Setup

Start the infrastructure (PostgreSQL, Redis):

```bash
docker compose up -d postgres redis
```

Apply database migrations:

```bash
uv run alembic upgrade head
```

### 4. Running the Bot

You can run the bot natively using the CLI interface:

```bash
uv run trading-bot
```

Or run everything entirely via Docker:

```bash
docker compose up -d
```

## 🧠 Architecture Overview

The project heavily relies on Clean Architecture to separate concerns:
- **Domain**: Contains pure business rules (`Entities`, `Value Objects`, `Exceptions`). Knows nothing about the outside world.
- **Application**: Contains the workflow logic (`Use Cases`, `DTOs`, `Interfaces`). Orchestrates domain objects and external services.
- **Infrastructure**: Concrete implementations of interfaces (`SQLAlchemy Repositories`, `Discord Selfbot Client`, `Bybit Exchange Adapter`).
- **Presentation / Main**: The entry points of the application, responsible for reading configs, building the DI container, and starting the runners.

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## ⚠️ Disclaimer

This bot is provided for educational and research purposes. Cryptocurrency trading carries a high level of risk. Always test your strategies on testnets/demo accounts before using real funds. The authors are not responsible for any financial losses.
