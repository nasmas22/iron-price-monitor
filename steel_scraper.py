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
    'oxintrading',
    'damirbazar',
    'pardissteel1',
    'ArianSteel',
    'Fuladnab',
    'javidsteel_bonab',
    'steelradhamedan',
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
    # Convert Persian numerals to English in the name
    name = fa_to_en(name)
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
    # 6+ digit prices are likely rial (e.g., 760000 rial = 76000 toman)
    if val > 100_000:
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
            # Clean non-breaking spaces and extra whitespace
            text = text.replace('\xa0', ' ')
            text = re.sub(r'\s+', ' ', text)

            # Skip if no price-like numbers
            # Check for: 5-7 digit numbers, or numbers with commas (750,000)
            if (not re.search(r'\b\d{5,7}\b', text) and 
                not re.search(r'\b\d{2}\.\d{3}\b', text) and
                not re.search(r'\b\d{3},\d{3}\b', text)):
                continue

            # Pattern 1: "product ... : price" or "product | ... ← price"
            # Handles formats like:
            #   میلگرد آجدار A2 سایز 8:|760000
            #   میلگرد آجدار A2 سایز 10: 755000
            #   میلگرد | سایز 8 | گرید (A2) ← 750,000
            for m in re.finditer(
                r'(میلگرد|ميلگرد|تیرآهن|ti*rahan|ورق|sheet)'
                r'\s*(?:آجدار\s*)?(A[234]|B500B|A500C)?'  # Capture grade
                r'\s*(?:سایز|سايز|SA)?\s*(\d+)?'
                r'(?:\s*(?:الی|تا)\s*(\d+))?'  # Optional range
                r'\s*(?:←|:|\|)\s*\|?\s*([\d,\.]+)',
                text, re.IGNORECASE
            ):
                prod = m.group(1)
                grade = m.group(2) or ''
                size = m.group(4) or m.group(3) or ''
                price = parse_price(m.group(5), text)
                if price:
                    # Build product name with grade
                    product_name = f'{prod}'
                    if grade:
                        product_name += f' {grade}'
                    if size:
                        product_name += f' {size}'
                    results.append({
                        'product': product_name.strip(),
                        'price': price,
                        'channel': username,
                    })

            # Pattern 1b: zafarSteelbonab format "سایز 8 | گرید (A2) ← 750,000"
            for m in re.finditer(
                r'سایز\s*(\d+)\s*\|\s*گرید\s*\((A[234]|B500B|A500C)\)\s*←\s*([\d,\.]+)',
                text
            ):
                size = m.group(1)
                grade = m.group(2)
                price = parse_price(m.group(3), text)
                if price:
                    results.append({
                        'product': f'milgird {grade} {size}',
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
def extract_grade_size(product: str) -> tuple[str, str]:
    """Extract grade and size from normalized product name."""
    product = product.strip()
    grade = ''
    size = ''

    # Try to match grade
    grade_match = re.search(r'(A[234]|B500B|A500C)', product)
    if grade_match:
        grade = grade_match.group(1)

    # Try to match size number
    size_match = re.search(r'(\d+)$', product)
    if size_match:
        size = size_match.group(1)

    return grade, size


def map_to_template(averages: list[dict]) -> list[dict]:
    """Map scraped prices to the fixed template structure."""
    # Fixed template order
    template = [
        {'product': 'میلگرد', 'size': '8', 'grade': 'A2'},
        {'product': 'میلگرد', 'size': '8', 'grade': 'A3'},
        {'product': 'میلگرد', 'size': '10', 'grade': 'A2'},
        {'product': 'میلگرد', 'size': '10', 'grade': 'A3'},
        {'product': 'میلگرد', 'size': '12', 'grade': 'A2'},
        {'product': 'میلگرد', 'size': '12', 'grade': 'A3'},
        {'product': 'میلگرد', 'size': '14-25', 'grade': 'A3'},
        {'product': 'میلگرد', 'size': '28-32', 'grade': 'A3'},
        {'product': 'میلگرد', 'size': '14-25', 'grade': 'A4'},
        {'product': 'میلگرد', 'size': '10', 'grade': 'B500B'},
        {'product': 'میلگرد', 'size': '10', 'grade': 'A500C'},
        {'product': 'میلگرد', 'size': '12', 'grade': 'B500B'},
        {'product': 'میلگرد', 'size': '12', 'grade': 'A500C'},
        {'product': 'میلگرد', 'size': '14-25', 'grade': 'B500B'},
        {'product': 'میلگرد', 'size': '14-25', 'grade': 'A500C'},
    ]

    # Build lookup from scraped data
    prices_map = {}
    for item in averages:
        grade, size = extract_grade_size(item['product'])
        if grade and size:
            prices_map[(grade, size)] = item['avg']

    # Fill template
    result = []
    for t in template:
        key = (t['grade'], t['size'])
        price = prices_map.get(key)

        # For grouped sizes (14-25, 28-32), try to aggregate
        if price is None and '-' in t['size']:
            lo, hi = t['size'].split('-')
            group_prices = []
            for s in range(int(lo), int(hi) + 1):
                p = prices_map.get((t['grade'], str(s)))
                if p:
                    group_prices.append(p)
            if group_prices:
                price = round(sum(group_prices) / len(group_prices))

        result.append({
            'product': t['product'],
            'size': t['size'],
            'grade': t['grade'],
            'price': price,
        })

    return result


def load_previous_prices() -> dict:
    """Load previous day's prices from cache file."""
    cache_path = os.path.join(os.path.dirname(__file__), '.price_cache.json')
    try:
        with open(cache_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_prices(data: list[dict]):
    """Save current prices to cache file for next comparison."""
    cache_path = os.path.join(os.path.dirname(__file__), '.price_cache.json')
    cache = {}
    for item in data:
        if item['price'] is not None:
            key = f"{item['grade']}_{item['size']}"
            cache[key] = item['price']
    with open(cache_path, 'w') as f:
        json.dump(cache, f, ensure_ascii=False)


def format_price_block(item: dict, prev_prices: dict) -> str:
    """Format a single price block with bullet points."""
    lines = [f"🔸 <b>{item['product']}</b>"]
    lines.append(f"   • سایز: {item['size']}")
    lines.append(f"   • گرید: {item['grade']}")

    if item['price'] is not None:
        price_str = f"{item['price']:,}".replace(',', '.')
        cache_key = f"{item['grade']}_{item['size']}"
        prev = prev_prices.get(cache_key)

        # Price change indicator
        indicator = ''
        if prev and prev != item['price']:
            if item['price'] > prev:
                indicator = ' 🟢↑'
            elif item['price'] < prev:
                indicator = ' 🔴↓'

        lines.append(f"   • قیمت (تومان): {price_str}{indicator}")
    else:
        lines.append(f"   • قیمت (تومان): —")

    return '\n'.join(lines)


def format_report(averages: list[dict], channel_stats: dict) -> str:
    """Format the report as HTML for Telegram."""
    iran_tz = timezone(timedelta(hours=3, minutes=30))
    now = datetime.now(iran_tz)

    day_names = ['دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنجشنبه', 'جمعه', 'شنبه', 'یکشنبه']
    day_name = day_names[now.weekday()]
    jdate = now.strftime('%Y/%m/%d')

    # Map prices to template
    template_data = map_to_template(averages)
    prev_prices = load_previous_prices()

    lines = [
        '☀️ <b>سلام و روز بخیر</b>',
        f'📅 {day_name}، {jdate}',
        '',
        '📊 <b>قیمت روزانه میلگرد</b>',
        f'🕐 {now.strftime("%H:%M")}',
        '━━━━━━━━━━━━━━━━━━━━',
        '',
    ]

    for item in template_data:
        lines.append(format_price_block(item, prev_prices))
        lines.append('')

    lines.append('━━━━━━━━━━━━━━━━━━━━')
    total_sources = sum(r['sources'] for r in averages)
    lines.append(f'📌 {len(averages)} محصول | {total_sources} منبع کل')
    lines.append('')
    lines.append('⚠️ رنگ‌ها: 🟢 قیمت ↑ | 🔴 قیمت ↓')
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

    # Save prices for next comparison
    template_data = map_to_template(averages)
    save_prices(template_data)

    if post:
        post_to_telegram(report)


if __name__ == '__main__':
    main()
