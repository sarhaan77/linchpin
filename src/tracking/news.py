import asyncio
from typing import List

import requests
from markdownify import markdownify as md
from pydantic import BaseModel, Field

from src.bb import bb_get_html
from src.bot import send_msg, setup_logger
from src.config import settings

channels = {
    "defense": 1314477322178531338,
    "business": 1314490175375806505,
    "world": 1314491244428398622,
}

base_urls = [
    {
        "title": "Defense News",
        "url": "https://www.defensenews.com/",
        "category": "defense",
        "jina": True,
    },
    {
        "title": "TechCrunch",
        "url": "https://techcrunch.com",
        "category": "business",
        "jina": True,
    },
    {
        "title": "Reuters",
        "url": "https://www.reuters.com/business/aerospace-defense/",
        "category": "defense",
        "jina": False,
        "proxy": True,
    },
    {
        "title": "Financial Times",
        "url": "https://www.ft.com/companies",
        "category": "business",
        "jina": False,
        "proxy": True,
    },
    {
        "title": "Financial Times",
        "url": "https://www.ft.com/world",
        "category": "world",
        "jina": False,
        "proxy": True,
    },
    {
        "title": "Eric Berger",
        "url": "https://arstechnica.com/author/ericberger/",
        "category": "defense",
        "jina": True,
    },
    # WSJ blocks browserbase
    # {
    #     "title": "WSJ",
    #     "url": "https://www.wsj.com/business",
    #     "category": "business",
    #     "jina": False,
    #     "proxy": True,
    #     "captcha": True,
    # },
]


logger = setup_logger(__name__)


class Article(BaseModel):
    headline: str = Field(description="The headline of the news article")
    url: str = Field(
        description="Absolute URL of the news article, if URL is relative, please convert to absolute URL"
    )


class Articles(BaseModel):
    articles: List[Article] = Field(description="List of articles on the page")


def use_jina(url: str):
    headers = {"Authorization": f"Bearer {settings.JINA_API_KEY}", "X-No-Cache": "true"}
    response = requests.get(f"https://r.jina.ai/{url}", headers=headers)
    return response.text


async def scrape(url: str, jina: bool, proxy: bool = False, captcha: bool = False):
    if jina:
        content = use_jina(url)
    else:
        html = await asyncio.to_thread(bb_get_html, url, proxy=proxy, captcha=captcha)
        content = md(html)

    prompt = f"You are given content from a news websites main page, please retrieve all the articles and their URLs. Again, the user is only interested in reading articles, not any other content on the page. Here is the content: {content}"
    articles = await settings.async_openai_client.chat.completions.create(
        model="gpt-4o-mini",
        response_model=Articles,
        messages=[{"role": "user", "content": prompt}],
    )
    articles = [x.model_dump() for x in articles.articles]
    non_duplicates = (
        settings.supabase_client.table("news")
        .upsert(
            articles,
            ignore_duplicates=True,
            returning="representation",
            count="exact",
        )
        .execute()
    )
    return non_duplicates


async def track_news() -> list[dict]:
    for base_url in base_urls:
        try:
            url = base_url["url"]
            jina = base_url["jina"]
            title = base_url["title"]
            proxy = base_url.get("proxy", False)
            captcha = base_url.get("captcha", False)
            channel_id = channels[base_url["category"]]
            logger.info(f"[NEWS] [{url}] Scraping")

            non_duplicates = await scrape(url, jina, proxy, captcha)

            for a in non_duplicates.data:
                await send_msg(
                    channel_id,
                    f"[{title}] [{a['headline']}]({a['url']})",
                )
            logger.info(
                f"[NEWS] [{url}] Scraped {len(non_duplicates.data)} new articles"
            )
        except Exception as e:
            logger.error(f"[NEWS] [{url}] Error scraping: {e}")
