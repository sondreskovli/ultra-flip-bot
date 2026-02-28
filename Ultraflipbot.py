import feedparser
import requests
import re
import sqlite3
import statistics
import gc
import time

################################
# CONFIG
################################

TOKEN = "8646755134:AAH0lIW83diJ-BslB65Ir40AXl0QyUVJZQg"
CHAT_ID = "5331968688"

SEARCH = {
    "iphone": "https://www.finn.no/bap/forsale/search.html?q=iphone+OR+iphon+OR+apple+iphone&rss=true",
    "airpods": "https://www.finn.no/bap/forsale/search.html?q=airpods+OR+airpod+OR+air+pods&rss=true",
    "ps5": "https://www.finn.no/bap/forsale/search.html?q=ps5+OR+ps-5+OR+playstation+5+OR+play+station+5&rss=true",
    "macbook": "https://www.finn.no/bap/forsale/search.html?q=macbook+OR+mac+book+OR+mackbook&rss=true",
    "ipad": "https://www.finn.no/bap/forsale/search.html?q=ipad+OR+ipad+pro+OR+ipadd&rss=true"
}

DEFAULT_MARKET = {
    "ps5": 4500,
    "iphone": 6000,
    "airpods": 1500,
    "macbook": 8000,
    "ipad": 4000
}

################################
# DATABASE
################################

def setup_db():
    conn = sqlite3.connect("market.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS ads (
        id TEXT PRIMARY KEY,
        title TEXT,
        price INTEGER,
        category TEXT,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

def save_ad(ad_id, title, price, category):
    conn = sqlite3.connect("market.db")
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO ads VALUES (?, ?, ?, ?, datetime('now'))",
        (ad_id, title, price, category)
    )
    conn.commit()
    conn.close()

def get_market_price(category):
    conn = sqlite3.connect("market.db")
    c = conn.cursor()
    c.execute("""
        SELECT price FROM ads
        WHERE category=? AND date >= datetime('now','-30 days')
    """, (category,))
    prices = [row[0] for row in c.fetchall()]
    conn.close()

    if len(prices) >= 5:
        return statistics.median(prices)

    return DEFAULT_MARKET.get(category)

################################
# TELEGRAM
################################

def send(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        r = requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
        print("Telegram status:", r.status_code)
    except Exception as e:
        print("Telegram error:", e)

################################
# HELPERS
################################

def extract_price(text):
    if not text:
        return None
    cleaned = text.replace(" ", "")
    nums = re.findall(r'\d+', cleaned)
    return int(nums[0]) if nums else None

################################
# MAIN
################################

def run_once():
    print("🔥 CRON RUN STARTED")

    # Test Telegram
    send("Bot kjører ✅")

    summary = []

    for category in SEARCH:
    print(f"Scanning {category}")

    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(SEARCH[category], headers=headers)
    feed = feedparser.parse(response.text)

    print("Entries found:", len(feed.entries))

        for entry in feed.entries:
            try:
                ad_id = entry.get("id", "")
                title = entry.get("title", "")
                summary_text = entry.get("summary", "")

                # 🔥 HENTER PRIS FRA TITLE + SUMMARY
                asking = extract_price(title + " " + summary_text)

                if not asking:
                    continue

                save_ad(ad_id, title, asking, category)

                market_price = get_market_price(category)
                if not market_price:
                    continue

                profit = market_price - asking
                roi = (profit / asking) * 100 if asking else 0

                print(title, asking, "ROI:", round(roi, 1))

                # 🚀 SEND ALT MED PRIS
                summary.append(
                    f"🔥 DEAL\n{title}\nPris: {asking}\nFlip: {profit}\nROI: {round(roi,1)}%"
                )

            except Exception as e:
                print("Entry error:", e)
                continue

    if summary:
        send("📊 TRADER FEED\n\n" + "\n\n".join(summary[:10]))

    print("✅ CRON RUN DONE")
    gc.collect()

################################
# ENTRY
################################

if __name__ == "__main__":
    setup_db()
    run_once()
