import asyncio

import pandas as pd
import requests
from pydantic import BaseModel, Field
from tqdm.asyncio import tqdm

from src.bot import send_embed, setup_logger
from src.config import settings

logger = setup_logger(__name__)
# tracking>sbir-grants
CHANNEL_ID = 1314432734697095238
url = "https://www.sbir.gov/topics"


class Summary(BaseModel):
    summary: str = Field(description="Summary of the topic")


def load_sbir_from_website():
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
        "cache-control": "max-age=0",
        "content-type": "application/x-www-form-urlencoded",
        "origin": "https://www.sbir.gov",
        "referer": "https://www.sbir.gov/topics",
        "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "same-origin",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    }
    data = {
        "keywords": "",
        "open_date_from": "",
        "open_date_to": "",
        "close_date_from": "",
        "close_date_to": "",
        "status": "Open",
        "op": "Download",
        "form_build_id": "form-0jgcyUu86pIPRqKw0IAXvAXNYCgR42B6R2l4SLh4580",
        "form_id": "topics_search",
    }

    response = requests.post(url, headers=headers, data=data)

    # Write the response to file
    with open("tmp/sbir.csv", "w") as f:
        f.write(response.text)


async def track_sbir() -> list[dict]:
    """
    STEPS:
    1. Scrape the SBIR website by running the curl command
    2. Upload to the database > sbir, primary key is url; ignore all duplicates; if not exists, add to db
    3. Get all rows where summary is null, summarize, add to db, send to discord > tracking >
    4. if any error send to discord > errors
    """

    async def summarizer(info: dict, sem: asyncio.Semaphore) -> dict | None:
        async with sem:
            prompt = f"Please concisely summarize the SBIR grant info:\n\nTopic Title: {info['Topic Title']}\nTopic Description: {info['Topic Description']}."
            try:
                summary = await settings.async_openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    response_model=Summary,
                    messages=[{"role": "user", "content": prompt}],
                )
                info["summary"] = summary.summary
                return info
            except Exception as e:
                logger.error(
                    f"[TRACKING>SBIR>SUMMARIZER] Could not summarize: {info}; {e}"
                )
                return None

    try:
        logger.info(f"[TRACKING>SBIR] Fetching SBIR Grants from {url}")

        load_sbir_from_website()
        df = pd.read_csv("tmp/sbir.csv")
        # if 0 lines raise error
        if len(df) == 0:
            raise Exception("No SBIR Grants found on the website")

        rows = df.to_dict(orient="records")
        # ignore duplicates coz we dont wanna overwrite existing rows which have summaries
        settings.supabase_client.table("sbir").upsert(
            rows, ignore_duplicates=True
        ).execute()

        sem = asyncio.Semaphore(72)
        # this wont ever go above a 1000 so we aint too worried about supabase only returning 1000 rows
        rows = (
            settings.supabase_client.table("sbir")
            .select("*")
            .is_("summary", "null")
            .execute()
        )
        if len(rows.data) == 0:
            logger.info("[TRACKING>SBIR] No SBIR Grants to summarize")
            return

        tasks = [summarizer(info, sem) for info in rows.data]
        summaries = await tqdm.gather(
            *tasks, desc="Summarizing SBIR Grants", total=len(rows.data)
        )
        summaries = [s for s in summaries if s]
        # dont ignore duplicates coz we are updating the rows with summaries
        settings.supabase_client.table("sbir").upsert(summaries).execute()
        for summary in summaries:
            await send_embed(
                CHANNEL_ID,
                summary["Topic Title"],
                summary["summary"],
                summary["SBIRTopicLink"],
            )
        logger.info("[TRACKING>SBIR] SBIR Grants fetched and summarized")
    except Exception as e:
        logger.error(f"[TRACKING>SBIR>SUMMARIZER] {e}")
