import feedparser
import time
import requests
import re
import sqlite3
import statistics
import gc

#############################
# CONFIG
#############################

TOKEN = "PUT_YOUR_NEW_TOKEN_HERE"
CHAT_ID = "PUT_YOUR_CHAT_ID_HERE"

SEARCH = {
    "iphone": "https://www.finn.no/bap/forsale/search.html?q=iphone&rss=true",
    "airpods": "https://www.finn.no/bap/forsale/search.html?q=airpods&rss=true",
    "ps5": "https://www.finn.no/bap/forsale/search.html?q=playstation+5&rss=true",
    "macbook": "https://www.finn.no/bap/forsale/search.html?q=macbook&rss=true",
    "ipad": "https://www.finn.no/bap/forsale/search.html?q=ipad&rss=true"
}

# Fallback markedspriser hvis databasen er tom
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

    # fallback hvis ikke nok data
    return DEFAULT_MARKET.get(category)

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

    flags = ["forskudd", "western union", "ingen kvittering",
             "må sendes", "kun vipps", "haster"]
    
    for f in flags:
        if f in text:
            score += 25

    if market and asking < market * 0.5:
        score += 30

    if len(text) < 35:
        score += 10

    return min(score, 100)

#############################
# START
#############################

setup_db()
send("🚀 ULTRA FLIP BOT STARTET")

print("Bot started...")

#############################
# MAIN LOOP
#############################

while True:
    total_found = 0
    total_matches = []

    for category in SEARCH:
        try:
            feed = feedparser.parse(SEARCH[category])
        except Exception as e:
            print("RSS error:", e)
            continue

        print(f"Scanning {category}...")

        for entry in feed.entries:
            total_found += 1

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

                # Trigger nivåer
                if roi > 30 and profit > 1000 and scam < 40:
                    total_matches.append(
                        f"🚨 BUY NOW\n{entry.title}\nPris: {asking}\nFlip: +{profit}\n{entry.link}\n"
                    )

                elif roi > 20 and profit > 600 and scam < 50:
                    total_matches.append(
                        f"🔥 STRONG\n{entry.title}\nPris: {asking}\nFlip: +{profit}\n{entry.link}\n"
                    )

                elif roi > 10 and profit > 400 and scam < 60:
                    total_matches.append(
                        f"💰 PRUTE\n{entry.title}\nPris: {asking}\nMulig flip: +{profit}\n{entry.link}\n"
                    )

            except Exception as e:
                print("Entry error:", e)
                continue

    print(f"Found {total_found} ads this round")

    if total_matches:
        send("📊 ULTRA FEED\n\n" + "\n".join(total_matches[:15]))

    gc.collect()
    time.sleep(300)
