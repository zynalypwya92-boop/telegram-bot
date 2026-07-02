"""
tools.py
ابزارهای کمکی: ترجمه، قیمت ارز دیجیتال (نمونه‌ی API رایگان واقعی)، و تبدیل ویدیو به گیف.
"""

import subprocess
import requests
from deep_translator import GoogleTranslator

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def generate_crypto_chart(coin_id: str, path: str, days: int = 7) -> bool:
    """
    نمودار ۷ روزه‌ی قیمت رمزارز رو می‌سازه و به‌صورت عکس ذخیره می‌کنه (فقط برای کریپتو، چون تاریخچه‌ی رایگان داره).
    """
    try:
        resp = requests.get(
            f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart",
            params={"vs_currency": "usd", "days": days},
            timeout=15,
        )
        prices = resp.json()["prices"]
        xs = [p[0] for p in prices]
        ys = [p[1] for p in prices]
        color = "#16c784" if ys[-1] >= ys[0] else "#ea3943"

        plt.figure(figsize=(6, 3.2))
        plt.plot(xs, ys, color=color, linewidth=2.2)
        plt.fill_between(xs, ys, min(ys), color=color, alpha=0.15)
        plt.axis("off")
        plt.tight_layout(pad=0.3)
        plt.savefig(path, dpi=150, facecolor="#111111")
        plt.close()
        return True
    except Exception:
        return False


def translate_text(text: str, target_lang: str = "fa") -> str:
    """
    ترجمه متن با deep-translator (رایگان، بدون نیاز به کلید API).
    اگه متن فارسیه و target 'fa' باشه، خودکار به انگلیسی ترجمه می‌کنه.
    """
    try:
        # تشخیص ساده: اگه حروف فارسی توی متن هست، مقصد رو انگلیسی کن
        has_persian = any("\u0600" <= ch <= "\u06FF" for ch in text)
        target = "en" if has_persian and target_lang == "fa" else target_lang
        result = GoogleTranslator(source="auto", target=target).translate(text)
        return result
    except Exception as e:
        return f"خطا در ترجمه: {e}"


def get_persian_market_price(keyword_fa: str, api_key: str) -> str:
    """
    قیمت دلار/یورو/طلا/سکه/بیت‌کوین به تومان از BrsApi.ir (رایگان، نیاز به کلید رایگان از سایت).
    کلید رایگان: از brsapi.ir ثبت‌نام کن (بدون پرداخت) و کلید بده.
    """
    if not api_key or api_key == "PUT_YOUR_BRSAPI_KEY_HERE":
        return "برای این قابلیت باید کلید رایگان BrsApi رو تنظیم کنی (متغیر BRS_API_KEY)."

    url = "https://BrsApi.ir/Api/Market/Gold_Currency.php"
    params = {"key": api_key}
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
    except Exception as e:
        return f"خطا در دریافت قیمت: {e}"

    # داده‌ها معمولا زیر بخش‌های gold / currency / cryptocurrency هستن
    for section in data.values():
        if isinstance(section, list):
            for item in section:
                name = str(item.get("name", ""))
                if keyword_fa in name:
                    price = item.get("price", "نامشخص")
                    unit = item.get("unit", "تومان")
                    return f"{name}: {price} {unit}"

    return f"قیمت «{keyword_fa}» پیدا نشد."


def get_crypto_price(coin_id: str = "bitcoin", vs_currency: str = "usd") -> str:

    """
    قیمت لحظه‌ای ارز دیجیتال از CoinGecko (API رایگان و بدون نیاز به کلید).
    مثال coin_id: bitcoin, ethereum, dogecoin, tether
    """
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": coin_id, "vs_currencies": vs_currency}
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if coin_id not in data:
            return f"ارز '{coin_id}' پیدا نشد. اسم انگلیسی دقیق‌تر امتحان کن (مثلا bitcoin)."
        price = data[coin_id][vs_currency]
        return f"قیمت {coin_id}: {price} {vs_currency.upper()}"
    except Exception as e:
        return f"خطا در دریافت قیمت: {e}"


def get_usd_to_toman_rate(api_key: str):
    """نرخ دلار به تومان رو از همون BrsApi می‌گیره (برای تبدیل قیمت‌های دلاری)."""
    if not api_key or api_key == "PUT_YOUR_BRSAPI_KEY_HERE":
        return None
    url = "https://BrsApi.ir/Api/Market/Gold_Currency.php"
    try:
        resp = requests.get(url, params={"key": api_key}, timeout=10)
        data = resp.json()
        for section in data.values():
            if isinstance(section, list):
                for item in section:
                    if "دلار" in str(item.get("name", "")):
                        return float(item.get("price"))
    except Exception:
        pass
    return None


def search_coin_id(query: str):
    """جستجوی هر رمزارزی (فارسی یا انگلیسی) توی CoinGecko."""
    url = "https://api.coingecko.com/api/v3/search"
    try:
        resp = requests.get(url, params={"query": query}, timeout=10)
        coins = resp.json().get("coins", [])
        if coins:
            c = coins[0]
            return c["id"], c["name"], c["symbol"]
    except Exception:
        pass
    return None, None, None


def get_crypto_price_full(query: str, usd_to_toman: float = None) -> str:
    """قیمت هر رمزارزی با اسم فارسی یا انگلیسی، دو خط و با ایموجی."""
    coin_id, name, symbol = search_coin_id(query)
    if not coin_id:
        return f"❓ رمزارز «{query}» پیدا نشد."
    try:
        resp = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": coin_id, "vs_currencies": "usd", "include_24hr_change": "true"},
            timeout=10,
        )
        d = resp.json()[coin_id]
        usd = d["usd"]
        change = d.get("usd_24h_change", 0) or 0
        arrow = "🟢" if change >= 0 else "🔴"
        line1 = f"💰 {name} ({symbol.upper()}): ${usd:,.4g} {arrow} {change:.1f}%"
        if usd_to_toman:
            toman = int(usd * usd_to_toman)
            line1 += f"\n💵 معادل: {toman:,} تومان"
        return line1
    except Exception as e:
        return f"خطا در دریافت قیمت: {e}"


# قیمت‌های تقریبی رسمی تلگرام (دلاری، پلن داخل اپ) - این قیمت‌ها ممکنه تغییر کنن
TELEGRAM_PREMIUM_USD = {
    "۱ ماهه": 4.99,
    "۶ ماهه": 24.99,
    "۱۲ ماهه": 35.99,
}
TELEGRAM_STAR_USD = 0.02  # قیمت تقریبی هر استار داخل اپ


def get_telegram_premium_price(usd_to_toman: float = None) -> str:
    lines = ["⭐️ پرمیوم تلگرام (تقریبی):"]
    parts = []
    for plan, usd in TELEGRAM_PREMIUM_USD.items():
        p = f"{plan}: ${usd}"
        if usd_to_toman:
            p += f" (~{int(usd * usd_to_toman):,} ت)"
        parts.append(p)
    lines.append(" | ".join(parts))
    return "\n".join(lines)


def get_telegram_stars_price(count: int = 100, usd_to_toman: float = None) -> str:
    usd = count * TELEGRAM_STAR_USD
    text = f"⭐️ {count} استار ≈ ${usd:.2f}"
    if usd_to_toman:
        text += f"\n💵 معادل: {int(usd * usd_to_toman):,} تومان"
    return text


def ai_generate_text(prompt: str, api_key: str, system: str = None, model: str = "llama-3.3-70b-versatile") -> str:
    """
    تماس با Groq (رایگان و سریع، بدون محدودیت منطقه‌ای). کلید رو از console.groq.com بگیر.
    """
    if not api_key or api_key == "PUT_YOUR_GROQ_KEY_HERE":
        return "برای این قابلیت باید کلید رایگان Groq رو تنظیم کنی (GROQ_API_KEY)."

    url = "https://api.groq.com/openai/v1/chat/completions"
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        resp = requests.post(
            url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages},
            timeout=30,
        )
        data = resp.json()
        if "choices" not in data:
            return f"خطا از سمت هوش مصنوعی: {data.get('error', {}).get('message', 'نامشخص')}"
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"خطا در ارتباط با هوش مصنوعی: {e}"


def convert_video_to_gif(input_path: str, output_path: str, fps: int = 10, width: int = 480) -> bool:
    """
    تبدیل ویدیو به گیف با ffmpeg (باید ffmpeg روی سرور نصب باشه - رایگان و متن‌باز).
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", f"fps={fps},scale={width}:-1:flags=lanczos",
        "-loop", "0",
        output_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=120)
        return result.returncode == 0
    except Exception:
        return False
