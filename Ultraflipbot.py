import feedparser
import time
import requests
import re
import sqlite3
import statistics

TOKEN = "8646755134:AAH0lIW83diJ-BslB65Ir40AXl0QyUVJZQg"
CHAT_ID = "5331968688"

SEARCH = {
    "ps5": "https://www.finn.no/bap/forsale/search.html?q=playstation+5&rss=true",
    "iphone": "https://www.finn.no/bap/forsale/search.html?q=iphone&rss=true"
}

def setup_db():
    send("🚀 BOT ER LIVE 🚀")
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

def send(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

def extract_price(text):
    nums = re.findall(r'\d+', text.replace(" ", ""))
    return int(nums[0]) if nums else None

def save_ad(ad_id, title, price, category):
    conn = sqlite3.connect("market.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO ads VALUES (?, ?, ?, ?, datetime('now'))",
              (ad_id, title, price, category))
    conn.commit()

def get_market_price(category):
    conn = sqlite3.connect("market.db")
    c = conn.cursor()
    c.execute("""
    SELECT price FROM ads
    WHERE category=? AND date >= datetime('now', '-30 days')
    """, (category,))
    prices = [row[0] for row in c.fetchall()]
    if len(prices) < 5:
        return None
    return statistics.median(prices)

def scam_score(text, asking, market):
    score = 0
    text = text.lower()

    red_flags = ["forskudd", "western union", "ingen kvittering", "må sendes"]

    for flag in red_flags:
        if flag in text:
            score += 25

    if market and asking < market * 0.6:
        score += 30

    if len(text) < 40:
        score += 10

    return min(score, 100)

setup_db()

while True:
    for category in SEARCH:
        feed = feedparser.parse(SEARCH[category])

        for entry in feed.entries:
            ad_id = entry.id
            text = entry.title + " " + entry.summary
            asking = extract_price(entry.summary)

            if not asking:
                continue

            save_ad(ad_id, entry.title, asking, category)

            market_price = get_market_price(category)

            if not market_price:
                continue

            profit = market_price - asking
            roi = (profit / asking) * 100
            scam = scam_score(text, asking, market_price)

            if True:
                msg = f"""
🔥 ULTRA FLIP ALERT 🔥

{entry.title}

Pris: {asking} kr
Markedspris: {market_price} kr
Profit: {profit} kr
ROI: {roi:.1f} %

Scam Risk: {scam}/100

{entry.link}
"""
                send(msg)

    time.sleep(20)
