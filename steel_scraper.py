#!/usr/bin/env python3
"""
Iran Steel Price Monitor - Scrapes 11 Telegram channels for iron/steel prices.
Calculates averages and publishes to a Telegram channel.

Usage:
  python3 steel_scraper.py                  # Print report to stdout
  python3 steel_scraper.py --post           # Print + post to Telegram channel
  python3 steel_scraper.py --json           # Output raw JSON data
"""

import requests
import re
import sys
import json
import urllib.request
import os
from bs4 import BeautifulSoup
from collections import defaultdict
from datetime import datetime, timedelta, timezone

# ── Configuration ──────────────────────────────────────────────
CHANNELS = [
    'saebsteelco',
    'zafarSteelbonab',
    'FSDTABRIZ',
    'sfk_steels',
    'dorpadtabriz_co',
    'afasteel',
    'fuladarvintejarat',
    'oxintrading',
    'damirbazar',
    'pardissteel1',
    'ArianSteel',
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# Persian/Arabic numeral mapping
FA_NUMS = {
    '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
    '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9',
}


# ── Helpers ────────────────────────────────────────────────────
def fa_to_en(s: str) -> str:
    """Convert Persian/Arabic numerals to English."""
    for k, v in FA_NUMS.items():
        s = s.replace(k, v)
    return s


def normalize_product(name: str) -> str:
    """Normalize product names across channels."""
    name = name.strip()
    name = re.sub(r'^milgird', 'میلگرد', name)
    name = re.sub(r'^ميلگرد', 'میلگرد', name)
    name = re.sub(r'میلگرد\s+آجدار\s+A(\d)', r'میلگرد A\1', name)
    name = re.sub(r'میلگرد\s+A(\d)\s+سایز\s+(\d+)', r'میلگرد A\1 \2', name)
    return name


def parse_price(raw: str, text_around: str = '') -> int | None:
    """Parse a price string, return value in toman or None."""
    raw = raw.replace(',', '').replace(' ', '')
    
    # Handle dot as thousands separator (e.g., "72.300")
    if '.' in raw:
        parts = raw.split('.')
        if len(parts) == 2 and len(parts[1]) == 3:
            raw = parts[0] + parts[1]
    
    raw = re.sub(r'[^\d]', '', raw)
    if not raw:
        return None
    
    try:
        val = int(raw)
    except ValueError:
        return None
    
    # Convert rial to toman if price is too high
    if val > 2_000_000:
        val = val // 10
    
    # Reasonable range: 5,000 - 200,000 toman/kg
    if 5_000 < val < 200_000:
        return val
    return None


# ── Scraping ───────────────────────────────────────────────────
def scrape_channel(username: str) -> list[dict]:
    """Scrape a single Telegram channel's public page."""
    url = f'https://t.me/s/{username}'
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, 'html.parser')
        messages = soup.find_all('div', class_='tgme_widget_message_wrap')
        results = []

        for msg in messages:
            td = msg.find('div', class_='tgme_widget_message_text')
            if not td:
                continue
            text = fa_to_en(td.get_text(separator='|', strip=True))

            # Skip if no price-like numbers
            if not re.search(r'\b\d{5,7}\b', text) and not re.search(r'\b\d{2}\.\d{3}\b', text):
                continue

            # Pattern 1: "product ... : price" or "product | ... ← price"
            for m in re.finditer(
                r'(میلگرد|ميلگرد|تیرآهن|ti*rahan|ورق|sheet)'
                r'\s*(?:آجدار\s*)?(?:A[234]|B500B)?'
                r'\s*(?:سایز|سايز|SA)?\s*(\d+)?'
                r'\s*(?:الی|تا)?\s*(\d+)?'
                r'\s*(?:←|:|\|)\s*([\d,\.]+)',
                text, re.IGNORECASE
            ):
                prod = m.group(1)
                size = m.group(3) or m.group(2) or ''
                price = parse_price(m.group(4), text)
                if price:
                    results.append({
                        'product': f'{prod} {size}'.strip(),
                        'price': price,
                        'channel': username,
                    })

            # Pattern 2: sfk_steels format "گرید A2 سایز 8 : 72.300"
            for m in re.finditer(
                r'گرید\s*(A[234])\s*(?:سایز|سايز)\s*(\d+)'
                r'\s*(?:_?\s*(\d+))?\s*[:\|]\s*(\d{1,2}\.\d{3})',
                text
            ):
                grade = m.group(1)
                size = m.group(3) or m.group(2)
                price = parse_price(m.group(4))
                if price:
                    results.append({
                        'product': f'milgird {grade} {size}',
                        'price': price,
                        'channel': username,
                    })

        return results
    except Exception as e:
        print(f'Error @{username}: {e}', file=sys.stderr)
        return []


def scrape_all() -> tuple[list[dict], dict]:
    """Scrape all configured channels."""
    all_prices = []
    channel_stats = {}
    for ch in CHANNELS:
        prices = scrape_channel(ch)
        all_prices.extend(prices)
        channel_stats[ch] = len(prices)
        print(f'  @{ch}: {len(prices)} prices', file=sys.stderr)
    return all_prices, channel_stats


# ── Analysis ───────────────────────────────────────────────────
def calculate_averages(prices: list[dict]) -> list[dict]:
    """Group by product, remove outliers, calculate avg/min/max."""
    grouped = defaultdict(list)
    for p in prices:
        grouped[normalize_product(p['product'])].append(p)

    averages = []
    for prod, items in sorted(grouped.items()):
        vals = sorted([i['price'] for i in items])
        median = vals[len(vals) // 2]
        filtered = [v for v in vals if abs(v - median) / median < 0.2]
        if not filtered:
            filtered = vals

        avg = round(sum(filtered) / len(filtered))
        sources = len(set(i['channel'] for i in items))
        averages.append({
            'product': prod,
            'avg': avg,
            'min': min(filtered),
            'max': max(filtered),
            'sources': sources,
        })
    return averages


# ── Report Formatting ──────────────────────────────────────────
def format_report(averages: list[dict], channel_stats: dict) -> str:
    """Format the report as HTML for Telegram."""
    iran_tz = timezone(timedelta(hours=3, minutes=30))
    now = datetime.now(iran_tz)

    day_names = ['دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنجشنبه', 'جمعه', 'شنبه', 'یکشنبه']
    day_name = day_names[now.weekday()]
    jdate = now.strftime('%Y/%m/%d')

    lines = [
        '☀️ <b>سلام و روز بخیر</b>',
        f'📅 {day_name}، {jdate}',
        '',
        '📊 <b>قیمت روزانه آهن‌آلات</b>',
        f'🕐 {now.strftime("%H:%M")}',
        '━━━━━━━━━━━━━━━━━━━━',
        '',
    ]

    for r in averages:
        mn = f"{r['min']:,}".replace(',', '.')
        mx = f"{r['max']:,}".replace(',', '.')
        avg = f"{r['avg']:,}".replace(',', '.')
        lines.append(f'▪️ <b>{r["product"]}</b>: {avg} تومان/kg')
        if r['min'] != r['max']:
            lines.append(f'   📉 {mn} — 📈 {mx} ({r["sources"]} منبع)')
        else:
            lines.append(f'   ({r["sources"]} منبع)')
        lines.append('')

    lines.append('━━━━━━━━━━━━━━━━━━━━')
    total_sources = sum(r['sources'] for r in averages)
    lines.append(f'📌 {len(averages)} محصول | {total_sources} منبع کل')

    active = [f'@{k}' for k, v in channel_stats.items() if v > 0]
    if active:
        lines.append(f'📡 کانال‌های فعال: {", ".join(active)}')
    lines.append('')
    lines.append('🤖 گزارش خودکار')

    return '\n'.join(lines)


# ── Telegram Posting ───────────────────────────────────────────
def post_to_telegram(text: str) -> bool:
    """Post the report to the configured Telegram channel."""
    env_path = os.environ.get('HERMES_HOME', os.path.expanduser('~/.hermes'))
    env_file = os.path.join(env_path, '.env')

    bot_token = None
    chat_id = None

    # Read from .env
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line.startswith('TELEGRAM_BOT_TOKEN='):
                    bot_token = line.split('=', 1)[1]
                if line.startswith('TELEGRAM_CHANNEL_ID='):
                    chat_id = line.split('=', 1)[1]

    # Fallback: env vars
    if not bot_token:
        bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not chat_id:
        chat_id = os.environ.get('TELEGRAM_CHANNEL_ID', '-1004431236647')

    if not bot_token:
        print('❌ No TELEGRAM_BOT_TOKEN found', file=sys.stderr)
        return False

    data = json.dumps({
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True,
    }).encode()

    req = urllib.request.Request(
        f'https://api.telegram.org/bot{bot_token}/sendMessage',
        data=data,
        headers={'Content-Type': 'application/json'},
    )

    try:
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read())
        msg_id = result.get('result', {}).get('id', '?')
        print(f'✅ Posted: message_id={msg_id}', file=sys.stderr)
        return True
    except Exception as e:
        print(f'❌ Post failed: {e}', file=sys.stderr)
        return False


# ── Main ───────────────────────────────────────────────────────
def main():
    post = '--post' in sys.argv
    json_out = '--json' in sys.argv

    print('📡 Scraping channels...', file=sys.stderr)
    all_prices, channel_stats = scrape_all()
    print(f'\n📊 Total: {len(all_prices)} prices', file=sys.stderr)

    averages = calculate_averages(all_prices)

    if json_out:
        print(json.dumps({
            'averages': averages,
            'channel_stats': channel_stats,
            'total_prices': len(all_prices),
        }, ensure_ascii=False, indent=2))
        return

    report = format_report(averages, channel_stats)
    print(report)

    if post:
        post_to_telegram(report)


if __name__ == '__main__':
    main()
