import asyncio

import uvicorn
from fastapi import FastAPI

from src.bot import bot
from src.config import settings
from src.tracking import track_blogs, track_news, track_sbir

app = FastAPI()


# register an asyncio.create_task(client.start()) on app's startup event
@app.on_event("startup")
async def lifespan():
    asyncio.create_task(bot.start(settings.DISCORD_TOKEN))
    await asyncio.sleep(4)
    print(f"Started discord bot {bot.user}")


@app.get("/cron/tracking/sbir")
async def cron_tracking_sbir():
    asyncio.create_task(track_sbir())
    return {"status": "success"}


@app.get("/cron/tracking/blogs")
async def cron_tracking_blogs():
    asyncio.create_task(track_blogs())
    return {"status": "success"}


@app.get("/cron/tracking/news")
async def cron_tracking_news():
    asyncio.create_task(track_news())
    return {"status": "success"}


if __name__ == "__main__":
    if settings.RAILWAY_ENVIRONMENT_NAME == "development":
        uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=True)
    else:
        uvicorn.run(app, host="0.0.0.0", port=settings.PORT)
