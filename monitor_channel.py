#!/usr/bin/env python3
"""
Channel Price Monitor — checks for new price posts, generates image, posts to target.
Usage: python3 monitor_channel.py <channel_name>
"""
import sys, os, re, json, time, subprocess
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone

# ── Config ────────────────────────────────────────────────────
REPO_DIR = '/data/workspace/iron-price-monitor'
CACHE_FILE = os.path.join(REPO_DIR, '.price_monitor_cache.json')
OUTPUT_IMG = '/data/workspace/price_monitor_output.png'
TARGET_CHAT = '-1004431236647'
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
FA = {'۰':'0','۱':'1','۲':'2','۳':'3','۴':'4','۵':'5','۶':'6','۷':'7','۸':'8','۹':'9'}

def fa_to_en(s):
    for k,v in FA.items(): s = s.replace(k,v)
    return s

def load_cache():
    try:
        with open(CACHE_FILE) as f: return json.load(f)
    except: return {}

def save_cache(data):
    with open(CACHE_FILE, 'w') as f: json.dump(data, f, ensure_ascii=False, indent=2)

def get_bot_token():
    env_path = os.path.expanduser('~/.hermes/.env')
    with open(env_path) as f:
        for line in f:
            if line.startswith('TELEGRAM_BOT_TOKEN='):
                return line.split('=',1)[1].strip()
    return None

# ── Scrape latest message ─────────────────────────────────────
def get_latest_message(channel):
    """Get the latest message with price data from a channel."""
    url = f'https://t.me/s/{channel}'
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')
        msgs = soup.find_all('div', class_='tgme_widget_message_wrap')
        
        for msg in reversed(msgs):  # Latest first
            td = msg.find('div', class_='tgme_widget_message_text')
            time_tag = msg.find('time')
            
            # Get message link
            msg_link = ''
            wrap = msg.find('a', class_='tgme_widget_message_date')
            if wrap:
                msg_link = wrap.get('href', '')
            
            if not td:
                # Check for photo-only messages (some channels post prices as images)
                photo = msg.find('a', class_='tgme_widget_message_photo_wrap')
                if photo and msg_link:
                    return {
                        'has_text': False,
                        'has_photo': True,
                        'link': msg_link,
                        'msg_id': msg_link.split('/')[-1] if '/' in msg_link else '',
                        'text': '',
                        'timestamp': time_tag.get('datetime', '') if time_tag else '',
                    }
                continue
            
            text = fa_to_en(td.get_text(separator='|', strip=True))
            text = text.replace('\xa0', ' ')
            text = re.sub(r'\s+', ' ', text)
            
            # Check if has price data
            has_price = (re.search(r'\b\d{5,7}\b', text) or 
                        re.search(r'\b\d{2}\.\d{3}\b', text) or
                        re.search(r'\b\d{3},\d{3}\b', text))
            
            if has_price:
                return {
                    'has_text': True,
                    'has_photo': False,
                    'link': msg_link,
                    'msg_id': msg_link.split('/')[-1] if '/' in msg_link else '',
                    'text': text,
                    'timestamp': time_tag.get('datetime', '') if time_tag else '',
                }
        
        return None
    except Exception as e:
        print(f'Error scraping @{channel}: {e}', file=sys.stderr)
        return None

# ── Extract prices from text ──────────────────────────────────
def extract_prices(text):
    """Extract product/grade/size/price from message text."""
    prices = []
    
    # Pattern 1: میلگرد آجدار A2 سایز 8:|760000
    for m in re.finditer(
        r'(میلگرد|ميلگرد|تیرآهن|ti*rahan|ورق|sheet)'
        r'\s*(?:آجدار\s*)?(A[234]|B500B|A500C)?'
        r'\s*(?:سایز|سايز|SA)?\s*(\d+)?'
        r'(?:\s*(?:الی|تا)\s*(\d+))?'
        r'\s*(?:←|:|\|)\s*\|?\s*([\d,\.]+)',
        text, re.IGNORECASE
    ):
        prod = m.group(1)
        grade = m.group(2) or ''
        size = m.group(4) or m.group(3) or ''
        price = parse_price(m.group(5))
        if price:
            name = f'{prod}'
            if grade: name += f' {grade}'
            if size: name += f' {size}'
            prices.append({'product': name.strip(), 'price': price})
    
    # Pattern 2: zafarSteelbonab format
    for m in re.finditer(
        r'سایز\s*(\d+)\s*\|\s*گرید\s*\((A[234]|B500B|A500C)\)\s*←\s*([\d,\.]+)',
        text
    ):
        size, grade, price_raw = m.group(1), m.group(2), m.group(3)
        price = parse_price(price_raw)
        if price:
            prices.append({'product': f'mیلگرد {grade} {size}', 'price': price})
    
    # Pattern 3: sfk format
    for m in re.finditer(
        r'گرید\s*(A[234])\s*(?:سایز|سايز)\s*(\d+)'
        r'\s*(?:_?\s*(\d+))?\s*[:\|]\s*(\d{1,2}\.\d{3})',
        text
    ):
        grade, size = m.group(1), m.group(3) or m.group(2)
        price = parse_price(m.group(4))
        if price:
            prices.append({'product': f'mیلگرد {grade} {size}', 'price': price})
    
    return prices

def parse_price(raw):
    raw = raw.replace(',', '').replace(' ', '')
    if '.' in raw:
        parts = raw.split('.')
        if len(parts) == 2 and len(parts[1]) == 3:
            raw = parts[0] + parts[1]
    raw = raw.replace('.', '')
    raw = re.sub(r'[^\d]', '', raw)
    if not raw: return None
    try: val = int(raw)
    except: return None
    if val > 100_000: val = val // 10
    if 5_000 < val < 200_000: return val
    return None

# ── Generate image ────────────────────────────────────────────
def generate_image(channel, prices, source_link):
    """Generate price image using the image generator script."""
    import jdatetime
    from PIL import Image, ImageDraw, ImageFont
    import arabic_reshaper
    from bidi.algorithm import get_display
    
    def fa(text):
        return get_display(arabic_reshaper.reshape(text))
    
    FB = os.path.join(REPO_DIR, 'fonts', 'Vazirmatn-Bold.ttf')
    FR = os.path.join(REPO_DIR, 'fonts', 'Vazirmatn.ttf')
    
    # Font sizes
    f_company = ImageFont.truetype(FB, 36)
    f_title = ImageFont.truetype(FB, 40)
    f_date = ImageFont.truetype(FR, 28)
    f_head = ImageFont.truetype(FB, 22)
    f_prod = ImageFont.truetype(FR, 22)
    f_grade = ImageFont.truetype(FB, 24)
    f_size = ImageFont.truetype(FR, 22)
    f_price = ImageFont.truetype(FB, 30)
    f_branch = ImageFont.truetype(FB, 22)
    f_phone = ImageFont.truetype(FR, 20)
    f_foot = ImageFont.truetype(FR, 18)
    f_source = ImageFont.truetype(FR, 16)
    
    # Light theme colors
    BG = '#f5f5f5'
    CARD = '#ffffff'
    CARD2 = '#eef1f5'
    RED = '#c0392b'
    GOLD = '#d4880f'
    GREEN = '#1a8a3f'
    TEXT = '#1a1a1a'
    GRAY = '#555555'
    LINE = '#cccccc'
    BLUE = '#1565c0'
    
    # Date
    tz = timezone(timedelta(hours=3, minutes=30))
    now = datetime.now(tz)
    day_names = ['دوشنبه','سه‌شنبه','چهارشنبه','پنجشنبه','جمعه','شنبه','یکشنبه']
    day_name = day_names[now.weekday()]
    shamsi = jdatetime.datetime.fromgregorian(datetime=now)
    jdate = shamsi.strftime('%Y/%m/%d')
    
    # Contacts
    contacts = [
        ('شعبه تبریز', ['041-34461257', '041-34479961-4', '09144502358', '09120798972']),
        ('شعبه مرکزی (تهران)', ['021-48814676', '021-48814677']),
    ]
    
    # Layout
    W = 800
    PAD = 30
    ROW_H = 55
    n_rows = len(prices)
    
    H = (PAD + 58 + 55 + 40 + 20 + 40 + 8 +
         n_rows * ROW_H +
         20 + 40 + 40 + 10 + 40 + 10 + 30 + 50 + PAD)
    
    img = Image.new('RGB', (W, H), BG)
    draw = ImageDraw.Draw(img)
    y = PAD
    
    # Company
    company = fa('شرکت فولاد آروین تجارت امین ایرانیان')
    cw = draw.textbbox((0,0), company, font=f_company)[2]
    draw.text(((W-cw)//2, y), company, fill=BLUE, font=f_company)
    y += 58
    
    # Title
    title = fa('📊 قیمت روزانه میلگرد')
    tw = draw.textbbox((0,0), title, font=f_title)[2]
    draw.text(((W-tw)//2, y), title, fill=GOLD, font=f_title)
    y += 55
    
    # Date
    dt = fa(f'📅 {day_name}، {jdate}')
    dw = draw.textbbox((0,0), dt, font=f_date)[2]
    draw.text(((W-dw)//2, y), dt, fill=GRAY, font=f_date)
    y += 40
    
    # Top line
    draw.line([(PAD, y), (W-PAD, y)], fill=RED, width=3)
    y += 20
    
    # Columns
    COL_W = (W - 2*PAD) // 4
    c_prod = PAD
    c_grade = PAD + COL_W
    c_size = PAD + COL_W * 2
    c_price = PAD + COL_W * 3
    
    # Headers
    for cx, label in [(c_prod, 'محصول'), (c_grade, 'گرید'), (c_size, 'سایز'), (c_price, 'قیمت (تومان)')]:
        draw.text((cx + 10, y), fa(label), fill=GRAY, font=f_head)
    y += 40
    draw.line([(PAD, y), (W-PAD, y)], fill=LINE, width=1)
    y += 5
    
    # Data rows
    for i, p in enumerate(prices):
        bg = CARD if i % 2 == 0 else CARD2
        draw.rounded_rectangle([(PAD-3, y), (W-PAD+3, y+ROW_H-4)], radius=6, fill=bg)
        ty = y + 12
        
        # Parse product name for grade/size
        name = p['product']
        grade_match = re.search(r'(A[234]|B500B|A500C)', name)
        grade = grade_match.group(1) if grade_match else ''
        size_match = re.search(r'(\d+)(?:\s*(?:الی|تا)\s*(\d+))?', name)
        size = ''
        if size_match:
            size = size_match.group(1)
            if size_match.group(2):
                size += f' الی {size_match.group(2)}'
        
        prod_label = re.sub(r'\s*(A[234]|B500B|A500C)\s*\d+.*', '', name).strip()
        if not prod_label:
            prod_label = 'میلگرد'
        
        price_str = f"{p['price']:,}".replace(',', '.')
        
        draw.text((c_prod + 10, ty), fa(prod_label), fill=TEXT, font=f_prod)
        draw.text((c_grade + 10, ty), fa(grade), fill=GREEN, font=f_grade)
        draw.text((c_size + 10, ty), fa(size), fill=TEXT, font=f_size)
        
        pw = draw.textbbox((0,0), price_str, font=f_price)[2]
        px = c_price + COL_W - pw - 10
        draw.text((px, ty - 1), price_str, fill=GOLD, font=f_price)
        
        y += ROW_H
    
    # Bottom line
    y += 3
    draw.line([(PAD, y), (W-PAD, y)], fill=RED, width=3)
    y += 20
    
    # Contacts
    for branch, phones in contacts:
        bt = fa(branch)
        bw = draw.textbbox((0,0), bt, font=f_branch)[2]
        draw.text(((W-bw)//2, y), bt, fill=BLUE, font=f_branch)
        y += 35
        phone_line = '  |  '.join(phones)
        pw = draw.textbbox((0,0), phone_line, font=f_phone)[2]
        draw.text(((W-pw)//2, y), phone_line, fill=TEXT, font=f_phone)
        y += 35
        if branch != contacts[-1][0]:
            draw.line([(PAD+100, y+5), (W-PAD-100, y+5)], fill=LINE, width=1)
            y += 15
    
    y += 10
    
    # Source link
    source_text = f'🔗 منبع: @{channel}'
    sw = draw.textbbox((0,0), source_text, font=f_source)[2]
    draw.text(((W-sw)//2, y), source_text, fill=BLUE, font=f_source)
    y += 25
    
    # Footer
    ft = fa('🤖 گزارش خودکار | @IronwarePriceTestChannel')
    fw = draw.textbbox((0,0), ft, font=f_foot)[2]
    draw.text(((W-fw)//2, y), ft, fill=GRAY, font=f_foot)
    
    img.save(OUTPUT_IMG, 'PNG')
    return OUTPUT_IMG

# ── Post to Telegram ──────────────────────────────────────────
def post_photo(image_path, caption, source_link):
    """Post photo to Telegram channel."""
    token = get_bot_token()
    if not token:
        print('❌ No bot token', file=sys.stderr)
        return False
    
    # Add source link to caption
    full_caption = f'{caption}\n\n🔗 {source_link}'
    
    result = subprocess.run([
        'curl', '-s', '-F', f'chat_id={TARGET_CHAT}',
        '-F', f'photo=@{image_path}',
        '-F', f'caption={full_caption}',
        f'https://api.telegram.org/bot{token}/sendPhoto'
    ], capture_output=True, text=True)
    
    resp = json.loads(result.stdout)
    if resp.get('ok'):
        print(f'✅ Posted: message_id={resp["result"]["message_id"]}')
        return True
    else:
        print(f'❌ Failed: {resp}', file=sys.stderr)
        return False

# ── Main ──────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print('Usage: python3 monitor_channel.py <channel_name>')
        sys.exit(1)
    
    channel = sys.argv[1]
    cache = load_cache()
    
    # Get latest message
    latest = get_latest_message(channel)
    if not latest:
        print(f'@{channel}: No messages found')
        return
    
    # Check if already processed
    last_id = cache.get(channel, {}).get('last_msg_id', '')
    if latest['msg_id'] == last_id:
        print(f'@{channel}: No new posts (last: {last_id})')
        return
    
    print(f'@{channel}: New post detected! msg_id={latest["msg_id"]}')
    
    if latest['has_text']:
        # Extract prices
        prices = extract_prices(latest['text'])
        if not prices:
            print(f'@{channel}: No prices found in text')
            cache[channel] = {'last_msg_id': latest['msg_id']}
            save_cache(cache)
            return
        
        # Generate image
        img_path = generate_image(channel, prices, latest['link'])
        
        # Post
        caption = f'📊 قیمت روزانه میلگرد | @{channel}'
        post_photo(img_path, caption, latest['link'])
    
    elif latest['has_photo']:
        print(f'@{channel}: Price posted as image (text not available)')
        # TODO: OCR for image-based channels
    
    # Update cache
    cache[channel] = {'last_msg_id': latest['msg_id']}
    save_cache(cache)

if __name__ == '__main__':
    main()
