from src.bot import send_msg, setup_logger
from src.tracking.news import scrape

CHANNEL_ID = 1314496562008690761
logger = setup_logger(__name__)
base_urls = [
    {
        "title": "Stratechery",
        "url": "https://stratechery.com/category/articles/",
        "category": "world",
        "jina": True,
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


async def track_blogs() -> list[dict]:
    for base_url in base_urls:
        try:
            url = base_url["url"]
            jina = base_url["jina"]
            title = base_url["title"]
            logger.info(f"[BLOGS] [{url}] Scraping")

            non_duplicates = await scrape(url, jina)

            for a in non_duplicates.data:
                await send_msg(
                    CHANNEL_ID,
                    f"[{title}] [{a['headline']}]({a['url']})",
                )

            logger.info(
                f"[BLOGS] [{url}] Scraped {len(non_duplicates.data)} new articles"
            )
        except Exception as e:
            logger.error(f"[BLOGS] [{url}] Error scraping: {e}")
