import feedparser
import requests
import re
import sqlite3
import statistics
import gc
import time
from bs4 import BeautifulSoup

#############################
# CONFIG
#############################

TOKEN = "8646755134:AAH0lIW83diJ-BslB65Ir40AXl0QyUVJZQg"
CHAT_ID = "5331968688"

SEARCH = {
    "iphone": "https://www.finn.no/bap/forsale/search.html?q=iphone+OR+iphonee+OR+iphon+OR+apple+iphone&rss=true",

    "airpods": "https://www.finn.no/bap/forsale/search.html?q=airpods+OR+air+pods+OR+airpod+OR+air+pod&rss=true",

    "ps5": "https://www.finn.no/bap/forsale/search.html?q=ps5+OR+ps-5+OR+playstation+5+OR+play+station+5+OR+ps+5&rss=true",

    "macbook": "https://www.finn.no/bap/forsale/search.html?q=macbook+OR+mac+book+OR+mackbook+OR+macbok+OR+apple+macbook&rss=true",

    "ipad": "https://www.finn.no/bap/forsale/search.html?q=ipad+OR+ipad+pro+OR+ipadd+OR+apple+ipad&rss=true"
}
DEFAULT_MARKET = {
    "ps5": 4500,
    "iphone": 6000,
    "airpods": 1500,
    "macbook": 8000,
    "ipad": 4000
}

#############################
# DATABASE
#############################

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

    c.execute("""
    CREATE TABLE IF NOT EXISTS config (
        key TEXT PRIMARY KEY,
        value TEXT
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
        WHERE category=? AND date >= datetime('now', '-30 days')
    """, (category,))
    prices = [row[0] for row in c.fetchall()]
    conn.close()

    if len(prices) >= 5:
        return statistics.median(prices)

    return DEFAULT_MARKET.get(category)

def get_start_time():
    conn = sqlite3.connect("market.db")
    c = conn.cursor()

    c.execute("SELECT value FROM config WHERE key='start_time'")
    row = c.fetchone()

    if row:
        start_time = float(row[0])
    else:
        start_time = time.time()
        c.execute("INSERT INTO config VALUES ('start_time', ?)", (str(start_time),))
        conn.commit()

    conn.close()
    return start_time

#############################
# TELEGRAM
#############################

def send(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except Exception as e:
        print("Telegram error:", e)

#############################
# HELPERS
#############################

def extract_price(text):
    cleaned = text.replace(" ", "")
    nums = re.findall(r'\d+', cleaned)
    return int(nums[0]) if nums else None

def scam_score(text, asking, market):
    score = 0
    text = text.lower()

    flags = ["forskudd","western union","ingen kvittering",
             "må sendes","kun vipps","haster"]

    for f in flags:
        if f in text:
            score += 25

    if market and asking < market * 0.5:
        score += 30

    if len(text) < 35:
        score += 10

    return min(score,100)

#############################
# MAIN RUN
#############################

def run_once():
    print("🔥 CRON RUN STARTED")

    summary = []

    for category in SEARCH:
        print(f"Scanning {category}")

        feed = feedparser.parse(SEARCH[category])

        for entry in feed.entries:
            try:
                ad_id = entry.id
                text = entry.title + " " + entry.summary
                asking = extract_price(entry.summary)

                if not asking:
                    continue

                if asking > 20000:
                    continue

                save_ad(ad_id, entry.title, asking, category)

                market_price = get_market_price(category)
                if not market_price:
                    continue

                profit = market_price - asking
                roi = (profit / asking) * 100
                scam = scam_score(text, asking, market_price)

                print(f"{entry.title} | {asking} | ROI {round(roi,1)}%")

                if roi > 15 and profit > 500 and scam < 55:
                    summary.append(
                        f"🔥 DEAL\n{entry.title}\nPris:{asking}\nFlip:+{profit}\nROI:{round(roi,1)}%"
                    )

            except Exception as e:
                print("Entry error:", e)
                continue

    if summary:
        send("📊 TRADER FEED\n\n" + "\n\n".join(summary[:10]))

    print("✅ CRON RUN DONE")
    gc.collect()


#############################
# ENTRY
#############################

if __name__ == "__main__":
    setup_db()
    run_once()
