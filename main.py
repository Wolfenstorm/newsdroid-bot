import asyncio
import feedparser
import httpx
from datetime import datetime, timedelta
from telegram import Bot
from telegram.constants import ParseMode
import logging

# --- CONFIGURATION ---
CHANNEL_ID = '@NewsDroid_Test'
BOT_TOKEN = '7577336852:AAG_AV8gLnFacBIbLfl3tFyubSr3GEN30-U'

# Пріоритетні джерела (україномовні, закордонні)
PRIORITY_DOMAINS = [
    "ukrainian.voanews.com",
    "www.radiosvoboda.org",
    "www.dw.com",
    "www.bbc.com",
    "www.eurointegration.com.ua",
    "www.ukrainianweek.com"
]

# Всі RSS-стрічки
RSS_FEEDS = [
    "https://www.unian.ua/rss/index.rss",
    "https://www.radiosvoboda.org/api/zipoyomegoy",
    "https://rss.dw.com/rdf/rss-uk-top",
    "https://www.bbc.com/ukrainian/index.xml",
    "https://www.eurointegration.com.ua/rss/",
    "https://ukrainian.voanews.com/api/zgqyveuq$moq",
    "https://tyzhden.ua/rss/",
    "https://rss.nv.ua/rss/allnews.xml",
    "https://www.ukrinform.ua/rss",
    "https://www.5.ua/5_uamp.rss",
    "https://glavcom.ua/rss/",
    "https://news.liga.net/all/rss.xml",
    "https://www.unn.com.ua/rss/news_uk.xml",
    "https://www.apostrophe.ua/rss.xml",
    "https://rubryka.com/feed/",
    "https://hromadske.ua/feed",
    "https://espreso.tv/rss",
    "https://www.ukrinform.ua/rss/rubric-polytics",
    "https://zn.ua/rss.xml",
    "https://suspilne.media/rss/all.xml",
    "https://armyinform.com.ua/feed/"
]

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- FETCH & PARSE ---
async def fetch_feed(session, url):
    try:
        response = await session.get(url)
        feed = feedparser.parse(response.text)
        return feed.entries
    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
        return []

async def fetch_all_feeds():
    async with httpx.AsyncClient(timeout=10) as client:
        tasks = [fetch_feed(client, url) for url in RSS_FEEDS]
        results = await asyncio.gather(*tasks)
        all_entries = [item for sublist in results for item in sublist]
        return all_entries

# --- FILTER & PRIORITIZE ---
def prioritize_news(news_list):
    def is_priority(entry):
        return any(domain in entry.get("link", "") for domain in PRIORITY_DOMAINS)

    priority = [n for n in news_list if is_priority(n)]
    regular = [n for n in news_list if not is_priority(n)]
    return priority + regular

def filter_recent(news_list, minutes=15):
    cutoff = datetime.utcnow() - timedelta(minutes=minutes)
    seen_links = set()
    filtered = []
    for entry in news_list:
        published = entry.get("published_parsed")
        link = entry.get("link", "")
        if not published or not link:
            continue
        published_dt = datetime(*published[:6])
        if published_dt > cutoff and link not in seen_links:
            seen_links.add(link)
            filtered.append(entry)
    return filtered

# --- POST TO TELEGRAM ---
async def send_to_telegram(bot, entry):
    title = entry.get("title", "Без заголовка")
    link = entry.get("link", "")
    summary = entry.get("summary", "").strip().replace('<br>', '\n')

    text = f"<b>{title}</b>\n\n{summary}\n\n<a href='{link}'>Читати повністю</a>"

    try:
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=False,
        )
        logger.info(f"✅ Sent: {title}")
    except Exception as e:
        logger.error(f"❌ Failed to send: {e}")

# --- MAIN ---
async def main():
    logger.info("📡 Fetching RSS feeds...")
    entries = await fetch_all_feeds()

    logger.info(f"📋 Total entries fetched: {len(entries)}")
    recent_news = filter_recent(entries)
    logger.info(f"🕓 Filtered recent news: {len(recent_news)}")

    sorted_news = prioritize_news(recent_news)

    bot = Bot(token=BOT_TOKEN)

    for entry in sorted_news:
        await send_to_telegram(bot, entry)
        await asyncio.sleep(1.5)  # avoid flood

if __name__ == "__main__":
    asyncio.run(main())
