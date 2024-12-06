from typing import List

import requests
from markdownify import markdownify as md
from pydantic import BaseModel, Field

from src.config import settings, setup_logger
from src.scrape import run

channels = {
    "defense": 1314477322178531338,
    "business": 1314490175375806505,
    "world": 1314491244428398622,
    "blogs": 1314496562008690761,
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
        "title": "Eric Berger",
        "url": "https://arstechnica.com/author/ericberger/",
        "category": "defense",
        "jina": True,
    },
    {
        "title": "Stratechery",
        "url": "https://stratechery.com/category/articles/",
        "category": "world",
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
        "title": "Reuters",
        "url": "https://www.reuters.com/business/",
        "category": "business",
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
        "title": "WSJ",
        "url": "https://www.wsj.com/business",
        "category": "business",
        "jina": False,
        "proxy": True,
    },
    {
        "title": "Snippet Finance",
        "url": "https://snippet.finance/",
        "category": "blogs",
        "jina": True,
    },
    {
        "title": "Subsea Cables & Internet Infrastructure",
        "url": "https://subseacables.blogspot.com/",
        "category": "blogs",
        "jina": True,
    },
    {
        "title": "Outside Five Sigma",
        "url": "https://jwt625.github.io/",
        "category": "blogs",
        "jina": True,
    },
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


async def track_news(fn_send_msg, fn_send_error) -> list[dict]:
    """
    Args:
    async fn_send_msg (function): send_embed function
       - message (str): message to send

    async fn_send_error (function): send_error function
        - message (str): error message
    """

    logger.info("[NEWS] Starting to scrape news articles")
    for base_url in base_urls:
        try:
            url = base_url["url"]
            jina = base_url["jina"]
            title = base_url["title"]
            channel_id = channels[base_url["category"]]
            logger.info(f"[NEWS] Scraping {url}")

            if jina:
                content = use_jina(url)
            else:
                html = await run(url, proxy=base_url.get("proxy", False))
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
            for a in non_duplicates.data:
                await fn_send_msg(
                    channel_id,
                    f"[{title}] [{a['headline']}]({a['url']})",
                )

            logger.info(
                f"[NEWS] [{url}] Scraped {len(non_duplicates.data)} new articles"
            )
        except Exception as e:
            error_msg = f"[NEWS] [{url}] Error scraping: {e}"
            logger.error(error_msg)
            await fn_send_error(error_msg)
