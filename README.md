# 🇮🇷 Iran Steel Price Monitor

Automatic daily scraping of iron & steel prices from 11 Iranian Telegram channels, with smart averaging and Telegram channel publishing.

## 🔌 Channels Monitored

| Channel | Description |
|---------|-------------|
| [@saebsteelco](https://t.me/saebsteelco) | فولاد صائب تبریز |
| [@zafarSteelbonab](https://t.me/zafarSteelbonab) | مجتمع فولاد ظفر بناب |
| [@FSDTABRIZ](https://t.me/FSDTABRIZ) | فولاد سازان دقيقی هشترود |
| [@sfk_steels](https://t.me/sfk_steels) | SFK Steels |
| [@dorpadtabriz_co](https://t.me/dorpadtabriz_co) | گروه صنعتی درپاد |
| [@afasteel](https://t.me/afasteel) | آذر فولاد امین |
| [@fuladarvintejarat](https://t.me/fuladarvintejarat) | فولاد آروین تجارت |
| [@oxintrading](https://t.me/oxintrading) | اوکسین تریدینگ |
| [@damirbazar](https://t.me/damirbazar) | دمیر بازار |
| [@pardissteel1](https://t.me/pardissteel1) | پردیس استیل |
| [@ArianSteel](https://t.me/ArianSteel) | آرین استیل |

## 🚀 Usage

```bash
# Install dependencies
pip install requests beautifulsoup4

# Print report to stdout
python3 steel_scraper.py

# Print report + post to Telegram channel
python3 steel_scraper.py --post

# Output raw JSON data
python3 steel_scraper.py --json
```

## ⚙️ Configuration

Set these in `~/.hermes/.env` or as environment variables:

```
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHANNEL_ID=-100xxxxxxxxxx
```

## 📊 Sample Output

```
📊 قیمت روزانه آهن‌آلات
🗓 2026/08/07 | 🕐 10:00
━━━━━━━━━━━━━━━━━━━━

▪️ میلگرد A2 8: 76.500 تومان/kg
   📉 75.300 — 📈 77.800 (4 منبع)

▪️ میلگرد A3 12: 76.200 تومان/kg
   📉 75.000 — 📈 77.300 (5 منبع)

▪️ میلگرد A3 14: 75.800 تومان/kg
   📉 74.700 — 📈 76.500 (4 منبع)

━━━━━━━━━━━━━━━━━━━━
📌 19 محصول | 22 منبع کل
```

## 🏗 Architecture

1. **Scraping**: Fetches public Telegram channel pages (`t.me/s/USERNAME`)
2. **Extraction**: Regex-based price extraction with Persian/Arabic numeral support
3. **Normalization**: Product names unified across channels
4. **Outlier Removal**: Prices >20% from median are excluded
5. **Averaging**: Weighted average calculated per product
6. **Publishing**: Formatted HTML report posted via Telegram Bot API

## 📜 License

MIT
