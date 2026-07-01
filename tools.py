"""
tools.py
ابزارهای کمکی: ترجمه، قیمت ارز دیجیتال (نمونه‌ی API رایگان واقعی)، و تبدیل ویدیو به گیف.
"""

import subprocess
import requests
from deep_translator import GoogleTranslator


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
                    
