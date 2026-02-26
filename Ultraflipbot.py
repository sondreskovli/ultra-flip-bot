import feedparser
import time
import requests
import re
import sqlite3
import statistics
import gc

TOKEN = "DIN_TOKEN"
CHAT_ID = "DIN_CHAT_ID"

SEARCH = {
    "iphone": "https://www.finn.no/bap/forsale/search.html?q=iphone&rss=true",
    "airpods": "https://www.finn.no/bap/forsale/search.html?q=airpods&rss=true",
    "ps5": "https://www.finn.no/bap/forsale/search.html?q=playstation+5&rss=true",
    "macbook": "https://www.finn.no/bap/forsale/search.html?q=macbook&rss=true",
    "ipad": "https://www.finn.no/bap/forsale/search.html?q=ipad&rss=true"
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
    conn.commit()
    conn.close()

def save_ad(ad_id, title, price, category):
    conn = sqlite3.connect("market.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO ads VALUES (?, ?, ?, ?, datetime('now'))",
              (ad_id, title, price, category))
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

    if len(prices) < 5:
        return None
    return statistics.median(prices)

#############################
# TELEGRAM
#############################

def send(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except:
        pass

#############################
# HELPERS
#############################

def extract_price(text):
    nums = re.findall(r'\d+', text.replace(" ", ""))
    return int(nums[0]) if nums else None

def scam_score(text, asking, market):
    score = 0
    text = text.lower()

    flags = ["forskudd","western union","ingen kvittering","må sendes","kun vipps","haster"]
    for f in flags:
        if f in text:
            score += 25

    if market and asking < market * 0.5:
        score += 30

    if len(text) < 35:
        score += 10

    return min(score,100)

#############################
# START
#############################

setup_db()
send("🚀 TRADER ENGINE LIVE")

startup_mode = True
start_time = time.time()

#############################
# MAIN LOOP
#############################

while True:
    summary = []

    for category in SEARCH:
        try:
            feed = feedparser.parse(SEARCH[category])
        except:
            continue

        for entry in feed.entries:
            try:
                ad_id = entry.id
                text = entry.title + " " + entry.summary
                asking = extract_price(entry.summary)

                if not asking:
                    continue

                if asking > 10000:
                    continue

                save_ad(ad_id, entry.title, asking, category)
                market_price = get_market_price(category)

                if not market_price:
                    continue

                profit = market_price - asking
                roi = (profit / asking) * 100
                scam = scam_score(text, asking, market_price)

                # STARTUP 24h
                if startup_mode:
                    if roi > 10 and profit > 250 and scam < 65:
                        summary.append(
                            f"🚀 START\n{entry.title}\nPris:{asking}\nFlip:+{profit}\n{entry.link}\n"
                        )

                # NORMAL MODE
                else:
                    if roi > 28 and profit > 900 and scam < 40:
                        summary.append(
                            f"🚨 BUY NOW\n{entry.title}\nPris:{asking}\nFlip:+{profit}\n{entry.link}\n"
                        )

                    elif roi > 18 and profit > 600 and scam < 50:
                        summary.append(
                            f"🔥 STRONG\n{entry.title}\nPris:{asking}\nFlip:+{profit}\n{entry.link}\n"
                        )

                    elif roi > 5 and profit > 400 and scam < 60:
                        summary.append(
                            f"💰 PRUTE\n{entry.title}\nPris:{asking}\nMulig flip:+{profit}\n{entry.link}\n"
                        )

            except:
                continue

    if summary:
        send("📊 TRADER FEED\n\n" + "\n".join(summary[:15]))

    # startup varer 24t
    if time.time() - start_time > 86400:
        startup_mode = False

    # frigjør memory (viktig for Render free tier)
    gc.collect()

    time.sleep(300)
