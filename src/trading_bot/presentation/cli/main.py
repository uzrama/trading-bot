import asyncio
import logging
import multiprocessing

import typer

from trading_bot.main.bootstrap import run_application
from trading_bot.main.runners.discord import DiscordRunner
from trading_bot.main.runners.tracker import TrackerRunner

app = typer.Typer(help="Discord Trade Bot Management Utility", add_completion=False)

logger = logging.getLogger()


@app.command()
def discord():
    """Start the Discord Listener process"""
    asyncio.run(run_application(DiscordRunner, "Discord Listener"))


@app.command()
def tracker():
    """Start the WebSocket Tracker process"""
    asyncio.run(run_application(TrackerRunner, "WebSocket Tracker"))


@app.command()
def all():
    """Start all components concurrently (for local development)"""
    processes = []

    # List of functions to run in separate processes
    targets = [discord, tracker]

    for target in targets:
        process = multiprocessing.Process(target=target)
        process.start()
        processes.append(process)

    try:
        for process in processes:
            process.join()
    except KeyboardInterrupt:
        logger.warning("\nStopping all processes...")
        for process in processes:
            process.terminate()


if __name__ == "__main__":
    app()
