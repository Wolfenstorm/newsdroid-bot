import asyncio
import httpx
import feedparser
import json
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

# --- Налаштування ---
BOT_TOKEN = "7577336852:AAGz1yyJen2HRGVzwLQB3HVWa75fO-bZ9pU"
CHAT_ID = "-1002650930903"

RSS_FEEDS = [
    "https://rss.unian.net/site/news_ukr.rss",
    "https://www.epravda.com.ua/rss/main/",
    "https://www.eurointegration.com.ua/rss/",
    "https://www.radiosvoboda.org/api/zrqiteuu$ute",
    "https://novynarnia.com/feed/",
    "https://gordonua.com/xml/rss.xml",
    "https://lb.ua/export/rss/all.xml",
    "https://www.unn.com.ua/uk/rss/news_ukr.xml",
    "https://www.ukrinform.ua/rss/block-lastnews",
    "https://www.ukrinform.ua/rss/block-world",
    "https://zn.ua/rss.xml",
    "https://suspilne.media/rss/news.xml",
    "https://www.5.ua/rss",
    "https://hromadske.ua/rss",
    "https://glavcom.ua/rss/all.xml",
    "https://apostrophe.ua/rss",
    "https://interfax.com.ua/news/general.rss",
    "https://news.liga.net/politics/rss.xml",
    "https://mind.ua/rss/news",
    "https://life.pravda.com.ua/rss/",
    "https://armyinform.com.ua/feed/"
]

SOURCE_PRIORITY = {
    "unian.net": 1,
    "radiosvoboda.org": 2
}

POSTED_FILE = "posted.json"

# --- Завантаження вже опублікованих новин ---
def load_posted_urls():
    if os.path.exists(POSTED_FILE):
        with open(POSTED_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

# --- Збереження нових опублікованих новин ---
def save_posted_urls(posted_urls):
    with open(POSTED_FILE, "w", encoding="utf-8") as f:
        json.dump(list(posted_urls), f, ensure_ascii=False, indent=2)

# --- Отримання домену (для пріоритету) ---
def get_domain(url):
    parsed = urlparse(url)
    return parsed.netloc.replace("www.", "")

# --- Отримання новин за останню годину ---
def fetch_recent_news():
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    news_items = []

    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            if hasattr(entry, 'published_parsed'):
                pub_time = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                if pub_time >= one_hour_ago:
                    domain = get_domain(entry.link)
                    source_score = SOURCE_PRIORITY.get(domain, 99)
                    news_items.append({
                        "title": entry.title,
                        "url": entry.link,
                        "source_score": source_score,
                        "length_score": len(entry.title),
                        "published": pub_time.isoformat()
                    })
    return news_items

# --- Публікація повідомлення ---
async def publish_post(chat_id, message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "disable_web_page_preview": False,
        "parse_mode": "HTML"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload)
            print(f"[✅] Telegram: {response.status_code} - {response.text}")
            response.raise_for_status()
            return True
        except httpx.HTTPStatusError as e:
            print(f"[!] HTTP error: {e.response.status_code} - {e.response.text}")
            return False
        except Exception as e:
            print(f"[!] Unexpected error: {e}")
            return False

# --- Основна логіка публікації новин ---
async def main():
    print("🟢 Старт. Шукаємо новини за останню годину...")

    posted_urls = load_posted_urls()
    recent_news = fetch_recent_news()

    new_news = [
        news for news in recent_news
        if news["url"] not in posted_urls
    ]

    print(f"📥 Новин за останню годину: {len(recent_news)} | Нових: {len(new_news)}")

    sorted_news = sorted(
        new_news,
        key=lambda n: (n["source_score"], -n["length_score"], n["published"])
    )[:21]

    for news in sorted_news:
        message = f"<b>{news['title']}</b>\n{news['url']}"
        success = await publish_post(CHAT_ID, message)
        if success:
            posted_urls.add(news["url"])
        await asyncio.sleep(2)

    save_posted_urls(posted_urls)
    print("✅ Завершено. Новини опубліковані.")

# --- Безкінечний цикл (автоматичний запуск щогодини) ---
async def loop_forever():
    while True:
        await main()
        print("⏳ Очікуємо наступну перевірку через 1 годину...")
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(loop_forever())
    except KeyboardInterrupt:
        print("🛑 Зупинено вручну.")
