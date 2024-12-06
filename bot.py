import asyncio
from typing import Optional

import discord
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.config import settings
from src.tracking.sbir import track_sbir

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

app = FastAPI()


# register an asyncio.create_task(client.start()) on app's startup event
@app.on_event("startup")
async def lifespan():
    asyncio.create_task(bot.start(settings.DISCORD_TOKEN))
    await asyncio.sleep(4)
    print(f"{bot.user}")


@app.get("/cron/tracking/sbir")
async def cron_tracking_sbir():
    asyncio.create_task(track_sbir(send_embed, send_error))
    return {"status": "success"}


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
    # Make the send call async
    await channel.send(embed=embed)


async def send_error(message: str):
    DISCORD_ERRORS_CHANNEL_ID = 1314432677323083816
    channel = bot.get_channel(DISCORD_ERRORS_CHANNEL_ID)
    await channel.send(message)


if __name__ == "__main__":
    if settings.RAILWAY_ENVIRONMENT_NAME == "development":
        uvicorn.run("bot:app", host="0.0.0.0", port=settings.API_PORT, reload=True)
    else:
        uvicorn.run(app, host="0.0.0.0", port=settings.API_PORT)
