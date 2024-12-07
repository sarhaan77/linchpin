import asyncio
import logging

import discord
from fastapi import HTTPException

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)


async def send_msg(channel_id: int, message: str):
    channel = bot.get_channel(channel_id)
    await channel.send(message)


async def send_embed(
    channel_id: int, embed_title: str, embed_description: str, embed_url: str
):
    channel = bot.get_channel(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    embed = discord.Embed(
        title=embed_title,
        url=embed_url,
        description=embed_description,
        color=0xFF23A7,
    )
    await channel.send(embed=embed)


async def send_log(message: str, level: int):
    CHANNEL_ID = 1314854224797896715
    channel = bot.get_channel(CHANNEL_ID)

    if level == logging.ERROR:
        # Create an embed for error messages with red color
        embed = discord.Embed(
            title="🚨 Error Log",
            description=f"```diff\n{message}\n```",  # Using Discord markdown for red text
            color=0xFF0000,  # Red color
        )
        await channel.send(embed=embed)
    else:
        await channel.send(message, suppress_embeds=True)


class DiscordLogger(logging.Logger):
    def _log(
        self,
        level,
        msg,
        args,
        exc_info=None,
        extra=None,
        stack_info=False,
        stacklevel=1,
        discord=True,
    ):
        # First, do normal console logging
        super()._log(level, msg, args, exc_info, extra, stack_info, stacklevel)

        # If discord flag is True, send to Discord
        if discord:
            formatted_msg = self.handlers[0].formatter.format(
                logging.LogRecord(self.name, level, "", 0, msg, args, exc_info, None)
            )

            # Get or create event loop
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Schedule the coroutine to run
            if loop.is_running():
                # If we're already in an async context, create_task is safe
                loop.create_task(send_log(formatted_msg, level))
            else:
                # If we're not in an async context, run the coroutine
                loop.run_until_complete(send_log(formatted_msg, level))


def setup_logger(name=__name__, level=logging.INFO):
    # Set logger class
    logger = DiscordLogger(name)
    logger.setLevel(level)

    # Add console handler if it doesn't exist
    if not logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)

        # Create formatter
        formatter = logging.Formatter("%(levelname)s:    %(message)s")
        console_handler.setFormatter(formatter)

        # Add handler to the logger
        logger.addHandler(console_handler)

    return logger
