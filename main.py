from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import time
import os

# ================= CONFIG =================
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

IST = ZoneInfo("Asia/Kolkata")

# ==========================================


def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
        print("✅ Telegram sent")
    except Exception as e:
        print(f"❌ Telegram error: {e}")


# ================= MARKET =================


def market_open():
    now = datetime.now(IST)
    return now.weekday() < 5 and dtime(9, 15) <= now.time() <= dtime(15, 30)


def avoid_bad_times():
    now = datetime.now(IST).time()
    return not (
        dtime(9, 15) <= now <= dtime(9, 25) or dtime(15, 0) <= now <= dtime(15, 30)
    )


# ================= NSE SCREENER =================


def get_nse_top_stocks():
    try:
        session = requests.Session()

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en-US,en;q=0.9",
        }

        # Step 1: Load homepage (sets cookies)
        session.get("https://www.nseindia.com", headers=headers, timeout=5)

        # Step 2: API call
        url = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY 50"
        res = session.get(url, headers=headers, timeout=5)

        if res.status_code != 200 or not res.text:
            raise Exception("Empty NSE response")

        data = res.json()["data"]

        data = sorted(data, key=lambda x: abs(x["pChange"]), reverse=True)

        stocks = [x["symbol"] + ".NS" for x in data[:12]]

        print("🔥 NSE STOCKS:", stocks)

        return stocks

    except Exception as e:
        print("⚠️ NSE FAILED, using fallback:", e)

        # ✅ Smart fallback list (BEST intraday stocks)
        return [
            "ADANIENT.NS",
            "ADANIPOWER.NS",
            "RELIANCE.NS",
            "ETERNAL.NS",
            "HINDCOPPER.NS",
            "VEDL.NS",
            "COALINDIA.NS",
            "TCS.NS",
        ]


# ================= SCORING ENGINE =================


def score_stock(stock):
    try:
        df = yf.download(stock, period="1d", interval="5m", progress=False)

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        if len(df) < 30:
            return None

        df = df.dropna()

        latest = df.iloc[-1]

        price = latest["Close"]

        move = abs(df["Close"].pct_change()).sum()

        avg_vol = df["Volume"].rolling(20).mean().iloc[-1]
        vol_spike = latest["Volume"] / avg_vol if avg_vol > 0 else 0

        recent_high = df["High"].rolling(20).max().iloc[-2]
        breakout = 1 if price > recent_high else 0

        ema20 = df["Close"].ewm(span=20).mean().iloc[-1]
        trend_strength = abs(price - ema20)

        score = (move * 1000) + (vol_spike * 50) + (breakout * 200) + trend_strength

        return score

    except:
        return None


# ================= FINAL STOCK SELECTOR =================


def get_hedge_stocks():
    base_stocks = get_nse_top_stocks()

    ranked = []

    for s in base_stocks:
        sc = score_stock(s)
        if sc:
            ranked.append((s, sc))

    ranked = sorted(ranked, key=lambda x: x[1], reverse=True)

    top = [x[0] for x in ranked[:8]]

    print("🔥 HEDGE STOCKS:", ", ".join(top))

    return top


# ================= INDICATORS =================


def calculate_rsi(df, period=14):
    delta = df["Close"].diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


# ================= ANALYSIS =================


def calculate_atr(df, period=14):
    hl = df["High"] - df["Low"]
    hc = abs(df["High"] - df["Close"].shift())
    lc = abs(df["Low"] - df["Close"].shift())
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def analyze_stock(stock):
    try:
        df = yf.download(stock, period="1d", interval="5m", progress=False)

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.dropna()

        if len(df) < 20:
            return None

        df["EMA9"] = df["Close"].ewm(span=9).mean()
        df["EMA21"] = df["Close"].ewm(span=21).mean()
        df["RSI"] = calculate_rsi(df)

        latest = df.iloc[-1]

        price = round(float(latest["Close"]), 2)
        ema9 = float(latest["EMA9"])
        ema21 = float(latest["EMA21"])
        rsi = float(latest["RSI"])

        if ema9 > ema21:
            signal = "BUY"
        else:
            signal = "SELL"

        confirmed = rsi > 50 if signal == "BUY" else rsi < 50

        print(
            f"📊 {stock} | ₹{price} | RSI:{round(rsi, 1)} | "
            f"Signal:{signal} {'✅ CONFIRMED' if confirmed else '⚠️ WEAK'}"
        )

        # ATR based SL/Target
        df["ATR"] = calculate_atr(df)
        atr = float(df.iloc[-1]["ATR"])

        if signal == "BUY":
            sl = round(price - atr, 2)
            target = round(price + (2 * atr), 2)
        else:
            sl = round(price + atr, 2)
            target = round(price - (2 * atr), 2)

        return {
            "stock": stock,
            "signal": signal,
            "confirmed": confirmed,  # ✅ FIX
            "price": price,
            "sl": sl,  # ✅ FIX
            "target": target,  # ✅ FIX
        }

    except Exception as e:
        print(f"❌ {stock} error: {e}")
        return None


# ================= MAIN LOOP =================

print("🤖 HEDGE FUND BOT STARTED")

from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import time
import os

# ================= CONFIG =================
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

IST = ZoneInfo("Asia/Kolkata")

# ==========================================


def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
        print("✅ Telegram sent")
    except Exception as e:
        print(f"❌ Telegram error: {e}")


# ================= MARKET =================


def market_open():
    now = datetime.now(IST)
    return now.weekday() < 5 and dtime(9, 15) <= now.time() <= dtime(15, 30)


def avoid_bad_times():
    now = datetime.now(IST).time()
    return not (
        dtime(9, 15) <= now <= dtime(9, 25) or dtime(15, 0) <= now <= dtime(15, 30)
    )


# ================= NSE SCREENER =================


def get_nse_top_stocks():
    try:
        session = requests.Session()

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en-US,en;q=0.9",
        }

        # Step 1: Load homepage (sets cookies)
        session.get("https://www.nseindia.com", headers=headers, timeout=5)

        # Step 2: API call
        url = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY 50"
        res = session.get(url, headers=headers, timeout=5)

        if res.status_code != 200 or not res.text:
            raise Exception("Empty NSE response")

        data = res.json()["data"]

        data = sorted(data, key=lambda x: abs(x["pChange"]), reverse=True)

        stocks = [x["symbol"] + ".NS" for x in data[:12]]

        print("🔥 NSE STOCKS:", stocks)

        return stocks

    except Exception as e:
        print("⚠️ NSE FAILED, using fallback:", e)

        # ✅ Smart fallback list (BEST intraday stocks)
        return [
            "ADANIENT.NS",
            "ADANIPOWER.NS",
            "RELIANCE.NS",
            "ETERNAL.NS",
            "HINDCOPPER.NS",
            "VEDL.NS",
            "COALINDIA.NS",
            "TCS.NS",
        ]


# ================= SCORING ENGINE =================


def score_stock(stock):
    try:
        df = yf.download(stock, period="1d", interval="5m", progress=False)

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        if len(df) < 30:
            return None

        df = df.dropna()

        latest = df.iloc[-1]

        price = latest["Close"]

        move = abs(df["Close"].pct_change()).sum()

        avg_vol = df["Volume"].rolling(20).mean().iloc[-1]
        vol_spike = latest["Volume"] / avg_vol if avg_vol > 0 else 0

        recent_high = df["High"].rolling(20).max().iloc[-2]
        breakout = 1 if price > recent_high else 0

        ema20 = df["Close"].ewm(span=20).mean().iloc[-1]
        trend_strength = abs(price - ema20)

        score = (move * 1000) + (vol_spike * 50) + (breakout * 200) + trend_strength

        return score

    except:
        return None


# ================= FINAL STOCK SELECTOR =================


def get_hedge_stocks():
    base_stocks = get_nse_top_stocks()

    ranked = []

    for s in base_stocks:
        sc = score_stock(s)
        if sc:
            ranked.append((s, sc))

    ranked = sorted(ranked, key=lambda x: x[1], reverse=True)

    top = [x[0] for x in ranked[:8]]

    print("🔥 HEDGE STOCKS:", ", ".join(top))

    return top


# ================= INDICATORS =================


def calculate_rsi(df, period=14):
    delta = df["Close"].diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


# ================= ANALYSIS =================


def calculate_atr(df, period=14):
    hl = df["High"] - df["Low"]
    hc = abs(df["High"] - df["Close"].shift())
    lc = abs(df["Low"] - df["Close"].shift())
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def analyze_stock(stock):
    try:
        df = yf.download(stock, period="1d", interval="5m", progress=False)

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.dropna()

        if len(df) < 20:
            return None

        df["EMA9"] = df["Close"].ewm(span=9).mean()
        df["EMA21"] = df["Close"].ewm(span=21).mean()
        df["RSI"] = calculate_rsi(df)

        latest = df.iloc[-1]

        price = round(float(latest["Close"]), 2)
        ema9 = float(latest["EMA9"])
        ema21 = float(latest["EMA21"])
        rsi = float(latest["RSI"])

        if ema9 > ema21:
            signal = "BUY"
        else:
            signal = "SELL"

        confirmed = rsi > 50 if signal == "BUY" else rsi < 50

        print(
            f"📊 {stock} | ₹{price} | RSI:{round(rsi, 1)} | "
            f"Signal:{signal} {'✅ CONFIRMED' if confirmed else '⚠️ WEAK'}"
        )

        # ATR based SL/Target
        df["ATR"] = calculate_atr(df)
        atr = float(df.iloc[-1]["ATR"])

        if signal == "BUY":
            sl = round(price - atr, 2)
            target = round(price + (2 * atr), 2)
        else:
            sl = round(price + atr, 2)
            target = round(price - (2 * atr), 2)

        return {
            "stock": stock,
            "signal": signal,
            "confirmed": confirmed,  # ✅ FIX
            "price": price,
            "sl": sl,  # ✅ FIX
            "target": target,  # ✅ FIX
        }

    except Exception as e:
        print(f"❌ {stock} error: {e}")
        return None


# ================= MAIN LOOP =================

print("🤖 HEDGE FUND BOT STARTED")

def run_bot():
    now = datetime.now(IST)

    print("⏱ Checking market conditions...")

    if not market_open():
        print(f"🚫 Market CLOSED — {now.strftime('%H:%M:%S IST')}")
        return

    if not avoid_bad_times():
        print(f"⚠️ Avoiding volatile time — {now.strftime('%H:%M:%S IST')}")
        return

    print("=" * 60)
    print(f"🤖 RUNNING | {now.strftime('%H:%M')}")
    print("=" * 60)

    stocks = get_hedge_stocks()
    results = []

    for s in stocks:
        res = analyze_stock(s)
        if res:
            results.append(res)

    if results:
        msg = ["📊 SIGNAL UPDATE\n"]

        for r in results:
            emoji = "🟢" if r["signal"] == "BUY" else "🔴"
            status = (
                "✅ CONFIRMED — Trade it!" if r["confirmed"] else "⚠️ WEAK — Skip it"
            )

            msg.append(
                f"{emoji} {r['stock'].replace('.NS', '')}\n"
                f"Signal : {r['signal']}\n"
                f"Status : {status}\n"
                f"Price  : ₹{r['price']}\n"
                f"SL     : ₹{r['sl']}\n"
                f"Target : ₹{r['target']}"
            )

        send_telegram("\n\n".join(msg))


if __name__ == "__main__":
    print("🤖 BOT TRIGGERED")
    try:
        run_bot()
    except Exception as e:
        print("ERROR:", e)
    time.sleep(300)
